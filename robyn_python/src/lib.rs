use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use std::sync::Arc;
use tokio::runtime::Runtime;

// Validation module
mod validation {
    use super::*;
    use robyn_validation::*;
    use serde_json::Value;
    use std::collections::HashMap;
    use pyo3::types::PyList;

    #[pyclass]
    #[derive(Clone)]
    pub struct ValidationError {
        #[pyo3(get)]
        pub field: String,
        #[pyo3(get)]
        pub message: String,
        #[pyo3(get)]
        pub error_type: String,
        #[pyo3(get)]
        pub input: Option<String>,
    }

    #[pymethods]
    impl ValidationError {
        fn __repr__(&self) -> String {
            format!("ValidationError(field='{}', type='{}', message='{}')",
                self.field, self.error_type, self.message)
        }

        fn to_dict(&self) -> HashMap<String, String> {
            let mut dict = HashMap::new();
            dict.insert("field".to_string(), self.field.clone());
            dict.insert("message".to_string(), self.message.clone());
            dict.insert("type".to_string(), self.error_type.clone());
            if let Some(input) = &self.input {
                dict.insert("input".to_string(), input.clone());
            }
            dict
        }
    }

    impl From<robyn_validation::ValidationError> for ValidationError {
        fn from(e: robyn_validation::ValidationError) -> Self {
            Self {
                field: e.field,
                message: e.message,
                error_type: e.error_type,
                input: e.input,
            }
        }
    }

    #[pyclass]
    pub struct Validator {
        schema: SchemaValidator,
    }

    #[pymethods]
    impl Validator {
        #[new]
        fn new() -> Self {
            Self {
                schema: SchemaValidator::new(),
            }
        }

        fn add_field(&mut self, name: String, rules: Vec<String>) -> PyResult<()> {
            let mut field_validator = FieldValidator::new();

            for rule in rules {
                let validation_rule = parse_rule(&rule)?;
                field_validator = field_validator.add_rule(validation_rule);
            }

            self.schema = std::mem::replace(&mut self.schema, SchemaValidator::new())
                .add_field(name, field_validator);
            Ok(())
        }

        fn validate(&self, data: &PyDict) -> PyResult<Vec<ValidationError>> {
            let mut hash_data = HashMap::new();

            for (key, value) in data.iter() {
                let key_str: String = key.extract()?;
                let value_json = python_to_json(value)?;
                hash_data.insert(key_str, value_json);
            }

            match self.schema.validate(&hash_data) {
                Ok(_) => Ok(Vec::new()),
                Err(robyn_validation::ValidationErrors::Multiple(errors)) => {
                    Ok(errors.into_iter().map(|e| e.into()).collect())
                }
                Err(e) => Err(PyValueError::new_err(format!("Validation error: {}", e))),
            }
        }

        fn validate_json(&self, json_str: &str) -> PyResult<Vec<ValidationError>> {
            let data: HashMap<String, Value> = serde_json::from_str(json_str)
                .map_err(|e| PyValueError::new_err(format!("Invalid JSON: {}", e)))?;

            match self.schema.validate(&data) {
                Ok(_) => Ok(Vec::new()),
                Err(robyn_validation::ValidationErrors::Multiple(errors)) => {
                    Ok(errors.into_iter().map(|e| e.into()).collect())
                }
                Err(e) => Err(PyValueError::new_err(format!("Validation error: {}", e))),
            }
        }
    }

