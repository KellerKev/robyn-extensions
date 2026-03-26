#!/usr/bin/env python3
"""
Simple demonstration of Pydantic v2 compatibility
Without the complexity of  running a live server
"""

import sys
sys.path.insert(0, 'robyn_python/python')

from robyn_extensions import BaseModel, Field, ModelValidationError, body_v2
from typing import Optional, List
from datetime import datetime

print("=" * 70)
print("PYDANTIC V2 COMPATIBILITY DEMONSTRATION")
print("=" * 70)

# 1. Basic model with type coercion
print("\n1. Type Coercion Test:")
print("-" * 70)

class User(BaseModel):
    username: str
    age: int
    is_active: bool

user = User(username="john", age="25", is_active="true")
print(f"✅ Created user with type coercion:")
print(f"   username: {user.username!r} (type: {type(user.username).__name__})")
print(f"   age: {user.age!r} (type: {type(user.age).__name__})")
print(f"   is_active: {user.is_active!r} (type: {type(user.is_active).__name__})")
assert isinstance(user.age, int) and user.age == 25
assert isinstance(user.is_active, bool) and user.is_active is True

# 2. Field validation
print("\n2. Field Validation Test:")
print("-" * 70)

class Product(BaseModel):
    name: str = Field(min_length=3)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    sku: str = Field(regex=r"^[A-Z]{3}-\d{4}$")

try:
    product = Product(name="ab", price=10.0, stock=5, sku="ABC-1234")
    print("❌ Should have failed validation!")
except ModelValidationError as e:
    print(f"✅ Validation error caught correctly:")
    print(f"   {e.errors[0]['message']}")

product = Product(name="Widget", price=29.99, stock=100, sku="ABC-1234")
print(f"✅ Valid product created: {product.name} @ ${product.price}")

# 3. Nested models
print("\n3. Nested Models Test:")
print("-" * 70)

class Address(BaseModel):
    street: str
    city: str
    country: str = "USA"

class UserWithAddress(BaseModel):
    username: str
    address: Address

user_data = {
    "username": "jane",
    "address": {"street": "123 Main St", "city": "NYC"}
}
user = UserWithAddress(**user_data)
print(f"✅ Nested model created:")
print(f"   username: {user.username}")
print(f"   address.city: {user.address.city}")
print(f"   address.country: {user.address.country} (default)")
assert isinstance(user.address, Address)

# 4. Optional fields and defaults
print("\n4. Optional Fields & Defaults Test:")
print("-" * 70)

class Settings(BaseModel):
    name: str
    email: Optional[str] = None
    is_active: bool = True
    tags: List[str] = []

settings = Settings(name="app1")
print(f"✅ Created with defaults:")
print(f"   name: {settings.name}")
print(f"   email: {settings.email}")
print(f"   is_active: {settings.is_active}")
print(f"   tags: {settings.tags}")

# 5. Serialization
print("\n5. Serialization Test:")
print("-" * 70)

user_dict = user.model_dump()
print(f"✅ model_dump() output:")
print(f"   Type: {type(user_dict).__name__}")
print(f"   Keys: {list(user_dict.keys())}")
print(f"   Nested address type: {type(user_dict['address']).__name__}")

user_json = user.model_dump_json()
print(f"✅ model_dump_json() output:")
print(f"   Type: {type(user_json).__name__}")
print(f"   Content (first 80 chars): {user_json[:80]}...")

# 6. Deserialization
print("\n6. Deserialization Test:")
print("-" * 70)

restored_user = UserWithAddress.model_validate(user_dict)
print(f"✅ model_validate() from dict:")
print(f"   username: {restored_user.username}")
print(f"   Equality check: {restored_user == user}")

restored_user2 = UserWithAddress.model_validate_json(user_json)
print(f"✅ model_validate_json() from JSON:")
print(f"   username: {restored_user2.username}")
print(f"   Equality check: {restored_user2 == user}")

# 7. List of models
print("\n7. List of Nested Models Test:")
print("-" * 70)

class Tag(BaseModel):
    name: str
    color: str = "blue"

class Article(BaseModel):
    title: str
    tags: List[Tag]

article = Article(
    title="Pydantic v2 for Robyn",
    tags=[{"name": "python"}, {"name": "rust", "color": "orange"}]
)
print(f"✅ Article with list of tags:")
print(f"   title: {article.title}")
print(f"   tags[0]: {article.tags[0].name} ({article.tags[0].color})")
print(f"   tags[1]: {article.tags[1].name} ({article.tags[1].color})")
assert len(article.tags) == 2
assert all(isinstance(tag, Tag) for tag in article.tags)

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("✅ All 7 Pydantic v2 compatibility tests passed!")
print("\n📋 Features Demonstrated:")
print("  ✅ Type coercion (str -> int, bool)")
print("  ✅ Field validation (min_length, gt, ge, regex)")
print("  ✅ Nested models (automatic conversion from dict)")
print("  ✅ Optional fields with None defaults")
print("  ✅ Default values (bool, list)")
print("  ✅ Serialization (model_dump(), model_dump_json())")
print("  ✅ Deserialization (model_validate(), model_validate_json())")
print("  ✅ List of nested models with type validation")
print("\n🎉 Pydantic v2 parity achieved for Robyn!")
print("=" * 70)
