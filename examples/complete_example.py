"""
Complete example showing all features of robyn-extensions:
  - Pydantic v2-compatible models with field constraints and validators
  - Request body and query parameter validation
  - Rate limiting with presets
  - OpenAPI auto-documentation (Swagger UI + ReDoc)
  - JWT authentication with scope-based access control
"""

from robyn import Robyn, Request
from robyn_extensions import (
    # Models
    BaseModel, Field, computed_field, field_validator, model_validator,
    # Decorators
    body_v2, query, returns, validated_route,
    # Rate limiting
    rate_limit, strict, moderate,
    # Auth
    setup_auth, AuthConfig, require_auth, optional_auth, admin_required,
    # OpenAPI
    AutoDocs,
)
from typing import Optional, List

app = Robyn(__file__)

# --- Auth setup (uncomment with your provider) ---
# setup_auth(AuthConfig.auth0(domain="your-app.auth0.com", audience="your-api"))

# --- Auto-documentation ---
docs = AutoDocs(app, title="Example API", version="1.0.0", description="Full-featured Robyn API")


# === Models ===

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str = Field(regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(ge=18, le=120)
    bio: Optional[str] = Field(default=None, max_length=500)

    @field_validator('username')
    @classmethod
    def no_reserved_names(cls, v):
        if v.lower() in ('admin', 'root', 'system'):
            raise ValueError('Reserved username')
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    age: int

    @computed_field
    @property
    def is_adult(self) -> bool:
        return self.age >= 18


class SearchParams(BaseModel):
    q: str = Field(default="")
    page: int = Field(ge=1, default=1)
    limit: int = Field(ge=1, le=100, default=20)


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)

    @model_validator(mode='after')
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError('New password and confirmation do not match')
        if self.old_password == self.new_password:
            raise ValueError('New password must differ from old password')
        return self


# === Routes ===

@app.get("/")
@moderate()
def index(request: Request):
    return {"message": "Welcome to the API", "docs": "/docs"}


@app.post("/users")
@body_v2(UserCreate)
@rate_limit(requests=10, per_seconds=60)
def create_user(request: Request, user: UserCreate):
    '''Create a new user account with validation'''
    return UserResponse(
        id=1, username=user.username, email=user.email, age=user.age
    ).model_dump()


@app.get("/users")
@query(SearchParams)
@rate_limit(requests=100, per_seconds=60)
def list_users(request, params: SearchParams):
    '''Search and list users with pagination'''
    users = [
        {"id": 1, "username": "alice", "email": "alice@example.com", "age": 30},
        {"id": 2, "username": "bob", "email": "bob@example.com", "age": 25},
    ]
    if params.q:
        users = [u for u in users if params.q.lower() in u["username"].lower()]
    start = (params.page - 1) * params.limit
    return {"users": users[start:start + params.limit], "total": len(users)}


@app.get("/users/:id")
@returns(UserResponse)
def get_user(request: Request):
    '''Get a user by ID'''
    return UserResponse(id=1, username="alice", email="alice@example.com", age=30)


# Uncomment these routes if auth is configured:

# @app.get("/me")
# @require_auth()
# def get_me(request: Request):
#     '''Get the current authenticated user'''
#     return {"user_id": request.user.sub, "claims": request.user.extra}
#
#
# @app.get("/feed")
# @optional_auth()
# def feed(request: Request):
#     '''Public feed, personalized if authenticated'''
#     if hasattr(request, 'user'):
#         return {"feed": "personalized", "user": request.user.sub}
#     return {"feed": "default"}
#
#
# @app.delete("/users/:id")
# @admin_required()
# def delete_user(request: Request):
#     '''Delete a user (admin only)'''
#     return {"deleted": True}
#
#
# @app.post("/users/:id/password")
# @body_v2(PasswordChange)
# @require_auth()
# @strict()
# def change_password(request: Request, data: PasswordChange):
#     '''Change user password (strict rate limit)'''
#     return {"message": "Password changed"}


if __name__ == "__main__":
    app.start(port=8080)
    # Visit http://localhost:8080/docs for Swagger UI
    # Visit http://localhost:8080/redoc for ReDoc
