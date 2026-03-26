"""
Authentication example — JWT/OAuth2 with scope-based access control.

Demonstrates:
  - Provider setup (Auth0, Google, Okta, or custom JWKS)
  - Route protection with @require_auth
  - Scope-based access control
  - Optional authentication
"""

from robyn import Robyn, Request
from robyn_extensions import (
    BaseModel, Field, body_v2,
    setup_auth, AuthConfig, OIDCProviders,
    require_auth, optional_auth,
    require_scope, require_any_scope, require_all_scopes,
    admin_required, read_required, write_required,
)

app = Robyn(__file__)


# === Auth Provider Setup (choose one) ===

# Auth0
# setup_auth(AuthConfig.auth0(
#     domain="your-app.auth0.com",
#     audience="https://your-api.example.com"
# ))

# Google
# setup_auth(AuthConfig.google(client_id="your-client-id.apps.googleusercontent.com"))

# Okta
# setup_auth(AuthConfig.okta(domain="your-org.okta.com", audience="your-api"))

# Custom JWKS provider
# setup_auth(AuthConfig.from_jwks(
#     jwks_url="https://your-provider.com/.well-known/jwks.json",
#     audience="your-api",
#     issuer="https://your-provider.com/"
# ))

# RSA public key (for self-signed JWTs)
# setup_auth(AuthConfig.from_public_key(
#     public_key=open("public_key.pem").read(),
#     audience="your-api"
# ))


# === Models ===

class Message(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


# === Public Routes ===

@app.get("/public")
def public_endpoint(request: Request):
    return {"message": "This endpoint is public"}


# === Protected Routes ===

@app.get("/protected")
@require_auth()
def protected_endpoint(request: Request):
    '''Requires any valid JWT token'''
    return {
        "message": "Authenticated!",
        "user_id": request.user.sub,
        "issuer": request.user.iss,
    }


@app.get("/profile")
@optional_auth()
def profile(request: Request):
    '''Works for both authenticated and anonymous users'''
    if hasattr(request, 'user'):
        return {"user_id": request.user.sub, "authenticated": True}
    return {"authenticated": False, "message": "Login for personalized content"}


# === Scope-based Access Control ===

@app.get("/items")
@read_required()
def list_items(request: Request):
    '''Requires "read" scope'''
    return {"items": [{"id": 1, "name": "Widget"}]}


@app.post("/items")
@write_required()
@body_v2(Message)
def create_item(request: Request, msg: Message):
    '''Requires "write" scope'''
    return {"created": True, "content": msg.content}


@app.get("/admin/dashboard")
@admin_required()
def admin_dashboard(request: Request):
    '''Requires "admin" scope'''
    return {"users": 42, "active_sessions": 15}


@app.post("/admin/config")
@require_all_scopes("admin", "write")
def update_config(request: Request):
    '''Requires BOTH "admin" AND "write" scopes'''
    return {"updated": True}


@app.get("/reports")
@require_any_scope("admin", "analyst", "manager")
def view_reports(request: Request):
    '''Requires ANY of the listed scopes'''
    return {"reports": [...]}


if __name__ == "__main__":
    app.start(port=8080)
