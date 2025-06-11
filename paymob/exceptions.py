# Basic exceptions

# Placeholders for now
class APIException(Exception):
    pass

class ValidationError(APIException):
    pass

class PaymobError(Exception):
    """Base exception for Paymob-related errors."""
    pass


class AuthenticationError(PaymobError):
    """Raised when authentication fails."""
    pass


class ConfigurationError(PaymobError):
    """Raised when configuration is invalid or missing."""
    pass
