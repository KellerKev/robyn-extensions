#!/usr/bin/env python3
"""
Comprehensive tests for advanced Pydantic v2 features:
- JSON Schema generation
- Computed fields
- Field validators
- Model validators
"""

import pytest
import sys
import json
sys.path.insert(0, 'robyn_python/python')

from robyn_extensions import (
    BaseModel,
    Field,
    ModelValidationError,
    computed_field,
    field_validator,
    model_validator,
)
from typing import Optional, List


# ============================================================================
# JSON SCHEMA GENERATION TESTS
# ============================================================================

def test_json_schema_basic():
    """Test basic JSON Schema generation"""
    class User(BaseModel):
        username: str
        age: int
        is_active: bool

    schema = User.model_json_schema()

    assert schema["title"] == "User"
    assert schema["type"] == "object"
    assert "username" in schema["properties"]
    assert "age" in schema["properties"]
    assert "is_active" in schema["properties"]
    assert schema["properties"]["username"]["type"] == "string"
    assert schema["properties"]["age"]["type"] == "integer"
    assert schema["properties"]["is_active"]["type"] == "boolean"
    assert set(schema["required"]) == {"username", "age", "is_active"}


def test_json_schema_with_constraints():
    """Test JSON Schema with field constraints"""
    class Product(BaseModel):
        name: str = Field(min_length=3, max_length=50)
        price: float = Field(gt=0, le=10000)
        sku: str = Field(regex=r"^[A-Z]{3}-\d{4}$")

    schema = Product.model_json_schema()

    assert schema["properties"]["name"]["minLength"] == 3
    assert schema["properties"]["name"]["maxLength"] == 50
    assert schema["properties"]["price"]["exclusiveMinimum"] == 0
    assert schema["properties"]["price"]["maximum"] == 10000
    assert schema["properties"]["sku"]["pattern"] == r"^[A-Z]{3}-\d{4}$"


def test_json_schema_optional_fields():
    """Test JSON Schema with Optional fields"""
    class User(BaseModel):
        username: str
        email: Optional[str] = None

    schema = User.model_json_schema()

    assert "username" in schema["required"]
    assert "email" not in schema["required"]
    assert schema["properties"]["email"]["nullable"] is True


def test_json_schema_nested_models():
    """Test JSON Schema with nested models"""
    class Address(BaseModel):
        street: str
        city: str

    class User(BaseModel):
        username: str
        address: Address

    schema = User.model_json_schema()

    assert "$defs" in schema
    assert "Address" in schema["$defs"]
    assert schema["properties"]["address"]["$ref"] == "#/$defs/Address"
    assert schema["$defs"]["Address"]["properties"]["street"]["type"] == "string"


def test_json_schema_list_types():
    """Test JSON Schema with List types"""
    class Article(BaseModel):
        title: str
        tags: List[str]

    schema = Article.model_json_schema()

    assert schema["properties"]["tags"]["type"] == "array"
    assert schema["properties"]["tags"]["items"]["type"] == "string"


def test_json_schema_with_description():
    """Test JSON Schema with field descriptions"""
    class User(BaseModel):
        username: str = Field(description="The user's unique username")
        age: int = Field(ge=18, description="Must be 18 or older")

    schema = User.model_json_schema()

    assert schema["properties"]["username"]["description"] == "The user's unique username"
    assert schema["properties"]["age"]["description"] == "Must be 18 or older"


def test_json_schema_with_alias():
    """Test JSON Schema with field aliases"""
    class User(BaseModel):
        username: str = Field(alias="user_name")
        email: str

    # By default, use aliases
    schema = User.model_json_schema(by_alias=True)
    assert "user_name" in schema["properties"]
    assert "username" not in schema["properties"]

    # Without aliases
    schema_no_alias = User.model_json_schema(by_alias=False)
    assert "username" in schema_no_alias["properties"]
    assert "user_name" not in schema_no_alias["properties"]


# ============================================================================
# COMPUTED FIELDS TESTS
# ============================================================================

