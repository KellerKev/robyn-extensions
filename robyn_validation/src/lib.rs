use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationError {
    pub field: String,
    pub message: String,
    pub error_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub input: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub context: Option<HashMap<String, String>>,
}

impl ValidationError {
    pub fn new(field: impl Into<String>, message: impl Into<String>, error_type: impl Into<String>) -> Self {
        Self {
            field: field.into(),
            message: message.into(),
            error_type: error_type.into(),
            input: None,
            context: None,
        }
    }

    pub fn with_input(mut self, input: impl Into<String>) -> Self {
        self.input = Some(input.into());
        self
    }

    pub fn with_context(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.context.get_or_insert_with(HashMap::new)
            .insert(key.into(), value.into());
        self
    }
}

#[derive(Debug, Error)]
pub enum ValidationErrors {
    #[error("Validation failed with {} errors", .0.len())]
    Multiple(Vec<ValidationError>),
    #[error("JSON parsing error: {0}")]
    ParseError(String),
}

pub trait Validator {
    fn validate(&self) -> Result<(), ValidationErrors>;
}

pub trait FromRequest: Sized {
    fn from_json(json: &str) -> Result<Self, ValidationErrors>;
    fn from_dict(data: HashMap<String, Value>) -> Result<Self, ValidationErrors>;
}

/// Validation rules that can be applied to fields
#[derive(Debug, Clone)]
pub enum ValidationRule {
    Required,
    MinLength(usize),
    MaxLength(usize),
    Min(f64),
    Max(f64),
    Email,
    Url,
    Regex(String),
    Pattern(String),
    Custom(fn(&Value) -> bool),
    // Pydantic-like validators
    Gt(f64),  // Greater than
    Ge(f64),  // Greater than or equal
    Lt(f64),  // Less than
    Le(f64),  // Less than or equal
    MultipleOf(f64),
    StrContains(String),
    StrStartsWith(String),
    StrEndsWith(String),
}

pub struct FieldValidator {
    rules: Vec<ValidationRule>,
}

impl FieldValidator {
    pub fn new() -> Self {
        Self { rules: Vec::new() }
    }

    pub fn add_rule(mut self, rule: ValidationRule) -> Self {
        self.rules.push(rule);
        self
    }

    pub fn validate(&self, field_name: &str, value: &Value) -> Result<(), ValidationError> {
        for rule in &self.rules {
            match rule {
                ValidationRule::Required => {
                    if value.is_null() {
                        return Err(ValidationError::new(field_name, "Field is required", "required"));
                    }
                }
                ValidationRule::MinLength(min) => {
                    if let Some(s) = value.as_str() {
                        if s.len() < *min {
                            return Err(ValidationError::new(
                                field_name,
                                format!("String length must be at least {}", min),
                                "min_length"
                            ).with_context("min_length", min.to_string()));
                        }
                    }
                }
                ValidationRule::MaxLength(max) => {
                    if let Some(s) = value.as_str() {
                        if s.len() > *max {
                            return Err(ValidationError::new(
                                field_name,
                                format!("String length must be at most {}", max),
                                "max_length"
                            ).with_context("max_length", max.to_string()));
                        }
                    }
                }
                ValidationRule::Min(min) | ValidationRule::Ge(min) => {
                    if let Some(n) = value.as_f64() {
                        if n < *min {
                            return Err(ValidationError::new(
                                field_name,
                                format!("Value must be at least {}", min),
                                "min_value"
                            ).with_context("min", min.to_string()));
                        }
                    }
                }
                ValidationRule::Max(max) | ValidationRule::Le(max) => {
                    if let Some(n) = value.as_f64() {
                        if n > *max {
                            return Err(ValidationError::new(
                                field_name,
                                format!("Value must be at most {}", max),
                                "max_value"
                            ).with_context("max", max.to_string()));
                        }
                    }
                }
                ValidationRule::Gt(val) => {
                    if let Some(n) = value.as_f64() {
                        if n <= *val {
                            return Err(ValidationError::new(
                                field_name,
                                format!("Value must be greater than {}", val),
                                "greater_than"
                            ).with_context("gt", val.to_string()));
                        }
                    }
                }
                ValidationRule::Lt(val) => {
                    if let Some(n) = value.as_f64() {
                        if n >= *val {
                            return Err(ValidationError::new(
                                field_name,
                                format!("Value must be less than {}", val),
                                "less_than"
                            ).with_context("lt", val.to_string()));
                        }
                    }
                }
                ValidationRule::MultipleOf(multiple) => {
                    if let Some(n) = value.as_f64() {
                        if (n % multiple).abs() > f64::EPSILON {
                            return Err(ValidationError::new(
                                field_name,
                                format!("Value must be a multiple of {}", multiple),
                                "multiple_of"
                            ).with_context("multiple_of", multiple.to_string()));
                        }
                    }
                }
                ValidationRule::Email => {
                    if let Some(s) = value.as_str() {
                        let email_regex = regex::Regex::new(
                            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                        ).unwrap();
                        if !email_regex.is_match(s) {
                            return Err(ValidationError::new(field_name, "Invalid email format", "email")
                                .with_input(s));
                        }
                    }
                }
                ValidationRule::Url => {
                    if let Some(s) = value.as_str() {
                        let url_regex = regex::Regex::new(
                            r"^https?://[^\s/$.?#].[^\s]*$"
                        ).unwrap();
                        if !url_regex.is_match(s) {
                            return Err(ValidationError::new(field_name, "Invalid URL format", "url")
                                .with_input(s));
                        }
                    }
                }
                ValidationRule::Regex(pattern) | ValidationRule::Pattern(pattern) => {
                    if let Some(s) = value.as_str() {
                        let re = regex::Regex::new(pattern).map_err(|_|
                            ValidationError::new(field_name, "Invalid regex pattern", "regex")
                        )?;
                        if !re.is_match(s) {
                            return Err(ValidationError::new(
                                field_name,
                                format!("Does not match pattern: {}", pattern),
                                "pattern"
                            ).with_context("pattern", pattern.clone()).with_input(s));
                        }
                    }
                }
                ValidationRule::StrContains(substr) => {
                    if let Some(s) = value.as_str() {
                        if !s.contains(substr) {
                            return Err(ValidationError::new(
                                field_name,
                                format!("String must contain '{}'", substr),
                                "str_contains"
                            ).with_context("contains", substr.clone()));
                        }
                    }
                }
                ValidationRule::StrStartsWith(prefix) => {
                    if let Some(s) = value.as_str() {
                        if !s.starts_with(prefix) {
                            return Err(ValidationError::new(
                                field_name,
                                format!("String must start with '{}'", prefix),
                                "str_starts_with"
                            ).with_context("starts_with", prefix.clone()));
                        }
                    }
                }
                ValidationRule::StrEndsWith(suffix) => {
                    if let Some(s) = value.as_str() {
                        if !s.ends_with(suffix) {
                            return Err(ValidationError::new(
                                field_name,
                                format!("String must end with '{}'", suffix),
                                "str_ends_with"
                            ).with_context("ends_with", suffix.clone()));
                        }
                    }
                }
                ValidationRule::Custom(func) => {
                    if !func(value) {
                        return Err(ValidationError::new(field_name, "Custom validation failed", "custom"));
                    }
                }
            }
        }
        Ok(())
    }
}

