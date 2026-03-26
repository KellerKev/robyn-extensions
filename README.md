# Robyn Extensions

FastAPI-like validation, OpenAPI docs, rate limiting, and JWT/OAuth authentication for the [Robyn](https://robyn.tech) web framework — with Rust-powered performance.

## What This Solves

Robyn is a fast, Rust-backed Python web framework, but it lacks the developer-experience features that make FastAPI productive. This project adds:

- **Request validation** — Pydantic v2-compatible `BaseModel` with type coercion, nested models, field constraints
- **OpenAPI documentation** — Auto-generated Swagger UI (`/docs`) and ReDoc (`/redoc`)
- **Rate limiting** — Token bucket algorithm, per-IP/per-user, configurable presets
- **Authentication** — JWT validation, JWKS caching, OAuth2/OIDC with pre-configured providers (Auth0, Google, Okta, Azure AD)
- **REST API generator** — CRUD boilerplate elimination with filtering, pagination, sorting

All performance-critical operations run in Rust via PyO3:
- Validation: <1us per field
- Rate limiting: ~100ns overhead
- JWT validation: ~500us (with JWKS cache)

## Installation

```bash
# Clone and install dependencies
pixi install

# Build the Rust extension
pixi run develop

# Install Python package in development mode
pixi run pip install -e .

# Run tests
pixi run test          # Python tests (19 tests)
pixi run test-rust     # Rust tests (12 tests)
```

## Architecture

```
Request --> Python Decorators --> Rust Backends --> Handler
                 |                    |
            @body_v2()          robyn_validation (field/schema validation)
            @rate_limit()       robyn_ratelimit  (token bucket + DashMap)
            @require_auth()     robyn_auth       (JWT + JWKS caching)
                 |
            Auto-generated OpenAPI spec --> /docs, /redoc
```

### Rust Crates

| Crate | Purpose |
|---|---|
| `robyn_validation` | Field validation with 15+ rule types |
| `robyn_openapi` | OpenAPI 3.0.3 spec generation, Swagger UI, ReDoc |
| `robyn_ratelimit` | Token bucket rate limiting with DashMap |
| `robyn_auth` | JWT/JWKS validation, OAuth2, OIDC provider support |
| `robyn_python` | PyO3 bindings connecting everything to Python |

### Python Modules

| Module | Purpose |
|---|---|
| `models.py` | Pydantic v2-compatible BaseModel (type coercion, validators, computed fields) |
| `decorators_v2.py` | `@body()`, `@validated_route`, `@returns()` |
| `easy_auth.py` | `@require_auth()`, `@require_scope()`, OIDC provider setup |
| `ratelimit.py` | `@rate_limit()` with presets (strict, moderate, permissive) |
| `restapi.py` | CRUD resource generator with policies |
| `openapi_docs.py` | Swagger UI / ReDoc endpoint setup |

---

## Features & Usage

### 1. Request Validation (Pydantic v2-compatible Models)

Define models with type annotations and field constraints, just like Pydantic v2:

```python
from robyn_extensions import BaseModel, Field

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str = Field(regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(ge=18, le=120)
    bio: str = Field(default="", description="User biography")

# Validate data
user = UserCreate(username="alice", email="alice@example.com", age=25)
print(user.model_dump())        # {"username": "alice", "email": "alice@example.com", "age": 25, "bio": ""}
print(user.model_dump_json())   # JSON string
print(UserCreate.model_json_schema())  # OpenAPI-compatible JSON Schema
```

**Supported field constraints:** `min_length`, `max_length`, `gt`, `ge`, `lt`, `le`, `regex`, `default`, `alias`, `description`

#### Computed Fields

```python
class FullUser(BaseModel):
    first_name: str
    last_name: str

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

user = FullUser(first_name="Alice", last_name="Smith")
user.model_dump()  # {"first_name": "Alice", "last_name": "Smith", "full_name": "Alice Smith"}
```

#### Field Validators

```python
from robyn_extensions import field_validator, model_validator

class SecureUser(BaseModel):
    username: str
    password: str
    password_confirm: str

    @field_validator('username')
    @classmethod
    def no_admin(cls, v):
        if 'admin' in v.lower():
            raise ValueError('Username cannot contain "admin"')
        return v

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self
```

#### Type Coercion

The `BaseModel` automatically coerces compatible types:

```python
class Item(BaseModel):
    count: int
    price: float
    active: bool

# All of these work:
Item(count="42", price="9.99", active="true")
Item(count=42.0, price=10, active=1)
```

Supported types: `str`, `int`, `float`, `bool`, `datetime`, `date`, `Optional[T]`, `List[T]`, `Dict[K, V]`, nested `BaseModel`, `Enum`

---

### 2. Request Body & Query Validation Decorators

#### `@body` / `@body_v2` — Validate request bodies

```python
from robyn import Robyn, Request
from robyn_extensions import body_v2, BaseModel, Field

app = Robyn(__file__)

class CreateItem(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    quantity: int = Field(ge=0, default=1)

@app.post("/items")
@body_v2(CreateItem)
def create_item(request: Request, item: CreateItem):
    return {"id": 1, **item.model_dump()}
```

Invalid requests get a `422` response with error details:

```json
{
  "error": "Validation failed",
  "details": [
    {"field": "price", "message": "Value must be greater than 0", "type": "gt"}
  ]
}
```

#### `@validated_route` — Auto-discover models from type hints

```python
from robyn_extensions import validated_route

@app.post("/items")
@validated_route
def create_item(request: Request, item: CreateItem):
    return item  # Auto-serialized to JSON
```

#### `@query` — Validate query parameters

```python
from robyn_extensions import query

class SearchParams(BaseModel):
    q: str = Field(min_length=1)
    page: int = Field(ge=1, default=1)
    limit: int = Field(ge=1, le=100, default=20)

@app.get("/search")
@query(SearchParams)
def search(request, params: SearchParams):
    return {"query": params.q, "page": params.page}
```

#### `@returns` — Auto-serialize response models

```python
from robyn_extensions import returns

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float

@app.get("/items/:id")
@returns(ItemResponse)
def get_item(request: Request):
    return ItemResponse(id=1, name="Widget", price=9.99)
    # Automatically serialized to JSON with Content-Type header
```

---

### 3. Rate Limiting

Rust-powered token bucket rate limiting with per-key tracking:

```python
from robyn_extensions import rate_limit, RateLimitConfig

# Basic: 100 requests per minute per IP
@app.get("/api/data")
@rate_limit(requests=100, per_seconds=60)
def get_data(request):
    return {"data": "..."}

# Per-user rate limiting
@app.get("/api/profile")
@rate_limit(
    requests=50,
    per_seconds=60,
    key_func=lambda r: r.headers.get("user_id", "anonymous")
)
def get_profile(request):
    return {"profile": "..."}
```

**Presets** for common patterns:

```python
from robyn_extensions import strict, moderate, permissive, api_standard

@app.get("/login")
@strict()           # 10 req/min — login, password reset
def login(request): ...

@app.get("/api/items")
@moderate()          # 60 req/min — standard API endpoints
def list_items(request): ...

@app.get("/api/search")
@permissive()        # 100 req/min — read-heavy endpoints
def search(request): ...

@app.get("/api/bulk")
@api_standard()      # 1000 req/hour — bulk operations
def bulk_export(request): ...
```

**Specialized limiters:**

```python
from robyn_extensions import rate_limit_per_user, rate_limit_per_ip, rate_limit_global

@app.get("/api/me")
@rate_limit_per_user(requests=50, per_seconds=60, user_key="user_id")
def my_profile(request): ...

@app.get("/api/public")
@rate_limit_per_ip(requests=60, per_seconds=60)
def public_data(request): ...

@app.get("/api/health")
@rate_limit_global(requests=1000, per_seconds=60)
def health_check(request): ...
```

When rate limited, clients receive a `429` response with a `Retry-After` header.

---

### 4. Authentication (JWT / OAuth2 / OIDC)

#### Quick Setup with Pre-configured Providers

```python
from robyn_extensions import setup_auth, AuthConfig, require_auth

# Auth0
setup_auth(AuthConfig.auth0(
    domain="your-app.auth0.com",
    audience="https://your-api.example.com"
))

# Google
setup_auth(AuthConfig.google(client_id="your-client-id.apps.googleusercontent.com"))

# Okta
setup_auth(AuthConfig.okta(domain="your-org.okta.com", audience="your-api"))
```

Other supported providers: **Azure AD**, **Keycloak**, **AWS Cognito** (via `OIDCProviders` helper).

#### Protecting Routes

```python
# Require any valid token
@app.get("/api/protected")
@require_auth()
def protected(request):
    user_id = request.user.sub  # JWT subject claim
    return {"user": user_id}

# Require specific scopes
@app.post("/api/admin/users")
@require_auth(scopes=["admin", "write"], require_all_scopes=True)
def admin_create(request):
    return {"created": True}
```

**Convenience decorators:**

```python
from robyn_extensions import (
    require_scope, require_any_scope, require_all_scopes,
    admin_required, read_required, write_required, delete_required,
    optional_auth
)

@app.delete("/api/items/:id")
@admin_required()
def delete_item(request): ...

@app.get("/api/items/:id")
@read_required()
def get_item(request): ...

# Optional auth — works for both logged-in and anonymous users
@app.get("/api/feed")
@optional_auth()
def feed(request):
    if hasattr(request, 'user'):
        return {"feed": "personalized", "user": request.user.sub}
    return {"feed": "default"}
```

#### Manual Configuration

```python
# From JWKS URL
setup_auth(AuthConfig.from_jwks(
    jwks_url="https://your-provider.com/.well-known/jwks.json",
    audience="your-api",
    issuer="https://your-provider.com/"
))

# From RSA public key
setup_auth(AuthConfig.from_public_key(
    public_key=open("public_key.pem").read(),
    audience="your-api"
))
```

---

### 5. OpenAPI Documentation (Swagger UI & ReDoc)

#### Automatic Setup

```python
from robyn_extensions import AutoDocs

app = Robyn(__file__)
docs = AutoDocs(
    app,
    title="My API",
    version="1.0.0",
    description="API with automatic documentation"
)

@app.post("/users")
@body_v2(UserCreate)
def create_user(request, user: UserCreate):
    '''Create a new user account'''
    return user.model_dump()

# Documentation is served automatically:
#   GET /docs        -> Swagger UI
#   GET /redoc       -> ReDoc
#   GET /openapi.json -> Raw OpenAPI spec
```

#### Manual Route Documentation

```python
from robyn_extensions import setup_openapi_docs

docs = setup_openapi_docs(app, title="My API", version="2.0.0")

@app.get("/items")
@docs.route(
    summary="List all items",
    description="Returns paginated list of items with optional filtering",
    tags=["Items"],
    response_model=ItemList
)
@query(SearchParams)
def list_items(request, params: SearchParams):
    return {"items": [...]}
```

---

### 6. REST API Generator

Auto-generate full CRUD endpoints with filtering, pagination, and sorting:

```python
from robyn_extensions import RestAPI, CRUDResource, BaseModel, Field
from robyn_extensions import require_auth, admin_required

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)
    category: str

class ProductResource(CRUDResource):
    def __init__(self):
        self.db = {}
        self.next_id = 1

    async def list(self, filters, offset=0, limit=100, order_by=None):
        items = list(self.db.values())
        return items[offset:offset+limit], len(items)

    async def get(self, id):
        return self.db.get(str(id))

    async def create(self, data):
        item = {**data, "id": self.next_id}
        self.db[str(self.next_id)] = item
        self.next_id += 1
        return item

    async def update(self, id, data):
        if str(id) in self.db:
            self.db[str(id)].update(data)
            return self.db[str(id)]
        return None

    async def delete(self, id):
        return self.db.pop(str(id), None) is not None

# Register the resource
api = RestAPI(app, prefix="/api/v1")
api.register_resource(
    "products",
    Product,
    ProductResource(),
    policies={
        "GET": True,                  # Public read access
        "POST": require_auth(),       # Auth required to create
        "PUT": require_auth(),        # Auth required to update
        "DELETE": admin_required(),   # Admin only
    },
    rate_limits={
        "GET": (100, 60),            # 100 reads/min
        "POST": (10, 60),            # 10 creates/min
    },
    tags=["Products"]
)
```

This auto-generates:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/products` | List with filtering & pagination |
| `GET` | `/api/v1/products/:id` | Get single product |
| `POST` | `/api/v1/products` | Create product |
| `PUT` | `/api/v1/products/:id` | Update product |
| `DELETE` | `/api/v1/products/:id` | Delete product |

**Filtering & pagination** (PyDAL-style query syntax):

```
GET /api/v1/products?category.eq=electronics&price.gt=10&@limit=20&@offset=0&@order=price
GET /api/v1/products?name.like=widget&price.le=100&@order=~price   # ~price = descending
GET /api/v1/products?status.in=active,featured&name.starts_with=Pro
```

Supported operators: `eq`, `ne`, `gt`, `ge`, `lt`, `le`, `in`, `like`, `contains`, `starts_with`, `ends_with`

---

### 7. Rust-backed Validator (Low-level API)

For direct access to the Rust validation engine:

```python
from robyn_extensions import Validator, ValidationError

validator = Validator()
validator.add_field("email", ["required", "email"])
validator.add_field("username", ["required", "min_length:3", "max_length:20"])
validator.add_field("age", ["required", "ge:18", "le:120"])
validator.add_field("website", ["url"])

errors = validator.validate({"email": "bad", "username": "ab", "age": 15})
for err in errors:
    print(f"{err.field}: {err.message} ({err.error_type})")

# Also validates JSON strings directly:
errors = validator.validate_json('{"email": "test@example.com", "username": "alice", "age": 25}')
```

**Available rules:** `required`, `email`, `url`, `min_length:N`, `max_length:N`, `min:N`, `max:N`, `gt:N`, `ge:N`, `lt:N`, `le:N`, `multiple_of:N`, `pattern:REGEX`, `contains:STR`, `starts_with:STR`, `ends_with:STR`

---

## Complete Example

```python
from robyn import Robyn, Request
from robyn_extensions import (
    BaseModel, Field, body_v2, returns, rate_limit, query,
    setup_auth, AuthConfig, require_auth, optional_auth,
    AutoDocs, computed_field, field_validator,
)

app = Robyn(__file__)

# Setup auth (optional — only if using authentication)
# setup_auth(AuthConfig.auth0(domain="your-app.auth0.com", audience="your-api"))

# Setup auto-documentation
docs = AutoDocs(app, title="My API", version="1.0.0")

# --- Models ---

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str = Field(regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(ge=18)

    @field_validator('username')
    @classmethod
    def no_reserved(cls, v):
        if v.lower() in ('admin', 'root', 'system'):
            raise ValueError('Reserved username')
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

class SearchParams(BaseModel):
    q: str = Field(default="")
    page: int = Field(ge=1, default=1)
    limit: int = Field(ge=1, le=100, default=20)

# --- Routes ---

@app.post("/users")
@body_v2(UserCreate)
@rate_limit(requests=10, per_seconds=60)
def create_user(request: Request, user: UserCreate):
    '''Create a new user'''
    return UserResponse(id=1, username=user.username, email=user.email).model_dump()

@app.get("/users")
@query(SearchParams)
@rate_limit(requests=100, per_seconds=60)
def list_users(request, params: SearchParams):
    '''Search and list users'''
    return {"users": [], "page": params.page, "limit": params.limit}

@app.get("/users/:id")
@returns(UserResponse)
def get_user(request: Request):
    '''Get a user by ID'''
    return UserResponse(id=1, username="alice", email="alice@example.com")

if __name__ == "__main__":
    app.start(port=8080)
```

## License

MIT License - Kevin Keller (https://kevinkeller.org)
