"""ImageCarousel: A pywidget that displays images with left/right navigation."""

from __future__ import annotations

import traitlets.traitlets as t

from .pywidget import PyWidget


class ImageCarousel(PyWidget):
    """A widget that displays a list of images with left/right navigation buttons.

    The widget accepts a list of image URLs or base64-encoded image data and
    renders them with previous/next navigation buttons in a horizontal layout.
    All navigation happens locally in the browser with no kernel round-trip.

    Parameters
    ----------
    images : list[str]
        A list of image URLs or base64-encoded image data strings.
    index : int
        The index of the currently displayed image (default 0).

    Examples
    --------
    >>> carousel = ImageCarousel(images=[
    ...     "https://example.com/image1.jpg",
    ...     "https://example.com/image2.jpg",
    ... ])
    >>> carousel  # displays directly in a Jupyter cell
    """

    images = t.List(t.Unicode(), []).tag(sync=True)
    index = t.Int(0).tag(sync=True)

    def render(self, el, model):
        images = list(model.get("images"))
        index = model.get("index")
        total = len(images)

        el.innerHTML = ""

        container = document.createElement("div")
        container.style.cssText = (
            "display:flex;align-items:center;justify-content:center;"
            "gap:8px;font-family:sans-serif;"
        )

        left_btn = document.createElement("button")
        left_btn.id = "carousel-left"
        left_btn.textContent = "\u25C0"
        left_btn.style.cssText = (
            "font-size:24px;padding:8px 12px;cursor:pointer;"
            "border:1px solid #ccc;border-radius:4px;background:#f5f5f5;"
        )
        left_btn.disabled = index <= 0

        img_el = document.createElement("img")
        img_el.id = "carousel-img"
        if total > 0 and 0 <= index < total:
            img_el.src = images[index]
        img_el.style.cssText = (
            "max-width:400px;max-height:300px;object-fit:contain;"
            "border:1px solid #ddd;border-radius:4px;"
        )
        img_el.alt = f"Image {index + 1} of {total}" if total > 0 else "No images"

        right_btn = document.createElement("button")
        right_btn.id = "carousel-right"
        right_btn.textContent = "\u25B6"
        right_btn.style.cssText = (
            "font-size:24px;padding:8px 12px;cursor:pointer;"
            "border:1px solid #ccc;border-radius:4px;background:#f5f5f5;"
        )
        right_btn.disabled = total == 0 or index >= total - 1

        counter = document.createElement("div")
        counter.id = "carousel-counter"
        counter.style.cssText = (
            "text-align:center;margin-top:4px;font-size:14px;color:#666;"
        )
        counter.textContent = f"{index + 1} / {total}" if total > 0 else "No images"

        container.appendChild(left_btn)
        container.appendChild(img_el)
        container.appendChild(right_btn)

        wrapper = document.createElement("div")
        wrapper.style.cssText = "display:flex;flex-direction:column;align-items:center;"
        wrapper.appendChild(container)
        wrapper.appendChild(counter)
        el.appendChild(wrapper)

        def refresh():
            cur = model.get("index")
            imgs = list(model.get("images"))
            n = len(imgs)
            img_node = el.querySelector("#carousel-img")
            if img_node:
                if n > 0 and 0 <= cur < n:
                    img_node.src = imgs[cur]
                    img_node.alt = f"Image {cur + 1} of {n}"
                else:
                    img_node.removeAttribute("src")
                    img_node.alt = "No images"
            cnt = el.querySelector("#carousel-counter")
            if cnt:
                cnt.textContent = f"{cur + 1} / {n}" if n > 0 else "No images"
            lb = el.querySelector("#carousel-left")
            if lb:
                lb.disabled = cur <= 0
            rb = el.querySelector("#carousel-right")
            if rb:
                rb.disabled = n == 0 or cur >= n - 1

        def on_left(event):
            cur = model.get("index")
            if cur > 0:
                new_idx = cur - 1
                model.set("index", new_idx)
                model.save_changes()
                refresh()

        def on_right(event):
            cur = model.get("index")
            imgs = list(model.get("images"))
            if cur < len(imgs) - 1:
                new_idx = cur + 1
                model.set("index", new_idx)
                model.save_changes()
                refresh()

        left_btn.addEventListener("click", create_proxy(on_left))
        right_btn.addEventListener("click", create_proxy(on_right))

    def update(self, el, model):
        cur = model.get("index")
        images = list(model.get("images"))
        n = len(images)
        img_node = el.querySelector("#carousel-img")
        if img_node:
            if n > 0 and 0 <= cur < n:
                img_node.src = images[cur]
                img_node.alt = f"Image {cur + 1} of {n}"
            else:
                img_node.removeAttribute("src")
                img_node.alt = "No images"
        cnt = el.querySelector("#carousel-counter")
        if cnt:
            cnt.textContent = f"{cur + 1} / {n}" if n > 0 else "No images"
        lb = el.querySelector("#carousel-left")
        if lb:
            lb.disabled = cur <= 0
        rb = el.querySelector("#carousel-right")
        if rb:
            rb.disabled = n == 0 or cur >= n - 1