    fn parse_rule(rule: &str) -> PyResult<ValidationRule> {
        let parts: Vec<&str> = rule.split(':').collect();
        match parts[0] {
            "required" => Ok(ValidationRule::Required),
            "email" => Ok(ValidationRule::Email),
            "url" => Ok(ValidationRule::Url),
            "min_length" if parts.len() > 1 => {
                let val = parts[1].parse::<usize>()
                    .map_err(|_| PyValueError::new_err("Invalid min_length value"))?;
                Ok(ValidationRule::MinLength(val))
            }
            "max_length" if parts.len() > 1 => {
                let val = parts[1].parse::<usize>()
                    .map_err(|_| PyValueError::new_err("Invalid max_length value"))?;
                Ok(ValidationRule::MaxLength(val))
            }
            "min" if parts.len() > 1 => {
                let val = parts[1].parse::<f64>()
                    .map_err(|_| PyValueError::new_err("Invalid min value"))?;
                Ok(ValidationRule::Min(val))
            }
            "max" if parts.len() > 1 => {
                let val = parts[1].parse::<f64>()
                    .map_err(|_| PyValueError::new_err("Invalid max value"))?;
                Ok(ValidationRule::Max(val))
            }
            "gt" if parts.len() > 1 => {
                let val = parts[1].parse::<f64>()
                    .map_err(|_| PyValueError::new_err("Invalid gt value"))?;
                Ok(ValidationRule::Gt(val))
            }
            "ge" if parts.len() > 1 => {
                let val = parts[1].parse::<f64>()
                    .map_err(|_| PyValueError::new_err("Invalid ge value"))?;
                Ok(ValidationRule::Ge(val))
            }
            "lt" if parts.len() > 1 => {
                let val = parts[1].parse::<f64>()
                    .map_err(|_| PyValueError::new_err("Invalid lt value"))?;
                Ok(ValidationRule::Lt(val))
            }
            "le" if parts.len() > 1 => {
                let val = parts[1].parse::<f64>()
                    .map_err(|_| PyValueError::new_err("Invalid le value"))?;
                Ok(ValidationRule::Le(val))
            }
            "multiple_of" if parts.len() > 1 => {
                let val = parts[1].parse::<f64>()
                    .map_err(|_| PyValueError::new_err("Invalid multiple_of value"))?;
                Ok(ValidationRule::MultipleOf(val))
            }
            "pattern" if parts.len() > 1 => {
                Ok(ValidationRule::Pattern(parts[1].to_string()))
            }
            "contains" if parts.len() > 1 => {
                Ok(ValidationRule::StrContains(parts[1].to_string()))
            }
            "starts_with" if parts.len() > 1 => {
                Ok(ValidationRule::StrStartsWith(parts[1].to_string()))
            }
            "ends_with" if parts.len() > 1 => {
                Ok(ValidationRule::StrEndsWith(parts[1].to_string()))
            }
            _ => Err(PyValueError::new_err(format!("Unknown validation rule: {}", rule)))
        }
    }

    fn python_to_json(value: &PyAny) -> PyResult<Value> {
        if value.is_none() {
            Ok(Value::Null)
        } else if let Ok(b) = value.extract::<bool>() {
            Ok(Value::Bool(b))
        } else if let Ok(i) = value.extract::<i64>() {
            Ok(Value::Number(serde_json::Number::from(i)))
        } else if let Ok(f) = value.extract::<f64>() {
            Ok(serde_json::Number::from_f64(f)
                .map(Value::Number)
                .unwrap_or(Value::Null))
        } else if let Ok(s) = value.extract::<String>() {
            Ok(Value::String(s))
        } else if let Ok(list) = value.downcast::<PyList>() {
            let mut vec = Vec::new();
            for item in list.iter() {
                vec.push(python_to_json(item)?);
            }
            Ok(Value::Array(vec))
        } else if let Ok(dict) = value.downcast::<PyDict>() {
            let mut map = serde_json::Map::new();
            for (k, v) in dict.iter() {
                let key: String = k.extract()?;
                map.insert(key, python_to_json(v)?);
            }
            Ok(Value::Object(map))
        } else {
            Ok(Value::Null)
        }
    }

    pub(crate) fn json_to_python(py: Python<'_>, value: &Value) -> PyResult<PyObject> {
        match value {
            Value::Null => Ok(py.None()),
            Value::Bool(b) => Ok(b.into_py(py)),
            Value::Number(n) => {
                if let Some(i) = n.as_i64() {
                    Ok(i.into_py(py))
                } else if let Some(f) = n.as_f64() {
                    Ok(f.into_py(py))
                } else {
                    Ok(py.None())
                }
            }
            Value::String(s) => Ok(s.into_py(py)),
            Value::Array(arr) => {
                let list = PyList::empty(py);
                for item in arr {
                    list.append(json_to_python(py, item)?)?;
                }
                Ok(list.into())
            }
            Value::Object(map) => {
                let dict = PyDict::new(py);
                for (key, val) in map {
                    dict.set_item(key, json_to_python(py, val)?)?;
                }
                Ok(dict.into())
            }
        }
    }
}

// Rate limiting module
mod ratelimit {
    use super::*;
    use robyn_ratelimit::*;
    use tokio::sync::Mutex;

    #[pyclass]
    pub struct RateLimitManager {
        inner: Arc<Mutex<robyn_ratelimit::RateLimitManager>>,
        runtime: Arc<Runtime>,
    }

