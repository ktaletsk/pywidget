# /// script
# dependencies = ["pywidget", "anywidget"]
# ///
import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # pywidget + Invent: Expressive Notebook Widgets in Python

    <img src="https://raw.githubusercontent.com/ktaletsk/pywidget/feat/invent-integration/docs/pywidget_invent_logos.svg" height="48" />

    **The problem pywidget solves:** You can write widget rendering logic in Python —
    no JavaScript required.

    **The problem that remains:** You still need to know HTML, CSS, and DOM APIs
    (`innerHTML`, `querySelector`, `addEventListener`, inline styles…).

    **This notebook shows the next step:** Using
    [Invent](https://github.com/invent-framework/invent) widgets inside pywidget,
    so you can build interactive notebook widgets **entirely in Python** — no HTML,
    no CSS, no DOM.

    ---

    ### How it works

    Invent is a Python-first UI framework originally built for
    [PyScript](https://pyscript.net/). Its widget/layout/event system is pure Python
    and maps directly onto Pyodide — the same WASM runtime pywidget already uses.

    A [soft-fork of Invent](https://github.com/ktaletsk/invent/tree/pyodide-compat)
    replaces PyScript-specific imports with their Pyodide equivalents.
    Install it into the Pyodide runtime by adding the GitHub zip URL to `_py_packages`:

    ```python
    INVENT_URL = (
        "https://cdn.jsdelivr.net/gh/ktaletsk/invent"
        "@282cf507379eac1cea3fdf84fbdeb82764cf46c1"
        "/dist/invent-0.0.1a2-py3-none-any.whl"
    )
    ```

    micropip installs it as a pre-built wheel served via jsDelivr CDN
    (which sets the required `Access-Control-Allow-Origin: *` header).
    Installation is **cached per Pyodide instance** — subsequent widgets on the same
    page do not re-download.

    **First cell load:** ~15–20 s (Pyodide + Invent download).
    **Subsequent cells:** instant (both cached).
    """)
    return


@app.cell
def _():
    import marimo as mo
    import traitlets
    from pywidget import PyWidget

    INVENT_URL = (
        "https://cdn.jsdelivr.net/gh/ktaletsk/invent"
        "@282cf507379eac1cea3fdf84fbdeb82764cf46c1"
        "/dist/invent-0.0.1a2-py3-none-any.whl"
    )
    return PyWidget, mo, traitlets, INVENT_URL


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## Part 1: The Status Quo

    A counter widget written **today** in pywidget — HTML strings, `querySelector`,
    `addEventListener`, inline CSS, DOM IDs. It works, but it requires
    knowledge of HTML, CSS, and the DOM API.
    """)
    return


@app.cell
def _(PyWidget, create_proxy, mo, traitlets):
    class CounterRawDOM(PyWidget):
        """Counter using raw HTML/DOM — the current pywidget approach."""
        count = traitlets.Int(0).tag(sync=True)

        def render(self, el, model):
            count = model.get("count")
            el.innerHTML = f"""
            <div style="font-family: sans-serif; display: flex;
                        align-items: center; gap: 12px; padding: 12px;">
                <button id="dec"
                        style="padding: 8px 16px; font-size: 18px; cursor: pointer;">
                    −
                </button>
                <span id="display"
                      style="font-size: 24px; min-width: 60px; text-align: center;">
                    {count}
                </span>
                <button id="inc"
                        style="padding: 8px 16px; font-size: 18px; cursor: pointer;">
                    +
                </button>
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

    counter_raw = mo.ui.anywidget(CounterRawDOM())
    counter_raw
    return (counter_raw,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## Part 2: Level 1 — `invent._compat` Element Factories

    The lowest-level Invent integration: swap HTML string templates for
    **Python element factory functions** — `div()`, `button()`, `span()`, etc.

    You still wire events manually with `create_proxy`, but:

    - No HTML strings to write, escape, or misformat
    - Elements are **Python objects** — no `querySelector` needed to find them
    - Composable: nest elements by passing them as positional args to the parent factory
    - No `innerHTML` injection risk

    Compare the `render` body below to the one above — same widget, no HTML.
    """)
    return


@app.cell
def _(PyWidget, create_proxy, mo, traitlets, INVENT_URL):
    class CounterCompat(PyWidget):
        """Counter using invent._compat element factories — no HTML strings."""
        _py_packages = [INVENT_URL]
        count = traitlets.Int(0).tag(sync=True)

        def render(self, el, model):
            from invent._compat import button, div, span

            display = span(str(model.get("count")))
            display.style.setProperty("font-size", "24px")
            display.style.setProperty("min-width", "60px")
            display.style.setProperty("text-align", "center")

            dec_btn = button("−")
            dec_btn.style.setProperty("padding", "8px 16px")
            dec_btn.style.setProperty("font-size", "18px")
            dec_btn.style.setProperty("cursor", "pointer")

            inc_btn = button("+")
            inc_btn.style.setProperty("padding", "8px 16px")
            inc_btn.style.setProperty("font-size", "18px")
            inc_btn.style.setProperty("cursor", "pointer")

            def on_inc(event):
                new_val = model.get("count") + 1
                model.set("count", new_val)
                model.save_changes()
                display.textContent = str(new_val)

            def on_dec(event):
                new_val = model.get("count") - 1
                model.set("count", new_val)
                model.save_changes()
                display.textContent = str(new_val)

            from pyodide.ffi import create_proxy as cp
            inc_btn.addEventListener("click", cp(on_inc))
            dec_btn.addEventListener("click", cp(on_dec))

            container = div(dec_btn, display, inc_btn)
            container.style.setProperty("font-family", "sans-serif")
            container.style.setProperty("display", "flex")
            container.style.setProperty("align-items", "center")
            container.style.setProperty("gap", "12px")
            container.style.setProperty("padding", "12px")
            el.appendChild(container)

    mo.ui.anywidget(CounterCompat())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## Part 3: Level 2 — Full Invent Widgets

    The full Invent widget system: **no HTML, no CSS, no DOM APIs at all**.

    Invent widgets (`Button`, `Label`, `Slider`, `TextInput`, …) render themselves
    and handle their own events internally. Invent containers (`Row`, `Column`, `Grid`)
    handle layout via CSS flexbox/grid — configured entirely with Python kwargs.

    Invent's reactive property system means setting `label.text = "new value"`
    directly updates the DOM — no `querySelector`, no `textContent` assignment needed.

    > **Note on event handling:** In a full Invent app, widgets communicate via
    > named **channels** using a global PubSub bus:
    > ```python
    > invent.subscribe(handler, to_channel="my_channel", when_subject=["press"])
    > ```
    > and widgets are given a `channel=` kwarg to publish to. In a pywidget context
    > there is no global `invent.App`, so we use the `.when()` convenience shortcut
    > instead — it wires a handler directly to one widget's channel without needing
    > a global subscription. This is simpler here but bypasses the DataStore / reactive
    > state system that makes Invent apps truly reactive.

    ### Example 3a: Counter (Button + Label + Row)

    Same counter, now with Invent `Button`, `Label`, and `Row`.
    The `@btn.when("press")` decorator replaces `addEventListener`.
    `label.text = …` replaces `el.querySelector("#display").textContent = …`.
    """)
    return


@app.cell
def _(PyWidget, mo, traitlets, INVENT_URL):
    class CounterInvent(PyWidget):
        """Counter using full Invent widgets — no HTML, no CSS, no DOM."""
        _py_packages = [INVENT_URL]
        count = traitlets.Int(0).tag(sync=True)

        def render(self, el, model):
            from invent.ui import Button, Label, Row

            dec_btn = Button(text="−")
            label = Label(text=str(model.get("count")))
            inc_btn = Button(text="+")

            @inc_btn.when("press")
            def on_inc(message):
                new_val = model.get("count") + 1
                model.set("count", new_val)
                model.save_changes()
                label.text = str(new_val)

            @dec_btn.when("press")
            def on_dec(message):
                new_val = model.get("count") - 1
                model.set("count", new_val)
                model.save_changes()
                label.text = str(new_val)

            row = Row(children=[dec_btn, label, inc_btn])
            el.appendChild(row.element)

    counter_invent = mo.ui.anywidget(CounterInvent())
    counter_invent
    return (counter_invent,)


@app.cell(hide_code=True)
def _(counter_invent, mo):
    mo.md(f"""
    Count (read from kernel via traitlet): **{counter_invent.widget.count}**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Example 3b: Slider (Slider + Label + Column)

    `Slider` is an Invent widget wrapping an HTML range input.
    It updates its `.value` property on user interaction.

    > **Design gap:** `Slider` handles its DOM `input` event internally to update
    > `slider.value`, but does **not** publish an Invent message. There is no
    > `@slider.when("change")` equivalent. We fall back to a raw DOM listener on
    > `slider.element` — the one place where Invent's abstraction doesn't yet reach.
    > Adding a `"change"` message to `Slider` upstream would eliminate this.
    """)
    return


@app.cell
def _(PyWidget, mo, traitlets, INVENT_URL):
    class SliderInvent(PyWidget):
        """Slider demo using Invent Slider + Label + Column."""
        _py_packages = [INVENT_URL]
        value = traitlets.Int(50).tag(sync=True)

        def render(self, el, model):
            from invent.ui import Slider, Label, Column
            from pyodide.ffi import create_proxy

            label = Label(text=f"Value: {model.get('value')}")
            slider = Slider(
                value=model.get("value"),
                minvalue=0,
                maxvalue=100,
            )

            def on_input(event):
                new_val = int(slider.value)
                model.set("value", new_val)
                model.save_changes()
                label.text = f"Value: {new_val}"

            slider.element.addEventListener("input", create_proxy(on_input))

            col = Column(children=[slider, label])
            el.appendChild(col.element)

    slider_widget = mo.ui.anywidget(SliderInvent())
    slider_widget
    return (slider_widget,)


@app.cell(hide_code=True)
def _(mo, slider_widget):
    mo.md(f"""
    Slider value (read from kernel): **{slider_widget.widget.value}**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Example 3c: Greeter Form (TextInput + Button + Label + Column)

    `TextInput` is an Invent widget. Its `.value` property stays in sync with the
    DOM input element automatically — no `event.target.value` needed.
    """)
    return


@app.cell
def _(PyWidget, mo, traitlets, INVENT_URL):
    class GreeterInvent(PyWidget):
        """Greeter form using Invent TextInput + Button + Label + Column."""
        _py_packages = [INVENT_URL]
        greeting = traitlets.Unicode("").tag(sync=True)

        def render(self, el, model):
            from invent.ui import TextInput, Button, Label, Column

            name_input = TextInput(placeholder="Enter your name…")
            greet_btn = Button(text="Greet", purpose="PRIMARY")
            output = Label(text="")

            @greet_btn.when("press")
            def on_greet(message):
                name = name_input.value or "World"
                result = f"Hello, {name}!"
                output.text = result
                model.set("greeting", result)
                model.save_changes()

            col = Column(children=[name_input, greet_btn, output])
            el.appendChild(col.element)

    greeter_invent = mo.ui.anywidget(GreeterInvent())
    greeter_invent
    return (greeter_invent,)


@app.cell(hide_code=True)
def _(greeter_invent, mo):
    mo.md(f"""
    Greeting (read from kernel): **{greeter_invent.widget.greeting or "*(not yet set)*"}**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Example 3d: RGB Color Mixer (Slider × 3 + Grid)

    Three `Slider` widgets laid out in a `Grid` control an RGB color swatch.
    The `Grid` maps to CSS grid with `columns=4` — no CSS string required.
    """)
    return


@app.cell
def _(PyWidget, mo, traitlets, INVENT_URL):
    class RGBMixer(PyWidget):
        """RGB mixer using Invent Slider, Label, Column, and Grid."""
        _py_packages = [INVENT_URL]
        r = traitlets.Int(100).tag(sync=True)
        g = traitlets.Int(150).tag(sync=True)
        b = traitlets.Int(200).tag(sync=True)

        def render(self, el, model):
            from invent.ui import Slider, Label, Column, Grid
            from pyodide.ffi import create_proxy

            # Colour swatch — a Label element styled as a coloured box
            rv, gv, bv = model.get("r"), model.get("g"), model.get("b")
            swatch = Label(text="")
            swatch.element.style.setProperty("background-color", f"rgb({rv},{gv},{bv})")
            swatch.element.style.setProperty("width", "100px")
            swatch.element.style.setProperty("height", "100px")
            swatch.element.style.setProperty("border-radius", "8px")
            swatch.element.style.setProperty("border", "1px solid #ccc")

            def make_channel(name, trait):
                lbl = Label(text=f"{name}: {model.get(trait)}")
                slider = Slider(value=model.get(trait), minvalue=0, maxvalue=255)

                def on_input(event):
                    val = int(slider.value)
                    model.set(trait, val)
                    model.save_changes()
                    lbl.text = f"{name}: {val}"
                    r = model.get("r")
                    g = model.get("g")
                    b = model.get("b")
                    swatch.element.style.setProperty("background-color", f"rgb({r},{g},{b})")

                slider.element.addEventListener("input", create_proxy(on_input))
                return Column(children=[lbl, slider])

            r_col = make_channel("R", "r")
            g_col = make_channel("G", "g")
            b_col = make_channel("B", "b")

            grid = Grid(columns=4, children=[r_col, g_col, b_col, swatch])
            el.appendChild(grid.element)

    mo.ui.anywidget(RGBMixer())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## Part 4: Level 3 — Invent Controls + numpy + matplotlib

    **Mixing data science packages with Invent — and nothing else.**

    `_py_packages` can combine Invent *and* scientific packages in the same
    Pyodide instance. Here `numpy` generates the data, `matplotlib` renders
    the chart, and the Invent `Image` widget displays it — updated reactively
    via `chart.image = new_data_uri`.

    ### Example 4: Distribution Explorer

    A `Selector` dropdown picks the distribution; an Invent `Slider` controls
    the sample size; a `Button` resamples. `chart.image = …` triggers Invent's
    reactive `on_image_changed` → `element.src =` automatically — no DOM, no
    `create_proxy`, no raw JavaScript (except the one `Slider` DOM listener
    noted in Example 3b).

    > **Key insight:** `Image.image` accepts any valid `src` string, including
    > `data:image/png;base64,…` URIs — so matplotlib output slots straight in.
    """)
    return


