---
title: pywidget in MyST
subtitle: Pure Python widgets running in the browser via Pyodide
---

# pywidget + MyST

This page demonstrates **pywidget** rendering logic running inside a MyST
site — no Python kernel required. The Python code executes in the browser
via [Pyodide](https://pyodide.org/) (CPython compiled to WebAssembly).

:::{note}
First load takes 3-5 seconds while Pyodide downloads (~11 MB WASM).
Subsequent widgets on the same page render instantly.
:::

## Example 1: Hello World

A minimal widget that renders static HTML from Python.

```{code-block} python
def render(el, model):
    el.innerHTML = """
    <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px; color: white; font-family: sans-serif;">
        <h2 style="margin: 0 0 8px 0;">Hello from Pyodide!</h2>
        <p style="margin: 0; opacity: 0.9;">
            This HTML was rendered by Python running in your browser via WebAssembly.
        </p>
    </div>
    """
```

```{anywidget} https://cdn.jsdelivr.net/npm/pywidget-bridge@0.1.1/pywidget-bridge.mjs
{
  "_py_render": "def render(el, model):\n    el.innerHTML = \"\"\"\n    <div style=\"padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n                border-radius: 12px; color: white; font-family: sans-serif;\">\n        <h2 style=\"margin: 0 0 8px 0;\">Hello from Pyodide!</h2>\n        <p style=\"margin: 0; opacity: 0.9;\">\n            This HTML was rendered by Python running in your browser via WebAssembly.\n        </p>\n    </div>\n    \"\"\""
}
```

## Example 2: Interactive Counter

A button that tracks clicks using the widget model for state.

```{code-block} python
def render(el, model):
    from js import document

    container = document.createElement('div')
    container.style.fontFamily = 'sans-serif'
    container.style.padding = '16px'

    btn = document.createElement('button')
    btn.style.cssText = (
        'padding: 10px 24px; font-size: 16px; cursor: pointer;'
        ' border: 2px solid #6366f1; border-radius: 8px;'
        ' background: #eef2ff; color: #4338ca;'
    )
    btn.textContent = 'Count: 0'

    count = 0
    def on_click(event):
        nonlocal count
        count += 1
        btn.textContent = f'Count: {count}'
    btn.addEventListener('click', create_proxy(on_click))

    container.appendChild(btn)
    el.appendChild(container)
```

```{anywidget} https://cdn.jsdelivr.net/npm/pywidget-bridge@0.1.1/pywidget-bridge.mjs
{
  "_py_render": "def render(el, model):\n    from js import document\n    container = document.createElement('div')\n    container.style.fontFamily = 'sans-serif'\n    container.style.padding = '16px'\n\n    btn = document.createElement('button')\n    btn.style.cssText = 'padding: 10px 24px; font-size: 16px; cursor: pointer; border: 2px solid #6366f1; border-radius: 8px; background: #eef2ff; color: #4338ca;'\n    btn.textContent = 'Count: 0'\n\n    count = 0\n    def on_click(event):\n        nonlocal count\n        count += 1\n        btn.textContent = f'Count: {count}'\n    btn.addEventListener('click', create_proxy(on_click))\n\n    container.appendChild(btn)\n    el.appendChild(container)",
  "count": 0
}
```

## Example 3: Python Computation

Using Python's standard library to compute and display results.

```{code-block} python
def render(el, model):
    import math
    import sys

    rows = ''
    for n in range(1, 11):
        rows += (
            f'<tr><td>{n}</td><td>{n**2}</td>'
            f'<td>{math.factorial(n):,}</td><td>{math.sqrt(n):.4f}</td></tr>'
        )

    el.innerHTML = f"""
    <div style="font-family: sans-serif; padding: 16px;">
        <p style="color: #666; margin-bottom: 12px;">
            Computed by Python {sys.version.split()[0]} (Pyodide) in your browser
        </p>
        <table style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr style="background: #f1f5f9;">
                    <th style="padding: 8px 12px; border: 1px solid #e2e8f0;">n</th>
                    <th style="padding: 8px 12px; border: 1px solid #e2e8f0;">n²</th>
                    <th style="padding: 8px 12px; border: 1px solid #e2e8f0;">n!</th>
                    <th style="padding: 8px 12px; border: 1px solid #e2e8f0;">√n</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """
```

```{anywidget} https://cdn.jsdelivr.net/npm/pywidget-bridge@0.1.1/pywidget-bridge.mjs
{
  "_py_render": "def render(el, model):\n    import math\n    import sys\n\n    rows = ''\n    for n in range(1, 11):\n        rows += f'<tr><td>{n}</td><td>{n**2}</td><td>{math.factorial(n):,}</td><td>{math.sqrt(n):.4f}</td></tr>'\n\n    el.innerHTML = f\"\"\"\n    <div style=\"font-family: sans-serif; padding: 16px;\">\n        <p style=\"color: #666; margin-bottom: 12px;\">Computed by Python {sys.version.split()[0]} (Pyodide) in your browser</p>\n        <table style=\"border-collapse: collapse; width: 100%;\">\n            <thead>\n                <tr style=\"background: #f1f5f9;\">\n                    <th style=\"padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;\">n</th>\n                    <th style=\"padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;\">n&sup2;</th>\n                    <th style=\"padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;\">n!</th>\n                    <th style=\"padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;\">&radic;n</th>\n                </tr>\n            </thead>\n            <tbody>{rows}</tbody>\n        </table>\n    </div>\n    \"\"\""
}
```

## Using External Libraries

Pyodide supports 250+ packages from the scientific Python ecosystem via
[micropip](https://micropip.pyodide.org/). List the packages you need in
`_py_packages` and they will be installed before your `render()` runs.

:::{note}
The first widget that uses a package will trigger an install (a few seconds).
Subsequent widgets on the same page reuse the already-loaded package — no
re-download.
:::

## Example 4: Mandelbrot Set (numpy + Pillow)

Vectorized fractal computation with numpy, rendered to PNG with Pillow.
Click anywhere on the image to re-center; use the buttons to zoom.

```{code-block} python
def render(el, model):
    import base64
    import io

    import numpy as np
    from PIL import Image

    cx = model.get("center_x")
    cy = model.get("center_y")
    z = model.get("zoom")
    max_it = model.get("max_iter")
    w = model.get("width")
    h = model.get("height")

    def compute(cx, cy, z, w, h, max_it):
        r = 3.0 / z
        aspect = w / h
        real = np.linspace(cx - r * aspect / 2, cx + r * aspect / 2, w)
        imag = np.linspace(cy - r / 2, cy + r / 2, h)
        c = real[np.newaxis, :] + 1j * imag[:, np.newaxis]
        z_arr = np.zeros_like(c)
        iters = np.zeros(c.shape, dtype=np.int32)
        mask = np.ones(c.shape, dtype=bool)
        for i in range(max_it):
            z_arr[mask] = z_arr[mask] ** 2 + c[mask]
            escaped = mask & (np.abs(z_arr) > 2.0)
            iters[escaped] = i + 1
            mask &= ~escaped
        return iters

    iters = compute(cx, cy, z, w, h, max_it)

    norm = iters.astype(np.float64) / max_it
    rgb = np.stack([
        (np.sin(norm * np.pi * 2) * 127 + 128).astype(np.uint8),
        (np.sin(norm * np.pi * 2 + 2.094) * 127 + 128).astype(np.uint8),
        (np.sin(norm * np.pi * 2 + 4.189) * 127 + 128).astype(np.uint8),
    ], axis=-1)
    rgb[iters == 0] = 0

    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    btn_style = "padding:6px 14px; font-size:14px; cursor:pointer; border:1px solid #ccc; border-radius:4px; background:#f8f8f8;"
    el.innerHTML = f"""
    <div style="font-family:sans-serif; display:inline-block;">
        <img id="fractal" src="data:image/png;base64,{b64}"
             width="{w}" height="{h}"
             style="cursor:crosshair; display:block; border:1px solid #ddd;" />
        <div style="display:flex; align-items:center; gap:10px; margin-top:8px; flex-wrap:wrap;">
            <button id="zoom-in" style="{btn_style}">Zoom In</button>
            <button id="zoom-out" style="{btn_style}">Zoom Out</button>
            <button id="reset" style="{btn_style}">Reset</button>
            <label style="display:flex; align-items:center; gap:6px; font-size:14px;">
                Iterations:
                <input id="iter-slider" type="range" min="10" max="500" step="10"
                       value="{max_it}" style="width:120px;" />
                <span id="iter-label">{max_it}</span>
            </label>
        </div>
        <div style="margin-top:4px; font-size:12px; color:#888;">
            Center: ({cx:.6f}, {cy:.6f}) | Zoom: {z:.1f}x
        </div>
    </div>
    """

    def on_click(event):
        cur_cx, cur_cy = model.get("center_x"), model.get("center_y")
        cur_z = model.get("zoom")
        cur_w, cur_h = model.get("width"), model.get("height")
        r = 3.0 / cur_z
        aspect = cur_w / cur_h
        model.set("center_x", float((cur_cx - r * aspect / 2) + (event.offsetX / cur_w) * r * aspect))
        model.set("center_y", float((cur_cy - r / 2) + (event.offsetY / cur_h) * r))
        model.save_changes()

    def on_zoom_in(event):
        model.set("zoom", model.get("zoom") * 2)
        model.save_changes()

    def on_zoom_out(event):
        model.set("zoom", max(model.get("zoom") / 2, 0.25))
        model.save_changes()

    def on_reset(event):
        model.set("center_x", -0.5)
        model.set("center_y", 0.0)
        model.set("zoom", 1.0)
        model.set("max_iter", 100)
        model.save_changes()
        el.querySelector("#iter-slider").value = "100"
        el.querySelector("#iter-label").textContent = "100"

    def on_iter_change(event):
        new_val = int(float(event.target.value))
        el.querySelector("#iter-label").textContent = str(new_val)
        model.set("max_iter", new_val)
        model.save_changes()

    el.querySelector("#fractal").addEventListener("click", create_proxy(on_click))
    el.querySelector("#zoom-in").addEventListener("click", create_proxy(on_zoom_in))
    el.querySelector("#zoom-out").addEventListener("click", create_proxy(on_zoom_out))
    el.querySelector("#reset").addEventListener("click", create_proxy(on_reset))
    el.querySelector("#iter-slider").addEventListener("change", create_proxy(on_iter_change))

def update(el, model):
    render(el, model)
```

```{anywidget} https://cdn.jsdelivr.net/npm/pywidget-bridge@0.1.1/pywidget-bridge.mjs
{
  "_py_render": "def render(el, model):\n    import base64\n    import io\n\n    import numpy as np\n    from PIL import Image\n\n    cx = model.get(\"center_x\")\n    cy = model.get(\"center_y\")\n    z = model.get(\"zoom\")\n    max_it = model.get(\"max_iter\")\n    w = model.get(\"width\")\n    h = model.get(\"height\")\n\n    def compute(cx, cy, z, w, h, max_it):\n        r = 3.0 / z\n        aspect = w / h\n        real = np.linspace(cx - r * aspect / 2, cx + r * aspect / 2, w)\n        imag = np.linspace(cy - r / 2, cy + r / 2, h)\n        c = real[np.newaxis, :] + 1j * imag[:, np.newaxis]\n        z_arr = np.zeros_like(c)\n        iters = np.zeros(c.shape, dtype=np.int32)\n        mask = np.ones(c.shape, dtype=bool)\n        for i in range(max_it):\n            z_arr[mask] = z_arr[mask] ** 2 + c[mask]\n            escaped = mask & (np.abs(z_arr) > 2.0)\n            iters[escaped] = i + 1\n            mask &= ~escaped\n        return iters\n\n    iters = compute(cx, cy, z, w, h, max_it)\n\n    norm = iters.astype(np.float64) / max_it\n    rgb = np.stack(\n        [\n            (np.sin(norm * np.pi * 2) * 127 + 128).astype(np.uint8),\n            (np.sin(norm * np.pi * 2 + 2.094) * 127 + 128).astype(np.uint8),\n            (np.sin(norm * np.pi * 2 + 4.189) * 127 + 128).astype(np.uint8),\n        ],\n        axis=-1,\n    )\n    rgb[iters == 0] = 0\n\n    buf = io.BytesIO()\n    Image.fromarray(rgb, \"RGB\").save(buf, format=\"PNG\")\n    b64 = base64.b64encode(buf.getvalue()).decode(\"ascii\")\n\n    btn_style = \"padding:6px 14px; font-size:14px; cursor:pointer; border:1px solid #ccc; border-radius:4px; background:#f8f8f8;\"\n\n    el.innerHTML = f\"\"\"\n    <div style=\"font-family:sans-serif; display:inline-block;\">\n        <img id=\"fractal\" src=\"data:image/png;base64,{b64}\"\n             width=\"{w}\" height=\"{h}\"\n             style=\"cursor:crosshair; display:block; border:1px solid #ddd;\" />\n        <div style=\"display:flex; align-items:center; gap:10px; margin-top:8px; flex-wrap:wrap;\">\n            <button id=\"zoom-in\" style=\"{btn_style}\">Zoom In</button>\n            <button id=\"zoom-out\" style=\"{btn_style}\">Zoom Out</button>\n            <button id=\"reset\" style=\"{btn_style}\">Reset</button>\n            <label style=\"display:flex; align-items:center; gap:6px; font-size:14px;\">\n                Iterations:\n                <input id=\"iter-slider\" type=\"range\" min=\"10\" max=\"500\" step=\"10\"\n                       value=\"{max_it}\" style=\"width:120px;\" />\n                <span id=\"iter-label\">{max_it}</span>\n            </label>\n        </div>\n        <div style=\"margin-top:4px; font-size:12px; color:#888;\">\n            Center: ({cx:.6f}, {cy:.6f}) | Zoom: {z:.1f}x\n        </div>\n    </div>\n    \"\"\"\n\n    def on_click(event):\n        cur_cx = model.get(\"center_x\")\n        cur_cy = model.get(\"center_y\")\n        cur_z = model.get(\"zoom\")\n        cur_w = model.get(\"width\")\n        cur_h = model.get(\"height\")\n        r = 3.0 / cur_z\n        aspect = cur_w / cur_h\n        new_cx = (cur_cx - r * aspect / 2) + (event.offsetX / cur_w) * r * aspect\n        new_cy = (cur_cy - r / 2) + (event.offsetY / cur_h) * r\n        model.set(\"center_x\", float(new_cx))\n        model.set(\"center_y\", float(new_cy))\n        model.save_changes()\n\n    def on_zoom_in(event):\n        model.set(\"zoom\", model.get(\"zoom\") * 2)\n        model.save_changes()\n\n    def on_zoom_out(event):\n        model.set(\"zoom\", max(model.get(\"zoom\") / 2, 0.25))\n        model.save_changes()\n\n    def on_reset(event):\n        model.set(\"center_x\", -0.5)\n        model.set(\"center_y\", 0.0)\n        model.set(\"zoom\", 1.0)\n        model.set(\"max_iter\", 100)\n        model.save_changes()\n        el.querySelector(\"#iter-slider\").value = \"100\"\n        el.querySelector(\"#iter-label\").textContent = \"100\"\n\n    def on_iter_change(event):\n        new_val = int(float(event.target.value))\n        el.querySelector(\"#iter-label\").textContent = str(new_val)\n        model.set(\"max_iter\", new_val)\n        model.save_changes()\n\n    el.querySelector(\"#fractal\").addEventListener(\"click\", create_proxy(on_click))\n    el.querySelector(\"#zoom-in\").addEventListener(\"click\", create_proxy(on_zoom_in))\n    el.querySelector(\"#zoom-out\").addEventListener(\"click\", create_proxy(on_zoom_out))\n    el.querySelector(\"#reset\").addEventListener(\"click\", create_proxy(on_reset))\n    el.querySelector(\"#iter-slider\").addEventListener(\"change\", create_proxy(on_iter_change))\n\ndef update(el, model):\n    render(el, model)",
  "_py_packages": ["numpy", "Pillow"],
  "center_x": -0.5,
  "center_y": 0.0,
  "zoom": 1.0,
  "max_iter": 100,
  "width": 400,
  "height": 400
}
```

## Example 5: K-Means Clustering (numpy + scikit-learn)

Click the canvas to add points. K-Means runs in the browser via Pyodide —
no server, no kernel. Adjust k with the buttons.

```{code-block} python
def render(el, model):
    import json
    import numpy as np

    points = json.loads(model.get("points_json"))
    n_clusters = model.get("n_clusters")

    COLORS = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
              "#59a14f", "#edc948", "#b07aa1", "#ff9da7"]

    labels = centers = inertia = None
    if len(points) >= n_clusters:
        from sklearn.cluster import KMeans
        X = np.array([[p["x"], p["y"]] for p in points])
        km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        km.fit(X)
        labels = km.labels_.tolist()
        centers = km.cluster_centers_.tolist()
        inertia = float(km.inertia_)

    # ... build SVG with colored circles and diamond centroids,
    #     wire up click-to-add-point and cluster-count buttons ...

def update(el, model):
    render(el, model)
```

```{anywidget} https://cdn.jsdelivr.net/npm/pywidget-bridge@0.1.1/pywidget-bridge.mjs
{
  "_py_render": "def render(el, model):\n    import json\n\n    import numpy as np\n\n    points = json.loads(model.get(\"points_json\"))\n    n_clusters = model.get(\"n_clusters\")\n\n    COLORS = [\n        \"#4e79a7\", \"#f28e2b\", \"#e15759\", \"#76b7b2\",\n        \"#59a14f\", \"#edc948\", \"#b07aa1\", \"#ff9da7\",\n    ]\n\n    labels = None\n    centers = None\n    inertia = None\n\n    if len(points) >= n_clusters:\n        from sklearn.cluster import KMeans\n\n        X = np.array([[p[\"x\"], p[\"y\"]] for p in points])\n        km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)\n        km.fit(X)\n        labels = km.labels_.tolist()\n        centers = km.cluster_centers_.tolist()\n        inertia = float(km.inertia_)\n\n    # Build SVG content\n    svg_width = 500\n    svg_height = 400\n\n    point_elements = \"\"\n    for i, p in enumerate(points):\n        if labels is not None:\n            color = COLORS[labels[i] % len(COLORS)]\n        else:\n            color = \"#999\"\n        point_elements += (\n            f'<circle cx=\"{p[\"x\"]}\" cy=\"{p[\"y\"]}\" r=\"6\" '\n            f'fill=\"{color}\" stroke=\"white\" stroke-width=\"1.5\" '\n            f'style=\"pointer-events:none;\" />'\n        )\n\n    centroid_elements = \"\"\n    if centers is not None:\n        for i, c in enumerate(centers):\n            cx, cy = c[0], c[1]\n            color = COLORS[i % len(COLORS)]\n            s = 10\n            diamond = (\n                f\"{cx},{cy - s} {cx + s},{cy} \"\n                f\"{cx},{cy + s} {cx - s},{cy}\"\n            )\n            centroid_elements += (\n                f'<polygon points=\"{diamond}\" '\n                f'fill=\"{color}\" stroke=\"#333\" stroke-width=\"2\" '\n                f'style=\"pointer-events:none;\" />'\n            )\n\n    # Stats\n    stats_html = \"\"\n    if labels is not None and centers is not None:\n        cluster_counts = {}\n        for lb in labels:\n            cluster_counts[lb] = cluster_counts.get(lb, 0) + 1\n        stats_items = \"\"\n        for ci in range(n_clusters):\n            color = COLORS[ci % len(COLORS)]\n            count = cluster_counts.get(ci, 0)\n            stats_items += (\n                f'<span style=\"display:inline-flex; align-items:center; gap:4px; margin-right:14px;\">'\n                f'<span style=\"width:12px; height:12px; background:{color}; '\n                f'border-radius:2px; display:inline-block;\"></span>'\n                f'Cluster {ci + 1}: {count} pts</span>'\n            )\n        stats_html = (\n            f'<div style=\"font-size:13px; color:#555; margin-top:6px;\">'\n            f'{stats_items}'\n            f'<span style=\"margin-left:10px; color:#888;\">| Inertia: {inertia:.1f}</span>'\n            f'</div>'\n        )\n\n    # Control bar: cluster count buttons + clear + info\n    btn_style = (\n        \"padding:5px 12px; font-size:13px; cursor:pointer; \"\n        \"border:1px solid #ccc; border-radius:4px; background:#f8f8f8; \"\n        \"min-width:30px; text-align:center;\"\n    )\n    active_btn_style = (\n        \"padding:5px 12px; font-size:13px; cursor:pointer; \"\n        \"border:2px solid #4e79a7; border-radius:4px; background:#e8f0fe; \"\n        \"min-width:30px; text-align:center; font-weight:bold; color:#4e79a7;\"\n    )\n\n    cluster_buttons = \"\"\n    for k in range(2, 9):\n        style = active_btn_style if k == n_clusters else btn_style\n        cluster_buttons += (\n            f'<button class=\"cluster-btn\" data-k=\"{k}\" style=\"{style}\">{k}</button>'\n        )\n\n    el.innerHTML = f\"\"\"\n    <div style=\"font-family:sans-serif; display:inline-block;\">\n        <div style=\"display:flex; align-items:center; gap:8px; margin-bottom:8px; flex-wrap:wrap;\">\n            <span style=\"font-size:13px; font-weight:600; color:#555;\">Clusters (k):</span>\n            {cluster_buttons}\n            <span style=\"width:1px; height:24px; background:#ddd; margin:0 4px;\"></span>\n            <button id=\"clear-btn\" style=\"{btn_style}\">Clear All</button>\n            <span style=\"font-size:13px; color:#888; margin-left:8px;\">{len(points)} points</span>\n        </div>\n        <svg id=\"canvas\" width=\"{svg_width}\" height=\"{svg_height}\"\n             style=\"cursor:crosshair; border:1px solid #ddd; border-radius:4px; display:block; background:#fafafa;\">\n            {point_elements}\n            {centroid_elements}\n        </svg>\n        <div id=\"stats\">{stats_html}</div>\n    </div>\n    \"\"\"\n\n    # Event: click on SVG to add a point\n    def on_svg_click(event):\n        svg = el.querySelector(\"#canvas\")\n        rect = svg.getBoundingClientRect()\n        x = float(event.clientX - rect.left)\n        y = float(event.clientY - rect.top)\n        current = json.loads(model.get(\"points_json\"))\n        current.append({\"x\": round(x, 1), \"y\": round(y, 1)})\n        model.set(\"points_json\", json.dumps(current))\n        model.save_changes()\n\n    el.querySelector(\"#canvas\").addEventListener(\"click\", create_proxy(on_svg_click))\n\n    # Event: cluster count buttons\n    def on_cluster_btn(event):\n        k = int(event.target.getAttribute(\"data-k\"))\n        model.set(\"n_clusters\", k)\n        model.save_changes()\n\n    proxy_cluster = create_proxy(on_cluster_btn)\n    for btn in el.querySelectorAll(\".cluster-btn\"):\n        btn.addEventListener(\"click\", proxy_cluster)\n\n    # Event: clear button\n    def on_clear(event):\n        model.set(\"points_json\", \"[]\")\n        model.save_changes()\n\n    el.querySelector(\"#clear-btn\").addEventListener(\"click\", create_proxy(on_clear))\n\ndef update(el, model):\n    render(el, model)",
  "_py_packages": ["numpy", "scikit-learn"],
  "points_json": "[]",
  "n_clusters": 3
}
```
