"""
Pydantic v2-like BaseModel implementation for Robyn
Provides drop-in compatible syntax with automatic validation
"""

from typing import Any, Dict, List, Optional, Union, get_type_hints, get_origin, get_args, Callable
from datetime import datetime, date
from enum import Enum
import json
from dataclasses import dataclass, field as dataclass_field
import inspect
from functools import wraps


class ValidationError(Exception):
    """Raised when validation fails"""
    def __init__(self, errors: List[Dict[str, Any]]):
        self.errors = errors
        super().__init__(f"Validation failed with {len(errors)} error(s)")

    def __str__(self):
        return f"ValidationError: {self.errors}"


@dataclass
class FieldInfo:
    """Information about a model field"""
    default: Any = None
    default_factory: Any = None
    alias: Optional[str] = None
    description: Optional[str] = None
    gt: Optional[float] = None
    ge: Optional[float] = None
    lt: Optional[float] = None
    le: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex: Optional[str] = None

    def has_default(self) -> bool:
        return self.default is not None or self.default_factory is not None

    def get_default(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        return self.default


def computed_field(func: Callable) -> property:
    """
    Decorator for computed fields (Pydantic v2 compatible)

    Usage:
        class User(BaseModel):
            first_name: str
            last_name: str

            @computed_field
            @property
            def full_name(self) -> str:
                return f"{self.first_name} {self.last_name}"
    """
    # If already a property, mark its fget function
    if isinstance(func, property):
        func.fget._is_computed_field = True
        return func
    # Otherwise mark the function and return as property
    func._is_computed_field = True
    return property(func)


def field_validator(*fields: str, mode: str = 'after'):
    """
    Decorator for field validators (Pydantic v2 compatible)

    Args:
        *fields: Field names to validate
        mode: 'before' (before type coercion) or 'after' (after type coercion)

    Usage:
        class User(BaseModel):
            username: str

            @field_validator('username')
            @classmethod
            def validate_username(cls, v):
                if 'admin' in v.lower():
                    raise ValueError('Username cannot contain "admin"')
                return v
    """
    def decorator(func: Callable) -> Callable:
        func._is_field_validator = True
        func._validator_fields = fields
        func._validator_mode = mode
        return func
    return decorator


def model_validator(*, mode: str = 'after'):
    """
    Decorator for model-level validators (Pydantic v2 compatible)

    Args:
        mode: 'before' (before field validation) or 'after' (after field validation)

    Usage:
        class User(BaseModel):
            password: str
            password_confirm: str

            @model_validator(mode='after')
            def check_passwords_match(self):
                if self.password != self.password_confirm:
                    raise ValueError('Passwords do not match')
                return self
    """
    def decorator(func: Callable) -> Callable:
        func._is_model_validator = True
        func._validator_mode = mode
        return func
    return decorator


def Field(
    default: Any = None,
    *,
    default_factory: Any = None,
    alias: Optional[str] = None,
    description: Optional[str] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None,
    **kwargs
) -> FieldInfo:
    """
    Define a field with validation constraints (Pydantic-compatible)

    Example:
        class User(BaseModel):
            age: int = Field(ge=18, le=120)
            username: str = Field(min_length=3, max_length=20)
    """
    return FieldInfo(
        default=default,
        default_factory=default_factory,
        alias=alias,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex
    )


class BaseModelMeta(type):
    """Metaclass for BaseModel to collect field information"""

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace)

        # Collect fields from type hints
        hints = get_type_hints(cls) if hasattr(cls, '__annotations__') else {}
        fields = {}

        # Collect validators
        field_validators = {}
        model_validators = []
        computed_fields = {}

        # Scan all class attributes
        for attr_name, attr_value in namespace.items():
            # Check for field validators
            if hasattr(attr_value, '_is_field_validator'):
                for field in attr_value._validator_fields:
                    if field not in field_validators:
                        field_validators[field] = []
                    field_validators[field].append({
                        'func': attr_value,
                        'mode': attr_value._validator_mode
                    })

            # Check for model validators
            if hasattr(attr_value, '_is_model_validator'):
                model_validators.append({
                    'func': attr_value,
                    'mode': attr_value._validator_mode
                })

            # Check for computed fields
            if isinstance(attr_value, property) and hasattr(attr_value.fget, '_is_computed_field'):
                computed_fields[attr_name] = attr_value

        for field_name, field_type in hints.items():
            if field_name.startswith('_'):
                continue

            # Skip computed fields
            if field_name in computed_fields:
                continue

            # Get field info if defined
            field_value = namespace.get(field_name)
            if isinstance(field_value, FieldInfo):
                field_info = field_value
            else:
                # Create default field info
                field_info = FieldInfo(default=field_value if field_value is not None else None)

            fields[field_name] = {
                'type': field_type,
                'info': field_info,
                'required': not field_info.has_default() and not _is_optional(field_type)
            }

        cls.__fields__ = fields
        cls.__field_validators__ = field_validators
        cls.__model_validators__ = model_validators
        cls.__computed_fields__ = computed_fields
        return cls


