"""
Easy Authentication for Robyn

FastAPI-style JWT validation with OAuth/OIDC providers and scope-based restrictions.
"""
from functools import wraps
from typing import Callable, Optional, List, Dict, Any
import json

try:
    from robyn_extensions._robyn_extensions import JwtValidator as RustJwtValidator
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    RustJwtValidator = None


# Popular OAuth/OIDC providers
class OIDCProviders:
    """Pre-configured OIDC providers with JWKS URLs"""

    @staticmethod
    def auth0(domain: str) -> str:
        """Auth0 JWKS URL"""
        return f"https://{domain}/.well-known/jwks.json"

    @staticmethod
    def google() -> str:
        """Google JWKS URL"""
        return "https://www.googleapis.com/oauth2/v3/certs"

    @staticmethod
    def okta(domain: str) -> str:
        """Okta JWKS URL"""
        return f"https://{domain}/oauth2/default/v1/keys"

    @staticmethod
    def azure_ad(tenant_id: str) -> str:
        """Azure AD JWKS URL"""
        return f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    @staticmethod
    def keycloak(domain: str, realm: str) -> str:
        """Keycloak JWKS URL"""
        return f"{domain}/realms/{realm}/protocol/openid-connect/certs"

    @staticmethod
    def cognito(region: str, user_pool_id: str) -> str:
        """AWS Cognito JWKS URL"""
        return f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"


class AuthConfig:
    """Authentication configuration"""

    def __init__(
        self,
        public_key: Optional[str] = None,
        jwks_url: Optional[str] = None,
        audience: Optional[str] = None,
        issuer: Optional[str] = None,
        leeway: int = 60,
    ):
        """
        Initialize authentication configuration

        Args:
            public_key: RSA public key in PEM format
            jwks_url: JWKS endpoint URL (for OIDC providers)
            audience: Expected audience claim
            issuer: Expected issuer claim
            leeway: Clock skew tolerance in seconds (default: 60)
        """
        self.public_key = public_key
        self.jwks_url = jwks_url
        self.audience = audience
        self.issuer = issuer
        self.leeway = leeway

        if not public_key and not jwks_url:
            raise ValueError("Either public_key or jwks_url must be provided")

    @classmethod
    def from_jwks(cls, jwks_url: str, **kwargs) -> "AuthConfig":
        """Create config from JWKS URL"""
        return cls(jwks_url=jwks_url, **kwargs)

    @classmethod
    def from_public_key(cls, public_key: str, **kwargs) -> "AuthConfig":
        """Create config from public key"""
        return cls(public_key=public_key, **kwargs)

    @classmethod
    def auth0(cls, domain: str, audience: str, **kwargs) -> "AuthConfig":
        """Pre-configured Auth0"""
        return cls(
            jwks_url=OIDCProviders.auth0(domain),
            issuer=f"https://{domain}/",
            audience=audience,
            **kwargs
        )

    @classmethod
    def google(cls, client_id: str, **kwargs) -> "AuthConfig":
        """Pre-configured Google OAuth"""
        return cls(
            jwks_url=OIDCProviders.google(),
            issuer="https://accounts.google.com",
            audience=client_id,
            **kwargs
        )

    @classmethod
    def okta(cls, domain: str, audience: str, **kwargs) -> "AuthConfig":
        """Pre-configured Okta"""
        return cls(
            jwks_url=OIDCProviders.okta(domain),
            issuer=f"https://{domain}/oauth2/default",
            audience=audience,
            **kwargs
        )


# Global validator instance
_global_validator = None
_global_config = None


def setup_auth(config: AuthConfig):
    """
    Setup global authentication configuration

    Usage:
        from robyn_extensions import setup_auth, AuthConfig

        # Using JWKS URL
        setup_auth(AuthConfig.from_jwks(
            "https://your-auth.com/.well-known/jwks.json",
            audience="your-api",
            issuer="https://your-auth.com/"
        ))

        # Using Auth0
        setup_auth(AuthConfig.auth0(
            domain="your-domain.auth0.com",
            audience="your-api-identifier"
        ))

        # Using Google
        setup_auth(AuthConfig.google(
            client_id="your-client-id.apps.googleusercontent.com"
        ))
    """
    global _global_validator, _global_config

    if not RUST_AVAILABLE:
        raise RuntimeError(
            "Rust JWT validator not available. "
            "Please build the extension with: pixi run develop"
        )

    _global_config = config
    _global_validator = RustJwtValidator(
        public_key=config.public_key,
        jwks_url=config.jwks_url,
        audience=config.audience,
        issuer=config.issuer,
    )


def get_auth_validator():
    """Get the global JWT validator"""
    if _global_validator is None:
        raise RuntimeError(
            "Authentication not configured. Call setup_auth() first."
        )
    return _global_validator


def extract_token(request) -> Optional[str]:
    """
    Extract JWT token from Authorization header

    Supports:
        Authorization: Bearer <token>
        Authorization: <token>
    """
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")

    if not auth_header:
        return None

    # Handle "Bearer <token>" format
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Handle raw token
    return auth_header


