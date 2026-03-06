# /// script
# dependencies = ["pywidget", "anywidget"]
# ///
import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # pywidget Demo

    This notebook demonstrates **pywidget** — write widgets entirely in Python,
    no JavaScript required.

    Your rendering code runs in the browser using
    [Pyodide](https://pyodide.org/) (CPython compiled to WebAssembly).

    **First load takes 3–5 seconds** while Pyodide downloads (~11 MB).
    Subsequent widgets render instantly.

    In marimo, wrap every `PyWidget` instance with `mo.ui.anywidget()` to
    hook into the reactive execution engine.
    """)
    return


@app.cell
def _():
    import json
    import random

    import marimo as mo
    import traitlets
    from pywidget import PyWidget

    return PyWidget, json, mo, random, traitlets


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Example 1: Static HTML
    """)
    return


@app.cell
def _(PyWidget, mo):
    class HelloWidget(PyWidget):
        def render(self, el, model):
            el.innerHTML = """
            <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 12px; color: white; font-family: sans-serif;">
                <h2 style="margin: 0 0 8px 0;">Hello from Pyodide!</h2>
                <p style="margin: 0; opacity: 0.9;">
                    This HTML was rendered by Python running in your browser via WebAssembly.
                </p>
            </div>
            """

    mo.ui.anywidget(HelloWidget())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Example 2: Reading Kernel State

    The `model.get()` API reads traitlets synced from the kernel.
    The `update()` method is called whenever state changes.

    Use the text box below to change the name — marimo's reactivity
    propagates the value automatically.
    """)
    return


@app.cell
def _(mo):
    name_input = mo.ui.text(value="World", label="Name")
    name_input
    return (name_input,)


@app.cell
def _(PyWidget, mo, name_input, traitlets):
    class GreeterWidget(PyWidget):
        name = traitlets.Unicode("World").tag(sync=True)

        def render(self, el, model):
            name = model.get("name")
            el.innerHTML = f"""
            <div style="padding: 16px; border: 2px solid #4CAF50; border-radius: 8px;
                        font-family: sans-serif;">
                <span style="font-size: 24px;">Hello, <strong>{name}</strong>!</span>
            </div>
            """

        def update(self, el, model):
            name = model.get("name")
            el.innerHTML = f"""
            <div style="padding: 16px; border: 2px solid #4CAF50; border-radius: 8px;
                        font-family: sans-serif;">
                <span style="font-size: 24px;">Hello, <strong>{name}</strong>!</span>
            </div>
            """

    greeter = GreeterWidget(name=name_input.value)
    mo.ui.anywidget(greeter)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Example 3: Bidirectional State (Click Counter)

    Full bidirectional sync:
    - **Browser to Kernel**: clicking the button calls `model.set()` +
      `model.save_changes()`
    - **Kernel to Browser**: the widget display updates via `update()`

    The current count is read reactively in the cell below the widget.
    """)
    return


@app.cell
def _(PyWidget, create_proxy, mo, traitlets):
    class CounterWidget(PyWidget):
        count = traitlets.Int(0).tag(sync=True)

        def render(self, el, model):
            count = model.get("count")
            el.innerHTML = f"""
            <div style="font-family: sans-serif; display: flex; align-items: center; gap: 12px;">
                <button id="dec" style="padding: 8px 16px; font-size: 18px; cursor: pointer;">-</button>
                <span id="display" style="font-size: 24px; min-width: 60px; text-align: center;">
                    {count}
                </span>
                <button id="inc" style="padding: 8px 16px; font-size: 18px; cursor: pointer;">+</button>
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

    counter = mo.ui.anywidget(CounterWidget())
    counter
    return (counter,)


@app.cell(hide_code=True)
def _(counter, mo):
    mo.md(f"""
    Current count (read reactively from kernel): **{counter.widget.count}**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Debugging Tips

    Your `render` and `update` code runs in the browser via Pyodide, so
    `print()` output goes to the **browser DevTools console** (open with
    Cmd+Option+J in Chrome, or Cmd+Option+I in Firefox/Safari).

    You can also use `console.log()`, `console.warn()`, and `console.error()`
    directly — the `console` object is available in the rendering namespace.
    """)
    return


@app.cell
def _(PyWidget, console, create_proxy, mo, traitlets):
    class DebugWidget(PyWidget):
        count = traitlets.Int(0).tag(sync=True)

        def render(self, el, model):
            print("render() called")
            console.log("count is", model.get("count"))

            el.innerHTML = f"""
            <div style="font-family: sans-serif; padding: 16px; background: #1e1e2e;
                        color: #cdd6f4; border-radius: 8px;">
                <p style="margin: 0 0 8px 0;">
                    Open <strong>DevTools → Console</strong> to see debug output.
                </p>
                <button id="btn" style="padding: 8px 16px; cursor: pointer;">
                    Click me (check console)
                </button>
            </div>
            """

            def on_click(event):
                new_val = model.get("count") + 1
                print(f"Button clicked! count = {new_val}")
                model.set("count", new_val)
                model.save_changes()

            el.querySelector("#btn").addEventListener("click", create_proxy(on_click))

    mo.ui.anywidget(DebugWidget())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Example 4: Browser-side NumPy

    Use `_py_packages` to install packages inside Pyodide.
    NumPy is pre-built for WASM, so it loads in seconds.

    Drag the slider to resize the random dataset — the stats recalculate
    in the browser.
    """)
    return