    #[pymethods]
    impl RateLimitManager {
        #[new]
        fn new() -> Self {
            Self {
                inner: Arc::new(Mutex::new(robyn_ratelimit::RateLimitManager::new())),
                runtime: Arc::new(Runtime::new().unwrap()),
            }
        }

        fn register_limit(&self, name: &str, requests: u32, per_seconds: u64) -> PyResult<()> {
            let config = RateLimitConfig::new(requests, per_seconds)
                .map_err(|e| PyValueError::new_err(e.to_string()))?;

            let inner = self.inner.clone();
            let name = name.to_string();
            self.runtime.block_on(async move {
                inner
                    .lock()
                    .await
                    .register_limit(&name, config)
                    .map_err(|e| PyValueError::new_err(e.to_string()))
            })
        }

        fn check(&self, limiter_name: &str, key: &str) -> PyResult<()> {
            let inner = self.inner.clone();
            let limiter_name = limiter_name.to_string();
            let key = key.to_string();
            self.runtime.block_on(async move {
                inner
                    .lock()
                    .await
                    .check(&limiter_name, &key)
                    .map_err(|e| PyRuntimeError::new_err(e.to_string()))
            })
        }

        fn check_async<'p>(&self, py: Python<'p>, limiter_name: String, key: String) -> PyResult<&'p PyAny> {
            let inner = self.inner.clone();
            pyo3_asyncio::tokio::future_into_py(py, async move {
                inner
                    .lock()
                    .await
                    .check_async(&limiter_name, &key)
                    .await
                    .map_err(|e| PyRuntimeError::new_err(e.to_string()))
            })
        }
    }
}

// Authentication module
mod auth {
    use super::*;
    use super::validation::json_to_python;
    use robyn_auth::*;
    use std::sync::Arc as StdArc;

    #[pyclass]
    pub struct JwtValidator {
        inner: StdArc<robyn_auth::JwtValidator>,
        runtime: StdArc<Runtime>,
    }

    #[pyclass]
    #[derive(Clone)]
    pub struct Claims {
        #[pyo3(get)]
        pub sub: String,
        #[pyo3(get)]
        pub exp: i64,
        #[pyo3(get)]
        pub iat: Option<i64>,
        #[pyo3(get)]
        pub iss: Option<String>,
        #[pyo3(get)]
        pub aud: Option<String>,
        #[pyo3(get)]
        pub extra: PyObject,
    }

    impl Claims {
        fn from_rust_claims(claims: robyn_auth::Claims, py: Python<'_>) -> PyResult<Self> {
            // Convert extra claims map to Python dict
            let extra_dict = PyDict::new(py);
            for (key, value) in claims.extra.iter() {
                extra_dict.set_item(key, json_to_python(py, value)?)?;
            }

            Ok(Self {
                sub: claims.sub,
                exp: claims.exp,
                iat: claims.iat,
                iss: claims.iss,
                aud: claims.aud,
                extra: extra_dict.into(),
            })
        }
    }

    #[pymethods]
    impl JwtValidator {
        #[new]
        fn new(
            public_key: Option<String>,
            jwks_url: Option<String>,
            audience: Option<String>,
            issuer: Option<String>,
        ) -> PyResult<Self> {
            let config = JwtConfig {
                public_key,
                jwks_url,
                algorithms: vec![jsonwebtoken::Algorithm::RS256],
                audience,
                issuer,
                leeway: 60,
            };

            Ok(Self {
                inner: StdArc::new(robyn_auth::JwtValidator::new(config)),
                runtime: StdArc::new(Runtime::new().unwrap()),
            })
        }

        fn validate<'p>(&self, py: Python<'p>, token: String) -> PyResult<&'p PyAny> {
            let inner = self.inner.clone();
            pyo3_asyncio::tokio::future_into_py(py, async move {
                let claims = inner
                    .validate(&token)
                    .await
                    .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
                Python::with_gil(|py| Claims::from_rust_claims(claims, py))
            })
        }

        fn validate_sync(&self, py: Python<'_>, token: &str) -> PyResult<Claims> {
            self.runtime.block_on(async {
                let claims = self.inner
                    .validate(token)
                    .await
                    .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
                Claims::from_rust_claims(claims, py)
            })
        }
    }
}

// OpenAPI module
mod openapi {
    use super::*;
    use robyn_openapi::*;

