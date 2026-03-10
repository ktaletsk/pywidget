# Invent + pywidget: Collaboration Proposal

## The Opportunity

[pywidget](https://github.com/ktaletsk/pywidget) lets people write Jupyter/marimo
widget rendering logic in pure Python — no JavaScript required. It works by running
Python in the browser via [Pyodide](https://pyodide.org/) (WASM), using
[anywidget](https://anywidget.dev/) as the transport layer.

The remaining friction: users still need to write HTML, CSS, and DOM APIs
(`innerHTML`, `querySelector`, `addEventListener`…) inside their `render()` methods.

**Invent solves exactly this.** Its `Button`, `Label`, `Slider`, `TextInput`,
`Row`, `Column`, `Grid`, and 25+ other widgets provide a fully Pythonic UI layer.
Users write `Button(text="Go")` instead of `<button style="…">Go</button>`.

This document proposes making Invent work on Pyodide — the same WASM runtime
Invent already uses under the hood via PyScript.

---

## What Was Done

A soft-fork of Invent at
[ktaletsk/invent — pyodide-compat](https://github.com/ktaletsk/invent/tree/pyodide-compat)
replaces all PyScript-specific imports with direct Pyodide equivalents across
all 48 source files.

### The complete mapping

| Was (PyScript) | Now (Pyodide) |
|---|---|
| `from pyscript.web import div, button, …` | `from invent._compat import div, button, …` |
| `from pyscript.ffi import create_proxy` | `from pyodide.ffi import create_proxy` |
| `from pyscript.ffi import to_js` | `from pyodide.ffi import to_js` |
| `from pyscript import window` | `from js import window` |
| `from pyscript.web import page` | `from js import document` |
| `element.classes.add("cls")` | `element.classList.add("cls")` |
| `element.style.remove("prop")` | `element.style.removeProperty("prop")` |
| `element.find("selector")` | `element.querySelectorAll("selector")` |

### New file: `src/invent/_compat.py`

A module of element factory functions (`div()`, `button()`, `input_()`, etc.)
that create raw DOM `JsProxy` elements via `js.document.createElement`. They
accept the same kwarg interface as `pyscript.web` factories, plus a `classes=`
kwarg for CSS class lists and positional child nodes.

### What is stubbed (not needed for notebook widget use)

- `load_js_modules()` — returns immediately. Leaflet, Chart.js, marked, DOMPurify
  can be loaded per-widget when needed.
- `IndexDBBackend` — falls back to in-memory storage. `LocalStorageBackend`
  still works via `js.window.localStorage`.
- `invent.go()` / `App` / `Page` — the full-page SPA lifecycle is not used when
  Invent widgets are embedded in notebook cells.

---

## Seeing It Work

The POC notebook is at
[`examples/invent_demo_mo.py`](examples/invent_demo_mo.py)
in the [ktaletsk/pywidget feat/invent-integration](https://github.com/ktaletsk/pywidget/tree/feat/invent-integration)
branch.

It shows four working examples — counter, slider, greeter form, RGB mixer — at
two levels of Invent integration, with direct before/after comparisons against
the raw DOM approach.

To run it locally:

```bash
git clone https://github.com/ktaletsk/pywidget.git
cd pywidget
git checkout feat/invent-integration
pip install -e .
marimo run examples/invent_demo_mo.py
```

---

## Inspecting the Diff

```bash
git clone https://github.com/ktaletsk/invent.git
cd invent
git diff main..pyodide-compat
```

The diff shows the complete scope of changes needed to make Invent
runtime-agnostic. It is mechanical and concentrated — the core architecture
(Component/Property/Event/PubSub/DataStore) required zero changes.

---

## The Upstream Proposal

Rather than maintaining a long-lived fork, the goal is to upstream this to
`invent-framework/invent` so Invent officially supports Pyodide alongside PyScript.

**Suggested approach:** introduce `src/invent/_platform.py` as a thin adapter
that the whole codebase imports from instead of directly from `pyscript`:

```python
# src/invent/_platform.py
try:
    from pyscript.ffi import create_proxy, to_js
    from pyscript.web import div, button, input_, ...
    from pyscript import window
except ImportError:
    # Pyodide path (no PyScript)
    from pyodide.ffi import create_proxy, to_js
    from invent._compat import div, button, input_, ...
    from js import window
```

This approach:
- Keeps PyScript as the primary/default runtime (no behaviour change for
  existing Invent users)
- Adds Pyodide as a supported alternative (enables notebook widget use)
- Is testable: Invent's CI can run the Pyodide path in a headless browser
- Makes the coupling explicit in one place rather than spread across 48 files

Once merged upstream, pywidget can add Invent as a direct dependency, and
users get `Button`, `Label`, `Slider`, `Row`, `Grid`, and the rest of the
Invent widget library out of the box.

---

## Contact

- pywidget: [@ktaletsk](https://github.com/ktaletsk)
- Invent: [@ntoll](https://github.com/ntoll) /
  [invent-framework](https://github.com/invent-framework)
