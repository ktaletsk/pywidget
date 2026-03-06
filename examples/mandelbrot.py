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
    # Mandelbrot Set Explorer
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
    class MandelbrotSetWidget(PyWidget):
        _py_packages = ["numpy", "Pillow"]

        center_x = traitlets.Float(-0.5).tag(sync=True)
        center_y = traitlets.Float(0.0).tag(sync=True)
        zoom = traitlets.Float(1.0).tag(sync=True)
        max_iter = traitlets.Int(100).tag(sync=True)
        width = traitlets.Int(400).tag(sync=True)
        height = traitlets.Int(400).tag(sync=True)

        def render(self, el, model):
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
            rgb = np.stack(
                [
                    (np.sin(norm * np.pi * 2) * 127 + 128).astype(np.uint8),
                    (np.sin(norm * np.pi * 2 + 2.094) * 127 + 128).astype(np.uint8),
                    (np.sin(norm * np.pi * 2 + 4.189) * 127 + 128).astype(np.uint8),
                ],
                axis=-1,
            )
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
                cur_cx = model.get("center_x")
                cur_cy = model.get("center_y")
                cur_z = model.get("zoom")
                cur_w = model.get("width")
                cur_h = model.get("height")
                r = 3.0 / cur_z
                aspect = cur_w / cur_h
                new_cx = (cur_cx - r * aspect / 2) + (event.offsetX / cur_w) * r * aspect
                new_cy = (cur_cy - r / 2) + (event.offsetY / cur_h) * r
                model.set("center_x", float(new_cx))
                model.set("center_y", float(new_cy))
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

        def update(self, el, model):
            render(el, model)

    w = mo.ui.anywidget(MandelbrotSetWidget())
    w
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
