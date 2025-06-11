from paymob.exceptions import ConfigurationError
from typing import Any

class PaymobConfig:
    """
    Paymob core configuration.
    These values can be found in your Paymob dashboard.
    
    """

    def __init__(
        self,
        api_key: str | None = None,
        public_key: str | None = None,
        secret_key: str | None = None,
        integration_id: str | None = None,
        base_url: str = "https://accept.paymob.com",
        hmac_secret_key: str | None = None,
    ):
        self.api_key = api_key
        self.public_key = public_key
        self.secret_key = secret_key
        self.integration_id = integration_id
        self.base_url = base_url.rstrip("/")
        self.hmac_secret_key = hmac_secret_key

        self.validate()

    @classmethod
    def from_env(cls) -> "PaymobConfig":
        """
        Create config from environment variables.
        expected variables:
            - PAYMOB_API_KEY
            - PAYMOB_PUBLIC_KEY
            - PAYMOB_SECRET_KEY
            - PAYMOB_INTEGRATION_ID
            - PAYMOB_BASE_URL
            - PAYMOB_HMAC_SECRET_KEY
        """
        import os

        return cls(
            api_key=os.getenv("PAYMOB_API_KEY"),
            public_key=os.getenv("PAYMOB_PUBLIC_KEY"),
            secret_key=os.getenv("PAYMOB_SECRET_KEY"),
            integration_id=os.getenv("PAYMOB_INTEGRATION_ID"),
            base_url=os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com"),
            hmac_secret_key=os.getenv("PAYMOB_HMAC_SECRET_KEY"),
        )

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "PaymobConfig":
        """
        Create config from dictionary.
        expected keys:
            - api_key
            - public_key
            - secret_key
            - integration_id
            - base_url
            - hmac_secret_key
        """
        return cls(
            api_key=config_dict.get("api_key"),
            public_key=config_dict.get("public_key"),
            secret_key=config_dict.get("secret_key"),
            integration_id=config_dict.get("integration_id"),
            base_url=config_dict.get("base_url", "https://accept.paymob.com"),
            hmac_secret_key=config_dict.get("hmac_secret_key"),
        )

    def validate(self) -> None:
        """Validate required configuration fields."""
        required = ["api_key", "secret_key", "public_key", "integration_id"]
        missing = [key for key in required if not getattr(self, key)]

        if missing:
            raise ConfigurationError(f"Missing required config: {', '.join(missing)}")

        # Validate base_url format
        if not self.base_url.startswith("https://"):
            raise ConfigurationError("base_url must start with https://")


class PaymobConnectionConfig:
    """Configuration for Paymob connection settings."""
    
    def __init__(
        self,
        pool_size: int = 1,
        timeout: int = 30,
        keep_alive: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 0.3
    ):
        self.pool_size = pool_size
        self.timeout = timeout
        self.keep_alive = keep_alive
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    @classmethod
    def default(cls) -> 'PaymobConnectionConfig':
        """Return default configuration."""
        return cls(
            pool_size=1,  # Single connection for most use cases
            timeout=15,   # 15 second timeout
            keep_alive=True,  # Enable keep-alive for better performance
            max_retries=3,    # Retry failed requests
            backoff_factor=0.3  # retries delay for {backoff factor} * (2 ** ({number of previous retries}))
        )
    
    @classmethod
    def high_throughput(cls) -> 'PaymobConnectionConfig':
        """Configuration for high-throughput scenarios."""
        return cls(
            pool_size=5,  # More concurrent connections
            timeout=10,   # Shorter timeout
            keep_alive=True,
            max_retries=2,
        )