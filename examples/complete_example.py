"""
Complete example showing all features of robyn-extensions.
"""

from robyn import Robyn
from robyn_extensions import body, query, oauth, rate_limit, openapi_route, OpenAPIGenerator
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Initialize Robyn app
app = Robyn(__file__)

# Initialize OpenAPI generator
openapi = OpenAPIGenerator(
    title="My API",
    version="1.0.0",
    description="Example API with validation, auth, and rate limiting"
)

# Configure OAuth (example with Auth0)
# app.config.oauth.jwks_url = "https://your-domain.auth0.com/.well-known/jwks.json"
# app.config.oauth.audience = "your-api-identifier"
# app.config.oauth.issuer = "https://your-domain.auth0.com/"


# === Models ===

class UserCreate(BaseModel):
    """User creation model."""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
    bio: Optional[str] = None


class UserResponse(BaseModel):
    """User response model."""
    id: int
    name: str
    email: str
    age: int


class QueryParams(BaseModel):
    """Query parameters for listing users."""
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)
    search: Optional[str] = None


class LoginRequest(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str = Field(..., min_length=8)


# === Routes ===

@app.get("/")
@rate_limit(requests=100, per_seconds=60)
def index(request):
    """Welcome endpoint."""
    return {"message": "Welcome to the API"}


@app.post("/users")
@body(UserCreate, description="User data to create")
@oauth(required=True)
@rate_limit(requests=10, per_seconds=60)
@openapi_route(
    summary="Create a new user",
    description="Creates a new user with validation",
    tags=["users"],
    responses={
        201: {"description": "User created successfully"},
        422: {"description": "Validation error"}
    }
)
def create_user(request, user: UserCreate):
    """Create a new user (authenticated)."""
    # Access authenticated user
    authenticated_user = request.user
    
    # In real app, save to database
    new_user = {
        "id": 1,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "created_by": authenticated_user.sub
    }
    
    return {
        "status_code": 201,
        "body": new_user
    }


@app.get("/users")
@query(QueryParams, description="Pagination and search parameters")
@rate_limit(requests=100, per_seconds=60)
@openapi_route(
    summary="List users",
    description="Get paginated list of users with optional search",
    tags=["users"]
)
def list_users(request, params: QueryParams):
    """List users with pagination."""
    # In real app, query database
    users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25},
    ]
    
    # Apply search filter
    if params.search:
        users = [u for u in users if params.search.lower() in u["name"].lower()]
    
    # Apply pagination
    start = (params.page - 1) * params.limit
    end = start + params.limit
    
    return {
        "users": users[start:end],
        "page": params.page,
        "limit": params.limit,
        "total": len(users)
    }


@app.get("/users/<user_id>")
@oauth(required=False)  # Optional auth
@rate_limit(requests=50, per_seconds=60)
@openapi_route(
    summary="Get user by ID",
    description="Retrieve a single user by ID",
    tags=["users"]
)
def get_user(request, user_id: int):
    """Get user by ID (optionally authenticated)."""
    # Check if authenticated
    is_authenticated = hasattr(request, "user")
    
    # In real app, query database
    user = {"id": user_id, "name": "Alice", "email": "alice@example.com", "age": 30}
    
    # Add extra data for authenticated users
    if is_authenticated:
        user["private_info"] = "Only visible when authenticated"
    
    return user


@app.post("/auth/login")
@body(LoginRequest)
@rate_limit(requests=5, per_seconds=60)  # Strict rate limit for auth
@openapi_route(
    summary="Login",
    description="Authenticate and get JWT token",
    tags=["auth"]
)
def login(request, credentials: LoginRequest):
    """Login endpoint."""
    # In real app, verify credentials and generate JWT
    # This is just an example
    
    if credentials.email == "test@example.com" and credentials.password == "password123":
        return {
            "token": "eyJ...",  # Generate real JWT here
            "token_type": "bearer",
            "expires_in": 3600
        }
    
    return {
        "status_code": 401,
        "body": {"error": "Invalid credentials"}
    }


@app.get("/protected")
@oauth(required=True)
@rate_limit(requests=20, per_seconds=60)
@openapi_route(
    summary="Protected endpoint",
    description="Requires valid JWT token",
    tags=["protected"]
)
def protected(request):
    """Protected endpoint requiring authentication."""
    user = request.user
    return {
        "message": "You are authenticated!",
        "user_id": user.sub,
        "email": user.extra.get("email", "N/A")
    }


# === OpenAPI Documentation Endpoints ===

@app.get("/openapi.json")
def openapi_spec(request):
    """Serve OpenAPI spec as JSON."""
    return {
        "headers": {"Content-Type": "application/json"},
        "body": openapi.to_json()
    }


@app.get("/docs")
def swagger_ui(request):
    """Serve Swagger UI for API documentation."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Documentation</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            SwaggerUIBundle({
                url: '/openapi.json',
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ]
            });
        </script>
    </body>
    </html>
    """
    return {
        "headers": {"Content-Type": "text/html"},
        "body": html
    }


# === Register routes with OpenAPI ===
# In a real integration, this would be automatic
openapi.add_route("/", "GET", index, tags=["general"])
openapi.add_route("/users", "POST", create_user, tags=["users"])
openapi.add_route("/users", "GET", list_users, tags=["users"])
openapi.add_route("/users/{user_id}", "GET", get_user, tags=["users"])
openapi.add_route("/auth/login", "POST", login, tags=["auth"])
openapi.add_route("/protected", "GET", protected, tags=["protected"])


if __name__ == "__main__":
    app.start(port=8080)
    print("API running at http://localhost:8080")
    print("Docs available at http://localhost:8080/docs")
