# Basic exceptions

# Placeholders for now
class APIException(Exception):
    pass


class PaymobError(Exception):
    """Base exception for Paymob-related errors."""
    pass

class ValidationError(PaymobError):
    params = None
    def __init__(self, message, params=None):
        super().__init__(message)
        self.params = params

class AuthenticationError(PaymobError):
    """Raised when authentication fails."""
    pass


class ConfigurationError(PaymobError):
    """Raised when configuration is invalid or missing."""
    pass