@app.cell
def _(PyWidget, mo, traitlets, INVENT_URL):
    class DistributionExplorer(PyWidget):
        """Matplotlib histogram controlled entirely by Invent widgets."""
        _py_packages = [INVENT_URL, "numpy", "matplotlib"]
        distribution = traitlets.Unicode("normal").tag(sync=True)
        n = traitlets.Int(500).tag(sync=True)

        def render(self, el, model):
            import numpy as np
            import matplotlib
            matplotlib.use("agg")
            import matplotlib.pyplot as plt
            import io, base64
            from invent.ui import Selector, Button, Image, Slider, Label, Row, Column
            from pyodide.ffi import create_proxy

            DISTS = ["normal", "uniform", "exponential", "lognormal"]

            def sample(dist, n):
                rng = np.random.default_rng()
                return {
                    "normal":      lambda: rng.normal(size=n),
                    "uniform":     lambda: rng.uniform(-3, 3, size=n),
                    "exponential": lambda: rng.exponential(size=n),
                    "lognormal":   lambda: rng.lognormal(size=n),
                }[dist]()

            def to_data_uri(data, dist):
                fig, ax = plt.subplots(figsize=(6, 3))
                ax.hist(data, bins=20, color="#4e79a7",
                        edgecolor="white", linewidth=0.6)
                ax.set_title(f"{dist.capitalize()} (n={len(data)})",
                             fontsize=12, color="#333")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                fig.tight_layout()
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
                plt.close(fig)
                return ("data:image/png;base64,"
                        + base64.b64encode(buf.getvalue()).decode())

            # controls
            dist_sel = Selector(choices=DISTS, value=model.get("distribution"))
            resample_btn = Button(text="↺ Resample", purpose="PRIMARY")

            init_n = model.get("n")
            n_label = Label(text=f"n = {init_n}")
            n_slider = Slider(value=init_n, minvalue=100, maxvalue=5000)

            # chart — Image widget, updated via chart.image = new_data_uri
            init_data = sample(model.get("distribution"), init_n)
            chart = Image(image=to_data_uri(init_data, model.get("distribution")))

            def compute():
                n = int(n_slider.value)
                dist = dist_sel.value
                data = sample(dist, n)
                chart.image = to_data_uri(data, dist)  # reactive update
                model.set("distribution", dist)
                model.set("n", n)
                model.save_changes()

            def on_slider_input(event):
                n_label.text = f"n = {int(n_slider.value)}"
                compute()

            n_slider.element.addEventListener("input", create_proxy(on_slider_input))

            @dist_sel.when("changed")
            def _(message): compute()

            @resample_btn.when("press")
            def _(message): compute()

            el.appendChild(Column(children=[
                Row(children=[dist_sel, resample_btn]),
                Row(children=[n_slider, n_label]),
                chart,
            ]).element)

    histogram = mo.ui.anywidget(DistributionExplorer())
    histogram
    return (histogram,)


