"""Exception hierarchy used by python-openioc.

All public errors derive from :class:`OpenIOCError`, so callers can catch
that single base class to handle any failure originating from this
library.
"""


class OpenIOCError(Exception):
    """Base class for all python-openioc exceptions.

    Catching this exception type matches any error raised by the
    library's parsers, writers, validator, or converter.
    """


class ParseError(OpenIOCError):
    """Raised when an OpenIOC document cannot be parsed.

    Triggered by malformed XML, an unexpected root element, or a
    required element being absent from the document.
    """


class ValidationError(OpenIOCError):
    """Raised when an :class:`~openioc.models.IOC` fails validation.

    Aggregates multiple findings so the caller can report all problems
    at once instead of one round-trip per error.

    Attributes:
        errors: Human-readable error messages collected during the
            validation pass.
        source_format: Either ``"1.0"`` or ``"1.1"`` (or ``""``) marking
            which schema the IOC was validated against. Useful when the
            same handler validates both formats.
    """

    def __init__(self, errors: list[str], source_format: str = "") -> None:
        """Initialise the exception.

        Args:
            errors: Non-empty list of error messages produced by the
                validator.
            source_format: Schema version that produced the errors.
        """
        self.errors = errors
        self.source_format = source_format
        super().__init__("\n".join(errors))


class ConversionError(OpenIOCError):
    """Raised when :func:`openioc.convert_10_to_11` cannot proceed.

    Typically because the input IOC has an unrecognised
    ``format_version``.
    """


class WriteError(OpenIOCError):
    """Raised when an :class:`~openioc.models.IOC` cannot be serialised.

    Triggered when required fields are missing for the chosen target
    format (for example, an empty ``Indicator.id`` is fatal in 1.1 but
    tolerated in 1.0).
    """
