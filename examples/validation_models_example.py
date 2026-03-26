"""
Validation models example — Pydantic v2-compatible BaseModel features.

Demonstrates:
  - Field constraints (min/max length, numeric bounds, regex)
  - Type coercion
  - Computed fields
  - Field validators and model validators
  - Nested models
  - JSON Schema generation
  - Rust-backed low-level Validator
"""

from robyn_extensions import (
    BaseModel, Field, computed_field, field_validator, model_validator,
    Validator, ValidationError,
)
from typing import Optional, List
from datetime import datetime


# === Basic Model with Field Constraints ===

class UserProfile(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str = Field(regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(ge=13, le=120)
    bio: Optional[str] = Field(default=None, max_length=500)
    website: Optional[str] = None


# Valid:
user = UserProfile(username="alice", email="alice@example.com", age=25)
print("User:", user.model_dump())
print("JSON:", user.model_dump_json())

# Invalid — raises ValidationError:
try:
    UserProfile(username="ab", email="bad", age=10)
except Exception as e:
    print("Validation errors:", e)


# === Type Coercion ===

class Config(BaseModel):
    port: int
    debug: bool
    rate: float

# Strings are coerced to the correct types:
config = Config(port="8080", debug="true", rate="1.5")
print(f"Port: {config.port} (type: {type(config.port).__name__})")
print(f"Debug: {config.debug} (type: {type(config.debug).__name__})")


# === Computed Fields ===

class FullName(BaseModel):
    first_name: str
    last_name: str

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def initials(self) -> str:
        return f"{self.first_name[0]}{self.last_name[0]}".upper()

person = FullName(first_name="Alice", last_name="Smith")
print("Full:", person.model_dump())
# {"first_name": "Alice", "last_name": "Smith", "full_name": "Alice Smith", "initials": "AS"}


# === Field Validators ===

class SecureAccount(BaseModel):
    username: str
    password: str = Field(min_length=8)

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain an uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain a digit')
        return v

acct = SecureAccount(username="Alice123", password="Secret42")
print("Username:", acct.username)  # "alice123" (lowered by validator)


# === Model Validators ===

class DateRange(BaseModel):
    start_date: str
    end_date: str

    @model_validator(mode='after')
    def end_after_start(self):
        if self.end_date <= self.start_date:
            raise ValueError('end_date must be after start_date')
        return self

valid_range = DateRange(start_date="2024-01-01", end_date="2024-12-31")
print("Range:", valid_range.model_dump())


# === Nested Models ===

class Address(BaseModel):
    street: str
    city: str
    country: str = Field(default="US")

class Company(BaseModel):
    name: str
    address: Address
    employees: int = Field(ge=1)

company = Company(
    name="Acme Corp",
    address={"street": "123 Main St", "city": "Springfield"},
    employees=50
)
print("Company:", company.model_dump())
print("City:", company.address.city)


# === JSON Schema Generation (OpenAPI-compatible) ===

schema = UserProfile.model_json_schema()
print("\nJSON Schema for UserProfile:")
import json
print(json.dumps(schema, indent=2))


# === Rust-backed Low-level Validator ===

print("\n--- Rust Validator ---")
validator = Validator()
validator.add_field("email", ["required", "email"])
validator.add_field("username", ["required", "min_length:3", "max_length:20"])
validator.add_field("age", ["required", "ge:13", "le:120"])
validator.add_field("website", ["url"])
validator.add_field("score", ["multiple_of:5"])

# Validate a dict
errors = validator.validate({
    "email": "not-an-email",
    "username": "ab",
    "age": 200,
    "website": "not-a-url",
    "score": 7,
})
print(f"Found {len(errors)} validation errors:")
for err in errors:
    print(f"  {err.field}: {err.message} ({err.error_type})")

# Validate JSON string
errors = validator.validate_json('{"email": "valid@example.com", "username": "alice", "age": 25}')
print(f"\nValid data errors: {len(errors)}")
