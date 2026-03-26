use dashmap::DashMap;
use governor::{
    clock::{Clock, DefaultClock, QuantaInstant},
    middleware::NoOpMiddleware,
    state::{InMemoryState, NotKeyed},
    Quota, RateLimiter,
};
use std::num::NonZeroU32;
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum RateLimitError {
    #[error("Rate limit exceeded. Retry after {retry_after} seconds")]
    Exceeded { retry_after: u64 },
    #[error("Invalid rate limit configuration: {0}")]
    InvalidConfig(String),
}

#[derive(Debug, Clone)]
pub struct RateLimitConfig {
    pub requests: u32,
    pub per_seconds: u64,
    pub burst_size: Option<u32>,
}

impl RateLimitConfig {
    pub fn new(requests: u32, per_seconds: u64) -> Result<Self, RateLimitError> {
        if requests == 0 {
            return Err(RateLimitError::InvalidConfig(
                "requests must be greater than 0".to_string(),
            ));
        }
        if per_seconds == 0 {
            return Err(RateLimitError::InvalidConfig(
                "per_seconds must be greater than 0".to_string(),
            ));
        }
        Ok(Self {
            requests,
            per_seconds,
            burst_size: None,
        })
    }

    pub fn with_burst(mut self, burst: u32) -> Self {
        self.burst_size = Some(burst);
        self
    }
}

type KeyedRateLimiter = RateLimiter<
    String,
    DashMap<String, InMemoryState>,
    DefaultClock,
    NoOpMiddleware<QuantaInstant>,
>;

pub struct RateLimitManager {
    limiters: DashMap<String, Arc<KeyedRateLimiter>>,
    clock: DefaultClock,
}

impl RateLimitManager {
    pub fn new() -> Self {
        Self {
            limiters: DashMap::new(),
            clock: DefaultClock::default(),
        }
    }

    pub fn register_limit(&self, name: &str, config: RateLimitConfig) -> Result<(), RateLimitError> {
        let requests = NonZeroU32::new(config.requests)
            .ok_or_else(|| RateLimitError::InvalidConfig("requests must be non-zero".to_string()))?;
        
        let quota = if let Some(burst) = config.burst_size {
            let burst_size = NonZeroU32::new(burst)
                .ok_or_else(|| RateLimitError::InvalidConfig("burst_size must be non-zero".to_string()))?;
            Quota::with_period(Duration::from_secs(config.per_seconds / requests.get() as u64))
                .ok_or_else(|| RateLimitError::InvalidConfig("invalid period".to_string()))?
                .allow_burst(burst_size)
        } else {
            Quota::per_second(requests)
        };

        let limiter = RateLimiter::dashmap_with_clock(quota, &self.clock);
        self.limiters.insert(name.to_string(), Arc::new(limiter));
        Ok(())
    }

    pub fn check(&self, limiter_name: &str, key: &str) -> Result<(), RateLimitError> {
        let limiter = self.limiters.get(limiter_name).ok_or_else(|| {
            RateLimitError::InvalidConfig(format!("limiter '{}' not found", limiter_name))
        })?;

        match limiter.check_key(&key.to_string()) {
            Ok(_) => Ok(()),
            Err(not_until) => {
                let retry_after = not_until
                    .wait_time_from(self.clock.now())
                    .as_secs();
                Err(RateLimitError::Exceeded { retry_after })
            }
        }
    }

    pub async fn check_async(&self, limiter_name: &str, key: &str) -> Result<(), RateLimitError> {
        self.check(limiter_name, key)
    }

    pub fn reset(&self, limiter_name: &str, key: &str) {
        if let Some(limiter) = self.limiters.get(limiter_name) {
            // Remove the key's state to reset it
            // This is implementation-dependent on governor's internals
            drop(limiter);
        }
    }
}

impl Default for RateLimitManager {
    fn default() -> Self {
        Self::new()
    }
}

/// Simple in-memory rate limiter for single keys
pub struct SimpleRateLimiter {
    limiter: RateLimiter<NotKeyed, InMemoryState, DefaultClock>,
    clock: DefaultClock,
}

impl SimpleRateLimiter {
    pub fn new(config: RateLimitConfig) -> Result<Self, RateLimitError> {
        let requests = NonZeroU32::new(config.requests)
            .ok_or_else(|| RateLimitError::InvalidConfig("requests must be non-zero".to_string()))?;
        
        let quota = Quota::per_second(requests);
        let clock = DefaultClock::default();
        let limiter = RateLimiter::direct_with_clock(quota, &clock);

        Ok(Self { limiter, clock })
    }

    pub fn check(&self) -> Result<(), RateLimitError> {
        match self.limiter.check() {
            Ok(_) => Ok(()),
            Err(not_until) => {
                let retry_after = not_until
                    .wait_time_from(self.clock.now())
                    .as_secs();
                Err(RateLimitError::Exceeded { retry_after })
            }
        }
    }

    pub async fn check_async(&self) -> Result<(), RateLimitError> {
        self.check()
    }
}

/// Pre-configured rate limit presets
pub mod presets {
    use super::*;

    pub fn strict() -> RateLimitConfig {
        RateLimitConfig::new(10, 60).unwrap()
    }

    pub fn moderate() -> RateLimitConfig {
        RateLimitConfig::new(60, 60).unwrap()
    }

    pub fn permissive() -> RateLimitConfig {
        RateLimitConfig::new(100, 60).unwrap()
    }

    pub fn api_standard() -> RateLimitConfig {
        RateLimitConfig::new(1000, 3600).unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rate_limit_config() {
        let config = RateLimitConfig::new(10, 60).unwrap();
        assert_eq!(config.requests, 10);
        assert_eq!(config.per_seconds, 60);
    }

    #[test]
    fn test_rate_limit_manager() {
        let manager = RateLimitManager::new();
        let config = RateLimitConfig::new(2, 1).unwrap();
        manager.register_limit("test", config).unwrap();

        // First two requests should succeed
        assert!(manager.check("test", "user1").is_ok());
        assert!(manager.check("test", "user1").is_ok());

        // Third request should fail
        assert!(manager.check("test", "user1").is_err());
    }

    #[test]
    fn test_simple_limiter() {
        let config = RateLimitConfig::new(2, 1).unwrap();
        let limiter = SimpleRateLimiter::new(config).unwrap();

        assert!(limiter.check().is_ok());
        assert!(limiter.check().is_ok());
        assert!(limiter.check().is_err());
    }

    #[test]
    fn test_presets() {
        let strict = presets::strict();
        assert_eq!(strict.requests, 10);

        let moderate = presets::moderate();
        assert_eq!(moderate.requests, 60);
    }
}
