"""Tests for the PyWidget class (Python-side only, no browser)."""

from __future__ import annotations

import traitlets.traitlets as t

from pywidget import PyWidget
from pywidget.pywidget import _extract_method_source, _strip_self_param


# ---------------------------------------------------------------------------
# Basic instantiation
# ---------------------------------------------------------------------------


def test_pywidget_instantiates() -> None:
    """PyWidget can be created with no arguments."""
    w = PyWidget()
    assert w is not None


def test_pywidget_has_py_render_trait() -> None:
    """_py_render becomes a synced Unicode traitlet."""
    w = PyWidget()
    assert w.has_trait("_py_render")
    assert w.trait_metadata("_py_render", "sync") is True
    assert w._py_render == ""


def test_pywidget_has_py_packages_trait() -> None:
    """_py_packages becomes a synced List traitlet."""
    w = PyWidget()
    assert w.has_trait("_py_packages")
    assert w.trait_metadata("_py_packages", "sync") is True
    assert w._py_packages == []


def test_pywidget_has_esm_trait() -> None:
    """_esm is set to the bridge JS and is a synced trait."""
    w = PyWidget()
    assert w.has_trait("_esm")
    assert w.trait_metadata("_esm", "sync") is True
    # The bridge JS should contain the Pyodide CDN URL
    assert "pyodide" in w._esm.lower()
    assert "ensurePyodide" in w._esm


def test_pywidget_has_anywidget_id() -> None:
    """_anywidget_id is set correctly by AnyWidget machinery."""
    w = PyWidget()
    assert w.has_trait("_anywidget_id")
    assert "PyWidget" in w._anywidget_id


# ---------------------------------------------------------------------------
# Subclassing with _py_render as class attribute
# ---------------------------------------------------------------------------


def test_subclass_py_render_class_attr() -> None:
    """_py_render defined as a plain string class attribute becomes a synced trait."""
    render_code = 'def render(el, model):\n    el.innerHTML = "hello"'

    class MyWidget(PyWidget):
        _py_render = render_code

    w = MyWidget()
    assert w.has_trait("_py_render")
    assert w._py_render == render_code
    assert w.trait_metadata("_py_render", "sync") is True


def test_subclass_py_packages_class_attr() -> None:
    """_py_packages defined as a plain list class attribute becomes a synced trait."""

    class MyWidget(PyWidget):
        _py_packages = ["numpy", "pandas"]

    w = MyWidget()
    assert w.has_trait("_py_packages")
    assert list(w._py_packages) == ["numpy", "pandas"]
    assert w.trait_metadata("_py_packages", "sync") is True


def test_subclass_py_render_as_traitlet() -> None:
    """_py_render defined as an explicit traitlet also works."""
    render_code = 'def render(el, model):\n    el.innerHTML = "hello"'

    class MyWidget(PyWidget):
        _py_render = t.Unicode(render_code).tag(sync=True)

    w = MyWidget()
    assert w.has_trait("_py_render")
    assert w._py_render == render_code


# ---------------------------------------------------------------------------
# Subclassing with additional user traitlets
# ---------------------------------------------------------------------------


def test_subclass_with_user_traitlets() -> None:
    """User-defined traitlets work alongside pywidget traits."""

    class Counter(PyWidget):
        count = t.Int(0).tag(sync=True)
        _py_render = 'def render(el, model):\n    el.innerHTML = "counter"'

    w = Counter()
    assert w.has_trait("count")
    assert w.count == 0
    assert w.has_trait("_py_render")
    assert w.has_trait("_esm")

    # Verify user traitlet is synced
    assert w.trait_metadata("count", "sync") is True

    # Verify we can set the user traitlet
    w.count = 42
    assert w.count == 42


def test_subclass_multiple_user_traitlets() -> None:
    """Multiple user traitlets coexist without interference."""

    class DataWidget(PyWidget):
        name = t.Unicode("World").tag(sync=True)
        value = t.Float(3.14).tag(sync=True)
        items = t.List(t.Int(), [1, 2, 3]).tag(sync=True)
        _py_render = 'def render(el, model):\n    el.innerHTML = "data"'

    w = DataWidget()
    assert w.name == "World"
    assert w.value == 3.14
    assert list(w.items) == [1, 2, 3]

    w.name = "Test"
    assert w.name == "Test"


# ---------------------------------------------------------------------------
# Keyword argument instantiation
# ---------------------------------------------------------------------------


def test_kwarg_py_render() -> None:
    """_py_render can be set via keyword argument."""
    code = 'def render(el, model):\n    el.innerHTML = "kwarg"'
    w = PyWidget(_py_render=code)
    assert w._py_render == code


def test_kwarg_py_packages() -> None:
    """_py_packages can be set via keyword argument."""
    w = PyWidget(_py_packages=["scipy"])
    assert list(w._py_packages) == ["scipy"]


# ---------------------------------------------------------------------------
# Bridge ESM content validation
# ---------------------------------------------------------------------------


def test_bridge_esm_exports_default() -> None:
    """The bridge ESM exports a default object with initialize and render."""
    w = PyWidget()
    assert "export default" in w._esm
    assert "async initialize" in w._esm
    assert "async render" in w._esm


def test_bridge_esm_has_model_proxy() -> None:
    """The bridge ESM contains the model proxy implementation."""
    w = PyWidget()
    assert "createModelProxy" in w._esm


def test_bridge_esm_has_error_handling() -> None:
    """The bridge ESM contains error display logic."""
    w = PyWidget()
    assert "showError" in w._esm


def test_bridge_esm_has_namespace_isolation() -> None:
    """The bridge ESM creates isolated namespaces per view."""
    w = PyWidget()
    # Check for the namespace creation pattern
    assert "pyodide.toPy({})" in w._esm


