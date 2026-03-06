# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pywidget",
#     "anywidget",
#     "marimo>=0.20.4",
# ]
# ///

import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # K-Means Clustering Playground

    Click on the canvas to place data points. K-Means clustering runs in the browser via scikit-learn.
    Points are colored by cluster assignment, and centroids are shown as diamond markers.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import traitlets
    from pywidget import PyWidget

    return PyWidget, mo, traitlets


@app.cell
def _(PyWidget, create_proxy, mo, traitlets):
    class KMeansWidget(PyWidget):
        _py_packages = ["numpy", "scikit-learn"]

        points_json = traitlets.Unicode("[]").tag(sync=True)
        n_clusters = traitlets.Int(3).tag(sync=True)

        def render(self, el, model):
            import json

            import numpy as np

            points = json.loads(model.get("points_json"))
            n_clusters = model.get("n_clusters")

            COLORS = [
                "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
                "#59a14f", "#edc948", "#b07aa1", "#ff9da7",
            ]

            labels = None
            centers = None
            inertia = None

            if len(points) >= n_clusters:
                from sklearn.cluster import KMeans

                X = np.array([[p["x"], p["y"]] for p in points])
                km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
                km.fit(X)
                labels = km.labels_.tolist()
                centers = km.cluster_centers_.tolist()
                inertia = float(km.inertia_)

            # Build SVG content
            svg_width = 500
            svg_height = 400

            point_elements = ""
            for i, p in enumerate(points):
                if labels is not None:
                    color = COLORS[labels[i] % len(COLORS)]
                else:
                    color = "#999"
                point_elements += (
                    f'<circle cx="{p["x"]}" cy="{p["y"]}" r="6" '
                    f'fill="{color}" stroke="white" stroke-width="1.5" '
                    f'style="pointer-events:none;" />'
                )

            centroid_elements = ""
            if centers is not None:
                for i, c in enumerate(centers):
                    cx, cy = c[0], c[1]
                    color = COLORS[i % len(COLORS)]
                    s = 10
                    diamond = (
                        f"{cx},{cy - s} {cx + s},{cy} "
                        f"{cx},{cy + s} {cx - s},{cy}"
                    )
                    centroid_elements += (
                        f'<polygon points="{diamond}" '
                        f'fill="{color}" stroke="#333" stroke-width="2" '
                        f'style="pointer-events:none;" />'
                    )

            # Stats
            stats_html = ""
            if labels is not None and centers is not None:
                cluster_counts = {}
                for lb in labels:
                    cluster_counts[lb] = cluster_counts.get(lb, 0) + 1
                stats_items = ""
                for ci in range(n_clusters):
                    color = COLORS[ci % len(COLORS)]
                    count = cluster_counts.get(ci, 0)
                    stats_items += (
                        f'<span style="display:inline-flex; align-items:center; gap:4px; margin-right:14px;">'
                        f'<span style="width:12px; height:12px; background:{color}; '
                        f'border-radius:2px; display:inline-block;"></span>'
                        f'Cluster {ci + 1}: {count} pts</span>'
                    )
                stats_html = (
                    f'<div style="font-size:13px; color:#555; margin-top:6px;">'
                    f'{stats_items}'
                    f'<span style="margin-left:10px; color:#888;">| Inertia: {inertia:.1f}</span>'
                    f'</div>'
                )

            # Control bar: cluster count buttons + clear + info
            btn_style = (
                "padding:5px 12px; font-size:13px; cursor:pointer; "
                "border:1px solid #ccc; border-radius:4px; background:#f8f8f8; "
                "min-width:30px; text-align:center;"
            )
            active_btn_style = (
                "padding:5px 12px; font-size:13px; cursor:pointer; "
                "border:2px solid #4e79a7; border-radius:4px; background:#e8f0fe; "
                "min-width:30px; text-align:center; font-weight:bold; color:#4e79a7;"
            )

            cluster_buttons = ""
            for k in range(2, 9):
                style = active_btn_style if k == n_clusters else btn_style
                cluster_buttons += (
                    f'<button class="cluster-btn" data-k="{k}" style="{style}">{k}</button>'
                )

            el.innerHTML = f"""
            <div style="font-family:sans-serif; display:inline-block;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; flex-wrap:wrap;">
                    <span style="font-size:13px; font-weight:600; color:#555;">Clusters (k):</span>
                    {cluster_buttons}
                    <span style="width:1px; height:24px; background:#ddd; margin:0 4px;"></span>
                    <button id="clear-btn" style="{btn_style}">Clear All</button>
                    <span style="font-size:13px; color:#888; margin-left:8px;">{len(points)} points</span>
                </div>
                <svg id="canvas" width="{svg_width}" height="{svg_height}"
                     style="cursor:crosshair; border:1px solid #ddd; border-radius:4px; display:block; background:#fafafa;">
                    {point_elements}
                    {centroid_elements}
                </svg>
                <div id="stats">{stats_html}</div>
            </div>
            """

            # Event: click on SVG to add a point
            def on_svg_click(event):
                svg = el.querySelector("#canvas")
                rect = svg.getBoundingClientRect()
                x = float(event.clientX - rect.left)
                y = float(event.clientY - rect.top)
                current = json.loads(model.get("points_json"))
                current.append({"x": round(x, 1), "y": round(y, 1)})
                model.set("points_json", json.dumps(current))
                model.save_changes()

            el.querySelector("#canvas").addEventListener("click", create_proxy(on_svg_click))

            # Event: cluster count buttons
            def on_cluster_btn(event):
                k = int(event.target.getAttribute("data-k"))
                model.set("n_clusters", k)
                model.save_changes()

            proxy_cluster = create_proxy(on_cluster_btn)
            for btn in el.querySelectorAll(".cluster-btn"):
                btn.addEventListener("click", proxy_cluster)

            # Event: clear button
            def on_clear(event):
                model.set("points_json", "[]")
                model.save_changes()

            el.querySelector("#clear-btn").addEventListener("click", create_proxy(on_clear))

        def update(self, el, model):
            render(el, model)

    w = mo.ui.anywidget(KMeansWidget())
    w
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
