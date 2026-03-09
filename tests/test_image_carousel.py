"""Tests for the ImageCarousel widget (Python-side only, no browser)."""

from __future__ import annotations

from pywidget import ImageCarousel


# ---------------------------------------------------------------------------
# Basic instantiation
# ---------------------------------------------------------------------------


def test_image_carousel_instantiates() -> None:
    """ImageCarousel can be created with no arguments."""
    w = ImageCarousel()
    assert w is not None


def test_image_carousel_default_images() -> None:
    """Default images list is empty."""
    w = ImageCarousel()
    assert list(w.images) == []


def test_image_carousel_default_index() -> None:
    """Default index is 0."""
    w = ImageCarousel()
    assert w.index == 0


# ---------------------------------------------------------------------------
# Traitlet metadata
# ---------------------------------------------------------------------------


def test_images_trait_synced() -> None:
    """images is a synced List traitlet."""
    w = ImageCarousel()
    assert w.has_trait("images")
    assert w.trait_metadata("images", "sync") is True


def test_index_trait_synced() -> None:
    """index is a synced Int traitlet."""
    w = ImageCarousel()
    assert w.has_trait("index")
    assert w.trait_metadata("index", "sync") is True


def test_has_py_render_trait() -> None:
    """_py_render is set from the render method extraction."""
    w = ImageCarousel()
    assert w.has_trait("_py_render")
    assert w.trait_metadata("_py_render", "sync") is True
    assert w._py_render != ""


def test_has_esm_trait() -> None:
    """_esm is set to the bridge JS."""
    w = ImageCarousel()
    assert w.has_trait("_esm")
    assert "pyodide" in w._esm.lower()


# ---------------------------------------------------------------------------
# Keyword argument instantiation
# ---------------------------------------------------------------------------


def test_kwarg_images() -> None:
    """images can be set via keyword argument."""
    urls = ["https://example.com/a.png", "https://example.com/b.png"]
    w = ImageCarousel(images=urls)
    assert list(w.images) == urls


def test_kwarg_index() -> None:
    """index can be set via keyword argument."""
    w = ImageCarousel(images=["url1", "url2", "url3"], index=2)
    assert w.index == 2


def test_kwarg_images_and_index() -> None:
    """Both images and index can be set via keyword arguments."""
    urls = ["a", "b", "c"]
    w = ImageCarousel(images=urls, index=1)
    assert list(w.images) == urls
    assert w.index == 1


# ---------------------------------------------------------------------------
# State mutation
# ---------------------------------------------------------------------------


def test_set_images() -> None:
    """images can be changed after creation."""
    w = ImageCarousel()
    w.images = ["url1", "url2"]
    assert list(w.images) == ["url1", "url2"]


def test_set_index() -> None:
    """index can be changed after creation."""
    w = ImageCarousel(images=["url1", "url2"])
    w.index = 1
    assert w.index == 1


# ---------------------------------------------------------------------------
# Render and update method extraction
# ---------------------------------------------------------------------------


def test_render_method_extracted() -> None:
    """render() is auto-extracted into _py_render."""
    w = ImageCarousel()
    assert "def render(el, model):" in w._py_render
    assert "self" not in w._py_render


def test_update_method_extracted() -> None:
    """update() is auto-extracted into _py_render."""
    w = ImageCarousel()
    assert "def update(el, model):" in w._py_render
    assert "self" not in w._py_render


def test_render_contains_navigation_logic() -> None:
    """render() contains left/right button navigation logic."""
    w = ImageCarousel()
    assert "carousel-left" in w._py_render
    assert "carousel-right" in w._py_render
    assert "carousel-img" in w._py_render


def test_render_contains_model_operations() -> None:
    """render() uses model.get, model.set, model.save_changes."""
    w = ImageCarousel()
    assert 'model.get("index")' in w._py_render
    assert 'model.set("index"' in w._py_render
    assert "model.save_changes()" in w._py_render


def test_render_contains_create_proxy() -> None:
    """render() wraps callbacks with create_proxy."""
    w = ImageCarousel()
    assert "create_proxy" in w._py_render


def test_render_handles_empty_images() -> None:
    """render() handles the case of an empty image list."""
    w = ImageCarousel()
    assert "No images" in w._py_render


def test_update_handles_empty_images() -> None:
    """update() handles the case of an empty image list."""
    w = ImageCarousel()
    # The update portion of _py_render should handle empty state
    source = w._py_render
    update_part = source[source.index("def update(el, model):"):]
    assert "No images" in update_part


# ---------------------------------------------------------------------------
# Multiple instances
# ---------------------------------------------------------------------------


def test_multiple_instances_independent() -> None:
    """Multiple ImageCarousel instances have independent state."""
    a = ImageCarousel(images=["url_a1", "url_a2"], index=0)
    b = ImageCarousel(images=["url_b1", "url_b2", "url_b3"], index=1)

    assert list(a.images) == ["url_a1", "url_a2"]
    assert list(b.images) == ["url_b1", "url_b2", "url_b3"]
    assert a.index == 0
    assert b.index == 1

    # Same bridge ESM
    assert a._esm == b._esm


# ---------------------------------------------------------------------------
# Anywidget ID
# ---------------------------------------------------------------------------


def test_anywidget_id() -> None:
    """ImageCarousel has an _anywidget_id containing the class name."""
    w = ImageCarousel()
    assert w.has_trait("_anywidget_id")
    assert "ImageCarousel" in w._anywidget_id
