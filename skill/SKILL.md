---
name: create-pywidget
description: Build interactive Jupyter and marimo widgets with pywidget using pure Python rendering via Pyodide. Use when user asks to "create a widget", "build a PyWidget", "make an interactive visualization", "write a pywidget", "build a widget with pywidget", or work with the pywidget library.
---

# pywidget

pywidget lets you write Jupyter/marimo widgets entirely in Python. `render()` and `update()` methods are extracted via `inspect.getsource()`, sent to the browser, and executed in Pyodide (WASM). The kernel never runs these methods.

## How it works

- Kernel side: define a `PyWidget` subclass with synced traitlets
- Browser side: `render(el, model)` and `update(el, model)` run in Pyodide
- Sync: `model.get()` / `model.set()` / `model.save_changes()` bridge kernel ↔ browser
- Builtins available in browser: `create_proxy`, `to_js`, `document`, `console`

## Complete working example

```python
import traitlets
from pywidget import PyWidget

class CounterWidget(PyWidget):
    count = traitlets.Int(0).tag(sync=True)

    def render(self, el, model):
        count = model.get("count")
        el.innerHTML = f"""
        <div style="display:flex; align-items:center; gap:12px; font-family:sans-serif;">
            <button id="dec">-</button>
            <span id="display">{count}</span>
            <button id="inc">+</button>
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
```

## Building a widget step by step

### 1. Traitlets — kernel ↔ browser state

```python
class MyWidget(PyWidget):
    count = traitlets.Int(0).tag(sync=True)
    name = traitlets.Unicode("").tag(sync=True)
    data = traitlets.List(traitlets.Float(), []).tag(sync=True)
    config_json = traitlets.Unicode("{}").tag(sync=True)
```

Types: `Int`, `Float`, `Unicode`, `Bool`, `List`, `Dict`, `Tuple`, `Bytes`.
For complex data, serialize to JSON string.

### 2. `render(self, el, model)` — called once on mount

Set `el.innerHTML`, then attach event listeners. All helper functions and
imports must be defined inside the method body (source is extracted as
standalone code).

### 3. `update(self, el, model)` — called on every traitlet change

For simple widgets, update specific DOM elements:
```python
def update(self, el, model):
    el.querySelector("#display").textContent = str(model.get("count"))
```

For complex widgets, delegate to render:
```python
def update(self, el, model):
    render(el, model)
```

### 4. Browser-side packages

```python
class StatsWidget(PyWidget):
    _py_packages = ["numpy"]

    def render(self, el, model):
        import numpy as np
        arr = np.array(list(model.get("data")))
        el.innerHTML = f"Mean: {arr.mean():.2f}"
```

### 5. marimo integration

```python
import marimo as mo
widget = mo.ui.anywidget(MyWidget())
widget
```

Read state in other cells: `widget.widget.count`

## Model API

| Method | Description |
|--------|-------------|
| `model.get(name)` | Read traitlet (returns Python types) |
| `model.set(name, value)` | Write traitlet (local until save_changes) |
| `model.save_changes()` | Push pending changes to kernel |
| `model.on(event, cb)` | Listen for changes, e.g. `"change:count"` |

## Boundaries

### ✅ Always

- Tag every synced traitlet with `.tag(sync=True)`
- Wrap every callback passed to JS APIs with `create_proxy(fn)`
- Call `model.save_changes()` after `model.set()`
- Define all helpers, imports, and computation inside `render()`/`update()`
- Use `render(el, model)` (bare function name) in `update()` for full re-render

### 🚫 Never

- Reference kernel-side variables, files, or non-Pyodide packages inside `render`/`update`
- Call `self.render(...)` — `self` is stripped; use bare `render(el, model)`
- Duplicate render logic in `update()` — just call `render(el, model)` instead
- Import `create_proxy`, `to_js`, `console`, or `document` — they are pre-injected
- Forget that `print()` goes to browser DevTools, not notebook output

### ⚠️ marimo-specific

marimo auto-detects all names referenced in a cell and adds them to the cell
function signature. `create_proxy`, `console`, etc. will appear as cell
parameters even though they are browser-only builtins. This is expected — do
not remove them from the signature.

## Additional examples

For more patterns (NumPy computation, Pandas tables, image rendering, sliders),
read `examples.md` in this skill directory.
