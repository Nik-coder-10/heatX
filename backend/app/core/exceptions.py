"""Custom security exceptions for the authentication system."""


class SecurityError(Exception):
    """Base exception for all security-related errors."""


class SecurityConfigurationError(SecurityError):
    """Raised when the security configuration is invalid or incomplete."""


class InvalidToken(SecurityError):
    """Raised when a token is invalid for any reason (base class).

    Examples: malformed JWT, bad signature, missing claims, wrong audience.
    """


class ExpiredToken(InvalidToken):
    """Raised when a token has exceeded its expiration time (exp claim)."""


class TokenRevoked(InvalidToken):
    """Raised when a token has been explicitly revoked/blacklisted."""


class InvalidPassword(SecurityError):
    """Raised when a password verification fails."""
