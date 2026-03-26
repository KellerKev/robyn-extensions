# Getting Started with Robyn Extensions

A comprehensive guide to testing and using the Robyn Extensions framework with all its features.

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Quick Start Examples](#quick-start-examples)
3. [Testing Each Feature](#testing-each-feature)
4. [Building Your First API](#building-your-first-api)
5. [Troubleshooting](#troubleshooting)

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- pixi (package manager) - [Install here](https://prefix.dev/)

### Setup Steps

```bash
# Clone/navigate to the project
cd robyn-extensions

# Install dependencies with pixi
pixi install

# Build the Rust extensions
pixi run maturin develop

# Verify installation
pixi run python -c "from robyn_extensions import *; print('✅ All imports successful')"
```

---

## Quick Start Examples

### 1. Basic Pydantic Validation

**File**: `test_basic.py`

```python
from robyn import Robyn
from robyn_extensions import BaseModel, Field
import json

app = Robyn(__file__)

class User(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: int = Field(..., ge=0, le=150)

@app.post("/users")
def create_user(request):
    try:
        user = User(**json.loads(request.body))
        return json.dumps({
            "success": True,
            "user": user.dict()
        })
    except Exception as e:
        return json.dumps({"error": str(e)}), 400

if __name__ == "__main__":
    app.start(port=8080)
```

**Test it:**

```bash
# Start server
pixi run python test_basic.py

# Valid request
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com", "age": 30}'

# Invalid email
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Bob", "email": "invalid-email", "age": 25}'
```

---

## Testing Each Feature

### Feature 1: Pydantic Models & Validation

Run the comprehensive test:

```bash
pixi run python pydantic_app.py
```

**Test endpoints:**

```bash
# Valid user creation
curl -X POST http://localhost:8081/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@test.com", "age": 30, "tags": ["python", "rust"]}'

# Missing required field
curl -X POST http://localhost:8081/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Bob"}'

# Invalid age
curl -X POST http://localhost:8081/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Charlie", "email": "charlie@test.com", "age": 200}'

# Get user (should fail - not implemented)
curl http://localhost:8081/api/users/1
```

**Expected behavior:**
- ✅ Valid requests return user data with generated ID
- ❌ Invalid requests return 422 with detailed validation errors
- Each error shows field name, error type, and helpful message

---

### Feature 2: OpenAPI Documentation

Run the autodocs example:

```bash
pixi run python rust_autodocs_example.py
```

**Access the docs:**

```bash
# Open in browser
open http://localhost:8082/docs

# Or view raw OpenAPI spec
curl http://localhost:8082/openapi.json | jq
```

**What to check:**
- Interactive Swagger UI at `/docs`
- All endpoints listed with methods (GET, POST, etc.)
- Request/response schemas shown
- Try executing requests directly from the UI

**Test endpoints from docs UI:**
1. Click on `/api/users` POST
2. Click "Try it out"
3. Enter test data
4. Click "Execute"
5. See response below

---

### Feature 3: Authentication & Authorization

Run the auth example:

```bash
pixi run python auth_example.py
```

**Get test tokens:**

```bash
# Read available test tokens
cat /tmp/test_tokens.json | jq
```

**Test authentication:**

```bash
# Public endpoint (no token needed)
curl http://localhost:8083/api/public

# Protected endpoint (requires any valid token)
curl http://localhost:8083/api/protected \
  -H "Authorization: Bearer $(cat /tmp/test_tokens.json | jq -r .read_only)"

# Admin endpoint (requires admin scope)
curl http://localhost:8083/api/admin \
  -H "Authorization: Bearer $(cat /tmp/test_tokens.json | jq -r .admin)"

# Try admin endpoint with read-only token (should fail)
curl http://localhost:8083/api/admin \
  -H "Authorization: Bearer $(cat /tmp/test_tokens.json | jq -r .read_only)"

# Expired token (should fail)
curl http://localhost:8083/api/protected \
  -H "Authorization: Bearer $(cat /tmp/test_tokens.json | jq -r .expired)"
```

**Expected responses:**
- Public: Always works
- Protected: Works with any valid token
- Admin: Only works with tokens having "admin" scope
- Expired: Returns 401 with "Token expired" error

---

### Feature 4: Rate Limiting

Run the rate limit example:

```bash
pixi run python ratelimit_example.py
```

**Test rate limits:**

```bash
# Public endpoint (100 requests per minute)
for i in {1..5}; do
  echo "Request $i:"
  curl -s http://localhost:8086/api/public | jq .request_count
done

# Try to exceed limit (make 105 requests quickly)
for i in {1..105}; do
  curl -s http://localhost:8086/api/public > /dev/null
done
# Should get rate limited around request 101

# Strict endpoint (3 requests per 10 seconds)
for i in {1..5}; do
  echo "Request $i:"
  curl http://localhost:8086/api/strict
  sleep 1
done
# Should fail on 4th request

# Check rate limit with different IPs
curl http://localhost:8086/api/per-ip -H "X-Forwarded-For: 1.2.3.4"
curl http://localhost:8086/api/per-ip -H "X-Forwarded-For: 5.6.7.8"
```

**Expected behavior:**
- Requests return with headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`
- When limit exceeded: 429 status with retry-after time
- Different rate limits per endpoint

---

### Feature 5: REST API Generator (PyDAL-style)

Run the REST API example:

```bash
pixi run python restapi_example.py
```

**Test CRUD operations:**

```bash
# List all users
curl http://localhost:8085/api/users | jq

# Get specific user
curl http://localhost:8085/api/users/1 | jq

# Create new user (requires auth - will fail)
curl -X POST http://localhost:8085/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "David", "email": "david@test.com", "age": 28, "role": "user"}'

# Filtering - users with role=admin
curl "http://localhost:8085/api/users?role.eq=admin" | jq

# List all posts
curl http://localhost:8085/api/posts | jq

# Get specific post
curl http://localhost:8085/api/posts/1 | jq
```

**Query syntax examples:**

```bash
# Equality
curl "http://localhost:8085/api/users?role.eq=admin"

# Greater than
curl "http://localhost:8085/api/users?age.gt=25"

# Less than or equal
curl "http://localhost:8085/api/users?age.le=30"

# LIKE (contains)
curl "http://localhost:8085/api/users?name.like=ali"

# Multiple conditions
curl "http://localhost:8085/api/users?age.gt=25&role.eq=user"

# Pagination
curl "http://localhost:8085/api/users?@limit=10&@offset=0"

# Ordering
curl "http://localhost:8085/api/users?@order=age"        # ascending
curl "http://localhost:8085/api/users?@order=~age"       # descending

# Combined
curl "http://localhost:8085/api/users?age.gt=25&@limit=5&@order=name"
```

---

## Building Your First API

### Step 1: Create Your Model

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

### Step 2: Implement CRUD Resource

```python
from robyn_extensions import CRUDResource

class ProductResource(CRUDResource):
    def __init__(self):
        self.products = []
        self.next_id = 1

    async def list(self, filters, offset=0, limit=100, order_by=None):
        # Apply filters
        results = self.products[:]
        for field, conditions in filters.items():
            for op, value in conditions.items():
                if op == 'eq':
                    results = [p for p in results if p.get(field) == value]
                elif op == 'gt':
                    results = [p for p in results if p.get(field, 0) > value]
                # Add more operators as needed

        # Pagination
        total = len(results)
        return results[offset:offset+limit], total

    async def get(self, id):
        for product in self.products:
            if product['id'] == int(id):
                return product
        return None

    async def create(self, data):
        product = data.copy()
        product['id'] = self.next_id
        product['created_at'] = datetime.utcnow().isoformat() + 'Z'
        self.next_id += 1
        self.products.append(product)
        return product

    async def update(self, id, data):
        for i, product in enumerate(self.products):
            if product['id'] == int(id):
                self.products[i].update(data)
                return self.products[i]
        return None

    async def delete(self, id):
        for i, product in enumerate(self.products):
            if product['id'] == int(id):
                del self.products[i]
                return True
        return False
```

### Step 3: Register API

```python
from robyn import Robyn
from robyn_extensions import RestAPI, require_auth, admin_required

app = Robyn(__file__)
api = RestAPI(app, prefix="/api", version="1.0")

api.register_resource(
    "products",
    Product,
    ProductResource(),
    policies={
        "GET": True,                  # Public read
        "POST": require_auth(),       # Create requires auth
        "PUT": require_auth(),        # Update requires auth
        "DELETE": admin_required(),   # Delete requires admin
    },
    rate_limits={
        "GET": (100, 60),    # 100 requests per minute
        "POST": (10, 60),    # 10 requests per minute
    },
    tags=["Products"]
)

if __name__ == "__main__":
    print("✅ Products API registered")
    print("   GET    /api/products       - List all products")
    print("   GET    /api/products/:id   - Get product by ID")
    print("   POST   /api/products       - Create product")
    print("   PUT    /api/products/:id   - Update product")
    print("   DELETE /api/products/:id   - Delete product")
    app.start(port=8000)
```

### Step 4: Test Your API

```bash
# Start server
pixi run python your_app.py

# Create product
curl -X POST http://localhost:8000/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop",
    "price": 999.99,
    "description": "High-performance laptop",
    "in_stock": true
  }'

# List products
curl http://localhost:8000/api/products | jq

# Filter by price
curl "http://localhost:8000/api/products?price.gt=500" | jq

# Get specific product
curl http://localhost:8000/api/products/1 | jq
```

---

## Complete Feature Example

Combine all features in one app:

```python
from robyn import Robyn
from robyn_extensions import (
    BaseModel, Field, RestAPI, CRUDResource,
    setup_openapi_docs, setup_auth, require_auth,
    rate_limit, OIDCProviders
)

app = Robyn(__file__)

# Setup OpenAPI docs
setup_openapi_docs(
    app,
    title="My API",
    version="1.0.0",
    description="Full-featured API with all extensions"
)

# Setup authentication
setup_auth(app, OIDCProviders.Auth0(
    client_id="your-client-id",
    client_secret="your-secret",
    domain="your-domain.auth0.com"
))

# Define model
class Task(BaseModel):
    id: int | None = None
    title: str = Field(..., min_length=1)
    completed: bool = False

# Implement resource
class TaskResource(CRUDResource):
    def __init__(self):
        self.tasks = []
        self.next_id = 1

    async def list(self, filters, offset=0, limit=100, order_by=None):
        return self.tasks[offset:offset+limit], len(self.tasks)

    async def get(self, id):
        return next((t for t in self.tasks if t['id'] == int(id)), None)

    async def create(self, data):
        task = data.copy()
        task['id'] = self.next_id
        self.next_id += 1
        self.tasks.append(task)
        return task

    async def update(self, id, data):
        task = await self.get(id)
        if task:
            task.update(data)
        return task

    async def delete(self, id):
        self.tasks = [t for t in self.tasks if t['id'] != int(id)]
        return True

# Register REST API
api = RestAPI(app, prefix="/api")
api.register_resource(
    "tasks",
    Task,
    TaskResource(),
    policies={
        "GET": True,
        "POST": require_auth(),
        "PUT": require_auth(),
        "DELETE": require_auth(),
    },
    rate_limits={
        "GET": (100, 60),
        "POST": (10, 60),
    }
)

# Add custom endpoint with rate limiting
@app.get("/health")
@rate_limit(requests=1000, per_seconds=60)
def health(request):
    return {"status": "healthy"}

if __name__ == "__main__":
    app.start(port=8000)
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8080
lsof -i :8080

# Kill process
kill -9 <PID>

# Or use a different port
pixi run python your_app.py --port 8090
```

### Import Errors

```bash
# Rebuild Rust extensions
pixi run maturin develop --release

# Verify installation
pixi run python -c "from robyn_extensions import *"
```

### Validation Not Working

- Check that you're using `BaseModel` from `robyn_extensions`, not pydantic
- Ensure field constraints are properly defined with `Field(...)`
- Look for validation errors in the response body

### Rate Limiting Not Triggering

- Check that you're making requests fast enough
- Verify rate limit config: `rate_limit(requests=N, per_seconds=S)`
- Look for `X-RateLimit-*` headers in response

### Authentication Failing

- Verify JWT token is properly formatted
- Check token hasn't expired
- Ensure token has required scopes
- Use test tokens from `/tmp/test_tokens.json` for testing

### REST API 500 Errors

- Check that CRUD methods are properly implemented
- Ensure async/await is used correctly
- Verify query parameter parsing
- Check server logs for detailed error messages

---

## Next Steps

1. **Integrate with a Database**: Replace in-memory storage with SQLAlchemy, Tortoise ORM, or PyMongo
2. **Add Custom Middleware**: Implement logging, CORS, request tracing
3. **Deploy**: Use Docker, systemd, or cloud platforms
4. **Monitor**: Add metrics, logging, health checks
5. **Secure**: Add HTTPS, CSRF protection, input sanitization

---

## Additional Resources

- [Robyn Documentation](https://robyn.tech/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [JWT.io](https://jwt.io/) - Debug JWT tokens
- [Example Apps](./examples/) - More complete examples

---

## Quick Reference Card

### Validation

```python
from robyn_extensions import BaseModel, Field

class Model(BaseModel):
    field: str = Field(..., min_length=1, max_length=100)
    number: int = Field(..., ge=0, le=100)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
```

### Authentication

```python
from robyn_extensions import require_auth, require_scope, admin_required

@app.get("/protected")
@require_auth()
def protected(request):
    return {"user": request.user}

@app.post("/admin")
@admin_required()
def admin(request):
    return {"action": "admin operation"}
```

### Rate Limiting

```python
from robyn_extensions import rate_limit

@app.get("/api/data")
@rate_limit(requests=100, per_seconds=60)
def data(request):
    return {"data": "..."}
```

### REST API

```python
from robyn_extensions import RestAPI, CRUDResource

api = RestAPI(app, prefix="/api")
api.register_resource("items", ItemModel, ItemResource(), policies={...})
```

---

**Happy coding! 🚀**
