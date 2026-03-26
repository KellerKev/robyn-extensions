"""
Tests for robyn_extensions decorators and functionality.
"""

import pytest
from pydantic import BaseModel, ValidationError
from robyn_extensions.decorators import body, query, rate_limit
from robyn_extensions.validation import validate_model, get_validation_errors


class TestModel(BaseModel):
    name: str
    age: int


class MockRequest:
    def __init__(self, body=None, query_params=None, headers=None, client_ip="127.0.0.1"):
        self.body = body
        self.query_params = query_params or {}
        self.headers = headers or {}
        self.client_ip = client_ip


def test_validate_model():
    """Test basic model validation."""
    data = {"name": "Alice", "age": 30}
    result = validate_model(TestModel, data)
    assert result.name == "Alice"
    assert result.age == 30


def test_validate_model_invalid():
    """Test validation with invalid data."""
    data = {"name": "Alice"}  # Missing age
    with pytest.raises(ValidationError):
        validate_model(TestModel, data)


def test_get_validation_errors():
    """Test getting validation errors."""
    data = {"name": "Alice"}
    result = get_validation_errors(TestModel, data)
    assert not result["valid"]
    assert len(result["errors"]) > 0


def test_body_decorator():
    """Test body validation decorator."""
    @body(TestModel)
    def handler(request, validated):
        return {"name": validated.name}
    
    request = MockRequest(body='{"name": "Alice", "age": 30}')
    result = handler(request)
    assert result["name"] == "Alice"


def test_body_decorator_invalid():
    """Test body decorator with invalid data."""
    @body(TestModel)
    def handler(request, validated):
        return {"name": validated.name}
    
    request = MockRequest(body='{"name": "Alice"}')
    result = handler(request)
    assert result["status_code"] == 422


def test_query_decorator():
    """Test query parameter validation."""
    @query(TestModel)
    def handler(request, validated):
        return {"name": validated.name}
    
    request = MockRequest(query_params={"name": "Alice", "age": "30"})
    result = handler(request)
    assert result["name"] == "Alice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