def test_computed_field_basic():
    """Test basic computed field"""
    class User(BaseModel):
        first_name: str
        last_name: str

        @computed_field
        @property
        def full_name(self) -> str:
            return f"{self.first_name} {self.last_name}"

    user = User(first_name="John", last_name="Doe")
    assert user.full_name == "John Doe"
    assert user.first_name == "John"
    assert user.last_name == "Doe"


def test_computed_field_in_model_dump():
    """Test computed fields are included in model_dump()"""
    class User(BaseModel):
        first_name: str
        last_name: str

        @computed_field
        @property
        def full_name(self) -> str:
            return f"{self.first_name} {self.last_name}"

    user = User(first_name="Jane", last_name="Smith")
    data = user.model_dump()

    assert "first_name" in data
    assert "last_name" in data
    assert "full_name" in data
    assert data["full_name"] == "Jane Smith"


def test_computed_field_complex():
    """Test computed field with complex logic"""
    class Product(BaseModel):
        price: float
        tax_rate: float = 0.1

        @computed_field
        @property
        def price_with_tax(self) -> float:
            return round(self.price * (1 + self.tax_rate), 2)

    product = Product(price=100.0, tax_rate=0.2)
    assert product.price_with_tax == 120.0


# ============================================================================
# FIELD VALIDATOR TESTS
# ============================================================================

def test_field_validator_basic():
    """Test basic field validator"""
    class User(BaseModel):
        username: str

        @field_validator('username')
        @classmethod
        def validate_username(cls, v):
            if 'admin' in v.lower():
                raise ValueError('Username cannot contain "admin"')
            return v

    # Valid username
    user = User(username="john_doe")
    assert user.username == "john_doe"

    # Invalid username
    with pytest.raises(ModelValidationError) as exc:
        User(username="admin_user")
    assert any('admin' in str(e['message']).lower() for e in exc.value.errors)


def test_field_validator_transformation():
    """Test field validator that transforms value"""
    class User(BaseModel):
        username: str

        @field_validator('username')
        @classmethod
        def normalize_username(cls, v):
            return v.strip().lower()

    user = User(username="  JohnDoe  ")
    assert user.username == "johndoe"


def test_field_validator_multiple_fields():
    """Test validator for multiple fields"""
    class User(BaseModel):
        email: str
        backup_email: str

        @field_validator('email', 'backup_email')
        @classmethod
        def validate_email(cls, v):
            if '@' not in v:
                raise ValueError('Invalid email format')
            return v

    # Valid
    user = User(email="john@example.com", backup_email="john2@example.com")
    assert user.email == "john@example.com"

    # Invalid email
    with pytest.raises(ModelValidationError) as exc:
        User(email="invalid", backup_email="also_invalid")


def test_field_validator_with_constraints():
    """Test field validator combined with Field constraints"""
    class User(BaseModel):
        username: str = Field(min_length=3)

        @field_validator('username')
        @classmethod
        def no_spaces(cls, v):
            if ' ' in v:
                raise ValueError('Username cannot contain spaces')
            return v

    # Valid
    user = User(username="john_doe")
    assert user.username == "john_doe"

    # Invalid: too short
    with pytest.raises(ModelValidationError) as exc:
        User(username="jo")
    assert any('length' in str(e['message']).lower() for e in exc.value.errors)

    # Invalid: has spaces
    with pytest.raises(ModelValidationError) as exc:
        User(username="john doe")
    assert any('spaces' in str(e['message']).lower() for e in exc.value.errors)


# ============================================================================
# MODEL VALIDATOR TESTS
# ============================================================================

def test_model_validator_basic():
    """Test basic model validator"""
    class UserRegistration(BaseModel):
        password: str
        password_confirm: str

        @model_validator(mode='after')
        def check_passwords_match(self):
            if self.password != self.password_confirm:
                raise ValueError('Passwords do not match')
            return self

    # Valid
    user = UserRegistration(password="secret123", password_confirm="secret123")
    assert user.password == "secret123"

    # Invalid
    with pytest.raises(ModelValidationError) as exc:
        UserRegistration(password="secret123", password_confirm="different")
    assert any('match' in str(e['message']).lower() for e in exc.value.errors)


