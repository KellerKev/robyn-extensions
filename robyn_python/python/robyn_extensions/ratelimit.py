"""
Easy rate limiting for Robyn using Rust-based rate limiter

Provides FastAPI-style decorators for rate limiting with high performance.
"""
from functools import wraps
from typing import Callable, Optional, Union
import json

try:
    from robyn_extensions._robyn_extensions import RateLimitManager as RustRateLimitManager
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    RustRateLimitManager = None


# Global rate limit manager instance
_global_manager = None


def get_rate_limiter():
    """Get or create the global rate limit manager"""
    global _global_manager
    if _global_manager is None:
        if not RUST_AVAILABLE:
            raise RuntimeError(
                "Rust rate limiter not available. "
                "Please build the extension with: pixi run develop"
            )
        _global_manager = RustRateLimitManager()
    return _global_manager


class RateLimitConfig:
    """Rate limit configuration presets"""

    @staticmethod
    def strict():
        """10 requests per minute"""
        return {"requests": 10, "per_seconds": 60}

    @staticmethod
    def moderate():
        """60 requests per minute"""
        return {"requests": 60, "per_seconds": 60}

    @staticmethod
    def permissive():
        """100 requests per minute"""
        return {"requests": 100, "per_seconds": 60}

    @staticmethod
    def api_standard():
        """1000 requests per hour"""
        return {"requests": 1000, "per_seconds": 3600}

    @staticmethod
    def custom(requests: int, per_seconds: int):
        """Custom rate limit"""
        return {"requests": requests, "per_seconds": per_seconds}


def rate_limit(
    requests: int = 60,
    per_seconds: int = 60,
    key_func: Optional[Callable] = None,
    limiter_name: Optional[str] = None,
):
    """
    Rate limit decorator for Robyn routes (FastAPI-style)

    Usage:
        @app.get("/api/data")
        @rate_limit(requests=10, per_seconds=60)  # 10 requests per minute
        def get_data(request):
            return {"data": "..."}

        # Use presets
        @app.get("/api/strict")
        @rate_limit(**RateLimitConfig.strict())
        def strict_endpoint(request):
            return {"data": "..."}

        # Custom key function (default uses IP address)
        @app.get("/api/users/:id")
        @rate_limit(requests=100, per_seconds=60, key_func=lambda req: req.path_params["id"])
        def per_user_limit(request):
            return {"user": "..."}

    Args:
        requests (int): Number of requests allowed
        per_seconds (int): Time window in seconds
        key_func (Callable, optional): Function to extract rate limit key from request.
                                       Defaults to IP address.
        limiter_name (str, optional): Name for this rate limiter. Auto-generated if not provided.

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        # Generate limiter name if not provided
        nonlocal limiter_name
        if limiter_name is None:
            limiter_name = f"{func.__name__}_{requests}_{per_seconds}"

        # Register this rate limiter
        manager = get_rate_limiter()
        manager.register_limit(limiter_name, requests, per_seconds)

        @wraps(func)
        def wrapper(request):
            # Extract rate limit key
            if key_func:
                key = key_func(request)
            else:
                # Default: use IP address
                key = getattr(request, 'ip_addr', None) or getattr(request, 'client', {}).get('ip', 'unknown')

            # Check rate limit
            try:
                manager.check(limiter_name, str(key))
            except RuntimeError as e:
                # Rate limit exceeded
                error_msg = str(e)
                retry_after = 60  # Default

                # Try to extract retry_after from error message
                if "Retry after" in error_msg:
                    try:
                        retry_after = int(error_msg.split("Retry after ")[1].split(" ")[0])
                    except:
                        pass

                return json.dumps({
                    "error": "Rate limit exceeded",
                    "message": error_msg,
                    "retry_after": retry_after
                }), 429, {
                    "Content-Type": "application/json",
                    "Retry-After": str(retry_after)
                }

            # Call the original function
            return func(request)

        return wrapper
    return decorator


def rate_limit_per_user(
    requests: int = 100,
    per_seconds: int = 60,
    user_key: str = "user_id"
):
    """
    Rate limit per user (extracts user_id from request)

    Usage:
        @app.get("/api/profile")
        @rate_limit_per_user(requests=50, per_seconds=60)
        def get_profile(request):
            user_id = request.headers.get("user_id")
            return {"profile": "..."}

    Args:
        requests (int): Number of requests allowed per user
        per_seconds (int): Time window in seconds
        user_key (str): Header/query param key for user identification
    """
    def key_func(request):
        # Try headers first
        user_id = request.headers.get(user_key)
        if user_id:
            return user_id

        # Try query params
        if hasattr(request, 'query_params'):
            user_id = request.query_params.get(user_key)
            if user_id:
                return user_id

        # Fallback to IP
        return getattr(request, 'ip_addr', 'unknown')

    return rate_limit(requests=requests, per_seconds=per_seconds, key_func=key_func)


def rate_limit_per_ip(requests: int = 60, per_seconds: int = 60):
    """
    Rate limit per IP address (explicit alias for default behavior)

    Usage:
        @app.get("/api/public")
        @rate_limit_per_ip(requests=30, per_seconds=60)
        def public_endpoint(request):
            return {"data": "..."}
    """
    return rate_limit(requests=requests, per_seconds=per_seconds)


def rate_limit_global(requests: int = 1000, per_seconds: int = 60):
    """
    Global rate limit (same limit for all requests)

    Usage:
        @app.get("/api/expensive")
        @rate_limit_global(requests=10, per_seconds=60)
        def expensive_operation(request):
            return {"result": "..."}
    """
    return rate_limit(
        requests=requests,
        per_seconds=per_seconds,
        key_func=lambda req: "global"
    )


# Export presets
strict = lambda: rate_limit(**RateLimitConfig.strict())
moderate = lambda: rate_limit(**RateLimitConfig.moderate())
permissive = lambda: rate_limit(**RateLimitConfig.permissive())
api_standard = lambda: rate_limit(**RateLimitConfig.api_standard())


__all__ = [
    "rate_limit",
    "rate_limit_per_user",
    "rate_limit_per_ip",
    "rate_limit_global",
    "RateLimitConfig",
    "strict",
    "moderate",
    "permissive",
    "api_standard",
    "get_rate_limiter",
]
