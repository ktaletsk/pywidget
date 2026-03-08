# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pywidget",
#     "anywidget",
#     "marimo>=0.20.4",
#     "numpy",
# ]
# ///

import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Interactive OpenCV Playground

    _A hands-on introduction to computer vision with OpenCV -- using your own webcam._

    This notebook demonstrates how to apply classic OpenCV image-processing
    operations to a **live webcam feed** running entirely in the browser. There
    is no server round-trip for each frame: the camera stream, pixel capture,
    and filter processing all happen client-side via
    [Pyodide](https://pyodide.org) (Python compiled to WebAssembly).

    ## How to use

    1. Click **Start Camera** below. Your browser will ask for camera permission.
    2. Pick a filter from the button bar to see it applied in real time.
    3. Click **Snapshot to kernel** to send the current frame to the Python
       kernel as a raw NumPy array -- then keep scrolling to see it arrive.

    ## Filters available

    | Filter | OpenCV call | What it does |
    |--------|------------|--------------|
    | **None** | _(passthrough -- no pixel copy)_ | Raw webcam feed |
    | **Gray** | `cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)` | Luminance-only conversion |
    | **Edges** | `cv2.Canny(gray, 100, 200)` | Gradient-based edge detection |
    | **Blur** | `cv2.GaussianBlur(frame, (15, 15), 0)` | Gaussian smoothing / noise reduction |
    | **Threshold** | `cv2.threshold(gray, 127, 255, THRESH_BINARY)` | Binary intensity segmentation |
    | **Cartoon** | bilateral filter + adaptive threshold | Stylized illustration effect |

    ## Architecture

    ```
    Browser (Pyodide / WASM)                              Python kernel
    ┌────────────────────────────────────────┐
    │  getUserMedia() -> <video> element     │
    │       |                                │
    │  canvas.drawImage(video) each tick     │
    │       |                                │
    │  getImageData() -> NumPy (RGBA)        │
    │       |                                │
    │  cv2 filter (selected by user)         │
    │       |                                │
    │  PIL JPEG encode -> <img> src          │
    │                                        │  "Snapshot to kernel"
    │  [Snapshot] -> base64(raw RGB bytes) ──┼──> decode -> np.frombuffer()
    └────────────────────────────────────────┘       -> (H, W, 3) uint8 array
    ```

    Zero network hops per frame. The only data that crosses to the kernel is
    an explicit snapshot (≈230 KB for 320x240 RGB).
    """)
    return


@app.cell
def _():
    import base64
    import io

    import marimo as mo
    import numpy as np
    import traitlets
    from pywidget import PyWidget

    return PyWidget, base64, io, mo, np, traitlets


@app.cell
def _(PyWidget, create_proxy, mo, traitlets):
    class OpenCVPlaygroundWidget(PyWidget):
        _py_packages = ["opencv-python", "numpy", "Pillow"]

        snapshot_data = traitlets.Unicode("").tag(sync=True)
        snapshot_width = traitlets.Int(0).tag(sync=True)
        snapshot_height = traitlets.Int(0).tag(sync=True)
        filter_name = traitlets.Unicode("none").tag(sync=True)

        async def render(self, el, model):
            from js import document, navigator, window, setInterval, clearInterval
            from pyodide.ffi import to_js
            import asyncio
            import base64
            import io
            import time

            import cv2
            import numpy as np
            from PIL import Image

            # --- Closure-based state ---
            state = {
                "interval_id": None,
                "stream": None,
                "running": False,
                "current_filter": model.get("filter_name") or "none",
                "frame_count": 0,
                "last_fps_time": 0.0,
                "last_rgb": None,
            }

            # --- Secure context check ---
            if not window.isSecureContext:
                el.innerHTML = (
                    '<div style="padding:20px; color:#c00; font-family:sans-serif;">'
                    "<strong>Secure context required.</strong><br>"
                    "Webcam access requires HTTPS or localhost. "
                    "This page is not in a secure context."
                    "</div>"
                )
                return

            # --- Styles ---
            BTN = (
                "padding:6px 14px; font-size:13px; cursor:pointer; "
                "border:1px solid #ccc; border-radius:4px; background:#f8f8f8;"
            )
            BTN_ACTIVE = (
                "padding:6px 14px; font-size:13px; cursor:pointer; "
                "border:2px solid #4e79a7; border-radius:4px; background:#e8f0fe; "
                "font-weight:bold; color:#4e79a7;"
            )
            BTN_DISABLED = (
                "padding:6px 14px; font-size:13px; "
                "border:1px solid #eee; border-radius:4px; background:#f0f0f0; "
                "color:#aaa; cursor:not-allowed;"
            )

            FILTERS = ["none", "gray", "edges", "blur", "threshold", "cartoon"]

            filter_buttons = ""
            for f in FILTERS:
                label = f.capitalize() if f != "none" else "None"
                filter_buttons += (
                    f'<button class="filter-btn" data-filter="{f}" '
                    f'style="{BTN_DISABLED}" disabled>{label}</button> '
                )

            el.innerHTML = f"""
            <div style="font-family:sans-serif; display:inline-block;">
                <div id="feed-container" style="position:relative; width:320px; height:240px;
                     background:#000; border:1px solid #ddd; border-radius:4px; overflow:hidden;
                     display:flex; align-items:center; justify-content:center;">
                    <canvas id="passthrough-canvas" width="320" height="240"
                            style="display:none; width:320px; height:240px;"></canvas>
                    <img id="processed-img" width="320" height="240"
                         style="display:none; width:320px; height:240px;" />
                    <div id="placeholder" style="color:#888; font-size:14px;
                         text-align:center; padding:20px;">
                        Click <strong>Start Camera</strong> to begin
                    </div>
                </div>
                <div id="filter-bar" style="display:flex; gap:6px; margin-top:8px; flex-wrap:wrap;">
                    {filter_buttons}
                </div>
                <div style="display:flex; gap:8px; margin-top:8px; align-items:center;">
                    <button id="start-btn" style="{BTN}">Start Camera</button>
                    <button id="snapshot-btn" style="{BTN_DISABLED}" disabled>Snapshot to kernel</button>
                </div>
                <div id="status-bar" style="margin-top:6px; font-size:12px; color:#888;">
                    FPS: --  |  320\u00d7240
                </div>
            </div>
            """

            # --- Hidden video element + offscreen canvas ---
            video = document.createElement("video")
            video.setAttribute("playsinline", "true")
            video.setAttribute("autoplay", "true")

            offscreen_canvas = document.createElement("canvas")
            offscreen_canvas.width = 320
            offscreen_canvas.height = 240
            offscreen_ctx = offscreen_canvas.getContext("2d")

            # --- Filter functions ---
            def apply_filter(frame_rgb, filter_name):
                if filter_name == "gray":
                    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
                    return np.stack([gray, gray, gray], axis=-1)
                elif filter_name == "edges":
                    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
                    edges = cv2.Canny(gray, 100, 200)
                    return np.stack([edges, edges, edges], axis=-1)
                elif filter_name == "blur":
                    return cv2.GaussianBlur(frame_rgb, (15, 15), 0)
                elif filter_name == "threshold":
                    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
                    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                    return np.stack([thresh, thresh, thresh], axis=-1)
                elif filter_name == "cartoon":
                    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
                    gray_blur = cv2.medianBlur(gray, 5)
                    edges = cv2.adaptiveThreshold(
                        gray_blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                        cv2.THRESH_BINARY, 9, 9,
                    )
                    color = cv2.bilateralFilter(frame_rgb, 9, 300, 300)
                    edges_3ch = np.stack([edges, edges, edges], axis=-1)
                    return cv2.bitwise_and(color, edges_3ch)
                else:
                    return frame_rgb

            # --- Frame processing callback for setInterval ---
            def process_frame():
                if not state["running"]:
                    return

                w = 320
                h = 240
                current_f = state["current_filter"]

                passthrough_canvas = el.querySelector("#passthrough-canvas")
                processed_img = el.querySelector("#processed-img")

                if current_f == "none":
                    passthrough_canvas.style.display = "block"
                    processed_img.style.display = "none"
                    pt_ctx = passthrough_canvas.getContext("2d")
                    pt_ctx.drawImage(video, 0, 0, w, h)
                else:
                    passthrough_canvas.style.display = "none"
                    processed_img.style.display = "block"

                    offscreen_ctx.drawImage(video, 0, 0, w, h)
                    image_data = offscreen_ctx.getImageData(0, 0, w, h)
                    buf_data = image_data.data.to_py()
                    rgba = np.frombuffer(buf_data, dtype=np.uint8).reshape((h, w, 4))
                    rgb = rgba[:, :, :3].copy()

                    processed = apply_filter(rgb, current_f)
                    state["last_rgb"] = processed

                    img = Image.fromarray(processed, "RGB")
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=80)
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                    processed_img.src = f"data:image/jpeg;base64,{b64}"

                # FPS counter (update once per second)
                now = time.time()
                state["frame_count"] += 1
                elapsed = now - state["last_fps_time"]
                if elapsed >= 1.0:
                    fps = state["frame_count"] / elapsed
                    status = el.querySelector("#status-bar")
                    if status:
                        status.textContent = f"FPS: {fps:.1f}  |  {w}\u00d7{h}"
                    state["frame_count"] = 0
                    state["last_fps_time"] = now

            # --- Start camera (async) ---
            async def start_camera():
                try:
                    constraints = to_js(
                        {"video": to_js({"width": 320, "height": 240})}
                    )
                    stream = await navigator.mediaDevices.getUserMedia(constraints)
                    state["stream"] = stream

                    video.srcObject = stream
                    await video.play()

                    # Enable filter buttons
                    for btn in el.querySelectorAll(".filter-btn"):
                        btn.disabled = False
                        f = btn.getAttribute("data-filter")
                        if f == state["current_filter"]:
                            btn.style = BTN_ACTIVE
                        else:
                            btn.style = BTN

                    # Enable snapshot button
                    snap_btn = el.querySelector("#snapshot-btn")
                    snap_btn.disabled = False
                    snap_btn.style = BTN

                    # Hide placeholder
                    placeholder = el.querySelector("#placeholder")
                    if placeholder:
                        placeholder.style.display = "none"

                    # Update button text
                    el.querySelector("#start-btn").textContent = "Stop Camera"

                    # Start processing loop
                    state["running"] = True
                    state["frame_count"] = 0
                    state["last_fps_time"] = time.time()

                    frame_proxy = create_proxy(process_frame)
                    state["interval_id"] = setInterval(frame_proxy, 66)

                except Exception as e:
                    error_msg = str(e)
                    placeholder = el.querySelector("#placeholder")
                    if "NotAllowedError" in error_msg or "Permission" in error_msg:
                        placeholder.innerHTML = (
                            '<div style="color:#c00;">'
                            "Camera access denied.<br>"
                            "Click the camera icon in your browser's address bar to allow it."
                            "</div>"
                        )
                    else:
                        placeholder.innerHTML = (
                            f'<div style="color:#c00;">Camera error: {error_msg}</div>'
                        )

            # --- Stop camera ---
            def stop_camera():
                state["running"] = False
                if state["interval_id"] is not None:
                    clearInterval(state["interval_id"])
                    state["interval_id"] = None
                if state["stream"]:
                    tracks = state["stream"].getTracks()
                    for i in range(tracks.length):
                        tracks[i].stop()
                    state["stream"] = None

                el.querySelector("#start-btn").textContent = "Start Camera"
                passthrough_canvas = el.querySelector("#passthrough-canvas")
                processed_img = el.querySelector("#processed-img")
                placeholder = el.querySelector("#placeholder")
                if passthrough_canvas:
                    passthrough_canvas.style.display = "none"
                if processed_img:
                    processed_img.style.display = "none"
                if placeholder:
                    placeholder.style.display = "block"
                    placeholder.innerHTML = (
                        "Click <strong>Start Camera</strong> to begin"
                    )

                for btn in el.querySelectorAll(".filter-btn"):
                    btn.disabled = True
                    btn.style = BTN_DISABLED
                snap_btn = el.querySelector("#snapshot-btn")
                snap_btn.disabled = True
                snap_btn.style = BTN_DISABLED

                el.querySelector("#status-bar").textContent = (
                    "FPS: --  |  320\u00d7240"
                )

            # --- Event: Start / Stop toggle ---
            def on_start_stop(event):
                if state["running"]:
                    stop_camera()
                else:
                    asyncio.ensure_future(start_camera())

            el.querySelector("#start-btn").addEventListener(
                "click", create_proxy(on_start_stop)
            )

            # --- Event: Filter selection ---
            def on_filter_click(event):
                f = event.target.getAttribute("data-filter")
                if f is None:
                    return
                state["current_filter"] = f
                model.set("filter_name", f)
                model.save_changes()
                for btn in el.querySelectorAll(".filter-btn"):
                    if btn.getAttribute("data-filter") == f:
                        btn.style = BTN_ACTIVE
                    else:
                        btn.style = BTN

            filter_proxy = create_proxy(on_filter_click)
            for btn in el.querySelectorAll(".filter-btn"):
                btn.addEventListener("click", filter_proxy)

            # --- Event: Snapshot ---
            def on_snapshot(event):
                w = 320
                h = 240
                if state["current_filter"] == "none":
                    pc = el.querySelector("#passthrough-canvas")
                    pc_ctx = pc.getContext("2d")
                    image_data = pc_ctx.getImageData(0, 0, w, h)
                    buf_data = image_data.data.to_py()
                    rgba = np.frombuffer(buf_data, dtype=np.uint8).reshape((h, w, 4))
                    rgb = rgba[:, :, :3].copy()
                else:
                    rgb = state["last_rgb"]

                if rgb is not None:
                    model.set("snapshot_data", base64.b64encode(rgb.tobytes()).decode("ascii"))
                    model.set("snapshot_width", w)
                    model.set("snapshot_height", h)
                    model.save_changes()
                    container = el.querySelector("#feed-container")
                    container.style.border = "3px solid #4e79a7"

                    def reset_border():
                        container.style.border = "1px solid #ddd"

                    window.setTimeout(create_proxy(reset_border), 300)

            el.querySelector("#snapshot-btn").addEventListener(
                "click", create_proxy(on_snapshot)
            )

    w = mo.ui.anywidget(OpenCVPlaygroundWidget())
    w
    return (w,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Captured frame

    When you click **Snapshot to kernel**, the widget sends the current
    processed frame as raw RGB pixel data (base64-encoded) to the Python
    kernel. The cell below decodes it back into a NumPy array of shape
    `(height, width, 3)` with `dtype=uint8` -- the standard format that
    OpenCV, PIL, matplotlib, scikit-image, and scikit-learn all understand.

    This is the bridge between the live browser-side processing and
    traditional kernel-side analysis: histogram computation, feature
    extraction, model inference, saving to disk, etc.
    """)
    return


@app.cell(hide_code=True)
def _(base64, io, mo, np, w):
    from PIL import Image

    _raw = w.widget.snapshot_data
    mo.stop(not _raw, mo.md("Click **Snapshot to kernel** to capture a frame."))
    _h = w.widget.snapshot_height
    _w = w.widget.snapshot_width
    _bytes = base64.b64decode(_raw)
    frame = np.frombuffer(_bytes, dtype=np.uint8).reshape((_h, _w, 3))

    _buf = io.BytesIO()
    Image.fromarray(frame).save(_buf, format="PNG")

    mo.vstack([
        mo.md(f"Captured frame: **{frame.shape}** (dtype: `{frame.dtype}`)"),
        mo.image(_buf.getvalue()),
    ])
    return


if __name__ == "__main__":
    app.run()
