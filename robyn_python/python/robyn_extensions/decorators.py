"""
Decorators for request validation, authentication, and rate limiting.
"""

import functools
import json
from typing import Type, Optional, Callable, Any
from pydantic import BaseModel, ValidationError

try:
    from robyn_extensions import RateLimitManager, JwtValidator
except ImportError:
    # Fallback if Rust module not built yet
    RateLimitManager = None
    JwtValidator = None


# Global instances
_rate_limiter = RateLimitManager() if RateLimitManager else None
_jwt_validators = {}
_openapi_routes = []


def body(model: Type[BaseModel], description: Optional[str] = None):
    """
    Validate request body against a Pydantic model.
    
    Args:
        model: Pydantic model class to validate against
        description: Optional description for OpenAPI docs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request):
            try:
                # Parse JSON body
                body_data = json.loads(request.body) if isinstance(request.body, str) else request.body
                
                # Validate with Pydantic
                validated = model(**body_data)
                
                # Add to request object
                request.validated_body = validated
                
                # Call original function with validated data
                return func(request, validated)
            except json.JSONDecodeError as e:
                return {
                    "status_code": 400,
                    "body": {"error": "Invalid JSON", "detail": str(e)}
                }
            except ValidationError as e:
                return {
                    "status_code": 422,
                    "body": {"error": "Validation failed", "detail": e.errors()}
                }
        
        # Store metadata for OpenAPI generation
        wrapper._body_model = model
        wrapper._body_description = description
        return wrapper
    return decorator


def query(model: Type[BaseModel], description: Optional[str] = None):
    """
    Validate query parameters against a Pydantic model.
    
    Args:
        model: Pydantic model class to validate against
        description: Optional description for OpenAPI docs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request):
            try:
                # Get query params
                query_params = getattr(request, 'query_params', {})
                
                # Validate with Pydantic
                validated = model(**query_params)
                
                # Add to request object
                request.validated_query = validated
                
                return func(request, validated)
            except ValidationError as e:
                return {
                    "status_code": 422,
                    "body": {"error": "Validation failed", "detail": e.errors()}
                }
        
        wrapper._query_model = model
        wrapper._query_description = description
        return wrapper
    return decorator


def oauth(
    jwks_url: Optional[str] = None,
    public_key: Optional[str] = None,
    audience: Optional[str] = None,
    issuer: Optional[str] = None,
    required: bool = True
):
    """
    Require OAuth/JWT authentication.
    
    Args:
        jwks_url: URL to fetch JWKS from
        public_key: Public key for JWT verification
        audience: Expected audience claim
        issuer: Expected issuer claim
        required: Whether authentication is required
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(request):
            # Get token from Authorization header
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header:
                if required:
                    return {
                        "status_code": 401,
                        "body": {"error": "Missing Authorization header"}
                    }
                return await func(request)
            
            # Extract token
            token = auth_header.replace("Bearer ", "").replace("bearer ", "")
            
            # Get or create validator
            cache_key = f"{jwks_url}:{public_key}:{audience}:{issuer}"
            if cache_key not in _jwt_validators and JwtValidator:
                _jwt_validators[cache_key] = JwtValidator(
                    public_key=public_key,
                    jwks_url=jwks_url,
                    audience=audience,
                    issuer=issuer
                )
            
            validator = _jwt_validators.get(cache_key)
            if not validator:
                if required:
                    return {
                        "status_code": 500,
                        "body": {"error": "JWT validator not configured"}
                    }
                return await func(request)
            
            try:
                # Validate token
                claims = await validator.validate(token)
                request.user = claims
                return await func(request)
            except Exception as e:
                if required:
                    return {
                        "status_code": 401,
                        "body": {"error": "Invalid token", "detail": str(e)}
                    }
                return await func(request)
        
        @functools.wraps(func)
        def sync_wrapper(request):
            # Synchronous version for compatibility
            import asyncio
            return asyncio.run(async_wrapper(request))
        
        # Return appropriate wrapper
        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        wrapper._oauth_config = {
            "jwks_url": jwks_url,
            "public_key": public_key,
            "audience": audience,
            "issuer": issuer,
            "required": required
        }
        return wrapper
    return decorator


def rate_limit(requests: int, per_seconds: int = 60, key_func: Optional[Callable] = None):
    """
    Apply rate limiting to a route.
    
    Args:
        requests: Number of requests allowed
        per_seconds: Time window in seconds
        key_func: Function to extract rate limit key from request (default: uses IP)
    """
    def decorator(func: Callable) -> Callable:
        # Register rate limiter
        limiter_name = f"{func.__name__}_{requests}_{per_seconds}"
        if _rate_limiter:
            _rate_limiter.register_limit(limiter_name, requests, per_seconds)
        
        @functools.wraps(func)
        def wrapper(request):
            if not _rate_limiter:
                return func(request)
            
            # Get rate limit key
            if key_func:
                key = key_func(request)
            else:
                key = getattr(request, 'client_ip', 'unknown')
            
            # Check rate limit
            try:
                _rate_limiter.check(limiter_name, key)
            except Exception as e:
                return {
                    "status_code": 429,
                    "body": {"error": "Rate limit exceeded", "detail": str(e)}
                }
            
            return func(request)
        
        wrapper._rate_limit = {
            "requests": requests,
            "per_seconds": per_seconds
        }
        return wrapper
    return decorator


def openapi_route(
    summary: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list] = None,
    responses: Optional[dict] = None
):
    """
    Add OpenAPI metadata to a route.
    
    Args:
        summary: Short summary of the endpoint
        description: Detailed description
        tags: Tags for grouping endpoints
        responses: Response definitions
    """
    def decorator(func: Callable) -> Callable:
        func._openapi_metadata = {
            "summary": summary,
            "description": description,
            "tags": tags or [],
            "responses": responses or {}
        }
        _openapi_routes.append(func)
        return func
    return decorator
