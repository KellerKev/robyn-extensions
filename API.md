# API Reference

## Decorators

### `@body(model, description=None)`

Validates request body against a Pydantic model.

**Parameters:**
- `model`: Pydantic model class
- `description`: Optional description for OpenAPI docs

**Returns:**
- Validated model instance passed as second argument to handler

**Example:**
```python
@app.post("/users")
@body(UserCreate)
def create_user(request, user: UserCreate):
    return {"name": user.name}
```

### `@query(model, description=None)`

Validates query parameters against a Pydantic model.

**Parameters:**
- `model`: Pydantic model class
- `description`: Optional description for OpenAPI docs

**Example:**
```python
@app.get("/users")
@query(QueryParams)
def list_users(request, params: QueryParams):
    return {"page": params.page}
```

### `@oauth(jwks_url=None, public_key=None, audience=None, issuer=None, required=True)`

Requires OAuth/JWT authentication.

**Parameters:**
- `jwks_url`: URL to fetch JWKS from
- `public_key`: RSA/EC public key for JWT verification
- `audience`: Expected audience claim
- `issuer`: Expected issuer claim
- `required`: Whether authentication is required (default: True)

**Example:**
```python
@app.get("/protected")
@oauth(jwks_url="https://auth.example.com/.well-known/jwks.json")
def protected(request):
    user = request.user  # JWT claims
    return {"user_id": user.sub}
```

### `@rate_limit(requests, per_seconds=60, key_func=None)`

Applies rate limiting to a route.

**Parameters:**
- `requests`: Number of requests allowed
- `per_seconds`: Time window in seconds (default: 60)
- `key_func`: Function to extract rate limit key (default: uses IP)

**Example:**
```python
@app.post("/api")
@rate_limit(requests=10, per_seconds=60)
def api_endpoint(request):
    return {"status": "ok"}
```

### `@openapi_route(summary=None, description=None, tags=None, responses=None)`

Adds OpenAPI metadata to a route.

**Parameters:**
- `summary`: Short summary
- `description`: Detailed description
- `tags`: List of tags for grouping
- `responses`: Response definitions dict

**Example:**
```python
@app.get("/users")
@openapi_route(
    summary="List users",
    tags=["users"],
    responses={200: {"description": "Success"}}
)
def list_users(request):
    return {"users": []}
```

## Classes

### `OpenAPIGenerator`

Generates OpenAPI 3.0 specifications.

**Methods:**

#### `__init__(title="API", version="1.0.0", description=None)`

Creates a new OpenAPI generator.

#### `add_route(path, method, handler, tags=None)`

Registers a route for documentation.

#### `generate_spec() -> dict`

Generates complete OpenAPI specification.

#### `to_json() -> str`

Exports specification as JSON.

#### `to_yaml() -> str`

Exports specification as YAML (requires PyYAML).

**Example:**
```python
openapi = OpenAPIGenerator("My API", "1.0.0")
openapi.add_route("/users", "GET", list_users)
spec = openapi.generate_spec()
```

### `JWTValidator`

JWT token validation with JWKS support.

**Methods:**

#### `__init__(public_key=None, jwks_url=None, audience=None, issuer=None)`

Creates validator with configuration.

#### `async validate(token: str) -> Claims`

Validates JWT token asynchronously.

#### `validate_sync(token: str) -> Claims`

Validates JWT token synchronously.

## Utility Functions

### `validate_model(model, data) -> BaseModel`

Validates data against a Pydantic model.

### `get_validation_errors(model, data) -> dict`

Returns validation errors without raising exceptions.

## Rust Components

### Rate Limiting

```rust
use robyn_ratelimit::{RateLimitManager, RateLimitConfig};

let manager = RateLimitManager::new();
let config = RateLimitConfig::new(100, 60)?;
manager.register_limit("api", config)?;
manager.check("api", "user123")?;
```

### JWT Validation

```rust
use robyn_auth::{JwtValidator, JwtConfig};

let config = JwtConfig {
    jwks_url: Some("https://...".to_string()),
    ..Default::default()
};
let validator = JwtValidator::new(config);
let claims = validator.validate(token).await?;
```

### OpenAPI Generation

```rust
use robyn_openapi::OpenApiBuilder;

let spec = OpenApiBuilder::new("API", "1.0.0")
    .description("My API")
    .add_bearer_auth()
    .build();
```
