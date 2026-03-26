# Quick Start: Robyn Validation Extension

## Installation

```bash
# Install with pixi
pixi install

# Build the extension
pixi run build

# Install the wheel
pixi run pip install target/wheels/robyn_extensions-0.1.0-cp38-abi3-macosx_11_0_arm64.whl
```

## Basic Usage

### 1. Import the Validator

```python
from robyn_extensions import Validator
```

### 2. Create a Validator and Add Rules

```python
validator = Validator()
validator.add_field("username", ["required", "min_length:3", "max_length:20"])
validator.add_field("email", ["required", "email"])
validator.add_field("age", ["ge:18", "le:120"])
```

### 3. Validate Data

```python
# Valid data
data = {"username": "johndoe", "email": "john@example.com", "age": 25}
errors = validator.validate(data)

if not errors:
    print("✅ Data is valid!")
else:
    for err in errors:
        print(f"❌ {err.field}: {err.message}")
```

## Available Validation Rules

### Required
```python
validator.add_field("field_name", ["required"])
```

### String Length
```python
validator.add_field("username", ["min_length:3", "max_length:20"])
```

### Numeric Ranges
```python
# Min/max (inclusive)
validator.add_field("age", ["min:18", "max:100"])

# Greater than/less than (exclusive)
validator.add_field("score", ["gt:0", "lt:100"])

# Greater/less than or equal
validator.add_field("rating", ["ge:1", "le:5"])
```

### Multiple Of
```python
validator.add_field("quantity", ["multiple_of:5"])
```

### Format Validators
```python
# Email
validator.add_field("email", ["email"])

# URL
validator.add_field("website", ["url"])

# Custom pattern
validator.add_field("code", ["pattern:^[A-Z]{3}-\\d{4}$"])
```

### String Patterns
```python
# Contains substring
validator.add_field("description", ["contains:important"])

# Starts with prefix
validator.add_field("code", ["starts_with:PREFIX_"])

# Ends with suffix
validator.add_field("file", ["ends_with:.pdf"])
```

## Using with Robyn Web Framework

```python
from robyn import Robyn, Request, Response
from robyn_extensions import Validator
import json

app = Robyn(__file__)

# Create validator
user_validator = Validator()
user_validator.add_field("username", ["required", "min_length:3"])
user_validator.add_field("email", ["required", "email"])
user_validator.add_field("age", ["required", "ge:18"])

@app.post("/users")
def create_user(request: Request):
    try:
        data = json.loads(request.body)
        errors = user_validator.validate(data)

        if errors:
            # Return validation errors
            error_list = [
                {"field": e.field, "message": e.message, "type": e.error_type}
                for e in errors
            ]
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"errors": error_list})
            )

        # Process valid data
        return Response(
            status_code=201,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"success": True, "data": data})
        )
    except json.JSONDecodeError:
        return Response(status_code=400, description="Invalid JSON")

app.start(port=8080)
```

## JSON Validation

You can also validate JSON strings directly:

```python
validator = Validator()
validator.add_field("name", ["required", "min_length:2"])
validator.add_field("age", ["required", "min:0"])

json_str = '{"name": "John", "age": 25}'
errors = validator.validate_json(json_str)

if not errors:
    print("✅ Valid JSON data")
```

## Error Handling

Each validation error contains:
- `field` - The field name that failed validation
- `message` - Human-readable error message
- `error_type` - Machine-readable error type
- `input` - (optional) The input value that failed

```python
for error in errors:
    print(f"Field: {error.field}")
    print(f"Type: {error.error_type}")
    print(f"Message: {error.message}")
    if error.input:
        print(f"Input: {error.input}")

    # Convert to dict
    error_dict = error.to_dict()
```

## Running the Examples

### Demo Script
```bash
pixi run python demo_validation.py
```

### Sample API Server
```bash
# Terminal 1: Start server
pixi run python sample_app.py

# Terminal 2: Run tests
pixi run python test_api.py
```

## Testing

Run all tests:
```bash
# Rust tests
pixi run test-rust

# Python tests
pixi run test

# Check compilation
pixi run check-rust
```

## Next Steps

1. Check out `sample_app.py` for a complete working example
2. Run `demo_validation.py` to see all validation features
3. Read `VALIDATION_API_DEMO.md` for detailed test results
4. Explore the test files for more usage patterns

## Performance Tips

- Create validators once and reuse them (they're thread-safe)
- Validation is performed in Rust for maximum speed
- No Python GIL contention during validation
- Zero-copy where possible for efficiency

## Support

For issues or questions:
- Check the examples in this repository
- Run the test suite to verify installation
- Review the API demo for usage patterns
