#!/usr/bin/env python3
"""
Test the Pydantic-compatible Robyn app
"""

import requests
import json
import time

BASE_URL = "http://localhost:8081"


def test_create_user_with_type_coercion():
    """Test creating user with automatic type coercion"""
    print("\n" + "="*70)
    print("TEST: Create User with Type Coercion (age as string)")
    print("="*70)

    data = {
        "username": "johndoe",
        "email": "john@example.com",
        "age": "25",  # String should be coerced to int!
        "is_active": "true",  # String should be coerced to bool!
        "tags": ["python", "rust", "web"]
    }

    response = requests.post(f"{BASE_URL}/users", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    result = response.json()
    assert result["age"] == 25  # Should be int, not string
    assert result["is_active"] is True
    print("✅ PASS: Type coercion works!")


def test_nested_model():
    """Test nested model validation"""
    print("\n" + "="*70)
    print("TEST: Nested Model (User with Address)")
    print("="*70)

    data = {
        "username": "janedoe",
        "email": "jane@example.com",
        "age": 30,
        "tags": ["javascript"],
        "address": {
            "street": "123 Main St",
            "city": "NYC",
            "country": "USA",
            "zip_code": "10001"
        }
    }

    response = requests.post(f"{BASE_URL}/users", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    result = response.json()
    assert result["address"]["city"] == "NYC"
    print("✅ PASS: Nested models work!")


def test_validation_error_min_length():
    """Test validation error for short username"""
    print("\n" + "="*70)
    print("TEST: Validation Error (username too short)")
    print("="*70)

    data = {
        "username": "jo",  # Too short (min 3)
        "email": "jo@example.com",
        "age": 25
    }

    response = requests.post(f"{BASE_URL}/users", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 422  # Validation error
    print("✅ PASS: Validation caught short username!")


def test_validation_error_age():
    """Test validation error for age"""
    print("\n" + "="*70)
    print("TEST: Validation Error (age under 18)")
    print("="*70)

    data = {
        "username": "teenager",
        "email": "teen@example.com",
        "age": 15  # Under 18
    }

    response = requests.post(f"{BASE_URL}/users", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 422
    print("✅ PASS: Validation caught underage!")


def test_optional_fields():
    """Test optional fields"""
    print("\n" + "="*70)
    print("TEST: Optional Fields (no address)")
    print("="*70)

    data = {
        "username": "minimalist",
        "email": "min@example.com",
        "age": 40
        # No address, no tags - should use defaults
    }

    response = requests.post(f"{BASE_URL}/users", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    result = response.json()
    assert result["address"] is None
    assert result["tags"] == []
    assert result["is_active"] is True  # Default value
    print("✅ PASS: Optional fields and defaults work!")


def test_product_with_regex():
    """Test product creation with regex SKU validation"""
    print("\n" + "="*70)
    print("TEST: Product with Regex Validation (SKU)")
    print("="*70)

    data = {
        "name": "Widget Pro",
        "description": "A professional widget",
        "price": 29.99,
        "stock": 100,
        "tags": ["hardware", "tools"],
        "sku": "ABC-1234"  # Must match pattern [A-Z]{3}-\d{4}
    }

    response = requests.post(f"{BASE_URL}/products", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    print("✅ PASS: Regex validation works!")


def test_product_invalid_sku():
    """Test invalid SKU pattern"""
    print("\n" + "="*70)
    print("TEST: Invalid SKU Pattern")
    print("="*70)

    data = {
        "name": "Widget",
        "price": 10.0,
        "stock": 50,
        "tags": [],
        "sku": "invalid"  # Doesn't match pattern
    }

    response = requests.post(f"{BASE_URL}/products", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 422
    print("✅ PASS: Invalid SKU rejected!")


def test_product_price_validation():
    """Test price must be greater than 0"""
    print("\n" + "="*70)
    print("TEST: Price Must Be Positive")
    print("="*70)

    data = {
        "name": "Free Widget",
        "price": 0,  # Must be > 0
        "stock": 10,
        "tags": [],
        "sku": "FRE-0000"
    }

    response = requests.post(f"{BASE_URL}/products", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 422
    print("✅ PASS: Zero price rejected!")


def test_list_users():
    """Test listing all users"""
    print("\n" + "="*70)
    print("TEST: List All Users")
    print("="*70)

    response = requests.get(f"{BASE_URL}/users")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Found {result['count']} users")

    assert response.status_code == 200
    assert "users" in result
    print("✅ PASS: List users works!")


def run_all_tests():
    print("\n" + "🚀 " * 20)
    print("PYDANTIC V2 COMPATIBILITY TEST SUITE")
    print("🚀 " * 20)

    # Wait for server
    print("\nWaiting for server...")
    for i in range(10):
        try:
            response = requests.get(f"{BASE_URL}/", timeout=2)
            if response.status_code == 200:
                print("✅ Server ready!")
                break
        except:
            print(f"Waiting... ({i+1}/10)")
            time.sleep(1)
    else:
        print("❌ Server not responding!")
        return

    tests = [
        ("Type Coercion", test_create_user_with_type_coercion),
        ("Nested Models", test_nested_model),
        ("Validation - Short Username", test_validation_error_min_length),
        ("Validation - Underage", test_validation_error_age),
        ("Optional Fields", test_optional_fields),
        ("Regex Validation", test_product_with_regex),
        ("Invalid SKU", test_product_invalid_sku),
        ("Price Validation", test_product_price_validation),
        ("List Users", test_list_users),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"❌ ERROR: {e}")

    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")
    print("="*70)

    if failed == 0:
        print("\n🎉 All Pydantic v2 compatibility tests passed!")
        print("\n📋 Features Validated:")
        print("  ✅ Type coercion (str -> int, bool)")
        print("  ✅ Nested models")
        print("  ✅ Optional fields")
        print("  ✅ Default values")
        print("  ✅ List types")
        print("  ✅ Field validation (min_length, ge, gt, regex)")
        print("  ✅ Automatic validation")
        print("  ✅ Automatic serialization")
        print("  ✅ ValidationError with 422 status")


if __name__ == "__main__":
    run_all_tests()
