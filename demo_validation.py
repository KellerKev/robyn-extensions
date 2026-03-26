#!/usr/bin/env python3
"""
Demo of Pydantic-like validation features implemented in Rust
for the Robyn web framework
"""

from robyn_extensions import Validator, ValidationError

print("=" * 60)
print("Robyn Extensions - Pydantic-like Validation Demo")
print("=" * 60)
print()

# Example 1: Basic validation
print("1. Basic Validation (required fields, min/max)")
print("-" * 60)
validator = Validator()
validator.add_field("username", ["required", "min_length:3", "max_length:20"])
validator.add_field("age", ["required", "min:18", "max:120"])

data = {"username": "johndoe", "age": 25}
errors = validator.validate(data)
print(f"✅ Valid data: {data}")
print(f"   Errors: {len(errors)}")

data = {"username": "jo", "age": 15}
errors = validator.validate(data)
print(f"\n❌ Invalid data: {data}")
print(f"   Errors: {len(errors)}")
for err in errors:
    print(f"   - {err.field}: {err.message}")

# Example 2: Email and URL validation
print("\n\n2. Email and URL Validation")
print("-" * 60)
validator = Validator()
validator.add_field("email", ["required", "email"])
validator.add_field("website", ["url"])

data = {"email": "user@example.com", "website": "https://example.com"}
errors = validator.validate(data)
print(f"✅ Valid: {data}")
print(f"   Errors: {len(errors)}")

data = {"email": "not-an-email", "website": "not a url"}
errors = validator.validate(data)
print(f"\n❌ Invalid: {data}")
for err in errors:
    print(f"   - {err.field}: {err.message}")

# Example 3: Numeric comparisons (gt, ge, lt, le)
print("\n\n3. Numeric Comparisons (gt, ge, lt, le)")
print("-" * 60)
validator = Validator()
validator.add_field("score", ["gt:0", "lt:100"])  # Must be between 0 and 100 (exclusive)
validator.add_field("rating", ["ge:1", "le:5"])   # Must be between 1 and 5 (inclusive)

data = {"score": 50, "rating": 3}
errors = validator.validate(data)
print(f"✅ Valid: {data}")

data = {"score": 0, "rating": 6}  # score=0 fails gt:0, rating=6 fails le:5
errors = validator.validate(data)
print(f"\n❌ Invalid: {data}")
for err in errors:
    print(f"   - {err.field}: {err.message} (type: {err.error_type})")

# Example 4: Multiple of validation
print("\n\n4. Multiple Of Validation")
print("-" * 60)
validator = Validator()
validator.add_field("quantity", ["multiple_of:5"])

data = {"quantity": 15}
errors = validator.validate(data)
print(f"✅ Valid (multiple of 5): {data}")

data = {"quantity": 17}
errors = validator.validate(data)
print(f"❌ Invalid (not multiple of 5): {data}")
for err in errors:
    print(f"   - {err.message}")

# Example 5: String pattern validation
print("\n\n5. String Pattern Validation (contains, starts_with, ends_with)")
print("-" * 60)
validator = Validator()
validator.add_field("code", ["starts_with:PREFIX_", "ends_with:_SUFFIX"])
validator.add_field("description", ["contains:important"])

data = {"code": "PREFIX_123_SUFFIX", "description": "This is important info"}
errors = validator.validate(data)
print(f"✅ Valid: {data}")

data = {"code": "123_PREFIX", "description": "This is info"}
errors = validator.validate(data)
print(f"\n❌ Invalid: {data}")
for err in errors:
    print(f"   - {err.field}: {err.message}")

# Example 6: Complex schema validation
print("\n\n6. Complex Schema Validation")
print("-" * 60)
validator = Validator()
validator.add_field("username", ["required", "min_length:3", "max_length:20"])
validator.add_field("email", ["required", "email"])
validator.add_field("age", ["required", "ge:18", "le:120"])
validator.add_field("website", ["url"])
validator.add_field("score", ["gt:0", "lt:100"])

valid_user = {
    "username": "johndoe",
    "email": "john@example.com",
    "age": 25,
    "website": "https://johndoe.com",
    "score": 85
}

errors = validator.validate(valid_user)
print(f"✅ Valid user data:")
print(f"   {valid_user}")
print(f"   Errors: {len(errors)}")

invalid_user = {
    "username": "jo",  # Too short
    "email": "invalid-email",  # Invalid format
    "age": 15,  # Too young
    "website": "not a url",  # Invalid URL
    "score": 100  # Must be less than 100
}

errors = validator.validate(invalid_user)
print(f"\n❌ Invalid user data:")
print(f"   {invalid_user}")
print(f"   Errors: {len(errors)}")
for err in errors:
    print(f"   - {err.field}: {err.message} ({err.error_type})")

# Example 7: JSON validation
print("\n\n7. JSON String Validation")
print("-" * 60)
validator = Validator()
validator.add_field("name", ["required", "min_length:3"])
validator.add_field("age", ["required", "min:18"])

json_str = '{"name": "John Doe", "age": 25}'
errors = validator.validate_json(json_str)
print(f"✅ Valid JSON: {json_str}")
print(f"   Errors: {len(errors)}")

json_str = '{"name": "Jo", "age": 15}'
errors = validator.validate_json(json_str)
print(f"\n❌ Invalid JSON: {json_str}")
for err in errors:
    print(f"   - {err.field}: {err.message}")

print("\n" + "=" * 60)
print("Demo Complete! All validation features working correctly.")
print("=" * 60)
