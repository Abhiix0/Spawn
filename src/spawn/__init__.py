from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("spawn")
except PackageNotFoundError:
    __version__ = "0.7.0"
