# /// script
# requires-python = ">=3.10"
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
    # Image Carousel

    A pure-Python image carousel widget with left/right navigation — no JavaScript required.

    All interaction (button clicks, image switching) runs locally in the browser via Pyodide.
    The kernel only needs to provide the list of image URLs.

    _Inspired by a [Jupyter Discourse question](https://discourse.jupyter.org/t/how-to-create-a-custom-ipywidget-in-python-and-not-in-javascipt/37918)
    about building a directly-displayable image carousel without JavaScript._
    """)
    return


@app.cell
def _():
    import marimo as mo
    import traitlets
    from pywidget import PyWidget

    return PyWidget, mo, traitlets


@app.cell
def _(PyWidget, mo, traitlets):
    class ImageCarousel(PyWidget):
        images = traitlets.List(traitlets.Unicode(), []).tag(sync=True)
        index = traitlets.Int(0).tag(sync=True)

        def render(self, el, model):
            images = list(model.get("images"))
            index = model.get("index")

            if not images:
                el.innerHTML = """
                <div style="font-family: sans-serif; padding: 40px; text-align: center;
                            color: #888; border: 2px dashed #ccc; border-radius: 12px;">
                    No images to display.
                </div>
                """
                return

            # Clamp index
            if index < 0:
                index = 0
            if index >= len(images):
                index = len(images) - 1

            prev_disabled = "disabled" if index == 0 else ""
            next_disabled = "disabled" if index == len(images) - 1 else ""

            el.innerHTML = f"""
            <div style="font-family: sans-serif; display: inline-block;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <button id="prev" {prev_disabled} style="
                        padding: 12px 16px; font-size: 22px; cursor: pointer;
                        border: 1px solid #ccc; border-radius: 8px; background: #f8f8f8;
                        color: #333; transition: background 0.15s;
                    ">&larr;</button>
                    <div style="text-align: center;">
                        <img id="carousel-img" src="{images[index]}"
                             style="max-width: 500px; max-height: 400px; border-radius: 8px;
                                    display: block; object-fit: contain;
                                    border: 1px solid #eee;" />
                        <span id="counter" style="display: block; margin-top: 8px;
                              font-size: 14px; color: #888;">
                            {index + 1} / {len(images)}
                        </span>
                    </div>
                    <button id="next" {next_disabled} style="
                        padding: 12px 16px; font-size: 22px; cursor: pointer;
                        border: 1px solid #ccc; border-radius: 8px; background: #f8f8f8;
                        color: #333; transition: background 0.15s;
                    ">&rarr;</button>
                </div>
            </div>
            """

            def update_display(new_index):
                img = el.querySelector("#carousel-img")
                counter = el.querySelector("#counter")
                prev_btn = el.querySelector("#prev")
                next_btn = el.querySelector("#next")
                current_images = list(model.get("images"))
                if img and current_images:
                    img.src = current_images[new_index]
                    counter.textContent = f"{new_index + 1} / {len(current_images)}"
                    prev_btn.disabled = new_index == 0
                    next_btn.disabled = new_index == len(current_images) - 1

            def on_prev(event):
                idx = model.get("index")
                if idx > 0:
                    idx = idx - 1
                    model.set("index", idx)
                    model.save_changes()
                    update_display(idx)

            def on_next(event):
                idx = model.get("index")
                current_images = list(model.get("images"))
                if idx < len(current_images) - 1:
                    idx = idx + 1
                    model.set("index", idx)
                    model.save_changes()
                    update_display(idx)

            el.querySelector("#prev").addEventListener("click", create_proxy(on_prev))
            el.querySelector("#next").addEventListener("click", create_proxy(on_next))

        def update(self, el, model):
            images = list(model.get("images"))
            index = model.get("index")

            if not images:
                el.innerHTML = """
                <div style="font-family: sans-serif; padding: 40px; text-align: center;
                            color: #888; border: 2px dashed #ccc; border-radius: 12px;">
                    No images to display.
                </div>
                """
                return

            # Clamp index
            if index < 0:
                index = 0
            if index >= len(images):
                index = len(images) - 1

            img = el.querySelector("#carousel-img")
            counter = el.querySelector("#counter")
            prev_btn = el.querySelector("#prev")
            next_btn = el.querySelector("#next")

            if img:
                img.src = images[index]
                counter.textContent = f"{index + 1} / {len(images)}"
                prev_btn.disabled = index == 0
                next_btn.disabled = index == len(images) - 1
            else:
                # Carousel DOM doesn't exist yet (e.g. images changed from empty
                # to non-empty); fall back to a full re-render.
                render(el, model)

    sample_images = [
        "https://picsum.photos/id/10/500/400",
        "https://picsum.photos/id/20/500/400",
        "https://picsum.photos/id/30/500/400",
        "https://picsum.photos/id/40/500/400",
        "https://picsum.photos/id/50/500/400",
    ]

    carousel = ImageCarousel(images=sample_images)
    mo.ui.anywidget(carousel)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## How it works

    The `ImageCarousel` widget uses two synced traitlets:

    - **`images`** — a list of image URLs (or base64 data URIs)
    - **`index`** — the currently displayed image index

    All navigation happens in the browser via Pyodide — clicking the arrow
    buttons updates the DOM directly with no kernel round-trip.
    The `update()` method handles kernel-side changes, so you can also
    set `carousel.index = 3` from Python to jump to a specific image.
    """)
    return


if __name__ == "__main__":
    app.run()
