"""pywidget: Jupyter widgets with pure Python rendering via Pyodide."""

from __future__ import annotations

from .image_carousel import ImageCarousel
from .pywidget import PyWidget

__version__ = "0.1.0"
__all__ = ["ImageCarousel", "PyWidget", "__version__"]
