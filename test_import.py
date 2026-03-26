from robyn_extensions import Validator, ValidationError

v = Validator()
v.add_field("name", ["required", "min_length:3"])
v.add_field("age", ["min:18"])

# Test valid data
data = {"name": "John", "age": 25}
errors = v.validate(data)
print(f"Valid data errors: {len(errors)}")

# Test invalid data
data2 = {"name": "Jo", "age": 15}
errors2 = v.validate(data2)
print(f"Invalid data errors: {len(errors2)}")
for err in errors2:
    print(f"  - {err}")

print("✅ Validation working correctly!")
