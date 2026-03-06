# pywidget examples

## Static HTML (simplest)

```python
class HelloWidget(PyWidget):
    def render(self, el, model):
        el.innerHTML = """
        <div style="padding:20px; background:linear-gradient(135deg,#667eea,#764ba2);
                    border-radius:12px; color:white; font-family:sans-serif;">
            <h2 style="margin:0 0 8px 0;">Hello from Pyodide!</h2>
            <p style="margin:0; opacity:0.9;">Rendered by Python in WebAssembly.</p>
        </div>
        """
```

## Kernel → browser (read-only display with update)

```python
class GreeterWidget(PyWidget):
    name = traitlets.Unicode("World").tag(sync=True)

    def render(self, el, model):
        name = model.get("name")
        el.innerHTML = f'<span style="font-size:24px;">Hello, <strong>{name}</strong>!</span>'

    def update(self, el, model):
        render(el, model)

# Usage: GreeterWidget(name="Alice")
```

## Browser → kernel (bidirectional counter)

```python
class CounterWidget(PyWidget):
    count = traitlets.Int(0).tag(sync=True)

    def render(self, el, model):
        count = model.get("count")
        el.innerHTML = f"""
        <div style="font-family:sans-serif; display:flex; align-items:center; gap:12px;">
            <button id="dec" style="padding:8px 16px; font-size:18px; cursor:pointer;">-</button>
            <span id="display" style="font-size:24px; min-width:60px; text-align:center;">{count}</span>
            <button id="inc" style="padding:8px 16px; font-size:18px; cursor:pointer;">+</button>
        </div>
        """
        def on_inc(event):
            new_val = model.get("count") + 1
            model.set("count", new_val)
            model.save_changes()
            el.querySelector("#display").textContent = str(new_val)

        def on_dec(event):
            new_val = model.get("count") - 1
            model.set("count", new_val)
            model.save_changes()
            el.querySelector("#display").textContent = str(new_val)

        el.querySelector("#inc").addEventListener("click", create_proxy(on_inc))
        el.querySelector("#dec").addEventListener("click", create_proxy(on_dec))

    def update(self, el, model):
        display = el.querySelector("#display")
        if display:
            display.textContent = str(model.get("count"))
```

## NumPy computation (browser-side packages)

```python
class StatsWidget(PyWidget):
    data = traitlets.List(traitlets.Float(), []).tag(sync=True)
    _py_packages = ["numpy"]

    def render(self, el, model):
        import numpy as np
        arr = np.array(list(model.get("data")))
        if arr.size == 0:
            el.innerHTML = '<p style="color:#999;">No data.</p>'
            return
        el.innerHTML = f"""
        <table style="font-family:monospace; border-collapse:collapse;">
            <tr><td style="padding:4px 12px;">Mean:</td><td>{arr.mean():.4f}</td></tr>
            <tr><td style="padding:4px 12px;">Std:</td><td>{arr.std():.4f}</td></tr>
            <tr><td style="padding:4px 12px;">Min:</td><td>{arr.min():.4f}</td></tr>
            <tr><td style="padding:4px 12px;">Max:</td><td>{arr.max():.4f}</td></tr>
        </table>
        """

    def update(self, el, model):
        render(el, model)
```

## Complex data via JSON (Pandas)

```python
class SalesTable(PyWidget):
    sales_json = traitlets.Unicode("[]").tag(sync=True)
    _py_packages = ["pandas"]

    def render(self, el, model):
        import json
        import pandas as pd

        rows = json.loads(model.get("sales_json"))
        if not rows:
            el.innerHTML = '<p style="color:#999;">No data.</p>'
            return
        df = pd.DataFrame(rows)
        summary = (
            df.groupby("region")
            .agg(total=("revenue", "sum"), avg=("revenue", "mean"), n=("revenue", "count"))
            .round(2).reset_index()
        )
        el.innerHTML = f"""
        <div style="font-family:sans-serif; padding:16px;">
            <h3>Sales Summary (Pandas in browser)</h3>
            {summary.to_html(index=False, border=0)}
            <p style="color:#888; font-size:13px;">{len(df)} rows aggregated</p>
        </div>
        """

    def update(self, el, model):
        render(el, model)
```

