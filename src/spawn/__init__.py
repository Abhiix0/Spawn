from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("spawnio")
except PackageNotFoundError:
    __version__ = "1.0.9"
