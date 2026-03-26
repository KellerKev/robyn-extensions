/// Automatic OpenAPI documentation generation for Robyn
/// Deep integration with routing system for zero-configuration docs

use crate::*;
use serde_json::json;
use std::sync::{Arc, RwLock};

/// Route metadata for documentation
#[derive(Debug, Clone)]
pub struct RouteMetadata {
    pub path: String,
    pub method: String,
    pub summary: Option<String>,
    pub description: Option<String>,
    pub tags: Vec<String>,
    pub request_schema: Option<String>,  // JSON schema as string
    pub response_schema: Option<String>, // JSON schema as string
}

/// Automatic documentation generator
pub struct AutoDocs {
    spec: Arc<RwLock<OpenApiSpec>>,
    routes: Arc<RwLock<Vec<RouteMetadata>>>,
    docs_path: String,
    openapi_path: String,
    redoc_path: String,
}

impl AutoDocs {
    pub fn new(title: &str, version: &str) -> Self {
        let spec = OpenApiSpec {
            openapi: "3.0.3".to_string(),
            info: Info {
                title: title.to_string(),
                version: version.to_string(),
                description: None,
                contact: None,
                license: None,
            },
            paths: IndexMap::new(),
            components: Some(Components {
                schemas: Some(IndexMap::new()),
                security_schemes: None,
            }),
            servers: None,
            security: None,
        };

        Self {
            spec: Arc::new(RwLock::new(spec)),
            routes: Arc::new(RwLock::new(Vec::new())),
            docs_path: "/docs".to_string(),
            openapi_path: "/openapi.json".to_string(),
            redoc_path: "/redoc".to_string(),
        }
    }

    /// Register a route with metadata
    pub fn register_route(&self, metadata: RouteMetadata) {
        let mut routes = self.routes.write().unwrap();
        routes.push(metadata);
    }

    /// Build the OpenAPI specification from registered routes
    pub fn build_spec(&self) -> OpenApiSpec {
        let routes = self.routes.read().unwrap();
        let mut spec = self.spec.write().unwrap();

        for route in routes.iter() {
            self.add_route_to_spec(&mut spec, route);
        }

        spec.clone()
    }

