class OpenIOCError(Exception):
    """Base exception for all python-openioc errors."""


class ParseError(OpenIOCError):
    """Raised when XML is malformed or a required element is missing."""


class ValidationError(OpenIOCError):
    """Raised when an IOC fails schema or structural validation."""

    def __init__(self, errors: list[str], source_format: str = "") -> None:
        self.errors = errors
        self.source_format = source_format
        super().__init__("\n".join(errors))


class ConversionError(OpenIOCError):
    """Raised when 1.0→1.1 conversion cannot proceed."""


class WriteError(OpenIOCError):
    """Raised when a model cannot be serialised to XML."""