def _is_optional(type_hint) -> bool:
    """Check if a type hint is Optional"""
    origin = get_origin(type_hint)
    if origin is Union:
        args = get_args(type_hint)
        return type(None) in args
    return False


def _get_inner_type(type_hint):
    """Get the inner type from Optional, List, etc."""
    origin = get_origin(type_hint)

    if origin is Union:
        # Optional[X] is Union[X, None]
        args = get_args(type_hint)
        return [arg for arg in args if arg is not type(None)][0]

    if origin in (list, List):
        args = get_args(type_hint)
        return args[0] if args else Any

    if origin in (dict, Dict):
        args = get_args(type_hint)
        return args if args else (Any, Any)

    return type_hint


def _coerce_type(value: Any, target_type: Any) -> Any:
    """Coerce a value to the target type (Pydantic-like behavior)"""

    # Handle None for optional types
    if value is None:
        return None

    # Get the actual type if it's wrapped in Optional, List, etc.
    inner_type = _get_inner_type(target_type)
    origin = get_origin(target_type)

    # Handle complex types
    if origin in (list, List):
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        item_type = get_args(target_type)[0] if get_args(target_type) else Any
        return [_coerce_type(item, item_type) for item in value]

    if origin in (dict, Dict):
        if not isinstance(value, dict):
            raise ValueError(f"Expected dict, got {type(value)}")
        return value  # TODO: Validate key/value types

    # Handle BaseModel (nested models)
    if inspect.isclass(inner_type) and issubclass(inner_type, BaseModel):
        if isinstance(value, dict):
            return inner_type(**value)
        elif isinstance(value, inner_type):
            return value
        else:
            raise ValueError(f"Expected {inner_type.__name__} or dict, got {type(value)}")

    # String coercion
    if inner_type is str:
        return str(value)

    # Integer coercion
    if inner_type is int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, str):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        raise ValueError(f"Cannot convert {value} to int")

    # Float coercion
    if inner_type is float:
        if isinstance(value, str):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        raise ValueError(f"Cannot convert {value} to float")

    # Boolean coercion
    if inner_type is bool:
        if isinstance(value, str):
            lower = value.lower()
            if lower in ('true', '1', 'yes', 'on'):
                return True
            if lower in ('false', '0', 'no', 'off'):
                return False
            raise ValueError(f"Cannot convert '{value}' to bool")
        return bool(value)

    # Datetime coercion
    if inner_type is datetime:
        if isinstance(value, str):
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Cannot parse datetime from '{value}'")
        if isinstance(value, datetime):
            return value
        raise ValueError(f"Cannot convert {value} to datetime")

    # Date coercion
    if inner_type is date:
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        if isinstance(value, date):
            return value
        raise ValueError(f"Cannot convert {value} to date")

    # Enum coercion
    if inspect.isclass(inner_type) and issubclass(inner_type, Enum):
        if isinstance(value, str):
            return inner_type[value]
        if isinstance(value, inner_type):
            return value
        raise ValueError(f"Cannot convert {value} to {inner_type.__name__}")

    # Default: return as-is
    return value


