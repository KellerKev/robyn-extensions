# Robyn Integration Guide

## Integration Strategy

This guide explains how to integrate robyn-extensions into Robyn core.

## Phase 1: Basic Integration

### 1.1 Add to Robyn's dependencies

In `robyn/Cargo.toml`:
```toml
[dependencies]
robyn_validation = { path = "../robyn-extensions/robyn_validation" }
robyn_openapi = { path = "../robyn-extensions/robyn_openapi" }
robyn_ratelimit = { path = "../robyn-extensions/robyn_ratelimit" }
robyn_auth = { path = "../robyn-extensions/robyn_auth" }
```

### 1.2 Expose in Python

In `robyn/__init__.py`:
```python
from robyn_extensions import (
    body, query, oauth, rate_limit,
    OpenAPIGenerator
)

__all__ = [..., "body", "query", "oauth", "rate_limit"]
```

### 1.3 Router Integration

Modify Robyn's router to auto-register decorated routes:

```python
class Robyn:
    def __init__(self):
        self.openapi = OpenAPIGenerator()
        
    def route(self, path, method):
        def decorator(func):
            # Auto-register with OpenAPI
            self.openapi.add_route(path, method, func)
            return func
        return decorator
```

## Phase 2: Automatic OpenAPI

### 2.1 Route Introspection

```python
class Robyn:
    def _register_openapi_routes(self):
        """Auto-register OpenAPI docs endpoints."""
        
        @self.get("/openapi.json")
        def openapi_spec(request):
            return {
                "headers": {"Content-Type": "application/json"},
                "body": self.openapi.to_json()
            }
        
        @self.get("/docs")
        def swagger_ui(request):
            return {
                "headers": {"Content-Type": "text/html"},
                "body": SWAGGER_UI_HTML.format(
                    openapi_url="/openapi.json"
                )
            }
```

### 2.2 Schema Extraction

```python
def extract_schema(handler):
    """Extract OpenAPI schema from decorated handler."""
    metadata = {}
    
    if hasattr(handler, "_body_model"):
        metadata["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": handler._body_model.model_json_schema()
                }
            }
        }
    
    if hasattr(handler, "_query_model"):
        schema = handler._query_model.model_json_schema()
        metadata["parameters"] = [
            {
                "name": name,
                "in": "query",
                "schema": prop,
                "required": name in schema.get("required", [])
            }
            for name, prop in schema["properties"].items()
        ]
    
    return metadata
```

## Phase 3: Middleware Integration

### 3.1 Rate Limiting Middleware

```python
class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app
        self.manager = RateLimitManager()
    
    async def __call__(self, request):
        # Extract handler
        handler = self.app._get_handler(request.path, request.method)
        
        # Check if rate limited
        if hasattr(handler, "_rate_limit"):
            rl = handler._rate_limit
            key = request.client_ip
            
            try:
                await self.manager.check_async(
                    f"{handler.__name__}", 
                    key
                )
            except RateLimitError as e:
                return Response(
                    status=429,
                    body={"error": str(e)},
                    headers={"Retry-After": str(e.retry_after)}
                )
        
        return await self.app(request)
```

### 3.2 OAuth Middleware

```python
class OAuthMiddleware:
    def __init__(self, app, config):
        self.app = app
        self.validator = JWTValidator(
            jwks_url=config.jwks_url,
            public_key=config.public_key,
            audience=config.audience,
            issuer=config.issuer
        )
    
    async def __call__(self, request):
        handler = self.app._get_handler(request.path, request.method)
        
        if hasattr(handler, "_oauth_config"):
            oauth_config = handler._oauth_config
            
            # Extract token
            auth_header = request.headers.get("Authorization", "")
            if not auth_header and oauth_config["required"]:
                return Response(status=401, body={"error": "Unauthorized"})
            
            if auth_header:
                token = auth_header.replace("Bearer ", "")
                try:
                    claims = await self.validator.validate(token)
                    request.user = claims
                except AuthError as e:
                    if oauth_config["required"]:
                        return Response(status=401, body={"error": str(e)})
        
        return await self.app(request)
```

## Phase 4: Configuration

### 4.1 App Config

```python
class RobynConfig:
    def __init__(self):
        self.oauth = OAuthConfig()
        self.rate_limit = RateLimitConfig()
        self.openapi = OpenAPIConfig()

class Robyn:
    def __init__(self):
        self.config = RobynConfig()
        
    def start(self):
        # Apply middleware
        self.add_middleware(RateLimitMiddleware(self))
        if self.config.oauth.enabled:
            self.add_middleware(OAuthMiddleware(self, self.config.oauth))
        
        # Register OpenAPI routes
        self._register_openapi_routes()
        
        # Start server
        super().start()
```

### 4.2 Environment Variables

```python
import os

class RobynConfig:
    def __init__(self):
        self.oauth = OAuthConfig(
            jwks_url=os.getenv("OAUTH_JWKS_URL"),
            audience=os.getenv("OAUTH_AUDIENCE"),
            issuer=os.getenv("OAUTH_ISSUER")
        )
```

## Phase 5: Testing

### 5.1 Integration Tests

```python
# tests/test_validation.py
def test_body_validation():
    app = Robyn()
    
    @app.post("/users")
    @body(UserModel)
    def create_user(request, user):
        return {"name": user.name}
    
    response = app.test_client.post(
        "/users",
        json={"name": "Alice", "age": 30}
    )
    assert response.status_code == 200
```

### 5.2 Performance Tests

```python
import pytest
from locust import HttpUser, task

class APIUser(HttpUser):
    @task
    def test_rate_limit(self):
        for _ in range(20):
            self.client.get("/api")
```

## Phase 6: Documentation

### 6.1 User Guide

Add to Robyn docs:
- Getting Started with Validation
- Adding Authentication
- Rate Limiting Best Practices
- Generating OpenAPI Docs

### 6.2 API Reference

Generate from docstrings:
```bash
pdoc robyn_extensions --html --output-dir docs/
```

## Migration Path

### From existing Robyn apps:

```python
# Before
@app.post("/users")
def create_user(request):
    data = json.loads(request.body)
    # Manual validation
    if not data.get("name"):
        return {"error": "name required"}
    return {"name": data["name"]}

# After
@app.post("/users")
@body(UserModel)
def create_user(request, user: UserModel):
    return {"name": user.name}
```

## Performance Impact

- Validation: +50-100μs per request
- Rate limiting: +10-50μs per request
- OAuth: +200-500μs per request (with cache)
- OpenAPI: One-time generation at startup

## Backward Compatibility

All changes are opt-in via decorators. Existing Robyn apps continue to work unchanged.

## Future Work

1. WebSocket support for @oauth decorator
2. GraphQL schema generation
3. Request/response logging decorators
4. Built-in caching decorators
5. API versioning support
