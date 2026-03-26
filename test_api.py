#!/usr/bin/env python3
"""
Test script for the Robyn validation API
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8080"

def print_test(name: str):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)

def print_response(response: requests.Response):
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_health():
    print_test("Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response)
    assert response.status_code == 200

def test_valid_user():
    print_test("Valid User Creation")
    data = {
        "username": "johndoe",
        "email": "john@example.com",
        "age": 25
    }
    response = requests.post(f"{BASE_URL}/api/users", json=data)
    print_response(response)
    assert response.status_code == 201

def test_invalid_user_short_username():
    print_test("Invalid User - Short Username")
    data = {
        "username": "jo",  # Too short
        "email": "john@example.com",
        "age": 25
    }
    response = requests.post(f"{BASE_URL}/api/users", json=data)
    print_response(response)
    assert response.status_code == 400

def test_invalid_user_email():
    print_test("Invalid User - Bad Email")
    data = {
        "username": "johndoe",
        "email": "not-an-email",
        "age": 25
    }
    response = requests.post(f"{BASE_URL}/api/users", json=data)
    print_response(response)
    assert response.status_code == 400

def test_invalid_user_age():
    print_test("Invalid User - Age Too Young")
    data = {
        "username": "johndoe",
        "email": "john@example.com",
        "age": 15  # Under 18
    }
    response = requests.post(f"{BASE_URL}/api/users", json=data)
    print_response(response)
    assert response.status_code == 400

def test_invalid_user_multiple_errors():
    print_test("Invalid User - Multiple Errors")
    data = {
        "username": "jo",  # Too short
        "email": "bad-email",  # Invalid
        "age": 15  # Too young
    }
    response = requests.post(f"{BASE_URL}/api/users", json=data)
    print_response(response)
    assert response.status_code == 400
    data = response.json()
    assert len(data.get("errors", [])) == 3

def test_valid_product():
    print_test("Valid Product Creation")
    data = {
        "name": "Widget",
        "price": 19.99,
        "quantity": 10,
        "sku": "SKU-12345"
    }
    response = requests.post(f"{BASE_URL}/api/products", json=data)
    print_response(response)
    assert response.status_code == 201

def test_invalid_product_price():
    print_test("Invalid Product - Price Must Be Positive")
    data = {
        "name": "Widget",
        "price": 0,  # Must be > 0
        "quantity": 10,
        "sku": "SKU-12345"
    }
    response = requests.post(f"{BASE_URL}/api/products", json=data)
    print_response(response)
    assert response.status_code == 400

def test_invalid_product_sku():
    print_test("Invalid Product - SKU Must Start with 'SKU-'")
    data = {
        "name": "Widget",
        "price": 19.99,
        "quantity": 10,
        "sku": "12345"  # Should start with SKU-
    }
    response = requests.post(f"{BASE_URL}/api/products", json=data)
    print_response(response)
    assert response.status_code == 400

def test_valid_contact():
    print_test("Valid Contact Form")
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "website": "https://janedoe.com",
        "message": "This is a test message that is long enough to pass validation."
    }
    response = requests.post(f"{BASE_URL}/api/contact", json=data)
    print_response(response)
    assert response.status_code == 200

def test_invalid_contact_message():
    print_test("Invalid Contact - Message Too Short")
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "website": "https://janedoe.com",
        "message": "Short"  # Too short (min 10)
    }
    response = requests.post(f"{BASE_URL}/api/contact", json=data)
    print_response(response)
    assert response.status_code == 400

def test_invalid_contact_url():
    print_test("Invalid Contact - Bad URL")
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "website": "not-a-url",
        "message": "This is a valid message that is long enough."
    }
    response = requests.post(f"{BASE_URL}/api/contact", json=data)
    print_response(response)
    assert response.status_code == 400

def test_valid_score():
    print_test("Valid Score Submission")
    data = {
        "score": 85,
        "rating": 4
    }
    response = requests.post(f"{BASE_URL}/api/scores", json=data)
    print_response(response)
    assert response.status_code == 200

def test_invalid_score_boundary():
    print_test("Invalid Score - Must Be Between 0 and 100 (Exclusive)")
    data = {
        "score": 0,  # Must be > 0
        "rating": 3
    }
    response = requests.post(f"{BASE_URL}/api/scores", json=data)
    print_response(response)
    assert response.status_code == 400

def test_invalid_rating_range():
    print_test("Invalid Rating - Must Be Between 1 and 5 (Inclusive)")
    data = {
        "score": 50,
        "rating": 6  # Must be <= 5
    }
    response = requests.post(f"{BASE_URL}/api/scores", json=data)
    print_response(response)
    assert response.status_code == 400

def test_missing_fields():
    print_test("Missing Required Fields")
    data = {}
    response = requests.post(f"{BASE_URL}/api/users", json=data)
    print_response(response)
    assert response.status_code == 400

def test_invalid_json():
    print_test("Invalid JSON")
    response = requests.post(
        f"{BASE_URL}/api/users",
        data="not json",
        headers={"Content-Type": "application/json"}
    )
    print_response(response)
    assert response.status_code == 400


def run_all_tests():
    print("\n" + "🚀 " * 20)
    print("ROBYN VALIDATION API TEST SUITE")
    print("🚀 " * 20)

    # Wait for server to be ready
    print("\nWaiting for server to be ready...")
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is ready!")
                break
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                print(f"Waiting... ({i+1}/{max_retries})")
                time.sleep(1)
            else:
                print("❌ Server not responding. Please start the server first:")
                print("   pixi run python sample_app.py")
                return

    tests = [
        ("Health Check", test_health),
        ("Valid User", test_valid_user),
        ("Invalid User - Short Username", test_invalid_user_short_username),
        ("Invalid User - Bad Email", test_invalid_user_email),
        ("Invalid User - Age", test_invalid_user_age),
        ("Invalid User - Multiple Errors", test_invalid_user_multiple_errors),
        ("Valid Product", test_valid_product),
        ("Invalid Product - Price", test_invalid_product_price),
        ("Invalid Product - SKU", test_invalid_product_sku),
        ("Valid Contact", test_valid_contact),
        ("Invalid Contact - Message", test_invalid_contact_message),
        ("Invalid Contact - URL", test_invalid_contact_url),
        ("Valid Score", test_valid_score),
        ("Invalid Score - Boundary", test_invalid_score_boundary),
        ("Invalid Rating - Range", test_invalid_rating_range),
        ("Missing Fields", test_missing_fields),
        ("Invalid JSON", test_invalid_json),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✅ PASSED")
        except AssertionError as e:
            failed += 1
            print(f"❌ FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"❌ ERROR: {e}")
        time.sleep(0.1)  # Small delay between tests

    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")
    print("="*60)

    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")


if __name__ == "__main__":
    run_all_tests()
