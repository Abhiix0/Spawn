class SpawnError(Exception):
    """Base exception for Spawn. ``exit_code`` is the CLI exit status."""

    exit_code = 1


class InvalidInputError(SpawnError):
    """Raised for invalid user input (names, options, values)."""

    exit_code = 1


class ConfigError(SpawnError):
    """Raised for invalid or unreadable config files."""

    exit_code = 1


class FilesystemError(SpawnError):
    """Raised for filesystem problems (destination exists, OS errors)."""

    exit_code = 3


class ToolchainError(SpawnError):
    """Raised when git or uv is missing or fails."""

    exit_code = 4


class GenerationError(SpawnError):
    """Raised when project generation fails."""

    exit_code = 5


class TemplateError(GenerationError):
    """Raised when a template cannot be resolved or built."""

    exit_code = 5


class PublishError(SpawnError):
    """Raised when publishing a generated project fails."""

    exit_code = 6


class StructureParseError(InvalidInputError):
    """Raised when pasted structure text cannot be parsed."""
