from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("spawn")
except PackageNotFoundError:
    __version__ = "0.5.0"
