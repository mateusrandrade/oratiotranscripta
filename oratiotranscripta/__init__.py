"""OratioTranscripta - pipeline modular."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("oratiotranscripta")
except PackageNotFoundError:  # pragma: no cover - fallback when run from source
    __version__ = "0.1.0"

from .cli import main

__all__ = ["main", "__version__"]