def require_auth(
    scopes: Optional[List[str]] = None,
    require_all_scopes: bool = False,
):
    """
    Decorator to require JWT authentication

    Usage:
        # Basic authentication
        @app.get("/api/protected")
        @require_auth()
        def protected_route(request):
            # request.user contains the JWT claims
            return {"user": request.user}

        # Require specific scopes
        @app.get("/api/admin")
        @require_auth(scopes=["admin"])
        def admin_route(request):
            return {"message": "Admin only"}

        # Require multiple scopes (any)
        @app.post("/api/write")
        @require_auth(scopes=["write:data", "admin"])
        def write_route(request):
            # User needs either "write:data" OR "admin" scope
            return {"status": "created"}

        # Require all scopes
        @app.delete("/api/admin/delete")
        @require_auth(scopes=["admin", "delete"], require_all_scopes=True)
        def admin_delete(request):
            # User needs BOTH "admin" AND "delete" scopes
            return {"status": "deleted"}

    Args:
        scopes: List of required scopes. If None, only checks authentication.
        require_all_scopes: If True, user must have ALL specified scopes.
                           If False, user needs ANY of the specified scopes.

    Returns:
        Decorator function that validates JWT and checks scopes
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request):
            # Extract token
            token = extract_token(request)

            if not token:
                return (
                    json.dumps({
                        "error": "Authentication required",
                        "message": "No token provided"
                    }),
                    {"Content-Type": "application/json"},
                    401
                )

            # Validate token
            validator = get_auth_validator()

            try:
                # Use the async validate method via sync wrapper
                # (Python bindings handle the async bridge)
                claims = validator.validate_sync(token)
            except RuntimeError as e:
                error_msg = str(e)

                if "expired" in error_msg.lower():
                    return (
                        json.dumps({
                            "error": "Token expired",
                            "message": error_msg
                        }),
                        {"Content-Type": "application/json"},
                        401
                    )
                else:
                    return (
                        json.dumps({
                            "error": "Invalid token",
                            "message": error_msg
                        }),
                        {"Content-Type": "application/json"},
                        401
                    )

            # Check scopes if specified
            if scopes:
                # Extract scopes from claims (common claim names)
                user_scopes = []

                # Try different scope claim formats
                if hasattr(claims, 'extra'):
                    # Check for "scope" claim (space-separated string)
                    if 'scope' in claims.extra:
                        scope_str = claims.extra['scope']
                        if isinstance(scope_str, str):
                            user_scopes = scope_str.split()

                    # Check for "scopes" claim (array)
                    if 'scopes' in claims.extra:
                        scopes_value = claims.extra['scopes']
                        if isinstance(scopes_value, list):
                            user_scopes = scopes_value

                    # Check for "permissions" claim (Auth0 style)
                    if 'permissions' in claims.extra:
                        perms = claims.extra['permissions']
                        if isinstance(perms, list):
                            user_scopes.extend(perms)

                # Check if user has required scopes
                if require_all_scopes:
                    # User must have ALL scopes
                    missing_scopes = [s for s in scopes if s not in user_scopes]
                    if missing_scopes:
                        return (
                            json.dumps({
                                "error": "Insufficient permissions",
                                "message": f"Missing required scopes: {', '.join(missing_scopes)}",
                                "required_scopes": scopes,
                                "user_scopes": user_scopes
                            }),
                            {"Content-Type": "application/json"},
                            403
                        )
                else:
                    # User needs ANY of the scopes
                    has_any_scope = any(s in user_scopes for s in scopes)
                    if not has_any_scope:
                        return (
                            json.dumps({
                                "error": "Insufficient permissions",
                                "message": f"Requires one of: {', '.join(scopes)}",
                                "required_scopes": scopes,
                                "user_scopes": user_scopes
                            }),
                            {"Content-Type": "application/json"},
                            403
                        )

            # Attach user claims to request
            request.user = claims

            # Call the original function
            return func(request)

        return wrapper
    return decorator


def optional_auth():
    """
    Decorator for optional authentication

    If token is provided, validates it and attaches user to request.
    If no token, continues without authentication.

    Usage:
        @app.get("/api/public")
        @optional_auth()
        def public_route(request):
            if hasattr(request, 'user'):
                return {"message": f"Hello {request.user.sub}"}
            else:
                return {"message": "Hello anonymous"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request):
            token = extract_token(request)

            if token:
                validator = get_auth_validator()
                try:
                    claims = validator.validate_sync(token)
                    request.user = claims
                except RuntimeError:
                    # Invalid token, but that's OK for optional auth
                    pass

            return func(request)

        return wrapper
    return decorator


# Convenience decorators for common scope patterns
def require_scope(scope: str):
    """Require a single scope"""
    return require_auth(scopes=[scope])


def require_any_scope(*scopes: str):
    """Require any of the specified scopes"""
    return require_auth(scopes=list(scopes), require_all_scopes=False)


def require_all_scopes(*scopes: str):
    """Require all of the specified scopes"""
    return require_auth(scopes=list(scopes), require_all_scopes=True)


# Common scope patterns
admin_required = lambda: require_scope("admin")
read_required = lambda: require_scope("read")
write_required = lambda: require_scope("write")
delete_required = lambda: require_scope("delete")


__all__ = [
    "setup_auth",
    "AuthConfig",
    "OIDCProviders",
    "require_auth",
    "optional_auth",
    "require_scope",
    "require_any_scope",
    "require_all_scopes",
    "admin_required",
    "read_required",
    "write_required",
    "delete_required",
    "extract_token",
]