# ---------------------------------------------------------------------------
# Multiple instances don't interfere
# ---------------------------------------------------------------------------


def test_multiple_instances_independent() -> None:
    """Multiple PyWidget instances have independent state."""

    class WidgetA(PyWidget):
        value = t.Int(1).tag(sync=True)
        _py_render = 'def render(el, model):\n    el.innerHTML = "A"'

    class WidgetB(PyWidget):
        value = t.Int(2).tag(sync=True)
        _py_render = 'def render(el, model):\n    el.innerHTML = "B"'

    a = WidgetA()
    b = WidgetB()

    assert a.value == 1
    assert b.value == 2
    assert a._py_render != b._py_render

    # Same bridge ESM
    assert a._esm == b._esm


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


def test_version() -> None:
    """pywidget exposes a version string."""
    from pywidget import __version__

    assert __version__ == "0.1.0"


# ---------------------------------------------------------------------------
# Source extraction helpers
# ---------------------------------------------------------------------------


def test_strip_self_param_with_args() -> None:
    assert _strip_self_param("def f(self, a, b):") == "def f(a, b):"


def test_strip_self_param_only_self() -> None:
    assert _strip_self_param("def f(self):") == "def f():"


def test_strip_self_param_no_self() -> None:
    assert _strip_self_param("def f(a, b):") == "def f(a, b):"


def test_strip_self_param_async() -> None:
    assert _strip_self_param("async def f(self, a):") == "async def f(a):"


def test_strip_self_param_extra_spaces() -> None:
    assert _strip_self_param("def f( self , a ):") == "def f(a ):"


def test_extract_method_source_strips_self() -> None:
    class Example:
        def render(self, el, model):
            el.innerHTML = "hello"

    source = _extract_method_source(Example.render)
    assert "def render(el, model):" in source
    assert "self" not in source
    assert 'el.innerHTML = "hello"' in source


def test_extract_method_source_dedents() -> None:
    class Example:
        def render(self, el, model):
            el.innerHTML = "hello"

    source = _extract_method_source(Example.render)
    # Should start at column 0, not indented
    assert source.startswith("def render(")


# ---------------------------------------------------------------------------
# Method-based API: __init_subclass__ extraction
# ---------------------------------------------------------------------------


def test_method_render_extracted() -> None:
    """A render method is auto-extracted into _py_render."""

    class MyWidget(PyWidget):
        def render(self, el, model):
            el.innerHTML = "hello from method"

    w = MyWidget()
    assert w.has_trait("_py_render")
    assert "def render(el, model):" in w._py_render
    assert "hello from method" in w._py_render
    assert "self" not in w._py_render


def test_method_render_and_update_extracted() -> None:
    """Both render and update methods are extracted and concatenated."""

    class MyWidget(PyWidget):
        def render(self, el, model):
            el.innerHTML = "render-part"

        def update(self, el, model):
            el.innerHTML = "update-part"

    w = MyWidget()
    assert "render-part" in w._py_render
    assert "update-part" in w._py_render
    # Both functions should be present
    assert "def render(el, model):" in w._py_render
    assert "def update(el, model):" in w._py_render


def test_method_update_only() -> None:
    """Only defining update (no render) still sets _py_render."""

    class MyWidget(PyWidget):
        def update(self, el, model):
            el.innerHTML = "update-only"

    # _py_render is set with just the update function
    assert hasattr(MyWidget, "_py_render")
    assert "def update(el, model):" in MyWidget._py_render


def test_explicit_py_render_overrides_methods() -> None:
    """If _py_render is set as a class attribute, methods are NOT extracted."""

    class MyWidget(PyWidget):
        _py_render = 'def render(el, model):\n    el.innerHTML = "explicit"'

        def render(self, el, model):
            el.innerHTML = "from method"

    w = MyWidget()
    assert "explicit" in w._py_render
    assert "from method" not in w._py_render


def test_method_with_user_traitlets() -> None:
    """Method extraction works alongside user-defined traitlets."""

    class Counter(PyWidget):
        count = t.Int(0).tag(sync=True)

        def render(self, el, model):
            count = model.get("count")
            el.innerHTML = f"Count: {count}"

        def update(self, el, model):
            el.innerHTML = f"Count: {model.get('count')}"

    w = Counter()
    assert w.has_trait("count")
    assert w.count == 0
    assert "def render(el, model):" in w._py_render
    assert "def update(el, model):" in w._py_render


def test_staticmethod_render() -> None:
    """@staticmethod render (no self) is also extracted."""

    class MyWidget(PyWidget):
        @staticmethod
        def render(el, model):
            el.innerHTML = "static"

    w = MyWidget()
    assert "def render(el, model):" in w._py_render
    assert "static" in w._py_render


def test_method_inheritance() -> None:
    """Child class without render inherits parent's extracted _py_render."""

    class Parent(PyWidget):
        def render(self, el, model):
            el.innerHTML = "parent"

    class Child(Parent):
        value = t.Int(0).tag(sync=True)

    w = Child()
    assert "parent" in w._py_render


def test_method_override_in_child() -> None:
    """Child class can override parent's render method."""

    class Parent(PyWidget):
        def render(self, el, model):
            el.innerHTML = "parent"

    class Child(Parent):
        def render(self, el, model):
            el.innerHTML = "child"

    w = Child()
    assert "child" in w._py_render
    assert "parent" not in w._py_render


def test_method_multiline_body() -> None:
    """Methods with multiline bodies are extracted correctly."""

    class MyWidget(PyWidget):
        def render(self, el, model):
            name = model.get("name")
            html = f"<div>Hello {name}</div>"
            el.innerHTML = html

    w = MyWidget()
    source = w._py_render
    assert 'name = model.get("name")' in source
    assert "el.innerHTML = html" in source
