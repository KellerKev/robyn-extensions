use jsonwebtoken::{
    decode, decode_header, Algorithm, DecodingKey, Validation,
};
use moka::future::Cache;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AuthError {
    #[error("Invalid token: {0}")]
    InvalidToken(String),
    #[error("Token expired")]
    TokenExpired,
    #[error("JWKS fetch failed: {0}")]
    JwksFetchError(String),
    #[error("Key not found in JWKS")]
    KeyNotFound,
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
    #[error("Missing required claim: {0}")]
    MissingClaim(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub exp: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub iat: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub iss: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub aud: Option<String>,
    #[serde(flatten)]
    pub extra: serde_json::Map<String, serde_json::Value>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Jwks {
    pub keys: Vec<Jwk>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Jwk {
    pub kty: String,
    pub kid: Option<String>,
    #[serde(rename = "use")]
    pub key_use: Option<String>,
    pub alg: Option<String>,
    pub n: Option<String>,
    pub e: Option<String>,
    pub x: Option<String>,
    pub y: Option<String>,
    pub crv: Option<String>,
}

#[derive(Debug, Clone)]
pub struct JwtConfig {
    pub public_key: Option<String>,
    pub jwks_url: Option<String>,
    pub algorithms: Vec<Algorithm>,
    pub audience: Option<String>,
    pub issuer: Option<String>,
    pub leeway: u64,
}

impl Default for JwtConfig {
    fn default() -> Self {
        Self {
            public_key: None,
            jwks_url: None,
            algorithms: vec![Algorithm::RS256],
            audience: None,
            issuer: None,
            leeway: 60, // 60 seconds leeway for clock skew
        }
    }
}

pub struct JwtValidator {
    config: JwtConfig,
    jwks_cache: Cache<String, Arc<Jwks>>,
    http_client: Client,
}

impl JwtValidator {
    pub fn new(config: JwtConfig) -> Self {
        let jwks_cache = Cache::builder()
            .time_to_live(Duration::from_secs(3600)) // Cache for 1 hour
            .build();

        Self {
            config,
            jwks_cache,
            http_client: Client::new(),
        }
    }

    pub async fn validate(&self, token: &str) -> Result<Claims, AuthError> {
        // Decode header to get kid
        let header = decode_header(token)
            .map_err(|e| AuthError::InvalidToken(e.to_string()))?;

        // Get the decoding key
        let decoding_key = if let Some(ref public_key) = self.config.public_key {
            DecodingKey::from_rsa_pem(public_key.as_bytes())
                .map_err(|e| AuthError::InvalidConfig(e.to_string()))?
        } else if let Some(ref jwks_url) = self.config.jwks_url {
            self.get_decoding_key_from_jwks(jwks_url, header.kid.as_deref())
                .await?
        } else {
            return Err(AuthError::InvalidConfig(
                "Either public_key or jwks_url must be provided".to_string(),
            ));
        };

        // Set up validation
        let mut validation = Validation::new(
            header.alg
        );
        validation.leeway = self.config.leeway;
        validation.set_audience(&[self.config.audience.clone().unwrap_or_default()]);
        validation.set_issuer(&[self.config.issuer.clone().unwrap_or_default()]);

        // Decode and validate token
        let token_data = decode::<Claims>(token, &decoding_key, &validation)
            .map_err(|e| match e.kind() {
                jsonwebtoken::errors::ErrorKind::ExpiredSignature => AuthError::TokenExpired,
                _ => AuthError::InvalidToken(e.to_string()),
            })?;

        Ok(token_data.claims)
    }

    async fn get_decoding_key_from_jwks(
        &self,
        jwks_url: &str,
        kid: Option<&str>,
    ) -> Result<DecodingKey, AuthError> {
        // Try to get from cache first
        let jwks = if let Some(cached) = self.jwks_cache.get(jwks_url).await {
            cached
        } else {
            // Fetch from URL
            let response = self
                .http_client
                .get(jwks_url)
                .send()
                .await
                .map_err(|e| AuthError::JwksFetchError(e.to_string()))?;

            let jwks: Jwks = response
                .json()
                .await
                .map_err(|e| AuthError::JwksFetchError(e.to_string()))?;

            let jwks = Arc::new(jwks);
            self.jwks_cache.insert(jwks_url.to_string(), jwks.clone()).await;
            jwks
        };

        // Find the right key
        let jwk = jwks
            .keys
            .iter()
            .find(|k| {
                if let Some(kid) = kid {
                    k.kid.as_deref() == Some(kid)
                } else {
                    true // Use first key if no kid specified
                }
            })
            .ok_or(AuthError::KeyNotFound)?;

        // Convert JWK to DecodingKey
        self.jwk_to_decoding_key(jwk)
    }

    fn jwk_to_decoding_key(&self, jwk: &Jwk) -> Result<DecodingKey, AuthError> {
        match jwk.kty.as_str() {
            "RSA" => {
                let n = jwk.n.as_ref().ok_or(AuthError::InvalidConfig(
                    "RSA key missing 'n' parameter".to_string(),
                ))?;
                let e = jwk.e.as_ref().ok_or(AuthError::InvalidConfig(
                    "RSA key missing 'e' parameter".to_string(),
                ))?;

                DecodingKey::from_rsa_components(n, e)
                    .map_err(|e| AuthError::InvalidConfig(e.to_string()))
            }
            "EC" => {
                let x = jwk.x.as_ref().ok_or(AuthError::InvalidConfig(
                    "EC key missing 'x' parameter".to_string(),
                ))?;
                let y = jwk.y.as_ref().ok_or(AuthError::InvalidConfig(
                    "EC key missing 'y' parameter".to_string(),
                ))?;

                DecodingKey::from_ec_components(x, y)
                    .map_err(|e| AuthError::InvalidConfig(e.to_string()))
            }
            _ => Err(AuthError::InvalidConfig(format!(
                "Unsupported key type: {}",
                jwk.kty
            ))),
        }
    }

    pub async fn refresh_jwks(&self) -> Result<(), AuthError> {
        if let Some(ref jwks_url) = self.config.jwks_url {
            self.jwks_cache.invalidate(jwks_url).await;
        }
        Ok(())
    }
}

/// OAuth2 configuration helpers
pub mod oauth2 {
    use super::*;

    pub struct OAuth2Config {
        pub authorization_url: String,
        pub token_url: String,
        pub client_id: String,
        pub client_secret: String,
        pub redirect_uri: String,
        pub scopes: Vec<String>,
    }

    impl OAuth2Config {
        pub fn authorization_url_with_state(&self, state: &str) -> String {
            format!(
                "{}?client_id={}&redirect_uri={}&response_type=code&scope={}&state={}",
                self.authorization_url,
                self.client_id,
                urlencoding::encode(&self.redirect_uri),
                self.scopes.join(" "),
                state
            )
        }
    }

    #[derive(Serialize)]
    struct TokenRequest {
        grant_type: String,
        code: String,
        redirect_uri: String,
        client_id: String,
        client_secret: String,
    }

    #[derive(Deserialize)]
    pub struct TokenResponse {
        pub access_token: String,
        pub token_type: String,
        pub expires_in: Option<u64>,
        pub refresh_token: Option<String>,
        pub scope: Option<String>,
    }

    pub async fn exchange_code_for_token(
        config: &OAuth2Config,
        code: &str,
    ) -> Result<TokenResponse, AuthError> {
        let client = Client::new();
        let request = TokenRequest {
            grant_type: "authorization_code".to_string(),
            code: code.to_string(),
            redirect_uri: config.redirect_uri.clone(),
            client_id: config.client_id.clone(),
            client_secret: config.client_secret.clone(),
        };

        let response = client
            .post(&config.token_url)
            .form(&request)
            .send()
            .await
            .map_err(|e| AuthError::InvalidConfig(e.to_string()))?;

        response
            .json()
            .await
            .map_err(|e| AuthError::InvalidConfig(e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_jwt_config_default() {
        let config = JwtConfig::default();
        assert_eq!(config.algorithms.len(), 1);
        assert_eq!(config.leeway, 60);
    }

    #[test]
    fn test_claims_serialization() {
        let claims = Claims {
            sub: "user123".to_string(),
            exp: 1234567890,
            iat: Some(1234567800),
            iss: Some("https://auth.example.com".to_string()),
            aud: Some("api".to_string()),
            extra: serde_json::Map::new(),
        };

        let json = serde_json::to_string(&claims).unwrap();
        assert!(json.contains("user123"));
    }
}
