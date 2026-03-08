import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Interactive Matplotlib Budget Editor

    Drag bar tops in a matplotlib chart and sync the edited values back to the
    Python kernel.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import json
    import traitlets
    from pywidget import PyWidget

    return PyWidget, json, mo, traitlets


@app.cell
def _(PyWidget, console, create_proxy, document, traitlets):
    class DraggableBarWidget(PyWidget):
        data_json = traitlets.Unicode('{"categories":[],"values":[]}').tag(sync=True)
        values_json = traitlets.Unicode("[]").tag(sync=True)
        _py_packages = ["matplotlib", "numpy"]

        def render(self, el, model):
            import matplotlib
            matplotlib.use("agg")
            import matplotlib.pyplot as plt
            import io
            import json

            data = json.loads(model.get("data_json"))
            categories = data.get("categories", [])
            values = list(data.get("values", []))
            n = len(categories)

            if n == 0:
                el.innerHTML = """
                <div style="font-family:sans-serif; padding:24px; color:#999;">
                    No data provided.
                </div>
                """
                return

            current_values = list(values)

            BAR_COLOR = "#4e79a7"
            DRAG_COLOR = "#f28e2b"
            y_max = max(values) * 1.5

            # Render matplotlib bar chart
            fig, ax = plt.subplots(figsize=(8, 4.5))
            bars = ax.bar(categories, values, color=BAR_COLOR, edgecolor="white", linewidth=0.8)

            ax.set_ylim(0, y_max)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_linewidth(0.5)
            ax.spines["bottom"].set_linewidth(0.5)
            ax.tick_params(axis="both", which="both", length=0)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
            ax.set_title(
                "Drag bar tops to adjust budget",
                fontsize=14, fontweight="bold", pad=14, color="#333"
            )
            fig.tight_layout()

            buf = io.StringIO()
            fig.savefig(buf, format="svg", bbox_inches="tight")
            plt.close(fig)
            svg_string = buf.getvalue()

            # Build value display cells
            total = sum(values)
            val_cells = "".join(
                f"""<div style="text-align:center; flex:1; padding:8px 4px;">
                    <div id="val-{i}" style="font-size:18px; font-weight:700; color:#333;">
                        ${v:,.0f}
                    </div>
                    <div style="font-size:12px; color:#999; margin-top:2px;">{cat}</div>
                    <div id="delta-{i}" style="font-size:11px; color:#ccc; margin-top:2px;">
                        &mdash;
                    </div>
                </div>"""
                for i, (cat, v) in enumerate(zip(categories, values))
            )

            el.innerHTML = f"""
            <div style="font-family:'Inter',system-ui,sans-serif; padding:20px; max-width:750px; user-select:none;">
                <div id="chart-container" style="cursor:default;">{svg_string}</div>
                <div id="values-panel" style="
                    display:flex; margin-top:4px; padding:12px 8px;
                    background:#f8f9fa; border-radius:10px;
                ">{val_cells}</div>
                <div id="total-panel" style="
                    display:flex; justify-content:space-between; align-items:center;
                    margin-top:10px; padding:10px 16px;
                    background:#e8f0fe; border-radius:8px; font-size:14px;
                ">
                    <span style="color:#555;">Total budget</span>
                    <span id="total-value" style="font-weight:700; font-size:18px; color:#1a73e8;">
                        ${total:,.0f}
                    </span>
                </div>
                <div style="margin-top:8px; text-align:center; font-size:12px; color:#bbb;">
                    Drag any bar to adjust &middot; values sync to Python
                </div>
            </div>
            """

            # Tag el with current data_json so update() knows when to re-render
            el.setAttribute("data-last-json", model.get("data_json"))

            # Sync initial values to kernel
            model.set("values_json", json.dumps(current_values))
            model.save_changes()

            # matplotlib renders bars as <path> elements, not <rect>.
            # Find bar paths by matching the fill color we used.
            svg_el = el.querySelector("svg")
            all_paths = el.querySelectorAll("svg path")
            bar_paths = []
            for idx_p in range(all_paths.length):
                p = all_paths.item(idx_p)
                style_attr = p.getAttribute("style") or ""
                fill_attr = p.getAttribute("fill") or ""
                # Match hex color (matplotlib may use either style or attribute)
                if BAR_COLOR in style_attr or BAR_COLOR in fill_attr:
                    bar_paths.append(p)

            # Sort by bounding box x position (left to right = category order)
            bar_paths.sort(key=lambda p: float(p.getBBox().x))
            bar_paths = bar_paths[:n]

            # Build bar_info from bounding boxes
            # Compute scale from the first bar with a positive value
            fallback_scale = 1.0
            for i, path in enumerate(bar_paths):
                if values[i] > 0:
                    bbox = path.getBBox()
                    fallback_scale = float(bbox.height) / values[i]
                    break

            bar_info = []
            for i, path in enumerate(bar_paths):
                bbox = path.getBBox()
                bx = float(bbox.x)
                by = float(bbox.y)
                bw = float(bbox.width)
                bh = float(bbox.height)
                baseline = by + bh  # SVG y of the bar bottom (value=0)
                scale = bh / values[i] if values[i] > 0 else fallback_scale
                bar_info.append({
                    "path": path,
                    "x": bx,
                    "width": bw,
                    "baseline": baseline,
                    "scale": scale,
                })
                path.style.cursor = "ns-resize"

            def make_rect_path(x, y, w, h):
                """Create an SVG path 'd' string for a rectangle."""
                return f"M {x} {y} L {x + w} {y} L {x + w} {y + h} L {x} {y + h} Z"

            # Drag state
            drag = {"active": False, "idx": -1}

            def get_svg_y(event):
                """Convert mouse event clientY to SVG y coordinate."""
                pt = svg_el.createSVGPoint()
                pt.x = float(event.clientX)
                pt.y = float(event.clientY)
                ctm = svg_el.getScreenCTM()
                if ctm is None:
                    return 0.0
                svg_pt = pt.matrixTransform(ctm.inverse())
                return float(svg_pt.y)

            def update_display():
                """Update value labels and total below the chart."""
                for i in range(n):
                    val_el = el.querySelector(f"#val-{i}")
                    delta_el = el.querySelector(f"#delta-{i}")
                    if val_el:
                        val_el.textContent = f"${current_values[i]:,.0f}"
                    if delta_el:
                        diff = current_values[i] - values[i]
                        if abs(diff) < 0.5:
                            delta_el.innerHTML = "&mdash;"
                            delta_el.style.color = "#ccc"
                        elif diff > 0:
                            delta_el.textContent = f"+${diff:,.0f}"
                            delta_el.style.color = "#34a853"
                        else:
                            delta_el.textContent = f"-${abs(diff):,.0f}"
                            delta_el.style.color = "#ea4335"
                total_el = el.querySelector("#total-value")
                if total_el:
                    new_total = sum(current_values)
                    total_el.textContent = f"${new_total:,.0f}"

            def make_mousedown(idx):
                def handler(event):
                    event.preventDefault()
                    drag["active"] = True
                    drag["idx"] = idx
                    bar_info[idx]["path"].style.setProperty("fill", DRAG_COLOR, "important")
                return handler

            def on_mousemove(event):
                if not drag["active"]:
                    return
                idx = drag["idx"]
                info = bar_info[idx]

                svg_y = get_svg_y(event)
                new_value = (info["baseline"] - svg_y) / info["scale"]
                new_value = max(0.0, round(new_value, 0))
                current_values[idx] = new_value

                # Redraw bar by rewriting the path's d attribute as a rectangle
                new_h = max(new_value * info["scale"], 0.5)
                new_y = info["baseline"] - new_h
                new_d = make_rect_path(info["x"], new_y, info["width"], new_h)
                info["path"].setAttribute("d", new_d)

                update_display()

            def on_mouseup(event):
                if not drag["active"]:
                    return
                idx = drag["idx"]
                drag["active"] = False
                drag["idx"] = -1

                bar_info[idx]["path"].style.setProperty("fill", BAR_COLOR, "important")

                model.set("values_json", json.dumps(current_values))
                model.save_changes()

            # Attach per-bar mousedown handlers
            for i in range(len(bar_info)):
                bar_info[i]["path"].addEventListener(
                    "mousedown", create_proxy(make_mousedown(i))
                )

            # Document-level move/up for smooth dragging even outside the chart
            document.addEventListener("mousemove", create_proxy(on_mousemove))
            document.addEventListener("mouseup", create_proxy(on_mouseup))

        def update(self, el, model):
            # Only re-render if the kernel changed data_json.
            # Skip re-render when values_json echoes back from the kernel,
            # otherwise it would wipe out the user's drag edits.
            prev = el.getAttribute("data-last-json")
            curr = model.get("data_json")
            if prev != curr:
                render(el, model)

    return (DraggableBarWidget,)


@app.cell
def _(DraggableBarWidget, json, mo):
    categories = ["Engineering", "Marketing", "Operations", "Research"]
    values = [420, 280, 190, 310]

    w = DraggableBarWidget(
        data_json=json.dumps({"categories": categories, "values": values})
    )
    widget = mo.ui.anywidget(w)
    widget
    return (widget,)


@app.cell
def _(json, mo, widget):
    edited = json.loads(widget.widget.values_json) if widget.widget.values_json != "[]" else []
    if edited:
        total = sum(edited)
        items = "".join(
            f"| {cat} | ${val:,.0f} |\n"
            for cat, val in zip(
                ["Engineering", "Marketing", "Operations", "Research"], edited
            )
        )
        _output = mo.md(
            f"""
    ### Budget Summary (from kernel)

    | Department | Budget |
    |------------|--------|
    {items}
    | **Total** | **${total:,.0f}** |
    """
        )
    else:
        _output = mo.md("_Drag bars to set budget allocations._")
    _output
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
