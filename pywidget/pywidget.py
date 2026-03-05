"""PyWidget: Write Jupyter widget rendering logic in pure Python via Pyodide.

PyWidget subclasses anywidget.AnyWidget and injects a JS bridge ESM that loads
a shared Pyodide instance in the browser, then executes the user's Python
rendering code (_py_render) inside that WASM runtime. The anywidget model API
(get/set/save_changes/on) is proxied through to the browser-side Python code,
enabling full bidirectional state sync without users writing any JavaScript.
"""

from __future__ import annotations

import inspect
import pathlib
import re
import textwrap

import traitlets.traitlets as t
from anywidget import AnyWidget

# Read the bridge JS from the co-located file. This string becomes the _esm
# traitlet value, which anywidget's standard machinery loads as an ES module
# in the browser (via Blob URL + dynamic import).
_BRIDGE_ESM = (pathlib.Path(__file__).parent / "_bridge.js").read_text()

# Methods on PyWidget subclasses that are auto-extracted for browser execution.
_BROWSER_METHODS = ("render", "update")


def _strip_self_param(source: str) -> str:
    """Remove ``self`` from a function definition's parameter list.

    Handles ``def f(self, ...)``, ``def f(self)``, and ``async def f(self, ...)``.
    If ``self`` is not present, the source is returned unchanged.
    """
    return re.sub(r"(def\s+\w+\s*\()\s*self\s*,?\s*", r"\1", source, count=1)


def _extract_method_source(method: object) -> str:
    """Extract a method's source code for browser execution.

    Dedents the source and strips the ``self`` parameter so the resulting
    code defines a standalone function suitable for ``runPythonAsync()``.
    """
    source = inspect.getsource(method)  # type: ignore[arg-type]
    source = textwrap.dedent(source)
    source = _strip_self_param(source)
    return source


class PyWidget(AnyWidget):
    """A widget where the rendering logic is written in Python and executed
    in the browser via Pyodide.

    There are two ways to define the browser-side rendering code:

    **Method-based** (recommended) -- define ``render`` and optionally
    ``update`` as regular methods.  The ``self`` parameter is stripped
    automatically; the methods' source code is extracted at class-creation
    time via ``inspect.getsource()`` and sent to the browser.

    >>> class Counter(PyWidget):
    ...     count = traitlets.Int(0).tag(sync=True)
    ...
    ...     def render(self, el, model):
    ...         el.innerHTML = f'Count: {model.get("count")}'
    ...
    ...     def update(self, el, model):
    ...         el.innerHTML = f'Count: {model.get("count")}'

    **String-based** -- set ``_py_render`` to a string containing
    ``render(el, model)`` and optionally ``update(el, model)`` functions.
    If ``_py_render`` is defined on the class, method extraction is skipped.

    The ``model`` object exposed to the browser-side Python code supports:

    - ``model.get(name)`` -- read a synced traitlet (returns Python-native types)
    - ``model.set(name, value)`` -- write a synced traitlet
    - ``model.save_changes()`` -- push pending changes to the kernel
    - ``model.on(event, callback)`` -- listen for changes (e.g. "change:count")

    The browser-side namespace also provides ``create_proxy`` (from
    ``pyodide.ffi``) for preventing garbage-collection of Python callbacks
    passed to JavaScript APIs like ``addEventListener``.
    """

    # The JS bridge is set as _esm. AnyWidget.__init__ converts this class
    # attribute into a synced Unicode traitlet via the standard path
    # (widget.py:41-48). Users should NOT override _esm.
    _esm = _BRIDGE_ESM

    def __init_subclass__(cls, **kwargs: dict) -> None:  # type: ignore[override]
        """Auto-extract ``render``/``update`` methods into ``_py_render``."""
        # If _py_render is explicitly defined on this class (string or
        # traitlet), the user wants full control — skip method extraction.
        if "_py_render" not in cls.__dict__:
            parts: list[str] = []
            for name in _BROWSER_METHODS:
                if name not in cls.__dict__:
                    continue
                method = cls.__dict__[name]
                # Unwrap staticmethod descriptors so inspect.getsource works.
                if isinstance(method, staticmethod):
                    method = method.__func__
                if not callable(method):
                    continue
                try:
                    parts.append(_extract_method_source(method))
                except (OSError, TypeError):
                    # inspect.getsource() can fail (e.g. built-in functions,
                    # or code defined in a context with no source).
                    pass
            if parts:
                cls._py_render = "\n\n".join(parts)

        super().__init_subclass__(**kwargs)

    def __init__(self, *args: object, **kwargs: object) -> None:
        # Dynamically create _py_render and _py_packages as synced traitlets.
        #
        # This mirrors how AnyWidget handles _esm (widget.py:41-48): if the
        # subclass defines _py_render as a plain class attribute (a string,
        # not a traitlet), we wrap it in a Unicode traitlet with sync=True.
        # This lets users write the natural:
        #
        #   class MyWidget(PyWidget):
        #       _py_render = "def render(el, model): ..."
        #
        # instead of the verbose:
        #
        #   class MyWidget(PyWidget):
        #       _py_render = traitlets.Unicode("...").tag(sync=True)
        py_traits: dict[str, t.TraitType] = {}

        # Handle _py_render
        if hasattr(self, "_py_render") and not self.has_trait("_py_render"):
            py_traits["_py_render"] = t.Unicode(str(getattr(self, "_py_render"))).tag(
                sync=True
            )
        elif not hasattr(self, "_py_render"):
            py_traits["_py_render"] = t.Unicode("").tag(sync=True)

        # Handle _py_packages
        if hasattr(self, "_py_packages") and not self.has_trait("_py_packages"):
            py_traits["_py_packages"] = t.List(
                t.Unicode(), list(getattr(self, "_py_packages"))
            ).tag(sync=True)
        elif not hasattr(self, "_py_packages"):
            py_traits["_py_packages"] = t.List(t.Unicode(), []).tag(sync=True)

        if py_traits:
            self.add_traits(**py_traits)

        super().__init__(*args, **kwargs)
