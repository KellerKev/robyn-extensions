#!/usr/bin/env python3
"""
Robyn app with Pydantic v2-compatible syntax
Drop-in replacement demonstration
"""

import sys
sys.path.insert(0, 'robyn_python/python')

from robyn import Robyn, Request
from robyn_extensions import BaseModel, Field, validated_route, body_v2, returns
from typing import Optional, List
from datetime import datetime

app = Robyn(__file__)

# ============================================================================
# PYDANTIC-STYLE MODELS (Drop-in compatible syntax!)
# ============================================================================

class Address(BaseModel):
    """Nested model for address"""
    street: str
    city: str
    country: str = "USA"
    zip_code: Optional[str] = None


class UserCreate(BaseModel):
    """Model for creating a user - Pydantic v2 compatible!"""
    username: str = Field(min_length=3, max_length=20)
    email: str
    age: int = Field(ge=18, le=120)
    is_active: bool = True
    tags: List[str] = []
    address: Optional[Address] = None


class UserResponse(BaseModel):
    """Model for user response"""
    id: int
    username: str
    email: str
    age: int
    is_active: bool
    tags: List[str]
    address: Optional[Address]
    created_at: str


class ProductCreate(BaseModel):
    """Product creation model"""
    name: str = Field(min_length=2)
    description: Optional[str] = None
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    tags: List[str] = []
    sku: str = Field(regex=r"^[A-Z]{3}-\d{4}$")


class ProductResponse(BaseModel):
    """Product response model"""
    id: int
    name: str
    description: Optional[str]
    price: float
    stock: int
    tags: List[str]
    sku: str


# ============================================================================
# AUTOMATIC VALIDATION ROUTES (FastAPI-style!)
# ============================================================================

# Simulated database
users_db = []
products_db = []
next_user_id = 1
next_product_id = 1


@app.get("/")
def index(request: Request):
    return """
    <html>
    <head><title>Pydantic-Compatible Robyn API</title></head>
    <body>
        <h1>🚀 Pydantic v2-Compatible API for Robyn</h1>
        <h2>Available Endpoints:</h2>
        <ul>
            <li><b>POST /users</b> - Create user (automatic validation)</li>
            <li><b>GET /users/{id}</b> - Get user by ID</li>
            <li><b>POST /products</b> - Create product</li>
            <li><b>GET /products/{id}</b> - Get product by ID</li>
        </ul>

        <h3>Example: Create User</h3>
        <pre>
curl -X POST http://localhost:8080/users \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "age": "25",
    "tags": ["python", "rust"],
    "address": {
      "street": "123 Main St",
      "city": "NYC",
      "country": "USA"
    }
  }'
        </pre>

        <h3>Features Demonstrated:</h3>
        <ul>
            <li>✅ Type coercion (age as string -> int)</li>
            <li>✅ Nested models (Address)</li>
            <li>✅ Optional fields</li>
            <li>✅ Default values</li>
            <li>✅ List types</li>
            <li>✅ Field validation (min_length, ge, gt, regex)</li>
            <li>✅ Automatic serialization</li>
        </ul>
    </body>
    </html>
    """


@app.post("/users")
@body_v2(UserCreate)
def create_user(request: Request, user: UserCreate):
    """
    Create a new user - automatic validation!
    Just like FastAPI: def create_user(user: UserCreate)
    """
    global next_user_id

    # Create response
    user_response = UserResponse(
        id=next_user_id,
        username=user.username,
        email=user.email,
        age=user.age,
        is_active=user.is_active,
        tags=user.tags,
        address=user.address,
        created_at=datetime.now().isoformat()
    )

    users_db.append(user_response.model_dump())
    next_user_id += 1

    # Automatic serialization!
    return user_response.model_dump_json()


@app.get("/users/:id")
def get_user(request: Request):
    """Get user by ID"""
    user_id = int(request.path_params.get("id"))

    for user in users_db:
        if user["id"] == user_id:
            return UserResponse(**user).model_dump_json()

    return {"error": "User not found"}, 404


@app.post("/products")
@body_v2(ProductCreate)
def create_product(request: Request, product: ProductCreate):
    """
    Create a new product - automatic validation!
    Demonstrates regex validation and numeric constraints
    """
    global next_product_id

    product_response = ProductResponse(
        id=next_product_id,
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        tags=product.tags,
        sku=product.sku
    )

    products_db.append(product_response.model_dump())
    next_product_id += 1

    return product_response.model_dump_json()


@app.get("/products/:id")
def get_product(request: Request):
    """Get product by ID"""
    product_id = int(request.path_params.get("id"))

    for product in products_db:
        if product["id"] == product_id:
            return ProductResponse(**product).model_dump_json()

    return {"error": "Product not found"}, 404


@app.get("/users")
def list_users(request: Request):
    """List all users"""
    return {"users": users_db, "count": len(users_db)}


@app.get("/products")
def list_products(request: Request):
    """List all products"""
    return {"products": products_db, "count": len(products_db)}


if __name__ == "__main__":
    print("🚀 Starting Pydantic-Compatible Robyn Server...")
    print("📍 http://localhost:8081")
    print("\n✨ Features:")
    print("  - Pydantic v2 syntax")
    print("  - Automatic validation")
    print("  - Type coercion")
    print("  - Nested models")
    print("  - FastAPI-like decorators")
    app.start(host="0.0.0.0", port=8081)
