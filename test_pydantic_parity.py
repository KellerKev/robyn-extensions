#!/usr/bin/env python3
"""
Comprehensive tests for Pydantic v2 parity
Testing all features implemented in BaseModel
"""

import pytest
import sys
sys.path.insert(0, 'robyn_python/python')

from robyn_extensions import BaseModel, Field, ModelValidationError
from typing import Optional, List
from datetime import datetime, date


def test_basic_model():
    """Test basic model creation"""
    class User(BaseModel):
        username: str
        email: str
        age: int

    user = User(username="john", email="john@example.com", age=25)
    assert user.username == "john"
    assert user.email == "john@example.com"
    assert user.age == 25


def test_field_validation():
    """Test Field() constraints"""
    class User(BaseModel):
        username: str = Field(min_length=3, max_length=20)
        age: int = Field(ge=18, le=120)

    # Valid user
    user = User(username="john", age=25)
    assert user.username == "john"

    # Invalid username (too short)
    with pytest.raises(ModelValidationError) as exc:
        User(username="jo", age=25)
    assert any('length' in str(e['message']).lower() for e in exc.value.errors)

    # Invalid age (too young)
    with pytest.raises(ModelValidationError) as exc:
        User(username="john", age=15)
    assert any('18' in str(e['message']) for e in exc.value.errors)


def test_type_coercion_string_to_int():
    """Test automatic type coercion from string to int"""
    class Product(BaseModel):
        price: int
        quantity: int

    # Should coerce strings to ints
    product = Product(price="25", quantity="10")
    assert product.price == 25
    assert product.quantity == 10
    assert isinstance(product.price, int)


def test_type_coercion_string_to_bool():
    """Test automatic type coercion from string to bool"""
    class Settings(BaseModel):
        enabled: bool
        active: bool

    settings = Settings(enabled="true", active="1")
    assert settings.enabled is True
    assert settings.active is True

    settings2 = Settings(enabled="false", active="0")
    assert settings2.enabled is False
    assert settings2.active is False


def test_type_coercion_string_to_datetime():
    """Test automatic type coercion from string to datetime"""
    class Event(BaseModel):
        created_at: datetime

    event = Event(created_at="2024-01-15 10:30:00")
    assert isinstance(event.created_at, datetime)
    assert event.created_at.year == 2024


def test_optional_fields():
    """Test Optional field handling"""
    class User(BaseModel):
        username: str
        email: Optional[str] = None
        bio: Optional[str] = None

    # Without optional fields
    user1 = User(username="john")
    assert user1.username == "john"
    assert user1.email is None
    assert user1.bio is None

    # With optional fields
    user2 = User(username="jane", email="jane@example.com")
    assert user2.email == "jane@example.com"


def test_default_values():
    """Test default field values"""
    class User(BaseModel):
        username: str
        role: str = "user"
        active: bool = True

    user = User(username="john")
    assert user.username == "john"
    assert user.role == "user"
    assert user.active is True

    user2 = User(username="admin", role="admin", active=False)
    assert user2.role == "admin"
    assert user2.active is False


def test_list_type():
    """Test List type validation"""
    class User(BaseModel):
        username: str
        tags: List[str]

    user = User(username="john", tags=["python", "rust", "web"])
    assert len(user.tags) == 3
    assert "python" in user.tags


def test_nested_models():
    """Test nested model validation"""
    class Address(BaseModel):
        street: str
        city: str
        country: str

    class User(BaseModel):
        username: str
        address: Address

    # Create with nested dict
    user = User(
        username="john",
        address={"street": "123 Main St", "city": "NYC", "country": "USA"}
    )
    assert isinstance(user.address, Address)
    assert user.address.city == "NYC"

    # Create with nested model
    address = Address(street="456 Oak Ave", city="LA", country="USA")
    user2 = User(username="jane", address=address)
    assert user2.address.street == "456 Oak Ave"


def test_model_dump():
    """Test model_dump() serialization"""
    class User(BaseModel):
        username: str
        email: str
        age: int

    user = User(username="john", email="john@example.com", age=25)
    data = user.model_dump()

    assert isinstance(data, dict)
    assert data["username"] == "john"
    assert data["email"] == "john@example.com"
    assert data["age"] == 25


def test_model_dump_json():
    """Test model_dump_json() serialization"""
    class User(BaseModel):
        username: str
        age: int

    user = User(username="john", age=25)
    json_str = user.model_dump_json()

    assert isinstance(json_str, str)
    assert '"username": "john"' in json_str
    assert '"age": 25' in json_str


def test_model_validate():
    """Test model_validate() class method"""
    class User(BaseModel):
        username: str
        age: int

    data = {"username": "john", "age": 25}
    user = User.model_validate(data)

    assert user.username == "john"
    assert user.age == 25


def test_model_validate_json():
    """Test model_validate_json() class method"""
    class User(BaseModel):
        username: str
        age: int

    json_str = '{"username": "john", "age": 25}'
    user = User.model_validate_json(json_str)

    assert user.username == "john"
    assert user.age == 25


