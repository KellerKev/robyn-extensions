"""
Enhanced decorators with automatic Pydantic-like validation for Robyn
"""

from functools import wraps
from robyn import Request, Response
import json
import inspect
from typing import get_type_hints
from .models import BaseModel, ValidationError


def body(model_class: type[BaseModel]):
    """
    Decorator for automatic request body validation using BaseModel

    Usage:
        @app.post("/users")
        @body_v2(UserModel)
        def create_user(request: Request, user: UserModel):
            return Response(...)

    Note: The validated model is attached to request.validated_data
    """
    def decorator(func):
        # Get function signature to find parameter name
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        # Find the model parameter name (should be second param after 'request')
        model_param_name = None
        if len(param_names) > 1 and param_names[0] == 'request':
            model_param_name = param_names[1]

        @wraps(func)
        def wrapper(request: Request):
            try:
                # Parse request body
                data = json.loads(request.body)

                # Validate and create model instance
                model_instance = model_class(**data)

                # Call original function with validated model as kwarg
                if model_param_name:
                    return func(request, **{model_param_name: model_instance})
                else:
                    return func(request)

            except json.JSONDecodeError:
                return Response(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    description=json.dumps({"error": "Invalid JSON"})
                )
            except ValidationError as e:
                return Response(
                    status_code=422,
                    headers={"Content-Type": "application/json"},
                    description=json.dumps({
                        "error": "Validation failed",
                        "detail": e.errors
                    })
                )
            except Exception as e:
                return Response(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    description=json.dumps({"error": str(e)})
                )

        # Override the signature so Robyn only sees (request: Request)
        wrapper.__wrapped__ = func
        wrapper.__signature__ = inspect.Signature(
            parameters=[inspect.Parameter('request', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request)]
        )
        return wrapper
    return decorator


def validated_route(func):
    """
    Decorator that automatically validates based on type hints (FastAPI-style)

    Usage:
        @app.post("/users")
        @validated_route
        def create_user(request: Request, user: UserModel):
            return user.model_dump()
    """
    # Get type hints
    hints = get_type_hints(func)
    sig = inspect.signature(func)

    # Find BaseModel parameters
    model_params = {}
    for param_name, param in sig.parameters.items():
        if param_name == 'request':
            continue
        param_type = hints.get(param_name)
        if param_type and inspect.isclass(param_type) and issubclass(param_type, BaseModel):
            model_params[param_name] = param_type

    @wraps(func)
    def wrapper(request: Request):
        try:
            # Parse request body for POST/PUT/PATCH
            if request.method in ['POST', 'PUT', 'PATCH']:
                data = json.loads(request.body)

                # Validate each model parameter
                validated_kwargs = {}
                for param_name, model_class in model_params.items():
                    model_instance = model_class(**data)
                    validated_kwargs[param_name] = model_instance

                # Call original function
                result = func(request, **validated_kwargs)

                # Auto-serialize if result is BaseModel
                if isinstance(result, BaseModel):
                    return Response(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        description=result.model_dump_json()
                    )
                elif isinstance(result, dict):
                    return Response(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        description=json.dumps(result)
                    )
                return result
            else:
                return func(request)

        except json.JSONDecodeError:
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": "Invalid JSON"})
            )
        except ValidationError as e:
            return Response(
                status_code=422,
                headers={"Content-Type": "application/json"},
                description=json.dumps({
                    "error": "Validation failed",
                    "detail": e.errors
                })
            )
        except Exception as e:
            return Response(
                status_code=500,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": str(e)})
            )

    # Override the signature so Robyn only sees (request: Request)
    wrapper.__wrapped__ = func
    wrapper.__signature__ = inspect.Signature(
        parameters=[inspect.Parameter('request', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request)]
    )
    return wrapper


def returns(model_class: type[BaseModel]):
    """
    Decorator for automatic response serialization

    Usage:
        @app.get("/users/{id}")
        @returns(UserModel)
        def get_user(request: Request):
            return UserModel(username="john", email="john@example.com", age=25)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # If result is already a Response, return as-is
            if isinstance(result, Response):
                return result

            # If result is BaseModel, serialize it
            if isinstance(result, BaseModel):
                return Response(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    description=result.model_dump_json()
                )

            # If result is dict or list, serialize it
            if isinstance(result, (dict, list)):
                return Response(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    description=json.dumps(result, default=str)
                )

            return result

        return wrapper
    return decorator
