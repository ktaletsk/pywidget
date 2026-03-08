---
name: create-pywidget
description: Build interactive Jupyter and marimo widgets with pywidget using pure Python rendering via Pyodide. Use when user asks to "create a widget", "build a PyWidget", "make an interactive visualization", "write a pywidget", "build a widget with pywidget", or work with the pywidget library.
---

pywidget lets you write Jupyter/marimo widgets entirely in Python — no JavaScript. `render()` and `update()` methods are extracted via `inspect.getsource()`, sent to the browser, and executed in Pyodide (WASM). The kernel never runs these methods.

<example title="Complete working widget">
```python
import traitlets
from pywidget import PyWidget


class CounterWidget(PyWidget):
    count = traitlets.Int(0).tag(sync=True)

    def render(self, el, model):
        count = model.get("count")
        el.innerHTML = f"""
        <div style="display:flex; align-items:center; gap:12px;
                    font-family:system-ui, sans-serif; padding:12px;">
            <button id="dec" style="padding:6px 14px; font-size:16px;
                cursor:pointer; border:1px solid currentColor;
                background:transparent; color:inherit; border-radius:6px;">−</button>
            <span id="display" style="font-size:22px; min-width:48px;
                text-align:center;">{count}</span>
            <button id="inc" style="padding:6px 14px; font-size:16px;
                cursor:pointer; border:1px solid currentColor;
                background:transparent; color:inherit; border-radius:6px;">+</button>
        </div>
        """

        def on_inc(event):
            new = model.get("count") + 1
            model.set("count", new)
            model.save_changes()
            el.querySelector("#display").textContent = str(new)

        def on_dec(event):
            new = model.get("count") - 1
            model.set("count", new)
            model.save_changes()
            el.querySelector("#display").textContent = str(new)

        el.querySelector("#inc").addEventListener("click", create_proxy(on_inc))
        el.querySelector("#dec").addEventListener("click", create_proxy(on_dec))

    def update(self, el, model):
        display = el.querySelector("#display")
        if display:
            display.textContent = str(model.get("count"))


# Jupyter: just display the instance
CounterWidget()

# marimo: wrap with mo.ui.anywidget
widget = mo.ui.anywidget(CounterWidget())
widget
# Read state from another cell: widget.value["count"]
```
</example>

The above is a minimal example. Widgets can grow much larger when they involve
heavy computation or elaborate HTML. For large `render` bodies, consider the
string-based `_py_render` alternative (see below).

When sharing the widget, keep the example minimal. Don't combine with other
marimo UI elements unless explicitly asked.

## Best Practices

Unless specifically told otherwise, assume the following:

1. **Define `render(self, el, model)` — called once on mount**:
   - Set `el.innerHTML`, then attach event listeners
   - Use `model.get(name)` to read traitlets, `model.set(name, value)` + `model.save_changes()` to write
   - All helper functions, imports, and computation must live inside the method body (source is extracted as standalone code)
   - Wrap every callback passed to a JS API with `create_proxy(fn)` to prevent garbage collection
   - `render` can be `async` for APIs that return promises (e.g. `navigator.mediaDevices`)

2. **Define `update(self, el, model)` — called on every traitlet change**:
   - For simple widgets, update specific DOM elements directly
   - For complex widgets, delegate to render: `render(el, model)` (bare function name, not `self.render`)
   - Never duplicate render logic — just call `render(el, model)` instead

3. **Style for both light and dark mode**:
   - Use `color: inherit` and `background: transparent` on interactive elements so they adapt to the host theme
   - For custom colors, use CSS variables or `@media (prefers-color-scheme: dark) { ... }` in a `<style>` tag within `el.innerHTML`
   - Avoid hardcoded light-only colors (white text on bright gradients, etc.) unless the design is self-contained

4. **Traitlets — kernel ↔ browser state**:
   - Tag every synced traitlet with `.tag(sync=True)`
   - Types: `Int`, `Float`, `Unicode`, `Bool`, `List`, `Dict`, `Tuple`, `Bytes`
   - For complex nested data, serialize to a JSON string (`traitlets.Unicode`)
   - Python constructors validate bounds, lengths, or choices; let `ValueError`/`TraitError` guide you instead of duplicating validation logic

5. **Browser-side packages** (`_py_packages`):
   - List packages to install via micropip before rendering
   - These must be Pyodide-compatible (pure Python or available as WASM wheels)
   - Import them inside `render`/`update`, not at module level

6. **Display the widget**:
   - **Jupyter / Colab**: display the instance directly (`CounterWidget()` or `display(widget)`)
   - **marimo**: wrap with `widget = mo.ui.anywidget(MyWidget())` and display `widget`
   - **marimo state access**: `widget.value` returns a dict of synced traitlets, e.g. `widget.value["count"]`

7. **Keep examples minimal**:
   - Show core utility only
   - Don't combine with other UI elements unless explicitly requested

## Model API (browser-side)

| Method | Description |
|--------|-------------|
| `model.get(name)` | Read traitlet (returns Python types via `pyodide.toPy`) |
| `model.set(name, value)` | Write traitlet (local until `save_changes`) |
| `model.save_changes()` | Push pending changes to kernel |
| `model.on(event, cb)` | Listen for changes, e.g. `"change:count"` |

Browser-side builtins (pre-injected, do not import): `create_proxy`, `to_js`, `document`, `console`.

## String-based `_py_render`

For large widgets or dynamically generated code, set `_py_render` directly
instead of defining methods. Method extraction is skipped when `_py_render`
is set.

```python
class SimpleWidget(PyWidget):
    _py_render = """
def render(el, model):
    el.innerHTML = "<h2>Hello from Pyodide!</h2>"
"""
```

## Boundaries

### Never

- Reference kernel-side variables, files, or non-Pyodide packages inside `render`/`update`
- Call `self.render(...)` — `self` is stripped; use bare `render(el, model)`
- Import `create_proxy`, `to_js`, `console`, or `document` — they are pre-injected
- Forget that `print()` goes to browser DevTools console, not notebook output

### marimo-specific

marimo auto-detects all names referenced in a cell and adds them to the cell
function signature. `create_proxy`, `console`, etc. will appear as cell
parameters even though they are browser-only builtins. This is expected — do
not remove them from the signature.

Dumber is better. Prefer obvious, direct code over clever abstractions — someone
new to the project should be able to read the code top-to-bottom and understand
it without tracing through indirection.

## Additional examples

For more patterns (NumPy computation, Pandas tables, image rendering, sliders),
read `examples.md` in this skill directory.
