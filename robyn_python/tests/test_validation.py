"""
Tests for the Rust-based validation module
"""

import pytest
import sys
import os

# Add the parent directory to the path to import robyn_extensions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))


def test_validator_basic():
    """Test basic validation functionality"""
    try:
        from robyn_extensions import Validator, ValidationError
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    # Create validator
    validator = Validator()
    validator.add_field("name", ["required", "min_length:3"])
    validator.add_field("age", ["required", "min:18"])

    # Valid data
    data = {"name": "John", "age": 25}
    errors = validator.validate(data)
    assert len(errors) == 0, "Valid data should have no errors"


def test_validator_required_field():
    """Test required field validation"""
    try:
        from robyn_extensions import Validator, ValidationError
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("name", ["required"])

    # Missing required field
    data = {}
    errors = validator.validate(data)
    assert len(errors) == 1, "Missing required field should error"
    assert errors[0].field == "name"
    assert errors[0].error_type == "required"


def test_validator_min_length():
    """Test minimum length validation"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("username", ["min_length:5"])

    # Too short
    data = {"username": "abc"}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "min_length"

    # Valid length
    data = {"username": "abcdef"}
    errors = validator.validate(data)
    assert len(errors) == 0


def test_validator_max_length():
    """Test maximum length validation"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("code", ["max_length:10"])

    # Too long
    data = {"code": "12345678901"}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "max_length"

    # Valid length
    data = {"code": "12345"}
    errors = validator.validate(data)
    assert len(errors) == 0


def test_validator_numeric_range():
    """Test numeric min/max validation"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("age", ["min:18", "max:100"])

    # Too low
    data = {"age": 15}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "min_value"

    # Too high
    data = {"age": 150}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "max_value"

    # Valid
    data = {"age": 25}
    errors = validator.validate(data)
    assert len(errors) == 0


def test_validator_gt_lt():
    """Test greater than / less than validation"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("score", ["gt:0", "lt:100"])

    # Equal to boundary (should fail)
    data = {"score": 0}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "greater_than"

    data = {"score": 100}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "less_than"

    # Valid
    data = {"score": 50}
    errors = validator.validate(data)
    assert len(errors) == 0


def test_validator_email():
    """Test email validation"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("email", ["email"])

    # Invalid email
    data = {"email": "not-an-email"}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "email"

    # Valid email
    data = {"email": "test@example.com"}
    errors = validator.validate(data)
    assert len(errors) == 0


def test_validator_url():
    """Test URL validation"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("website", ["url"])

    # Invalid URL
    data = {"website": "not a url"}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "url"

    # Valid URL
    data = {"website": "https://example.com"}
    errors = validator.validate(data)
    assert len(errors) == 0


def test_validator_string_patterns():
    """Test string pattern validations (contains, starts_with, ends_with)"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    # Test contains
    validator = Validator()
    validator.add_field("text", ["contains:hello"])

    data = {"text": "well hello there"}
    errors = validator.validate(data)
    assert len(errors) == 0

    data = {"text": "goodbye"}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "str_contains"

    # Test starts_with
    validator = Validator()
    validator.add_field("code", ["starts_with:PREFIX_"])

    data = {"code": "PREFIX_123"}
    errors = validator.validate(data)
    assert len(errors) == 0

    data = {"code": "123_PREFIX"}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "str_starts_with"


def test_validator_multiple_of():
    """Test multiple_of validation"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("quantity", ["multiple_of:5"])

    # Valid multiple
    data = {"quantity": 15}
    errors = validator.validate(data)
    assert len(errors) == 0

    # Invalid multiple
    data = {"quantity": 17}
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "multiple_of"


def test_validator_json():
    """Test JSON validation"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("name", ["required", "min_length:3"])
    validator.add_field("age", ["required", "min:18"])

    # Valid JSON
    json_str = '{"name": "John", "age": 25}'
    errors = validator.validate_json(json_str)
    assert len(errors) == 0

    # Invalid JSON data
    json_str = '{"name": "Jo", "age": 15}'
    errors = validator.validate_json(json_str)
    assert len(errors) == 2  # Both validations should fail


def test_validator_complex_schema():
    """Test complex validation schema with multiple fields and rules"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("username", ["required", "min_length:3", "max_length:20"])
    validator.add_field("email", ["required", "email"])
    validator.add_field("age", ["required", "ge:18", "le:120"])
    validator.add_field("website", ["url"])

    # Valid data
    data = {
        "username": "johndoe",
        "email": "john@example.com",
        "age": 25,
        "website": "https://johndoe.com"
    }
    errors = validator.validate(data)
    assert len(errors) == 0

    # Multiple validation errors
    data = {
        "username": "jo",  # Too short
        "email": "invalid-email",  # Invalid format
        "age": 15,  # Too young
        "website": "not a url"  # Invalid URL
    }
    errors = validator.validate(data)
    assert len(errors) == 4


def test_validation_error_representation():
    """Test ValidationError representation"""
    try:
        from robyn_extensions import Validator
    except ImportError:
        pytest.skip("robyn_extensions module not built yet")

    validator = Validator()
    validator.add_field("name", ["required"])

    data = {}
    errors = validator.validate(data)
    assert len(errors) == 1

    error = errors[0]
    repr_str = repr(error)
    assert "ValidationError" in repr_str
    assert "name" in repr_str

    error_dict = error.to_dict()
    assert error_dict["field"] == "name"
    assert error_dict["type"] == "required"
    assert "message" in error_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