## Image rendering (Pillow + base64)

```python
class FractalWidget(PyWidget):
    center_x = traitlets.Float(-0.5).tag(sync=True)
    center_y = traitlets.Float(0.0).tag(sync=True)
    zoom = traitlets.Float(1.0).tag(sync=True)
    _py_packages = ["numpy", "Pillow"]

    def render(self, el, model):
        import base64, io
        import numpy as np
        from PIL import Image

        def compute(cx, cy, z, w=400, h=400, max_iter=100):
            r = 3.0 / z
            real = np.linspace(cx - r/2, cx + r/2, w)
            imag = np.linspace(cy - r/2, cy + r/2, h)
            c = real[np.newaxis,:] + 1j * imag[:,np.newaxis]
            z_arr = np.zeros_like(c)
            iters = np.zeros(c.shape, dtype=np.int32)
            mask = np.ones(c.shape, dtype=bool)
            for i in range(max_iter):
                z_arr[mask] = z_arr[mask]**2 + c[mask]
                escaped = mask & (np.abs(z_arr) > 2.0)
                iters[escaped] = i + 1
                mask &= ~escaped
            return iters

        cx, cy, z = model.get("center_x"), model.get("center_y"), model.get("zoom")
        iters = compute(cx, cy, z)
        norm = iters.astype(np.float64) / 100
        rgb = np.stack([
            (np.sin(norm*np.pi*2)*127+128).astype(np.uint8),
            (np.sin(norm*np.pi*2+2.094)*127+128).astype(np.uint8),
            (np.sin(norm*np.pi*2+4.189)*127+128).astype(np.uint8),
        ], axis=-1)
        rgb[iters == 0] = 0

        buf = io.BytesIO()
        Image.fromarray(rgb, "RGB").save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        el.innerHTML = f'<img src="data:image/png;base64,{b64}" style="cursor:crosshair;" />'

        def on_click(event):
            r = 3.0 / z
            new_cx = (cx - r/2) + (event.offsetX / 400) * r
            new_cy = (cy - r/2) + (event.offsetY / 400) * r
            model.set("center_x", float(new_cx))
            model.set("center_y", float(new_cy))
            model.save_changes()

        el.querySelector("img").addEventListener("click", create_proxy(on_click))

    def update(self, el, model):
        render(el, model)
```

## Slider input (HTML range element)

```python
class SliderWidget(PyWidget):
    value = traitlets.Float(50.0).tag(sync=True)

    def render(self, el, model):
        val = model.get("value")
        el.innerHTML = f"""
        <div style="font-family:sans-serif; padding:16px;">
            <input id="slider" type="range" min="0" max="100" step="1"
                   value="{val}" style="width:200px;" />
            <span id="label">{val:.0f}</span>
        </div>
        """
        def on_input(event):
            new_val = float(event.target.value)
            el.querySelector("#label").textContent = f"{new_val:.0f}"
            model.set("value", new_val)
            model.save_changes()

        el.querySelector("#slider").addEventListener("input", create_proxy(on_input))

    def update(self, el, model):
        val = model.get("value")
        slider = el.querySelector("#slider")
        if slider:
            slider.value = str(val)
            el.querySelector("#label").textContent = f"{val:.0f}"
```

## marimo integration

```python
import marimo as mo
import traitlets
from pywidget import PyWidget

class MyWidget(PyWidget):
    value = traitlets.Int(0).tag(sync=True)
    def render(self, el, model):
        # ... render logic ...
        pass
    def update(self, el, model):
        render(el, model)

widget = mo.ui.anywidget(MyWidget(value=42))
widget  # display in cell

# In another cell, read state reactively:
# widget.widget.value
```

## String-based alternative

For simple widgets or dynamically generated code:

```python
class SimpleWidget(PyWidget):
    _py_render = """
def render(el, model):
    el.innerHTML = "<h2>Hello from Pyodide!</h2>"
"""
```
