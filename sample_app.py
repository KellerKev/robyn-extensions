#!/usr/bin/env python3
"""
Sample Robyn web application demonstrating validation features
"""

from robyn import Robyn, Request, Response, jsonify
from robyn_extensions import Validator
import json

app = Robyn(__file__)

# Create validators for different endpoints
user_validator = Validator()
user_validator.add_field("username", ["required", "min_length:3", "max_length:20"])
user_validator.add_field("email", ["required", "email"])
user_validator.add_field("age", ["required", "ge:18", "le:120"])

product_validator = Validator()
product_validator.add_field("name", ["required", "min_length:2"])
product_validator.add_field("price", ["required", "gt:0"])
product_validator.add_field("quantity", ["required", "multiple_of:1", "ge:0"])
product_validator.add_field("sku", ["required", "starts_with:SKU-"])

contact_validator = Validator()
contact_validator.add_field("name", ["required", "min_length:2"])
contact_validator.add_field("email", ["required", "email"])
contact_validator.add_field("website", ["url"])
contact_validator.add_field("message", ["required", "min_length:10", "max_length:500"])

score_validator = Validator()
score_validator.add_field("score", ["required", "gt:0", "lt:100"])
score_validator.add_field("rating", ["required", "ge:1", "le:5"])


@app.get("/")
def index(request: Request):
    return """
    <html>
    <head><title>Robyn Validation API</title></head>
    <body>
        <h1>Robyn Extensions - Validation API Demo</h1>
        <h2>Available Endpoints:</h2>
        <ul>
            <li><b>POST /api/users</b> - Create user (username, email, age)</li>
            <li><b>POST /api/products</b> - Create product (name, price, quantity, sku)</li>
            <li><b>POST /api/contact</b> - Contact form (name, email, website, message)</li>
            <li><b>POST /api/scores</b> - Submit score (score, rating)</li>
            <li><b>GET /health</b> - Health check</li>
        </ul>
        <h3>Example request:</h3>
        <pre>
curl -X POST http://localhost:8080/api/users \\
  -H "Content-Type: application/json" \\
  -d '{"username": "johndoe", "email": "john@example.com", "age": 25}'
        </pre>
    </body>
    </html>
    """


@app.get("/health")
def health(request: Request):
    return jsonify({"status": "healthy", "service": "robyn-validation-api"})


@app.post("/api/users")
def create_user(request: Request):
    """Create a new user with validation"""
    try:
        # Parse request body
        data = json.loads(request.body)

        # Validate
        errors = user_validator.validate(data)

        if errors:
            error_list = [
                {
                    "field": err.field,
                    "message": err.message,
                    "type": err.error_type
                }
                for err in errors
            ]
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({
                    "error": "Validation failed",
                    "errors": error_list
                })
            )

        # Success - return created user
        return Response(
            status_code=201,
            headers={"Content-Type": "application/json"},
            description=json.dumps({
                "success": True,
                "message": "User created successfully",
                "data": data
            })
        )

    except json.JSONDecodeError:
        return Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": "Invalid JSON"})
        )
    except Exception as e:
        return Response(
            status_code=500,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(e)})
        )


@app.post("/api/products")
def create_product(request: Request):
    """Create a new product with validation"""
    try:
        data = json.loads(request.body)
        errors = product_validator.validate(data)

        if errors:
            error_list = [
                {
                    "field": err.field,
                    "message": err.message,
                    "type": err.error_type
                }
                for err in errors
            ]
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({
                    "error": "Validation failed",
                    "errors": error_list
                })
            )

        return Response(
            status_code=201,
            headers={"Content-Type": "application/json"},
            description=json.dumps({
                "success": True,
                "message": "Product created successfully",
                "data": data
            })
        )

    except json.JSONDecodeError:
        return Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": "Invalid JSON"})
        )
    except Exception as e:
        return Response(
            status_code=500,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(e)})
        )


@app.post("/api/contact")
def contact_form(request: Request):
    """Submit contact form with validation"""
    try:
        data = json.loads(request.body)
        errors = contact_validator.validate(data)

        if errors:
            error_list = [
                {
                    "field": err.field,
                    "message": err.message,
                    "type": err.error_type
                }
                for err in errors
            ]
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({
                    "error": "Validation failed",
                    "errors": error_list
                })
            )

        return Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            description=json.dumps({
                "success": True,
                "message": "Contact form submitted successfully"
            })
        )

    except json.JSONDecodeError:
        return Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": "Invalid JSON"})
        )
    except Exception as e:
        return Response(
            status_code=500,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(e)})
        )


@app.post("/api/scores")
def submit_score(request: Request):
    """Submit a score with validation"""
    try:
        data = json.loads(request.body)
        errors = score_validator.validate(data)

        if errors:
            error_list = [
                {
                    "field": err.field,
                    "message": err.message,
                    "type": err.error_type
                }
                for err in errors
            ]
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({
                    "error": "Validation failed",
                    "errors": error_list
                })
            )

        return Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            description=json.dumps({
                "success": True,
                "message": "Score submitted successfully",
                "data": data
            })
        )

    except json.JSONDecodeError:
        return Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": "Invalid JSON"})
        )
    except Exception as e:
        return Response(
            status_code=500,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(e)})
        )


if __name__ == "__main__":
    print("🚀 Starting Robyn Validation API Server...")
    print("📍 Server running at: http://localhost:8080")
    print("📖 API docs: http://localhost:8080/")
    app.start(host="0.0.0.0", port=8080)
