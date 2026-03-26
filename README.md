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

## Quick Start

```bash
# Install dependencies and build
pixi install
pixi run develop

# Install Python package
pixi run pip install -e .

# Run tests
pixi run cargo test          # Rust tests
pixi run pytest test_advanced_features.py test_pydantic_parity.py -v  # Python tests
```

## Usage

```python
from robyn import Robyn, Request
from robyn_extensions import BaseModel, Field, body_v2, rate_limit, require_auth

app = Robyn(__file__)

class User(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str
    age: int = Field(ge=18, le=120)

@app.post("/users")
@body_v2(User)
@rate_limit(requests=100, per_seconds=60)
def create_user(request: Request, user: User):
    return user.model_dump_json()

app.start(port=8080)
```

## Architecture

```
Request → Python Decorators → Rust Backends → Handler
              │                    │
         @body_v2()          robyn_validation (field/schema validation)
         @rate_limit()       robyn_ratelimit  (token bucket + DashMap)
         @require_auth()     robyn_auth       (JWT + JWKS caching)
              │
         Auto-generated OpenAPI spec → /docs, /redoc
```

### Rust Crates

| Crate | Purpose |
|---|---|
| `robyn_validation` | Field validation with 19+ rule types |
| `robyn_openapi` | OpenAPI 3.0.3 spec generation, Swagger UI, ReDoc |
| `robyn_ratelimit` | Governor-based rate limiting with DashMap |
| `robyn_auth` | JWT/JWKS validation, OAuth2, OIDC provider support |
| `robyn_python` | PyO3 bindings connecting everything to Python |

### Python Layer

| Module | Purpose |
|---|---|
| `models.py` | Pydantic v2-compatible BaseModel (type coercion, validators, computed fields) |
| `decorators_v2.py` | `@body()`, `@validated_route`, `@returns()` |
| `easy_auth.py` | `@require_auth()`, `@require_scope()`, OIDC provider setup |
| `ratelimit.py` | `@rate_limit()` with presets (strict, moderate, permissive) |
| `restapi.py` | CRUD resource generator with policies |
| `openapi_docs.py` | Swagger UI / ReDoc endpoint setup |

## Documentation

- [Getting Started](GETTING_STARTED.md)
- [API Reference](API_REFERENCE.md)
- [Authentication Guide](AUTHENTICATION.md)
- [Rate Limiting Guide](RATE_LIMITING.md)
- [Pydantic v2 Compatibility](PYDANTIC_V2_COMPLETE.md)
- [Rust OpenAPI Architecture](RUST_OPENAPI.md)
- [Integration with Robyn Core](INTEGRATION.md)

## License

MIT License - Kevin Keller (https://kevinkeller.org)
