# API Reference - Robyn Extensions

Complete reference for all Robyn Extensions features.

## Table of Contents

1. [Pydantic Models](#pydantic-models)
2. [Validation](#validation)
3. [OpenAPI Documentation](#openapi-documentation)
4. [Authentication](#authentication)
5. [Rate Limiting](#rate-limiting)
6. [REST API Generator](#rest-api-generator)

---

## Pydantic Models

### BaseModel

Base class for defining data models with automatic validation.

```python
from robyn_extensions import BaseModel, Field

class User(BaseModel):
    name: str
    email: str
    age: int = 18  # Default value
```

### Field Constraints

```python
from robyn_extensions import Field

class Model(BaseModel):
    # String constraints
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')

    # Numeric constraints
    age: int = Field(..., ge=0, le=150)  # Greater/less than or equal
    price: float = Field(..., gt=0, lt=10000)  # Greater/less than

    # Optional fields
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
```

**Field Parameters:**
- `min_length` / `max_length` - String length constraints
- `ge` / `gt` - Greater than or equal / greater than (numbers)
- `le` / `lt` - Less than or equal / less than (numbers)
- `pattern` - Regex pattern for string validation
- `default` - Default value
- `default_factory` - Function to generate default value
- `...` - Required field (no default)

### Model Methods

```python
# Create instance
user = User(name="Alice", email="alice@example.com", age=30)

# Convert to dict
data = user.dict()
data = user.dict(exclude={'password'})  # Exclude fields
data = user.dict(exclude_unset=True)    # Only include set fields

# Convert to JSON
json_str = user.json()

# Parse from dict
user = User(**data_dict)

# Parse from JSON
user = User.parse_raw(json_str)

# Validation
try:
    user = User(name="", email="invalid")
except ValidationError as e:
    print(e.errors())
```

### Field Validators

```python
from robyn_extensions import BaseModel, field_validator

class User(BaseModel):
    email: str
    password: str

    @field_validator('email')
    def validate_email(cls, value):
        if '@' not in value:
            raise ValueError('Invalid email')
        return value.lower()

    @field_validator('password')
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError('Password too short')
        return value
```

### Model Validators

```python
from robyn_extensions import BaseModel, model_validator

class User(BaseModel):
    password: str
    password_confirm: str

    @model_validator(mode='after')
    def check_passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self
```

---

## Validation

### Request Body Validation

```python
from robyn_extensions import body_v2

@app.post("/users")
@body_v2(User)
def create_user(request):
    # Validated data available in request.validated_data
    user = request.validated_data
    return {"user": user.dict()}
```

**Error Response Format:**

```json
{
  "status": "error",
  "code": 422,
  "errors": [
    {
      "field": "email",
      "error": "Invalid email format",
      "type": "value_error"
    }
  ]
}
```

### Query Parameter Validation

```python
from robyn_extensions import query

class SearchParams(BaseModel):
    q: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

@app.get("/search")
@query(SearchParams)
def search(request):
    params = request.validated_query
    return {"query": params.q, "limit": params.limit}
```

---

## OpenAPI Documentation

### Setup

```python
from robyn_extensions import setup_openapi_docs

setup_openapi_docs(
    app,
    title="My API",
    version="1.0.0",
    description="API description here",
    contact={
        "name": "API Support",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)
```

### Documenting Endpoints

```python
from robyn_extensions import openapi_route

@app.get("/users")
@openapi_route(
    summary="List all users",
    description="Returns a paginated list of users",
    tags=["Users"],
    responses={
        200: {"description": "Success", "content": {"application/json": {...}}},
        401: {"description": "Unauthorized"}
    }
)
def list_users(request):
    return {"users": [...]}
```

### Access Documentation

- **Swagger UI**: `http://localhost:PORT/docs`
- **OpenAPI JSON**: `http://localhost:PORT/openapi.json`

---

## Authentication

### Setup Authentication

```python
from robyn_extensions import setup_auth, AuthConfig, OIDCProviders

# Option 1: Mock (for testing)
setup_auth(app, AuthConfig.mock(
    public_key="your-public-key",
    audience="test-api",
    issuer="test-issuer"
))

# Option 2: Auth0
setup_auth(app, OIDCProviders.Auth0(
    client_id="your-client-id",
    client_secret="your-secret",
    domain="your-domain.auth0.com"
))

# Option 3: Custom OIDC
setup_auth(app, AuthConfig(
    public_key="...",
    jwks_url="https://your-provider.com/.well-known/jwks.json",
    audience="your-api",
    issuer="https://your-provider.com"
))
```

### Auth Decorators

#### require_auth()

Requires a valid JWT token.

```python
from robyn_extensions import require_auth

@app.get("/protected")
@require_auth()
def protected_endpoint(request):
    # Access user info from token
    user_id = request.user.sub
    return {"user_id": user_id}
```

#### optional_auth()

Allows requests with or without authentication.

```python
from robyn_extensions import optional_auth

@app.get("/content")
@optional_auth()
def get_content(request):
    if request.user:
        # Authenticated user
        return {"premium": True, "user": request.user.sub}
    else:
        # Anonymous user
        return {"premium": False}
```

#### require_scope()

Requires specific OAuth scope.

```python
from robyn_extensions import require_scope

@app.post("/admin/users")
@require_scope("admin")
def admin_action(request):
    return {"action": "performed"}
```

#### require_any_scope()

Requires at least one of the specified scopes.

```python
from robyn_extensions import require_any_scope

@app.get("/content")
@require_any_scope("read", "write", "admin")
def get_content(request):
    return {"content": "..."}
```

#### require_all_scopes()

Requires all specified scopes.

```python
from robyn_extensions import require_all_scopes

@app.delete("/users/:id")
@require_all_scopes("admin", "delete")
def delete_user(request):
    return {"deleted": True}
```

### Convenience Decorators

```python
from robyn_extensions import (
    admin_required,
    read_required,
    write_required,
    delete_required
)

@app.post("/admin")
@admin_required()  # Requires "admin" scope
def admin_only(request):
    return {"admin": True}

@app.get("/data")
@read_required()  # Requires "read" scope
def read_data(request):
    return {"data": [...]}
```

### Making Authenticated Requests

```bash
# Get your JWT token from your auth provider
TOKEN="your.jwt.token"

# Include in Authorization header
curl http://localhost:8080/api/protected \
  -H "Authorization: Bearer $TOKEN"
```

### Token Claims Access

```python
@app.get("/profile")
@require_auth()
def get_profile(request):
    user = request.user
    return {
        "sub": user.sub,           # Subject (user ID)
        "email": user.email,       # Email (if present)
        "scopes": user.scopes,     # List of scopes
        "exp": user.exp,           # Expiration time
        "iat": user.iat,           # Issued at time
        "iss": user.iss,           # Issuer
        "aud": user.aud            # Audience
    }
```

---

## Rate Limiting

### Basic Rate Limiting

```python
from robyn_extensions import rate_limit

@app.get("/api/data")
@rate_limit(requests=100, per_seconds=60)  # 100 requests per minute
def get_data(request):
    return {"data": [...]}
```

### Per-User Rate Limiting

Requires authentication. Limits apply per user ID.

```python
from robyn_extensions import rate_limit_per_user, require_auth

@app.post("/api/actions")
@require_auth()
@rate_limit_per_user(requests=10, per_seconds=60)
def perform_action(request):
    return {"action": "performed"}
```

### Per-IP Rate Limiting

Limits apply per IP address.

```python
from robyn_extensions import rate_limit_per_ip

@app.get("/api/search")
@rate_limit_per_ip(requests=30, per_seconds=60)
def search(request):
    return {"results": [...]}
```

### Global Rate Limiting

Single limit across all users.

```python
from robyn_extensions import rate_limit_global

@app.post("/api/expensive")
@rate_limit_global(requests=100, per_seconds=3600)  # 100/hour globally
def expensive_operation(request):
    return {"result": "..."}
```

### Rate Limit Presets

```python
from robyn_extensions import strict, moderate, permissive, api_standard

@app.get("/strict")
@strict()  # 10 requests per 60 seconds
def strict_endpoint(request):
    return {"data": "..."}

@app.get("/moderate")
@moderate()  # 100 requests per 60 seconds
def moderate_endpoint(request):
    return {"data": "..."}

@app.get("/permissive")
@permissive()  # 1000 requests per 60 seconds
def permissive_endpoint(request):
    return {"data": "..."}

@app.get("/standard")
@api_standard()  # 60 requests per 60 seconds
def standard_endpoint(request):
    return {"data": "..."}
```

### Rate Limit Response Headers

When rate limited, responses include:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1234567890
Retry-After: 15
```

**429 Response:**

```json
{
  "error": "Rate limit exceeded",
  "retry_after": 15
}
```

---

## REST API Generator

### Overview

Auto-generate CRUD endpoints from Pydantic models with PyDAL-style querying.

### Define Model

```python
from robyn_extensions import BaseModel, Field
from typing import Optional
from datetime import datetime

class Product(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    in_stock: bool = True
    created_at: Optional[datetime] = None
```

### Implement CRUD Resource

```python
from robyn_extensions import CRUDResource

class ProductResource(CRUDResource):
    """
    Implement these methods to connect to your database.
    Can use SQLAlchemy, Tortoise ORM, PyMongo, or raw SQL.
    """

    async def list(self, filters, offset=0, limit=100, order_by=None):
        """
        List resources with filtering and pagination.

        Args:
            filters: Dict of field filters {"field": {"op": value}}
            offset: Skip N records
            limit: Return max N records
            order_by: List of fields to order by (prefix with - for desc)

        Returns:
            (items: List[Dict], total_count: int)
        """
        # Your database query logic here
        # Apply filters, pagination, ordering
        return items, total_count

    async def get(self, id):
        """Get a single resource by ID."""
        # Your database query logic
        return item_dict or None

    async def create(self, data):
        """Create a new resource."""
        # Your database insert logic
        return created_item_dict

    async def update(self, id, data):
        """Update an existing resource."""
        # Your database update logic
        return updated_item_dict or None

    async def delete(self, id):
        """Delete a resource."""
        # Your database delete logic
        return True  # or False if not found
```

### Register REST API

```python
from robyn import Robyn
from robyn_extensions import RestAPI, require_auth, admin_required

app = Robyn(__file__)
api = RestAPI(app, prefix="/api", version="1.0")

api.register_resource(
    name="products",
    model=Product,
    resource=ProductResource(),
    policies={
        "GET": True,                 # Public read access
        "POST": require_auth(),      # Create requires authentication
        "PUT": require_auth(),       # Update requires authentication
        "DELETE": admin_required(),  # Delete requires admin scope
    },
    rate_limits={
        "GET": (100, 60),   # 100 requests per minute
        "POST": (10, 60),   # 10 requests per minute
        "PUT": (20, 60),    # 20 requests per minute
        "DELETE": (5, 60),  # 5 requests per minute
    },
    tags=["Products"]
)
```

### Generated Endpoints

The above registration creates 5 endpoints:

```
GET    /api/products       - List all products
GET    /api/products/:id   - Get single product
POST   /api/products       - Create product
PUT    /api/products/:id   - Update product
DELETE /api/products/:id   - Delete product
```

### Query Syntax

#### Filtering

**Equality:**
```bash
GET /api/products?name.eq=Laptop
GET /api/products?in_stock.eq=true
```

**Comparison:**
```bash
GET /api/products?price.gt=100        # Greater than
GET /api/products?price.ge=100        # Greater or equal
GET /api/products?price.lt=1000       # Less than
GET /api/products?price.le=1000       # Less or equal
GET /api/products?price.ne=0          # Not equal
```

**Pattern Matching:**
```bash
GET /api/products?name.like=laptop    # Contains (case-insensitive)
```

**IN Operator:**
```bash
GET /api/products?category.in=electronics,computers
```

**Multiple Conditions (AND):**
```bash
GET /api/products?price.gt=100&in_stock.eq=true&category.eq=electronics
```

#### Pagination

```bash
GET /api/products?@limit=10           # Return max 10 items
GET /api/products?@offset=20          # Skip first 20 items
GET /api/products?@limit=10&@offset=20  # Page 3 (items 21-30)
```

#### Ordering

```bash
GET /api/products?@order=price        # Order by price ascending
GET /api/products?@order=~price       # Order by price descending (~ prefix)
GET /api/products?@order=category     # Order by category ascending
```

#### Combined Queries

```bash
GET /api/products?price.gt=100&in_stock.eq=true&@limit=20&@order=~price
# Products over $100 that are in stock, max 20 results, ordered by price descending
```

### Response Format

**Success Response:**

```json
{
  "api_version": "1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "success",
  "code": 200,
  "count": 2,
  "total": 50,
  "offset": 0,
  "limit": 100,
  "items": [
    {
      "id": 1,
      "name": "Laptop",
      "price": 999.99,
      "in_stock": true
    },
    {
      "id": 2,
      "name": "Mouse",
      "price": 29.99,
      "in_stock": true
    }
  ]
}
```

**Error Response:**

```json
{
  "api_version": "1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "error",
  "code": 404,
  "errors": ["products with id=999 not found"]
}
```

### Filter Implementation Example

```python
class ProductResource(CRUDResource):
    async def list(self, filters, offset=0, limit=100, order_by=None):
        # Start with all products
        results = self.products[:]

        # Apply filters
        for field, conditions in filters.items():
            for operator, value in conditions.items():
                if operator == 'eq':
                    results = [p for p in results if p.get(field) == value]
                elif operator == 'ne':
                    results = [p for p in results if p.get(field) != value]
                elif operator == 'gt':
                    results = [p for p in results if p.get(field, 0) > value]
                elif operator == 'ge':
                    results = [p for p in results if p.get(field, 0) >= value]
                elif operator == 'lt':
                    results = [p for p in results if p.get(field, 0) < value]
                elif operator == 'le':
                    results = [p for p in results if p.get(field, 0) <= value]
                elif operator == 'in':
                    results = [p for p in results if p.get(field) in value]
                elif operator == 'like':
                    results = [p for p in results
                              if value.lower() in str(p.get(field, '')).lower()]

        total = len(results)

        # Apply ordering
        if order_by:
            for order in reversed(order_by):
                reverse = order.startswith('-')
                field = order[1:] if reverse else order
                results.sort(key=lambda x: x.get(field, ''), reverse=reverse)

        # Apply pagination
        return results[offset:offset+limit], total
```

---

## Complete Example

Putting it all together:

```python
from robyn import Robyn
from robyn_extensions import (
    BaseModel, Field, RestAPI, CRUDResource,
    setup_openapi_docs, setup_auth, require_auth,
    rate_limit, OIDCProviders
)

app = Robyn(__file__)

# Setup documentation
setup_openapi_docs(
    app,
    title="Products API",
    version="1.0.0"
)

# Setup authentication
setup_auth(app, AuthConfig.mock(
    public_key="your-key",
    audience="api",
    issuer="issuer"
))

# Define model
class Product(BaseModel):
    id: int | None = None
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)

# Implement resource
class ProductResource(CRUDResource):
    # ... implement CRUD methods ...
    pass

# Register API
api = RestAPI(app, prefix="/api")
api.register_resource(
    "products",
    Product,
    ProductResource(),
    policies={"GET": True, "POST": require_auth()},
    rate_limits={"GET": (100, 60)}
)

if __name__ == "__main__":
    app.start(port=8000)
```

---

## Environment Variables

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE=memory  # or redis

# Authentication
JWT_PUBLIC_KEY=your-public-key
JWT_AUDIENCE=your-api
JWT_ISSUER=https://your-issuer.com
JWKS_URL=https://your-issuer.com/.well-known/jwks.json

# OpenAPI
OPENAPI_ENABLED=true
OPENAPI_DOCS_PATH=/docs
```

---

## Error Handling

All endpoints return consistent error formats:

```python
# Validation Error (422)
{
  "status": "error",
  "code": 422,
  "errors": [
    {"field": "email", "error": "Invalid format", "type": "value_error"}
  ]
}

# Authentication Error (401)
{
  "error": "Invalid token",
  "message": "Token signature verification failed"
}

# Authorization Error (403)
{
  "error": "Insufficient permissions",
  "required_scopes": ["admin"],
  "user_scopes": ["read"]
}

# Rate Limit Error (429)
{
  "error": "Rate limit exceeded",
  "retry_after": 30
}

# Not Found (404)
{
  "api_version": "1.0",
  "status": "error",
  "code": 404,
  "errors": ["Resource not found"]
}
```

---

For more examples, see the `examples/` directory and `GETTING_STARTED.md`.