/// Schema validation for complex objects
pub struct SchemaValidator {
    fields: HashMap<String, FieldValidator>,
}

impl SchemaValidator {
    pub fn new() -> Self {
        Self {
            fields: HashMap::new(),
        }
    }

    pub fn add_field(mut self, name: String, validator: FieldValidator) -> Self {
        self.fields.insert(name, validator);
        self
    }

    pub fn validate(&self, data: &HashMap<String, Value>) -> Result<(), ValidationErrors> {
        let mut errors = Vec::new();

        for (field_name, validator) in &self.fields {
            let value = data.get(field_name).unwrap_or(&Value::Null);
            if let Err(e) = validator.validate(field_name, value) {
                errors.push(e);
            }
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(ValidationErrors::Multiple(errors))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_required_validation() {
        let validator = FieldValidator::new().add_rule(ValidationRule::Required);
        assert!(validator.validate("test", &Value::Null).is_err());
        assert!(validator.validate("test", &Value::String("value".to_string())).is_ok());
    }

    #[test]
    fn test_min_length_validation() {
        let validator = FieldValidator::new().add_rule(ValidationRule::MinLength(5));
        assert!(validator.validate("test", &Value::String("abc".to_string())).is_err());
        assert!(validator.validate("test", &Value::String("abcdef".to_string())).is_ok());
    }

    #[test]
    fn test_email_validation() {
        let validator = FieldValidator::new().add_rule(ValidationRule::Email);
        assert!(validator.validate("email", &Value::String("test@example.com".to_string())).is_ok());
        assert!(validator.validate("email", &Value::String("invalid".to_string())).is_err());
    }

    #[test]
    fn test_schema_validation() {
        let mut data = HashMap::new();
        data.insert("name".to_string(), Value::String("John".to_string()));
        data.insert("age".to_string(), Value::Number(serde_json::Number::from(25)));

        let schema = SchemaValidator::new()
            .add_field(
                "name".to_string(),
                FieldValidator::new()
                    .add_rule(ValidationRule::Required)
                    .add_rule(ValidationRule::MinLength(2)),
            )
            .add_field(
                "age".to_string(),
                FieldValidator::new()
                    .add_rule(ValidationRule::Required)
                    .add_rule(ValidationRule::Min(18.0)),
            );

        assert!(schema.validate(&data).is_ok());
    }
}