    fn add_route_to_spec(&self, spec: &mut OpenApiSpec, route: &RouteMetadata) {
        let path_item = spec
            .paths
            .entry(route.path.clone())
            .or_insert(PathItem {
                get: None,
                post: None,
                put: None,
                patch: None,
                delete: None,
            });

        let mut operation = Operation {
            summary: route.summary.clone(),
            description: route.description.clone(),
            operation_id: None,
            tags: if route.tags.is_empty() {
                None
            } else {
                Some(route.tags.clone())
            },
            parameters: None,
            request_body: None,
            responses: IndexMap::new(),
            security: None,
        };

        // Add request body if schema provided
        if let Some(ref schema_json) = route.request_schema {
            if let Ok(schema_value) = serde_json::from_str::<serde_json::Value>(schema_json) {
                // Extract schema name if it's a reference
                let schema_name = schema_value
                    .get("title")
                    .and_then(|v| v.as_str())
                    .unwrap_or("RequestBody");

                // Add to components
                if let Ok(schema) = serde_json::from_value(schema_value.clone()) {
                    if let Some(ref mut components) = spec.components {
                        if let Some(ref mut schemas) = components.schemas {
                            schemas.insert(schema_name.to_string(), schema);
                        }
                    }
                }

                operation.request_body = Some(RequestBody {
                    description: None,
                    content: {
                        let mut map = IndexMap::new();
                        map.insert(
                            "application/json".to_string(),
                            MediaType {
                                schema: Schema::Reference {
                                    reference: format!("#/components/schemas/{}", schema_name),
                                },
                            },
                        );
                        map
                    },
                    required: Some(true),
                });
            }
        }

        // Add response
        if let Some(ref schema_json) = route.response_schema {
            if let Ok(schema_value) = serde_json::from_str::<serde_json::Value>(schema_json) {
                let schema_name = schema_value
                    .get("title")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Response");

                if let Ok(schema) = serde_json::from_value(schema_value.clone()) {
                    if let Some(ref mut components) = spec.components {
                        if let Some(ref mut schemas) = components.schemas {
                            schemas.insert(schema_name.to_string(), schema);
                        }
                    }
                }

                let mut content = IndexMap::new();
                content.insert(
                    "application/json".to_string(),
                    MediaType {
                        schema: Schema::Reference {
                            reference: format!("#/components/schemas/{}", schema_name),
                        },
                    },
                );

                operation.responses.insert(
                    "200".to_string(),
                    Response {
                        description: "Successful response".to_string(),
                        content: Some(content),
                    },
                );
            }
        } else {
            operation.responses.insert(
                "200".to_string(),
                Response {
                    description: "Successful response".to_string(),
                    content: None,
                },
            );
        }

        // Add validation error response
        let validation_error_schema = Schema::Object(SchemaObject {
            schema_type: Some("object".to_string()),
            properties: Some({
                let mut props = IndexMap::new();
                props.insert(
                    "error".to_string(),
                    Schema::Object(SchemaObject {
                        schema_type: Some("string".to_string()),
                        properties: None,
                        required: None,
                        items: None,
                        format: None,
                        description: None,
                    }),
                );
                props.insert(
                    "detail".to_string(),
                    Schema::Object(SchemaObject {
                        schema_type: Some("array".to_string()),
                        properties: None,
                        required: None,
                        items: Some(Box::new(Schema::Object(SchemaObject {
                            schema_type: Some("object".to_string()),
                            properties: None,
                            required: None,
                            items: None,
                            format: None,
                            description: None,
                        }))),
                        format: None,
                        description: None,
                    }),
                );
                props
            }),
            required: None,
            items: None,
            format: None,
            description: None,
        });

        let mut validation_content = IndexMap::new();
        validation_content.insert(
            "application/json".to_string(),
            MediaType {
                schema: validation_error_schema,
            },
        );

        operation.responses.insert(
            "422".to_string(),
            Response {
                description: "Validation Error".to_string(),
                content: Some(validation_content),
            },
        );

        // Insert operation into path item
        match route.method.to_lowercase().as_str() {
            "get" => path_item.get = Some(operation),
            "post" => path_item.post = Some(operation),
            "put" => path_item.put = Some(operation),
            "patch" => path_item.patch = Some(operation),
            "delete" => path_item.delete = Some(operation),
            _ => {}
        }
    }

    /// Get OpenAPI spec as JSON string
    pub fn get_openapi_json(&self) -> String {
        let spec = self.build_spec();
        serde_json::to_string_pretty(&spec).unwrap_or_else(|_| "{}".to_string())
    }

    /// Get Swagger UI HTML
    pub fn get_swagger_ui_html(&self, title: &str) -> String {
        format!(
            r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{} - Swagger UI</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.0/swagger-ui.css">
    <style>
        body {{ margin: 0; padding: 0; }}
        .swagger-ui .topbar {{ display: none; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.0/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            SwaggerUIBundle({{
                url: '{}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                layout: "StandaloneLayout",
                tryItOutEnabled: true
            }});
        }};
    </script>
</body>
</html>"#,
            title, self.openapi_path
        )
    }

    /// Get ReDoc HTML
    pub fn get_redoc_html(&self, title: &str) -> String {
        format!(
            r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{} - ReDoc</title>
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <redoc spec-url='{}'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
</body>
</html>"#,
            title, self.openapi_path
        )
    }

    /// Get documentation paths
    pub fn get_docs_path(&self) -> &str {
        &self.docs_path
    }

    pub fn get_openapi_path(&self) -> &str {
        &self.openapi_path
    }

    pub fn get_redoc_path(&self) -> &str {
        &self.redoc_path
    }
}

impl Clone for AutoDocs {
    fn clone(&self) -> Self {
        Self {
            spec: Arc::clone(&self.spec),
            routes: Arc::clone(&self.routes),
            docs_path: self.docs_path.clone(),
            openapi_path: self.openapi_path.clone(),
            redoc_path: self.redoc_path.clone(),
        }
    }
}