    #[pyclass]
    pub struct OpenApiBuilder {
        inner: robyn_openapi::OpenApiBuilder,
    }

    #[pymethods]
    impl OpenApiBuilder {
        #[new]
        fn new(title: String, version: String) -> Self {
            Self {
                inner: robyn_openapi::OpenApiBuilder::new(&title, &version),
            }
        }

        fn description(mut slf: PyRefMut<Self>, desc: String) -> PyRefMut<Self> {
            slf.inner = std::mem::take(&mut slf.inner).description(&desc);
            slf
        }

        fn add_server(mut slf: PyRefMut<Self>, url: String, description: Option<String>) -> PyRefMut<Self> {
            slf.inner = std::mem::take(&mut slf.inner).add_server(&url, description.as_deref());
            slf
        }

        fn add_bearer_auth(mut slf: PyRefMut<Self>) -> PyRefMut<Self> {
            slf.inner = std::mem::take(&mut slf.inner).add_bearer_auth();
            slf
        }

        fn to_json(&self) -> PyResult<String> {
            self.inner
                .to_json()
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))
        }
    }

    #[pyclass]
    #[derive(Clone)]
    pub struct RouteMetadata {
        #[pyo3(get, set)]
        pub path: String,
        #[pyo3(get, set)]
        pub method: String,
        #[pyo3(get, set)]
        pub summary: Option<String>,
        #[pyo3(get, set)]
        pub description: Option<String>,
        #[pyo3(get, set)]
        pub tags: Vec<String>,
        #[pyo3(get, set)]
        pub request_schema: Option<String>,
        #[pyo3(get, set)]
        pub response_schema: Option<String>,
    }

    #[pymethods]
    impl RouteMetadata {
        #[new]
        #[pyo3(signature = (path, method, summary=None, description=None, tags=None, request_schema=None, response_schema=None))]
        fn new(
            path: String,
            method: String,
            summary: Option<String>,
            description: Option<String>,
            tags: Option<Vec<String>>,
            request_schema: Option<String>,
            response_schema: Option<String>,
        ) -> Self {
            Self {
                path,
                method,
                summary,
                description,
                tags: tags.unwrap_or_default(),
                request_schema,
                response_schema,
            }
        }
    }

    impl From<RouteMetadata> for robyn_openapi::RouteMetadata {
        fn from(meta: RouteMetadata) -> Self {
            Self {
                path: meta.path,
                method: meta.method,
                summary: meta.summary,
                description: meta.description,
                tags: meta.tags,
                request_schema: meta.request_schema,
                response_schema: meta.response_schema,
            }
        }
    }

    #[pyclass]
    pub struct AutoDocs {
        inner: robyn_openapi::AutoDocs,
    }

    #[pymethods]
    impl AutoDocs {
        #[new]
        fn new(title: String, version: String) -> Self {
            Self {
                inner: robyn_openapi::AutoDocs::new(&title, &version),
            }
        }

        fn register_route(&self, metadata: RouteMetadata) {
            self.inner.register_route(metadata.into());
        }

        fn get_openapi_json(&self) -> String {
            self.inner.get_openapi_json()
        }

        fn get_swagger_ui_html(&self, title: String) -> String {
            self.inner.get_swagger_ui_html(&title)
        }

        fn get_redoc_html(&self, title: String) -> String {
            self.inner.get_redoc_html(&title)
        }

        fn get_docs_path(&self) -> String {
            self.inner.get_docs_path().to_string()
        }

        fn get_openapi_path(&self) -> String {
            self.inner.get_openapi_path().to_string()
        }

        fn get_redoc_path(&self) -> String {
            self.inner.get_redoc_path().to_string()
        }
    }

}

// Python module definition
#[pymodule]
fn _robyn_extensions(_py: Python, m: &PyModule) -> PyResult<()> {
    // Rate limiting
    m.add_class::<ratelimit::RateLimitManager>()?;

    // Authentication
    m.add_class::<auth::JwtValidator>()?;
    m.add_class::<auth::Claims>()?;

    // OpenAPI
    m.add_class::<openapi::OpenApiBuilder>()?;
    m.add_class::<openapi::AutoDocs>()?;
    m.add_class::<openapi::RouteMetadata>()?;

    // Validation
    m.add_class::<validation::Validator>()?;
    m.add_class::<validation::ValidationError>()?;

    Ok(())
}
