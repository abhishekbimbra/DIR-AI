from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("dir-ai")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.1.0"