def test_multiple_validation_errors():
    """Test that all validation errors are returned at once"""
    class User(BaseModel):
        username: str = Field(min_length=3)
        email: str
        age: int = Field(ge=18)

    # Missing required field + validation errors
    with pytest.raises(ModelValidationError) as exc:
        User(username="jo", age=15)  # Missing email, short username, young age

    errors = exc.value.errors
    assert len(errors) >= 2  # At least username and age errors


def test_nested_model_serialization():
    """Test nested model serialization"""
    class Address(BaseModel):
        city: str
        country: str

    class User(BaseModel):
        username: str
        address: Address

    address = Address(city="NYC", country="USA")
    user = User(username="john", address=address)

    data = user.model_dump()
    assert isinstance(data["address"], dict)
    assert data["address"]["city"] == "NYC"


def test_list_of_models():
    """Test list of nested models"""
    class Tag(BaseModel):
        name: str

    class Article(BaseModel):
        title: str
        tags: List[Tag]

    article = Article(
        title="Test Article",
        tags=[{"name": "python"}, {"name": "rust"}]
    )

    assert len(article.tags) == 2
    assert all(isinstance(tag, Tag) for tag in article.tags)
    assert article.tags[0].name == "python"


def test_field_alias():
    """Test field alias"""
    class User(BaseModel):
        username: str = Field(alias="user_name")
        email: str

    # Can create with alias
    user = User(user_name="john", email="john@example.com")
    assert user.username == "john"


def test_gt_lt_constraints():
    """Test gt (greater than) and lt (less than) constraints"""
    class Score(BaseModel):
        value: int = Field(gt=0, lt=100)

    # Valid score
    score = Score(value=50)
    assert score.value == 50

    # Invalid: equal to boundary
    with pytest.raises(ModelValidationError):
        Score(value=0)

    with pytest.raises(ModelValidationError):
        Score(value=100)


def test_model_equality():
    """Test model equality"""
    class User(BaseModel):
        username: str
        age: int

    user1 = User(username="john", age=25)
    user2 = User(username="john", age=25)
    user3 = User(username="jane", age=25)

    assert user1 == user2
    assert user1 != user3


def test_model_repr():
    """Test model __repr__"""
    class User(BaseModel):
        username: str
        age: int

    user = User(username="john", age=25)
    repr_str = repr(user)

    assert "User" in repr_str
    assert "username='john'" in repr_str
    assert "age=25" in repr_str


def test_exclude_none_in_dump():
    """Test exclude_none parameter in model_dump"""
    class User(BaseModel):
        username: str
        email: Optional[str] = None
        bio: Optional[str] = None

    user = User(username="john", email="john@example.com")

    # With None values
    data_with_none = user.model_dump()
    assert "bio" in data_with_none
    assert data_with_none["bio"] is None

    # Without None values
    data_without_none = user.model_dump(exclude_none=True)
    assert "bio" not in data_without_none
    assert "email" in data_without_none


def test_complex_nested_structure():
    """Test complex nested structure"""
    class Coordinate(BaseModel):
        lat: float
        lon: float

    class Address(BaseModel):
        street: str
        city: str
        coordinates: Coordinate

    class User(BaseModel):
        username: str
        addresses: List[Address]

    user = User(
        username="john",
        addresses=[
            {
                "street": "123 Main St",
                "city": "NYC",
                "coordinates": {"lat": 40.7128, "lon": -74.0060}
            },
            {
                "street": "456 Oak Ave",
                "city": "LA",
                "coordinates": {"lat": 34.0522, "lon": -118.2437}
            }
        ]
    )

    assert len(user.addresses) == 2
    assert isinstance(user.addresses[0], Address)
    assert isinstance(user.addresses[0].coordinates, Coordinate)
    assert user.addresses[0].coordinates.lat == 40.7128


def test_regex_validation():
    """Test regex pattern validation"""
    class Product(BaseModel):
        sku: str = Field(regex=r"^[A-Z]{3}-\d{4}$")

    # Valid SKU
    product = Product(sku="ABC-1234")
    assert product.sku == "ABC-1234"

    # Invalid SKU
    with pytest.raises(ModelValidationError) as exc:
        Product(sku="invalid")
    assert any('pattern' in str(e['message']).lower() for e in exc.value.errors)


def test_pydantic_compatibility_example():
    """Test full Pydantic-compatible example"""

    class User(BaseModel):
        username: str = Field(min_length=3, max_length=20)
        email: str
        age: int = Field(ge=18, le=120)
        is_active: bool = True
        tags: List[str] = []
        metadata: Optional[dict] = None

    # Create user
    user = User(
        username="johndoe",
        email="john@example.com",
        age="25",  # String should be coerced to int
        is_active="true",  # String should be coerced to bool
        tags=["python", "rust"]
    )

    # Verify types
    assert isinstance(user.age, int)
    assert isinstance(user.is_active, bool)
    assert isinstance(user.tags, list)

    # Test serialization
    data = user.model_dump()
    assert data["username"] == "johndoe"
    assert data["age"] == 25
    assert data["is_active"] is True

    # Test JSON serialization
    json_str = user.model_dump_json()
    assert isinstance(json_str, str)

    # Test validation
    user2 = User.model_validate_json(json_str)
    assert user2 == user


if __name__ == "__main__":
    print("Running Pydantic v2 Parity Tests...")
    pytest.main([__file__, "-v", "--tb=short"])
