class SpawnError(Exception):
    """Base exception for Spawn."""
    pass


class StructureParseError(SpawnError):
    """Raised when pasted structure text cannot be parsed."""
