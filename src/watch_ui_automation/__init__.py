from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("watch-ui-automation")
except PackageNotFoundError:
    __version__ = "0.1.0"
