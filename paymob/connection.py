from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException, HTTPError, Timeout, ConnectionError

import logging

logger = logging.getLogger(__name__)

class ConnectionPool:
    
    def __init__(
        self,
        pool_size: int = 1,
        timeout: int = 15,
        keep_alive: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 0.3
    ):
        self.pool_size = pool_size
        self.timeout = timeout
        self.keep_alive = keep_alive
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        
    def _get_session(self) -> requests.Session:
        """Get or create a session"""
        if not hasattr(self, 'session') or self.session is None:
            self.session = self._create_session()
        return self.session
    
    def _create_session(self) -> requests.Session:
        """Create a new requests session with connection pooling and retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=self.pool_size,
            pool_maxsize=self.pool_size,
            max_retries=retry_strategy
        )
        
        session.mount("https://", adapter)
        
        # Configure keep-alive (ignored for h2 and h3)
        if self.keep_alive:
            session.headers.update({
                'Connection': 'keep-alive',
                'Keep-Alive': 'timeout=30, max=100' # Keeps connection open for 30 seconds idle, or up to 100 requests, whichever comes first
            })
        
        return session
    
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        **kwargs
    ) -> requests.Response:
        """
        Make an HTTP request using the connection pool.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            headers: Optional headers dict
            json: JSON payload for POST/PUT requests
            data: Form data payload
            params: URL parameters
            **kwargs: Additional arguments passed to requests
            
        Returns:
            requests.Response object
            
        Raises:
            requests.RequestException: For connection or HTTP errors
        """
        # only https
        if not url.startswith('https://'):
            raise ValueError("Only HTTPS URLs are allowed for security reasons")
        
        session = self._get_session()
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        try:
            response = session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=json,
                data=data,
                params=params,
                **kwargs
            )
            return response
            
        except requests.exceptions.RequestException as e:
            # TODO: Handle HTTPErrors more gracefully, especially 40x
            #       403 error should be handled differently
            logger.error(f"Request failed: {method} {url} - {str(e)}")
            raise
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for GET requests."""
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for POST requests."""
        return self.request('POST', url, **kwargs)
    
    def put(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for PUT requests."""
        return self.request('PUT', url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for DELETE requests."""
        return self.request('DELETE', url, **kwargs)
    
    def close(self):
        """Close all sessions"""
        if hasattr(self, 'session') and self.session:
            self.session.close()
            self.session = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connections."""
        self.close()