def _validate_field(field_name: str, value: Any, field_info: FieldInfo) -> List[str]:
    """Validate a single field value"""
    errors = []

    # String validations
    if isinstance(value, str):
        if field_info.min_length is not None and len(value) < field_info.min_length:
            errors.append(f"String length must be at least {field_info.min_length}")
        if field_info.max_length is not None and len(value) > field_info.max_length:
            errors.append(f"String length must be at most {field_info.max_length}")
        if field_info.regex is not None:
            import re
            if not re.match(field_info.regex, value):
                errors.append(f"String does not match pattern: {field_info.regex}")

    # Numeric validations
    if isinstance(value, (int, float)):
        if field_info.gt is not None and value <= field_info.gt:
            errors.append(f"Value must be greater than {field_info.gt}")
        if field_info.ge is not None and value < field_info.ge:
            errors.append(f"Value must be at least {field_info.ge}")
        if field_info.lt is not None and value >= field_info.lt:
            errors.append(f"Value must be less than {field_info.lt}")
        if field_info.le is not None and value > field_info.le:
            errors.append(f"Value must be at most {field_info.le}")

    return errors


class BaseModel(metaclass=BaseModelMeta):
    """
    Pydantic v2-compatible BaseModel for Robyn

    Example:
        class User(BaseModel):
            username: str = Field(min_length=3, max_length=20)
            email: str
            age: int = Field(ge=18, le=120)
            tags: List[str] = []

        user = User(username="john", email="john@example.com", age=25)
        print(user.model_dump())
    """

    def __init__(self, **data):
        errors = []

        # Process each field
        for field_name, field_config in self.__fields__.items():
            field_type = field_config['type']
            field_info = field_config['info']
            is_required = field_config['required']

            # Check alias
            source_name = field_info.alias or field_name

            # Get value from data
            if source_name in data:
                raw_value = data[source_name]
            elif field_info.has_default():
                raw_value = field_info.get_default()
            elif not is_required:
                raw_value = None
            else:
                errors.append({
                    'field': field_name,
                    'message': 'Field is required',
                    'type': 'missing'
                })
                continue

            # Type coercion
            try:
                value = _coerce_type(raw_value, field_type)
            except (ValueError, TypeError) as e:
                errors.append({
                    'field': field_name,
                    'message': str(e),
                    'type': 'type_error'
                })
                continue

            # Validate constraints
            field_errors = _validate_field(field_name, value, field_info)
            for error_msg in field_errors:
                errors.append({
                    'field': field_name,
                    'message': error_msg,
                    'type': 'value_error'
                })

            # Run field validators (after mode)
            if hasattr(self.__class__, '__field_validators__') and field_name in self.__class__.__field_validators__:
                validators = self.__class__.__field_validators__[field_name]
                for validator_info in validators:
                    if validator_info['mode'] == 'after':
                        try:
                            # Handle classmethod - get the actual function
                            validator_func = validator_info['func']
                            if isinstance(validator_func, classmethod):
                                validator_func = validator_func.__func__
                            value = validator_func(self.__class__, value)
                        except ValueError as e:
                            errors.append({
                                'field': field_name,
                                'message': str(e),
                                'type': 'value_error'
                            })

            # Set the value
            setattr(self, field_name, value)

        if errors:
            raise ValidationError(errors)

        # Run model validators (after mode)
        if hasattr(self.__class__, '__model_validators__'):
            for validator_info in self.__class__.__model_validators__:
                if validator_info['mode'] == 'after':
                    try:
                        result = validator_info['func'](self)
                        if result is not None and result != self:
                            # If validator returns a model, use it
                            for field_name in self.__fields__:
                                setattr(self, field_name, getattr(result, field_name))
                    except ValueError as e:
                        raise ValidationError([{
                            'field': '__root__',
                            'message': str(e),
                            'type': 'value_error'
                        }])

    def model_dump(self, *, exclude_none: bool = False) -> Dict[str, Any]:
        """Convert model to dictionary (Pydantic-compatible)"""
        result = {}

        # Include regular fields
        for field_name in self.__fields__:
            value = getattr(self, field_name, None)

            if exclude_none and value is None:
                continue

            # Handle nested models
            if isinstance(value, BaseModel):
                value = value.model_dump(exclude_none=exclude_none)
            elif isinstance(value, list):
                value = [
                    item.model_dump(exclude_none=exclude_none) if isinstance(item, BaseModel) else item
                    for item in value
                ]

            result[field_name] = value

        # Include computed fields
        if hasattr(self.__class__, '__computed_fields__'):
            for field_name in self.__class__.__computed_fields__:
                value = getattr(self, field_name, None)
                if exclude_none and value is None:
                    continue
                result[field_name] = value

        return result

    def model_dump_json(self, *, exclude_none: bool = False) -> str:
        """Convert model to JSON string (Pydantic-compatible)"""
        return json.dumps(self.model_dump(exclude_none=exclude_none), default=str)

    @classmethod
    def model_validate(cls, data: Dict[str, Any]):
        """Validate and create model from dict (Pydantic-compatible)"""
        return cls(**data)

    @classmethod
    def model_validate_json(cls, json_data: str):
        """Validate and create model from JSON (Pydantic-compatible)"""
        data = json.loads(json_data)
        return cls(**data)

    def __repr__(self):
        fields = ', '.join(f"{k}={getattr(self, k)!r}" for k in self.__fields__)
        return f"{self.__class__.__name__}({fields})"

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return all(
            getattr(self, field) == getattr(other, field)
            for field in self.__fields__
        )

    @classmethod
    def model_json_schema(cls, *, by_alias: bool = True, ref_template: str = '#/$defs/{model}') -> Dict[str, Any]:
        """
        Generate JSON Schema for this model (Pydantic v2 compatible)

        Args:
            by_alias: Use field aliases in schema
            ref_template: Template for $ref URIs

        Returns:
            JSON Schema dictionary
        """
        schema = {
            "title": cls.__name__,
            "type": "object",
            "properties": {},
            "required": []
        }

        # Track nested models for $defs
        defs = {}

        def get_json_schema_type(field_type: Any, field_info: FieldInfo) -> Dict[str, Any]:
            """Convert Python type to JSON Schema type"""
            origin = get_origin(field_type)
            args = get_args(field_type)

            # Handle Optional[T]
            if origin is Union:
                non_none_types = [t for t in args if t is not type(None)]
                if len(non_none_types) == 1:
                    result = get_json_schema_type(non_none_types[0], field_info)
                    result["nullable"] = True
                    return result

            # Handle List[T]
            if origin is list or origin is List:
                item_schema = get_json_schema_type(args[0], field_info) if args else {"type": "string"}
                return {
                    "type": "array",
                    "items": item_schema
                }

            # Handle Dict[K, V]
            if origin is dict or origin is Dict:
                return {
                    "type": "object",
                    "additionalProperties": True
                }

            # Handle nested BaseModel
            if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
                # Add to $defs
                if field_type.__name__ not in defs:
                    defs[field_type.__name__] = field_type.model_json_schema(by_alias=by_alias, ref_template=ref_template)
                    # Remove $defs from nested schema to avoid duplication
                    if "$defs" in defs[field_type.__name__]:
                        nested_defs = defs[field_type.__name__].pop("$defs")
                        defs.update(nested_defs)

                return {"$ref": ref_template.format(model=field_type.__name__)}

            # Handle basic types
            type_map = {
                str: {"type": "string"},
                int: {"type": "integer"},
                float: {"type": "number"},
                bool: {"type": "boolean"},
                datetime: {"type": "string", "format": "date-time"},
                date: {"type": "string", "format": "date"},
            }

            result = type_map.get(field_type, {"type": "string"})

            # Add validation constraints
            if field_info.min_length is not None and "type" in result and result["type"] == "string":
                result["minLength"] = field_info.min_length
            if field_info.max_length is not None and "type" in result and result["type"] == "string":
                result["maxLength"] = field_info.max_length
            if field_info.regex is not None:
                result["pattern"] = field_info.regex
            if field_info.gt is not None:
                result["exclusiveMinimum"] = field_info.gt
            if field_info.ge is not None:
                result["minimum"] = field_info.ge
            if field_info.lt is not None:
                result["exclusiveMaximum"] = field_info.lt
            if field_info.le is not None:
                result["maximum"] = field_info.le
            if field_info.description is not None:
                result["description"] = field_info.description

            return result

        # Generate properties
        for field_name, field_config in cls.__fields__.items():
            field_type = field_config['type']
            field_info = field_config['info']
            is_required = field_config['required']

            # Use alias if specified and by_alias is True
            json_field_name = field_info.alias if (by_alias and field_info.alias) else field_name

            schema["properties"][json_field_name] = get_json_schema_type(field_type, field_info)

            # Add to required list if no default
            if is_required:
                schema["required"].append(json_field_name)

        # Add $defs if there are nested models
        if defs:
            schema["$defs"] = defs

        return schema
