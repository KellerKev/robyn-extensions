"""
Easy Authentication Example for Robyn

Demonstrates JWT validation with OAuth/OIDC providers and scope-based restrictions.
"""
import sys
sys.path.insert(0, 'robyn_python/python')

from robyn import Robyn, Request
from robyn_extensions import (
    setup_auth,
    AuthConfig,
    OIDCProviders,
    require_auth,
    optional_auth,
    require_scope,
    require_any_scope,
    require_all_scopes,
    admin_required,
    read_required,
    write_required,
)
import json

app = Robyn(__file__)

# ============================================================================
# SETUP - Choose one of these configurations
# ============================================================================

# Option 1: Using a JWKS URL (recommended for production)
# setup_auth(AuthConfig.from_jwks(
#     jwks_url="https://your-auth-provider.com/.well-known/jwks.json",
#     audience="your-api-identifier",
#     issuer="https://your-auth-provider.com/"
# ))

# Option 2: Using Auth0
# setup_auth(AuthConfig.auth0(
#     domain="your-domain.auth0.com",
#     audience="your-api-identifier"
# ))

# Option 3: Using Google OAuth
# setup_auth(AuthConfig.google(
#     client_id="your-client-id.apps.googleusercontent.com"
# ))

# Option 4: Using a public key (for testing/development)
# For this example, we'll use a mock setup (won't actually validate)
# In production, use one of the options above

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Z3VS5JJcds3xfn/6pAP
jRlcRNT2uTWuHf8xYMR8nOk3LAVbgEapxrfRDz9UkwHMPJ/J1bQrKJGHjJT9hQO/
Rg31eKWgBu4PrSMkNMQ4QlvYnMRkjZ5D6LLJPdS7hNKCqVXPWlDZDHUB8L9QMxlJ
jqVkNMNfXPdP3N5nYTLTrBQQNjbBXQP9YQFdU+LH4cHF3cN5CgKZPZNJfTWn9YPe
Sq2LvKKfR7R9wR9xTPJP0U4P3QmKqJQG5ZNr+B8YfPRX1bQV8hNXKGLHx9fGJFYW
pH2IQy4sNDPQ0Oce6vQPJ5QNJkNKQqHFNg0DKkMPQQVRQNYPKqHFNg0DKkMPQQVR
QNYPKQIDAQAB
-----END PUBLIC KEY-----"""

setup_auth(AuthConfig.from_public_key(
    public_key=PUBLIC_KEY,
    audience="test-api",
    issuer="test-issuer"
))

print("✅ Authentication configured")
print("   Provider: Mock (for demo)")
print("   Audience: test-api")
print()

# ============================================================================
# PUBLIC ENDPOINTS (No authentication required)
# ============================================================================

@app.get("/")
def index(request: Request):
    """API documentation"""
    return json.dumps({
        "title": "Authentication Demo for Robyn",
        "description": "JWT validation with OAuth/OIDC and scope-based restrictions",
        "endpoints": {
            "public": {
                "/": "This page",
                "/api/public": "Public endpoint (no auth)",
                "/api/optional": "Optional auth (works with or without token)"
            },
            "protected": {
                "/api/protected": "Requires valid JWT",
                "/api/profile": "Requires authentication, returns user info"
            },
            "scope_based": {
                "/api/read": "Requires 'read' scope",
                "/api/write": "Requires 'write' scope",
                "/api/admin": "Requires 'admin' scope",
                "/api/admin/delete": "Requires both 'admin' AND 'delete' scopes",
                "/api/editor": "Requires either 'write' OR 'admin' scope"
            }
        },
        "authentication": {
            "header": "Authorization: Bearer <token>",
            "providers": {
                "auth0": "AuthConfig.auth0(domain, audience)",
                "google": "AuthConfig.google(client_id)",
                "okta": "AuthConfig.okta(domain, audience)",
                "custom_jwks": "AuthConfig.from_jwks(jwks_url, audience, issuer)",
                "public_key": "AuthConfig.from_public_key(public_key, audience)"
            }
        },
        "scopes": {
            "format": "JWT claim: 'scope' (space-separated) or 'scopes' (array)",
            "examples": [
                "read",
                "write",
                "admin",
                "delete",
                "read:users",
                "write:posts"
            ]
        },
        "testing": {
            "note": "This demo uses a mock key. In production, use real OAuth/OIDC provider",
            "curl_example": "curl -H 'Authorization: Bearer your-jwt-token' http://localhost:8083/api/protected"
        }
    })


@app.get("/api/public")
def public_endpoint(request: Request):
    """Public endpoint - no authentication required"""
    return json.dumps({
        "endpoint": "/api/public",
        "auth_required": False,
        "message": "This endpoint is publicly accessible"
    })


@app.get("/api/optional")
@optional_auth()
def optional_endpoint(request: Request):
    """Optional authentication - works with or without token"""
    if hasattr(request, 'user'):
        return json.dumps({
            "endpoint": "/api/optional",
            "authenticated": True,
            "user_id": request.user.sub,
            "message": f"Hello, {request.user.sub}!"
        })
    else:
        return json.dumps({
            "endpoint": "/api/optional",
            "authenticated": False,
            "message": "Hello, anonymous user!"
        })


# ============================================================================
# PROTECTED ENDPOINTS (Authentication required)
# ============================================================================

@app.get("/api/protected")
@require_auth()
def protected_endpoint(request: Request):
    """Basic protected endpoint - requires valid JWT"""
    return json.dumps({
        "endpoint": "/api/protected",
        "auth_required": True,
        "user_id": request.user.sub,
        "message": "You are authenticated!"
    })


@app.get("/api/profile")
@require_auth()
def get_profile(request: Request):
    """Get user profile from JWT claims"""
    user = request.user

    # Extract all available claims
    profile = {
        "user_id": user.sub,
        "issued_at": user.iat if user.iat else None,
        "expires_at": user.exp,
        "issuer": user.iss if user.iss else None,
        "audience": user.aud if user.aud else None,
    }

    # Add any extra claims
    if hasattr(user, 'extra') and user.extra:
        profile["extra_claims"] = user.extra

    return json.dumps({
        "endpoint": "/api/profile",
        "profile": profile
    })


# ============================================================================
# SCOPE-BASED ENDPOINTS (Require specific permissions)
# ============================================================================

@app.get("/api/read")
@require_scope("read")
def read_endpoint(request: Request):
    """Requires 'read' scope"""
    return json.dumps({
        "endpoint": "/api/read",
        "required_scope": "read",
        "message": "You have read permissions",
        "data": ["item1", "item2", "item3"]
    })


@app.post("/api/write")
@require_scope("write")
def write_endpoint(request: Request):
    """Requires 'write' scope"""
    return json.dumps({
        "endpoint": "/api/write",
        "required_scope": "write",
        "message": "You have write permissions",
        "status": "created"
    })


@app.get("/api/admin")
@require_scope("admin")
def admin_endpoint(request: Request):
    """Requires 'admin' scope"""
    return json.dumps({
        "endpoint": "/api/admin",
        "required_scope": "admin",
        "message": "Welcome, admin!",
        "admin_data": "sensitive information"
    })


@app.delete("/api/admin/delete")
@require_all_scopes("admin", "delete")
def admin_delete(request: Request):
    """Requires BOTH 'admin' AND 'delete' scopes"""
    return json.dumps({
        "endpoint": "/api/admin/delete",
        "required_scopes": ["admin", "delete"],
        "requirement": "ALL scopes required",
        "message": "You have both admin and delete permissions",
        "status": "deleted"
    })


@app.post("/api/editor")
@require_any_scope("write", "admin")
def editor_endpoint(request: Request):
    """Requires EITHER 'write' OR 'admin' scope"""
    return json.dumps({
        "endpoint": "/api/editor",
        "required_scopes": ["write", "admin"],
        "requirement": "ANY scope required",
        "message": "You have editor permissions",
        "status": "updated"
    })


# ============================================================================
# ADVANCED: Custom scope checking
# ============================================================================

@app.get("/api/advanced/read-users")
@require_scope("read:users")
def read_users_endpoint(request: Request):
    """Requires hierarchical scope 'read:users'"""
    return json.dumps({
        "endpoint": "/api/advanced/read-users",
        "required_scope": "read:users",
        "message": "Hierarchical scopes supported",
        "users": ["alice", "bob", "charlie"]
    })


@app.post("/api/advanced/write-posts")
@require_scope("write:posts")
def write_posts_endpoint(request: Request):
    """Requires hierarchical scope 'write:posts'"""
    return json.dumps({
        "endpoint": "/api/advanced/write-posts",
        "required_scope": "write:posts",
        "message": "Post created",
        "post_id": "12345"
    })


# ============================================================================
# ERROR HANDLING EXAMPLES
# ============================================================================

@app.get("/api/test/no-token")
@require_auth()
def test_no_token(request: Request):
    """This will return 401 if no token provided"""
    return json.dumps({"message": "You won't see this without a token"})


@app.get("/api/test/invalid-scope")
@require_scope("super-admin")
def test_invalid_scope(request: Request):
    """This will return 403 if user doesn't have 'super-admin' scope"""
    return json.dumps({"message": "You won't see this without super-admin scope"})


if __name__ == "__main__":
    print("🚀 Starting Robyn with JWT Authentication...")
    print("📚 Endpoints:")
    print("   - Home:      http://localhost:8083/")
    print("   - Public:    http://localhost:8083/api/public")
    print("   - Protected: http://localhost:8083/api/protected")
    print("   - Profile:   http://localhost:8083/api/profile")
    print("   - Scopes:    http://localhost:8083/api/read (requires 'read' scope)")
    print()
    print("🔐 Authentication:")
    print("   Header: Authorization: Bearer <your-jwt-token>")
    print()
    print("⚠️  Note: This demo uses a mock key for illustration.")
    print("   In production, use AuthConfig.auth0(), .google(), .okta(), etc.")
    print()
    app.start(host="0.0.0.0", port=8083)
