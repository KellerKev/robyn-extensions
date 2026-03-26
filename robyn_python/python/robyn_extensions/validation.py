"""
Validation utilities for Pydantic models.
"""

from typing import Type, Dict, Any
from pydantic import BaseModel, ValidationError


def validate_model(model: Type[BaseModel], data: Any) -> BaseModel:
    """
    Validate data against a Pydantic model.
    
    Args:
        model: Pydantic model class
        data: Data to validate (dict, JSON string, or object)
    
    Returns:
        Validated model instance
    
    Raises:
        ValidationError: If validation fails
    """
    if isinstance(data, str):
        return model.model_validate_json(data)
    elif isinstance(data, dict):
        return model.model_validate(data)
    else:
        return model.model_validate(data)


def get_validation_errors(model: Type[BaseModel], data: Any) -> Dict[str, Any]:
    """
    Get validation errors without raising exceptions.
    
    Args:
        model: Pydantic model class
        data: Data to validate
    
    Returns:
        Dict with 'valid' boolean and 'errors' list
    """
    try:
        validate_model(model, data)
        return {"valid": True, "errors": []}
    except ValidationError as e:
        return {
            "valid": False,
            "errors": e.errors()
        }