def test_model_validator_complex():
    """Test model validator with complex logic"""
    class DateRange(BaseModel):
        start_date: str
        end_date: str

        @model_validator(mode='after')
        def check_date_order(self):
            if self.start_date > self.end_date:
                raise ValueError('Start date must be before end date')
            return self

    # Valid
    range1 = DateRange(start_date="2024-01-01", end_date="2024-12-31")
    assert range1.start_date == "2024-01-01"

    # Invalid
    with pytest.raises(ModelValidationError):
        DateRange(start_date="2024-12-31", end_date="2024-01-01")


def test_model_validator_multiple():
    """Test multiple model validators"""
    class User(BaseModel):
        username: str
        email: str
        age: int

        @model_validator(mode='after')
        def check_username_email_match(self):
            username_part = self.email.split('@')[0]
            if username_part != self.username:
                raise ValueError('Username must match email prefix')
            return self

        @model_validator(mode='after')
        def check_age_username(self):
            if self.age < 18 and 'kid' not in self.username:
                raise ValueError('Users under 18 must have "kid" in username')
            return self

    # Valid
    user = User(username="john", email="john@example.com", age=25)
    assert user.username == "john"

    # Invalid: username doesn't match email
    with pytest.raises(ModelValidationError) as exc:
        User(username="jane", email="john@example.com", age=25)
    assert any('email' in str(e['message']).lower() for e in exc.value.errors)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_all_features_together():
    """Test JSON Schema, computed fields, and validators together"""
    class User(BaseModel):
        first_name: str = Field(min_length=2, description="User's first name")
        last_name: str = Field(min_length=2, description="User's last name")
        email: str
        age: int = Field(ge=18, le=120)

        @computed_field
        @property
        def full_name(self) -> str:
            return f"{self.first_name} {self.last_name}"

        @field_validator('email')
        @classmethod
        def validate_email(cls, v):
            if '@' not in v or '.' not in v:
                raise ValueError('Invalid email format')
            return v.lower()

        @model_validator(mode='after')
        def check_name_email(self):
            email_user = self.email.split('@')[0]
            if self.first_name.lower() not in email_user.lower():
                raise ValueError('First name should be in email')
            return self

    # Valid user
    user = User(
        first_name="John",
        last_name="Doe",
        email="John.Doe@EXAMPLE.COM",
        age=30
    )
    assert user.full_name == "John Doe"
    assert user.email == "john.doe@example.com"  # Normalized

    # Test model_dump includes computed field
    data = user.model_dump()
    assert data["full_name"] == "John Doe"

    # Test JSON Schema
    schema = User.model_json_schema()
    assert schema["properties"]["first_name"]["minLength"] == 2
    assert schema["properties"]["age"]["minimum"] == 18
    assert "full_name" not in schema["properties"]  # Computed fields not in schema


def test_nested_with_validators():
    """Test nested models with validators"""
    class Address(BaseModel):
        street: str = Field(min_length=5)
        zip_code: str

        @field_validator('zip_code')
        @classmethod
        def validate_zip(cls, v):
            if not v.isdigit() or len(v) != 5:
                raise ValueError('ZIP code must be 5 digits')
            return v

    class User(BaseModel):
        username: str
        address: Address

        @field_validator('username')
        @classmethod
        def validate_username(cls, v):
            if len(v) < 3:
                raise ValueError('Username too short')
            return v

    # Valid
    user = User(
        username="john",
        address={"street": "123 Main St", "zip_code": "12345"}
    )
    assert user.address.zip_code == "12345"

    # Invalid ZIP
    with pytest.raises(ModelValidationError):
        User(
            username="john",
            address={"street": "123 Main St", "zip_code": "abc"}
        )


if __name__ == "__main__":
    print("Running Advanced Features Tests...")
    pytest.main([__file__, "-v", "--tb=short"])
