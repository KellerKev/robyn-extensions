use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use indexmap::IndexMap;

pub mod autodocs;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpenApiSpec {
    pub openapi: String,
    pub info: Info,
    pub paths: IndexMap<String, PathItem>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub components: Option<Components>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub servers: Option<Vec<Server>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub security: Option<Vec<SecurityRequirement>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Info {
    pub title: String,
    pub version: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub contact: Option<Contact>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub license: Option<License>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Contact {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub email: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct License {
    pub name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Server {
    pub url: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathItem {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub get: Option<Operation>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub post: Option<Operation>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub put: Option<Operation>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub patch: Option<Operation>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub delete: Option<Operation>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Operation {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub summary: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub operation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parameters: Option<Vec<Parameter>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub request_body: Option<RequestBody>,
    pub responses: IndexMap<String, Response>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub security: Option<Vec<SecurityRequirement>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Parameter {
    pub name: String,
    #[serde(rename = "in")]
    pub location: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub required: Option<bool>,
    pub schema: Schema,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestBody {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub content: IndexMap<String, MediaType>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub required: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Response {
    pub description: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<IndexMap<String, MediaType>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MediaType {
    pub schema: Schema,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Schema {
    Reference { #[serde(rename = "$ref")] reference: String },
    Object(SchemaObject),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchemaObject {
    #[serde(skip_serializing_if = "Option::is_none", rename = "type")]
    pub schema_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub properties: Option<IndexMap<String, Schema>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub required: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub items: Option<Box<Schema>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub format: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Components {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub schemas: Option<IndexMap<String, Schema>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub security_schemes: Option<IndexMap<String, SecurityScheme>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum SecurityScheme {
    #[serde(rename = "http")]
    Http {
        scheme: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        bearer_format: Option<String>,
    },
    #[serde(rename = "apiKey")]
    ApiKey {
        name: String,
        #[serde(rename = "in")]
        location: String,
    },
    #[serde(rename = "oauth2")]
    OAuth2 {
        flows: OAuthFlows,
    },
    #[serde(rename = "openIdConnect")]
    OpenIdConnect {
        #[serde(rename = "openIdConnectUrl")]
        open_id_connect_url: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OAuthFlows {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub implicit: Option<OAuthFlow>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub password: Option<OAuthFlow>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub client_credentials: Option<OAuthFlow>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub authorization_code: Option<OAuthFlow>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OAuthFlow {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub authorization_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub token_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub refresh_url: Option<String>,
    pub scopes: IndexMap<String, String>,
}

pub type SecurityRequirement = IndexMap<String, Vec<String>>;

// Re-export autodocs for convenience
pub use autodocs::{AutoDocs, RouteMetadata};

pub struct OpenApiBuilder {
    spec: OpenApiSpec,
}

impl OpenApiBuilder {
    pub fn new(title: &str, version: &str) -> Self {
        Self {
            spec: OpenApiSpec {
                openapi: "3.0.3".to_string(),
                info: Info {
                    title: title.to_string(),
                    version: version.to_string(),
                    description: None,
                    contact: None,
                    license: None,
                },
                paths: IndexMap::new(),
                components: None,
                servers: None,
                security: None,
            },
        }
    }

    pub fn description(mut self, desc: &str) -> Self {
        self.spec.info.description = Some(desc.to_string());
        self
    }

    pub fn add_server(mut self, url: &str, description: Option<&str>) -> Self {
        let server = Server {
            url: url.to_string(),
            description: description.map(|s| s.to_string()),
        };
        self.spec.servers.get_or_insert_with(Vec::new).push(server);
        self
    }

    pub fn add_path(mut self, path: &str, method: &str, operation: Operation) -> Self {
        let path_item = self.spec.paths.entry(path.to_string()).or_insert(PathItem {
            get: None,
            post: None,
            put: None,
            patch: None,
            delete: None,
        });

        match method.to_lowercase().as_str() {
            "get" => path_item.get = Some(operation),
            "post" => path_item.post = Some(operation),
            "put" => path_item.put = Some(operation),
            "patch" => path_item.patch = Some(operation),
            "delete" => path_item.delete = Some(operation),
            _ => {}
        }

        self
    }

    pub fn add_schema(mut self, name: &str, schema: Schema) -> Self {
        let components = self.spec.components.get_or_insert(Components {
            schemas: Some(IndexMap::new()),
            security_schemes: None,
        });
        components.schemas.as_mut().unwrap().insert(name.to_string(), schema);
        self
    }

    pub fn add_security_scheme(mut self, name: &str, scheme: SecurityScheme) -> Self {
        let components = self.spec.components.get_or_insert(Components {
            schemas: None,
            security_schemes: Some(IndexMap::new()),
        });
        components.security_schemes.as_mut().unwrap().insert(name.to_string(), scheme);
        self
    }

    pub fn add_bearer_auth(self) -> Self {
        self.add_security_scheme(
            "bearerAuth",
            SecurityScheme::Http {
                scheme: "bearer".to_string(),
                bearer_format: Some("JWT".to_string()),
            },
        )
    }

    pub fn build(self) -> OpenApiSpec {
        self.spec
    }

    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(&self.spec)
    }
}

impl Default for OpenApiBuilder {
    fn default() -> Self {
        Self::new("API", "1.0.0")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_builder() {
        let spec = OpenApiBuilder::new("Test API", "1.0.0")
            .description("A test API")
            .add_server("http://localhost:8080", Some("Development"))
            .add_bearer_auth()
            .build();

        assert_eq!(spec.info.title, "Test API");
        assert_eq!(spec.openapi, "3.0.3");
        assert!(spec.servers.is_some());
    }

    #[test]
    fn test_json_serialization() {
        let builder = OpenApiBuilder::new("Test API", "1.0.0");
        let json = builder.to_json().unwrap();
        assert!(json.contains("Test API"));
    }
}