@app.cell(hide_code=True)
def _(histogram, mo):
    mo.md(f"""
    Synced to kernel — distribution: `{histogram.widget.distribution}`,
    n: `{histogram.widget.n}`
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## Summary: Before vs After

    | | Before (raw DOM) | After (Invent) |
    |---|---|---|
    | **Rendering** | `el.innerHTML = f\"\"\"...\"\"\"` | `Button(text=…)`, `Label(text="…")` |
    | **Finding elements** | `el.querySelector(\"#id\")` | Direct Python variable |
    | **Event handling** | `addEventListener(\"click\", create_proxy(fn))` | `@btn.when(\"press\")` |
    | **Updating UI** | `el.querySelector(\"#display\").textContent = …` | `label.text = …` |
    | **Layout** | `style=\"display:flex; gap:12px; …\"` | `Row(children=[…])` |
    | **Required knowledge** | HTML, CSS, DOM API, JS events | Python |

    ### What stays the same

    - `model.get()` / `model.set()` / `model.save_changes()` for kernel↔browser sync
    - `_py_packages` for installing packages in Pyodide — Invent and data science
      packages share the same Pyodide instance, so `[INVENT_URL, "numpy", "matplotlib"]`
      works out of the box
    - Raw DOM access is still available — Invent does not prevent it

    ### Differences from canonical Invent style

    1. **`.when()` vs `invent.subscribe()`** — canonical Invent apps assign widgets
       a `channel=` kwarg and subscribe handlers globally via `invent.subscribe()`.
       Without a global `invent.App`, we use the `.when()` shortcut. This is a
       deliberate simplification; the PubSub/DataStore system is still intact underneath.

    2. **`Slider` DOM fallback** — `Slider` doesn't publish an Invent message on
       change, so we attach a raw DOM `input` listener on `slider.element`. Adding
       a `"change"` subject to `Slider` upstream would close this gap.

    3. **No `invent.App` / `invent.go()`** — lifecycle management (`Page`, `App`,
       `DataStore`) is replaced by pywidget's `render()` / `update()` pattern and
       traitlets for kernel sync.

    ### Collaboration proposal

    The Invent soft-fork lives at
    [ktaletsk/invent — pyodide-compat](https://github.com/ktaletsk/invent/tree/pyodide-compat).
    The goal is to propose this upstream to
    [invent-framework/invent](https://github.com/invent-framework/invent) so that
    Invent officially supports Pyodide alongside PyScript, and pywidget can depend
    on Invent directly.

    ```bash
    # Inspect the full scope of changes from upstream:
    git clone https://github.com/ktaletsk/invent.git
    cd invent
    git diff main..pyodide-compat
    ```
    """)
    return


if __name__ == "__main__":
    app.run()