@app.cell
def _(mo):
    n_points = mo.ui.slider(5, 100, value=20, label="Number of data points", step=5)
    n_points
    return (n_points,)


@app.cell(hide_code=True)
def _(PyWidget, mo, n_points, random, traitlets):
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
            <div style="font-family: monospace; padding: 16px; background: #f8f9fa;
                        border-radius: 8px; border: 1px solid #dee2e6;">
                <h3 style="margin: 0 0 12px 0; color: #495057;">Browser-side NumPy</h3>
                <table style="border-collapse: collapse;">
                    <tr><td style="padding: 4px 12px;">n:</td><td>{arr.size}</td></tr>
                    <tr><td style="padding: 4px 12px;">Mean:</td><td>{arr.mean():.4f}</td></tr>
                    <tr><td style="padding: 4px 12px;">Std:</td><td>{arr.std():.4f}</td></tr>
                    <tr><td style="padding: 4px 12px;">Min:</td><td>{arr.min():.4f}</td></tr>
                    <tr><td style="padding: 4px 12px;">Max:</td><td>{arr.max():.4f}</td></tr>
                    <tr><td style="padding: 4px 12px;">Sum:</td><td>{arr.sum():.4f}</td></tr>
                </table>
            </div>
            """

        def update(self, el, model):
            render(el, model)

    stats = StatsWidget(data=[random.gauss(50, 15) for _ in range(n_points.value)])
    mo.ui.anywidget(stats)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Example 5: Browser-side Pandas

    Pandas runs in Pyodide too. The kernel sends raw row data; the
    browser does all the aggregation and HTML formatting.

    Click **Regenerate** to push a new random dataset.
    """)
    return


@app.cell
def _(mo):
    regenerate = mo.ui.button(label="Regenerate sales data")
    regenerate
    return (regenerate,)


@app.cell(hide_code=True)
def _(PyWidget, json, mo, random, regenerate, traitlets):
    regenerate

    regions = ["North", "South", "East", "West"]
    sales = [
        {"region": random.choice(regions), "revenue": round(random.uniform(100, 5000), 2)}
        for _ in range(50)
    ]

    class SalesTable(PyWidget):
        sales_json = traitlets.Unicode("[]").tag(sync=True)
        _py_packages = ["pandas"]

        def render(self, el, model):
            import json
            import pandas as pd

            rows = json.loads(model.get("sales_json"))
            if not rows:
                el.innerHTML = '<p style="color:#999; font-family:sans-serif;">No data yet.</p>'
                return

            df = pd.DataFrame(rows)
            summary = (
                df.groupby("region")
                .agg(
                    total_revenue=("revenue", "sum"),
                    avg_revenue=("revenue", "mean"),
                    order_count=("revenue", "count"),
                )
                .round(2)
                .reset_index()
            )
            table_html = summary.to_html(index=False, border=0)

            el.innerHTML = f"""
            <div style="font-family: sans-serif; padding: 16px;">
                <h3 style="margin: 0 0 12px 0;">Sales Summary (computed in browser with Pandas)</h3>
                <style>
                    .pywidget-table table {{ border-collapse: collapse; width: 100%; }}
                    .pywidget-table th, .pywidget-table td {{
                        padding: 8px 12px; text-align: left; border-bottom: 1px solid #ddd;
                    }}
                    .pywidget-table th {{ background: #f0f0f0; font-weight: 600; }}
                    .pywidget-table tr:hover {{ background: #f9f9f9; }}
                </style>
                <div class="pywidget-table">{table_html}</div>
                <p style="color: #888; margin-top: 12px; font-size: 13px;">
                    {len(df)} rows &rarr; {len(summary)} regions, aggregated by Pandas in Pyodide
                </p>
            </div>
            """

        def update(self, el, model):
            render(el, model)

    sales_widget = SalesTable(sales_json=json.dumps(sales))
    mo.ui.anywidget(sales_widget)
    return


if __name__ == "__main__":
    app.run()
