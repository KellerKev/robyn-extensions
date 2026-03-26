"""
Authentication utilities and configuration.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OAuthConfig:
    """OAuth 2.0 configuration."""
    authorization_url: str
    token_url: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str]
    
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL with state."""
        from urllib.parse import urlencode
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state
        }
        return f"{self.authorization_url}?{urlencode(params)}"


def oauth_config(
    authorization_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    scopes: Optional[list[str]] = None
) -> OAuthConfig:
    """Create OAuth configuration."""
    return OAuthConfig(
        authorization_url=authorization_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=scopes or []
    )


class JWTValidator:
    """Wrapper for JWT validation (delegates to Rust implementation)."""
    
    def __init__(
        self,
        public_key: Optional[str] = None,
        jwks_url: Optional[str] = None,
        audience: Optional[str] = None,
        issuer: Optional[str] = None
    ):
        try:
            from robyn_extensions import JwtValidator as RustValidator
            self._validator = RustValidator(
                public_key=public_key,
                jwks_url=jwks_url,
                audience=audience,
                issuer=issuer
            )
        except ImportError:
            self._validator = None
    
    async def validate(self, token: str):
        """Validate JWT token asynchronously."""
        if self._validator:
            return await self._validator.validate(token)
        raise RuntimeError("Rust JWT validator not available")
    
    def validate_sync(self, token: str):
        """Validate JWT token synchronously."""
        if self._validator:
            return self._validator.validate_sync(token)
        raise RuntimeError("Rust JWT validator not available")
