import time
from paymob.exceptions import AuthenticationError
import logging
from paymob.cache import CacheBackend, MemoryCache
from paymob.connection import ConnectionPool
from paymob.config import PaymobConfig

logger = logging.getLogger(__name__)


class PaymobAuth:
    """
    Paymob requires a 1-hr expired token for some requests.
    This class handles token request, caching, and refreshing.

    PaymobAuth.get_token() returns the token.
    PaymobAuth.invalidate_token() removes the token from cache.
    """

    CACHE_KEY = "paymob:auth_token"

    def __init__(
        self,
        config: PaymobConfig,
        connection_pool: ConnectionPool,
        cache_backend: CacheBackend | None = None,
        token_ttl: int = 55 * 60,  # 55 minutes (5 minutes before actual expiry)
    ):
        self.config = config
        self.connection_pool = connection_pool
        self.cache_backend = cache_backend or MemoryCache()
        self._refresh_attempts = 0
        self._last_refresh_hour = -1
        self.token_ttl = token_ttl

    def _request_token(self) -> str:
        """Request new authentication token from Paymob API."""
        url = f"{self.config.base_url}/api/auth/tokens"
        data = {"api_key": self.config.api_key}

        try:
            response = self.connection_pool.post(url, json=data)
            response.raise_for_status()

            response_data = response.json()
            token = response_data.get("token")

            if not token:
                raise AuthenticationError("No token received from Paymob API")

            logger.info("Successfully obtained new Paymob authentication token")
            return token

        except Exception as e:
            logger.error(f"Failed to request authentication token: {e}")
            raise AuthenticationError(f"Token request failed: {e}")

    def _get_cached_token(self) -> str | None:
        """Get token from cache backend."""
        try:
            return self.cache_backend.get(self.CACHE_KEY)
        except Exception as e:
            logger.warning(f"Failed to get cached token: {e}")
            return None

    def _cache_token(self, token: str) -> None:
        """Cache token with TTL."""
        try:
            self.cache_backend.set(self.CACHE_KEY, token, self.token_ttl)
            logger.debug("Token cached successfully")
        except Exception as e:
            logger.warning(f"Failed to cache token: {e}")

    def _track_refresh_attempts(self) -> None:
        """Track token refresh attempts to detect issues."""
        current_hour = int(time.time() // 3600)

        if current_hour != self._last_refresh_hour:
            self._refresh_attempts = 0
            self._last_refresh_hour = current_hour

        self._refresh_attempts += 1

        if self._refresh_attempts > 3:  # More than 3 refreshes per hour
            logger.warning(
                f"High token refresh rate: {self._refresh_attempts} times this hour"
            )

    def get_token(self, force_refresh: bool = False) -> str:
        """
        Get valid authentication token.

        Args:
            force_refresh: If True, bypass cache and request new token

        Returns:
            Valid authentication token

        Raises:
            AuthenticationError: If token request fails
        """
        # Try cached token first (unless force refresh)
        if not force_refresh:
            cached_token = self._get_cached_token()
            if cached_token:
                logger.debug("Using cached authentication token")
                return cached_token

        # Track refresh attempts
        self._track_refresh_attempts()

        # Request new token
        logger.info("Requesting new authentication token")
        token = self._request_token()

        # Cache the new token
        self._cache_token(token)

        return token

    def invalidate_token(self) -> None:
        """Invalidate cached token."""
        try:
            self.cache_backend.delete(self.CACHE_KEY)
            logger.info("Authentication token invalidated")
        except Exception as e:
            logger.warning(f"Failed to invalidate token: {e}")
