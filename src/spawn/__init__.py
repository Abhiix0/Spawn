from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("spawnio")
except PackageNotFoundError:
    __version__ = "1.0.7"
