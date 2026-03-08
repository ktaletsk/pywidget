## Interactive Matplotlib (SVG click interaction)

### Concept

Render a matplotlib chart as inline SVG, then attach Python click handlers
to individual plot elements (bars, scatter points, line segments) using
pywidget's DOM access. Clicking a bar highlights it, shows its value, and
syncs the selection to the kernel.

This creates **interactive matplotlib plots without ipympl, ipywidgets, or
any special backend** -- just SVG + DOM + Python event handlers. It works
everywhere pywidget works: JupyterLite, marimo WASM, notebook.link,
Binder.

**Why this is novel**: matplotlib has no built-in mechanism for
browser-side click interaction. The existing solutions (ipympl / mpl_interactions
/ plotly) either require a running kernel for every interaction, don't work
in WASM, or aren't matplotlib at all. pywidget's approach renders
matplotlib to SVG (a static operation), then layers interactivity on top
via DOM event handlers written in Python. The interactivity is decoupled
from the rendering backend.

### Pyodide packages

- `matplotlib`
- `numpy`

### How matplotlib SVG rendering works

Matplotlib can render any figure to SVG in memory:

```python
import matplotlib
matplotlib.use("agg")  # non-interactive backend (works in Pyodide)
import matplotlib.pyplot as plt
import io

fig, ax = plt.subplots()
ax.bar(["A", "B", "C"], [10, 25, 15])

buf = io.StringIO()
fig.savefig(buf, format="svg", bbox_inches="tight")
plt.close(fig)
svg_string = buf.getvalue()
```

The resulting SVG string contains standard SVG elements: `<rect>` for bars,
`<circle>` or `<use>` for scatter points, `<path>` for lines, `<text>` for
labels. These are all DOM nodes that can be queried and event-listened.

### The key trick: identifying plot elements in the SVG

Matplotlib's SVG output uses `gid` attributes when you set them explicitly:

```python
bars = ax.bar(categories, values)
for i, bar in enumerate(bars):
    bar.set_gid(f"bar-{i}")
```

This produces `<rect id="bar-0" .../>`, `<rect id="bar-1" .../>`, etc. in
the SVG. We can then do:

```python
for i in range(len(categories)):
    rect = el.querySelector(f"#bar-{i}")
    rect.addEventListener("click", create_proxy(on_bar_click))
```

If `gid` doesn't work reliably across matplotlib versions, the fallback
is to query all `<rect>` elements inside the axes group and match by
position/index.

### Traitlets (synced to kernel)

- `selected_index = Int(-1)` -- index of the currently selected bar
  (-1 = none). Synced to kernel so downstream cells can react.
- `selected_label = Unicode("")` -- label of the selected bar.
- `data_json = Unicode('[...]')` -- the chart data (categories + values),
  sent from kernel. When updated, the widget re-renders the chart.

### Data flow

```
Kernel                              Browser (Pyodide)
┌──────────────┐                    ┌─────────────────────────────┐
│              │   data_json        │                             │
│  categories  │ ─────────────────> │  matplotlib renders SVG     │
│  values      │                    │  SVG injected into DOM      │
│              │                    │  click handlers on <rect>s  │
│              │                    │                             │
│              │   selected_index   │  user clicks bar            │
│              │ <───────────────── │  bar highlights             │
│              │   selected_label   │  detail panel updates       │
│              │                    │                             │
└──────────────┘                    └─────────────────────────────┘
```

### Interaction behavior

1. Widget renders a matplotlib bar chart as SVG. Below the chart, a detail
   panel shows "Click a bar to select it."
2. User clicks a bar:
   - The clicked bar changes color (e.g. orange highlight).
   - Any previously selected bar reverts to its original color.
   - The detail panel updates: "Selected: Category B — Value: 25".
   - `model.set("selected_index", i)` + `model.save_changes()` syncs the
     selection to the kernel.
3. Kernel-side code can observe `w.selected_index` and react (e.g. filter
   a dataframe, show related data, update another widget).
4. When the kernel updates `data_json`, the widget re-renders the SVG
   (via `update()`), reattaches click handlers, and clears the selection.

### Highlight implementation

To highlight a bar, change its SVG `fill` attribute directly:

```python
COLORS = ["#4e79a7"] * n  # default
HIGHLIGHT = "#f28e2b"     # selected

def on_bar_click(event):
    # Reset previous selection
    if current_selection >= 0:
        prev = el.querySelector(f"#bar-{current_selection}")
        if prev:
            prev.setAttribute("fill", COLORS[current_selection])

    # Highlight new selection
    idx = int(event.target.getAttribute("data-index"))
    event.target.setAttribute("fill", HIGHLIGHT)
    # ...
```

Alternatively, use CSS classes: inject a `<style>` tag with
`.bar-selected { fill: #f28e2b !important; }` and toggle the class.
The CSS approach is cleaner if matplotlib's SVG structure nests elements
in ways that make direct `fill` changes unreliable.

### UI layout

```
┌─────────────────────────────────────────────────┐
│  Interactive Matplotlib                          │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │                                         │    │
│  │   matplotlib bar chart (SVG)            │    │
│  │   bars are clickable                    │    │
│  │                                         │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  Selected: Category B — Value: 25               │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Kernel-side usage

```python
# Cell 1: create the widget
import json

categories = ["Q1", "Q2", "Q3", "Q4"]
values = [120, 340, 250, 410]

w = InteractivePlotWidget(
    data_json=json.dumps({"categories": categories, "values": values})
)
w

# Cell 2: react to selection
if w.selected_index >= 0:
    print(f"User selected: {categories[w.selected_index]}")
    print(f"Value: {values[w.selected_index]}")
    # filter a dataframe, update another visualization, etc.

# Cell 3: update the data -- widget re-renders
new_values = [v * 1.1 for v in values]
w.data_json = json.dumps({"categories": categories, "values": new_values})
```

### Generalizing beyond bar charts

The same SVG + event handler pattern works for:

- **Scatter plots**: set `gid` on each point, click to select/inspect.
- **Pie charts**: each wedge is a `<path>`, clickable for drill-down.
- **Heatmaps**: each cell is a `<rect>`, click to show the value.
- **Line plots**: click on a data point marker to select a timestamp.

The first implementation should focus on bar charts (simplest SVG
structure, clearest interaction model). Scatter and pie are natural
follow-ups.

### Open questions

1. **matplotlib SVG `gid` reliability**: Does `bar.set_gid("bar-0")`
   produce a usable `id` attribute in the SVG output across matplotlib
   versions? Need to verify with matplotlib 3.8.4 (the Pyodide version).
   Fallback: query `<rect>` elements by position within the axes group.

2. **SVG structure complexity**: matplotlib's SVG output has nested `<g>`
   groups, transforms, and clip paths. The `<rect>` for a bar may be
   inside several nested groups. `querySelector("#bar-0")` should still
   work (IDs are global in SVG), but event delegation might be needed if
   click events don't bubble as expected.

3. **Re-rendering cost**: Each `update()` call re-runs matplotlib figure
   creation + SVG export + DOM injection + event handler attachment.
   matplotlib's figure creation is not fast (~50-200ms per chart in
   Pyodide). This is fine for data updates from the kernel (infrequent)
   but too slow for animation.

4. **Style preservation on highlight**: Changing `fill` directly may
   conflict with matplotlib's SVG styling (which sometimes uses inline
   `style` attributes instead of `fill` attributes). Need to test whether
   `setAttribute("fill", ...)` overrides `style="fill:..."`. If not, use
   `element.style.fill = "..."` instead.