"""Domain-specific exceptions, mapped to HTTP responses in main.py."""


class AppException(Exception):
    """Base class for all application-level exceptions."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ModelFileNotFoundError(AppException):
    """Raised when the .pth checkpoint does not exist on disk."""


class ModelLoadError(AppException):
    """Raised when the checkpoint exists but fails to load (corrupted/mismatched)."""


class ModelNotReadyError(AppException):
    """Raised when an inference request arrives before the model has loaded."""


class ImageGenerationError(AppException):
    """Raised when the forward pass or tensor->image conversion fails."""


class InvalidFilenameError(AppException):
    """Raised when a requested filename is invalid or attempts path traversal."""


class ImageNotFoundError(AppException):
    """Raised when a requested generated image does not exist."""


class RateLimitExceededError(AppException):
    """Raised when a client exceeds the allowed generation request rate."""
