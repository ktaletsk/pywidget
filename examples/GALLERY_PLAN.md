# pywidget Gallery Examples — Implementation Plan

Four new examples that showcase pywidget's unique capability: **real Python
computation running in the browser** via Pyodide. Each example uses only
pure-Python Pyodide packages — no JavaScript required.

All examples will live in `examples/pywidget_gallery.ipynb` (Jupyter) and
`examples/pywidget_gallery_marimo.py` (marimo).

---

## Example 1: Mandelbrot Set Explorer

DONE

## Example 2: K-Means Clustering Playground

DONE

## Example 3: Markdown Previewer

**Concept**: Side-by-side editor and preview. Type Markdown in a textarea,
Python's `markdown` library converts to HTML, displayed live.

**Traitlets**:

- `text = Unicode("# Hello\n\nType **markdown** here...")` — the markdown
  source

**Pyodide packages**: `markdown`

**Render logic**:

1. Render a two-column layout (flexbox): textarea on the left, preview div
   on the right.
2. Textarea `input` event handler: read `textarea.value`, run
   `markdown.markdown(text)`, set preview div's `innerHTML` to the result.
3. Also sync the text back to the kernel via `model.set("text", ...)` /
   `model.save_changes()` so the kernel can read what was typed.
4. Style the preview to look like rendered documentation (proper heading
   sizes, code blocks, etc.).

**What this showcases**: Python stdlib-level processing (the `markdown`
library is pure Python, installable via micropip) running live in the
browser. Practical utility — a real tool, not just a demo.

---

## Example 4: OpenAI Chat (browser-side API call)

**Concept**: A chat widget where the user enters their API key and a prompt.
The OpenAI API call happens directly from the browser using
`pyodide.http.pyfetch`. The API key never touches the kernel — it stays in
the browser only.

Uses `pyfetch` over the `openai` SDK because:

- `pyfetch` uses the browser's native `fetch` and is proven reliable in
  Pyodide.
- The `openai` SDK depends on async `httpx` which may have WASM edge cases.
- Raw `pyfetch` makes the "browser-native" angle clearer.
- If the `openai` SDK ends up working, we can always switch later.

**Traitlets**:

- `response_text = Unicode("")` — the model's response (synced back to
  kernel)

**Pyodide packages**: none (just stdlib + `pyodide.http`)

**Render logic**:

1. Render a card with: API key input (`type=password`), model dropdown
   (`gpt-4o-mini`, `gpt-4o`), textarea for the prompt, "Send" button,
   response area.
2. Button click handler (async via `asyncio.ensure_future`):
   a. Read API key and prompt from DOM inputs.
   b. Call `pyodide.http.pyfetch("https://api.openai.com/v1/chat/completions", ...)`
      with the proper headers/body.
   c. Parse JSON response, extract the completion text.
   d. Display it in the response area.
   e. Sync to kernel via `model.set("response_text", ...)` /
      `model.save_changes()`.
3. Show loading state while request is in flight.
4. Error handling: display API errors cleanly (invalid key, rate limit,
   etc.).

**What this showcases**: Making authenticated API calls from Python running
in the browser. The privacy angle is strong — the API key is entered in the
browser and sent directly to OpenAI, never passing through a kernel or
server. The response is synced back to the kernel for downstream use.

---

## Open Questions / Risks

- **Async callbacks**: The OpenAI example needs `asyncio.ensure_future()`
  inside a sync event handler. This works in Pyodide because it integrates
  with the browser's event loop, but hasn't been tested in pywidget yet.
  Fallback: kernel-side API call via traitlet sync.
- **Mandelbrot performance**: For 400x400 at high iterations, NumPy in WASM
  is ~2-5x slower than native. May need to limit default resolution or
  show a progress indicator.
- **scikit-learn load time**: First import of sklearn in Pyodide takes a
  few seconds. The widget should show a loading state during this.
