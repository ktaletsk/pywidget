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

## Example 5: PII Scrubber (browser-side privacy-preserving data cleaning)

### Concept

A widget for editing and sanitizing sensitive documents before they reach the
kernel. The user writes or pastes a markdown document, the widget
auto-detects PII using regex, the user reviews and manually redacts
additional content, and only the sanitized text is synced to the kernel when
the user explicitly clicks Submit.

The privacy guarantee is **architectural**: the raw text lives only in
browser DOM and Pyodide WASM memory. No traitlet ever holds the raw text, so
it physically cannot cross the wire. The traitlet sync boundary IS the
privacy boundary.

```
Browser (Pyodide WASM)                   Kernel
┌──────────────────────────────┐         ┌──────────────────┐
│                              │         │                  │
│  Phase 1: Edit               │         │                  │
│    textarea ──> markdown     │         │                  │
│    (live preview)            │         │                  │
│                              │         │                  │
│  Phase 2: Auto-detect        │         │                  │
│    re.finditer() finds PII   │         │                  │
│    preview shows highlights  │         │                  │
│                              │         │                  │
│  Phase 3: Manual redact      │         │                  │
│    user selects text,        │         │                  │
│    clicks "Redact"           │         │                  │
│                              │         │                  │
│  Phase 4: Submit             │  sync   │                  │
│    user clicks "Submit" ────────────>  │  sanitized_text  │
│                              │         │  pii_summary     │
│                              │         │                  │
└──────────────────────────────┘         └──────────────────┘
```

### Pyodide packages

- `markdown` — render markdown preview in the browser

### Traitlets (synced to kernel)

Only populated after the user clicks Submit. Empty/default until then.

- `sanitized_text = Unicode("")` — the redacted document
- `pii_summary_json = Unicode("{}")` — JSON summary of what was redacted
  (e.g. `{"EMAIL": 2, "SSN": 1, "manual": 3}`)

What is **NOT** a traitlet (browser-only, never synced):

- The raw input text (lives in `<textarea>` DOM element)
- The PII findings list (Python list in render closure)
- The manual redaction list (Python list in render closure)
- All intermediate state before Submit

### PII detection patterns

Using `re` from stdlib. No external NLP dependencies.

| Type          | Pattern description                     | Example match               |
|---------------|-----------------------------------------|-----------------------------|
| `EMAIL`       | standard email format                   | `jane.smith@hospital.org`   |
| `PHONE`       | US phone with optional country code     | `(555) 867-5309`, `+1 555.123.4567` |
| `SSN`         | NNN-NN-NNNN                             | `123-45-6789`               |
| `CREDIT_CARD` | 16 digits, optional separators          | `4111-1111-1111-1111`       |
| `IP_ADDR`     | IPv4 dotted quad                        | `192.168.1.42`              |

Each type gets a distinct color for visual differentiation in the preview.

### User interaction flow

#### Phase 1: Edit

- Split layout: markdown source textarea (left), live rendered preview
  (right).
- As the user types, `markdown.markdown()` converts the source to HTML and
  updates the preview div. This is the standard Markdown Previewer
  behavior.
- No PII processing yet. Submit button is disabled.

#### Phase 2: Auto-detect

- User clicks **"Scan for PII"**.
- `re.finditer()` runs all patterns against the raw textarea content.
- The preview switches from clean render to **annotated render**: PII
  matches are wrapped in colored `<span>` elements with a border and
  background tint matching their type.
- A report appears below the preview showing counts per type (e.g.
  "Found: 2 EMAIL, 1 SSN, 1 CREDIT_CARD").
- Each detected item appears in a **findings list** with a checkbox
  (checked by default). The user can uncheck items that are false
  positives (e.g. a test email address that's OK to keep).
- Submit button remains disabled.

#### Phase 3: Manual redact

- User selects text in the **rendered preview** (standard browser text
  selection) and clicks a **"Redact selection"** button.
- The selected range is captured via `window.getSelection()` (accessible
  from Pyodide as `from js import window`). The corresponding character
  offsets in the raw source text are computed and added to a manual
  redaction list.
- Manually redacted spans appear in the preview with a different style
  (e.g. gray background with "MANUAL" label) to distinguish them from
  auto-detected PII.
- The findings list updates to include manual items.
- Submit button remains disabled.

#### Phase 4: Review & Submit

- User clicks **"Submit"**.
- All checked auto-detections and all manual redactions are applied to the
  raw text: each match is replaced with a placeholder like `[EMAIL]`,
  `[SSN]`, `[REDACTED]`, etc.
- The sanitized text is assigned to the `sanitized_text` traitlet via
  `model.set()` + `model.save_changes()`. This is the ONLY moment data
  crosses to the kernel.
- The `pii_summary_json` traitlet is also set with the redaction counts.
- The preview updates to show the final scrubbed document.
- A confirmation message appears: "Sanitized text sent to kernel."

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  🔒 Privacy: raw text stays in your browser.            │
│     Only scrubbed text is sent to the kernel.           │
├─────────────────────────────────────────────────────────┤
│  [EMAIL] [PHONE] [SSN] [CREDIT_CARD] [IP_ADDR] legend  │
├───────────────────────┬─────────────────────────────────┤
│  Raw Markdown Input   │  Rendered Preview               │
│  (textarea)           │  (with PII highlights after     │
│                       │   scan; supports text selection  │
│                       │   for manual redaction)          │
│                       │                                 │
│                       │                                 │
│                       │                                 │
├───────────────────────┴─────────────────────────────────┤
│  [Scan for PII]  [Redact Selection]  [Submit]           │
├─────────────────────────────────────────────────────────┤
│  Findings list (checkboxes):                            │
│    ☑ EMAIL: jane.smith@hospital.org                     │
│    ☑ SSN: 123-45-6789                                   │
│    ☑ MANUAL: "Jane Smith"                               │
│    ☐ PHONE: (555) 867-5309  (unchecked = keep)          │
├─────────────────────────────────────────────────────────┤
│  Report: Found 4 items. 3 will be redacted.             │
└─────────────────────────────────────────────────────────┘
```

### State management (all browser-side)

All mutable state lives in Python variables inside the `render()` closure.
None of it is stored in traitlets.

```python
# Inside render():
current_findings = []   # list of {type, value, start, end, checked}
manual_redactions = []  # list of {start, end, label}
phase = "edit"          # "edit" | "scanned" | "submitted"
```

Button enable/disable logic:

| Phase       | Scan  | Redact Selection | Submit  |
|-------------|-------|------------------|---------|
| `edit`      | on    | off              | off     |
| `scanned`   | on    | on               | on      |
| `submitted` | off   | off              | off     |

### Mapping selection offsets back to source

When the user selects text in the rendered HTML preview, we need to map that
selection back to character offsets in the raw markdown source. This is
non-trivial because the markdown-to-HTML conversion changes the structure.

**Approach**: Instead of trying to reverse-map HTML positions to markdown
positions, we run PII detection and manual redaction against the **raw
markdown source text** (the textarea value), not the rendered HTML. The
preview is only for display. Specifically:

- Auto-detect: runs `re.finditer()` on `textarea.value`. Findings store
  `start`/`end` offsets into that string.
- Manual redact: the user types or pastes the exact text to redact into a
  small input field next to the "Redact" button. We then use
  `str.find()` / `re.finditer(re.escape(selected))` to find all
  occurrences in the raw source and add them to the redaction list.

This avoids the HTML-to-source offset mapping problem entirely. The tradeoff
is that manual redaction is by substring match rather than by visual
selection. If visual selection is desired later, it can be added by
attaching `data-offset` attributes to spans in the rendered HTML.

**Alternative (visual selection)**: Render the raw markdown source into the
preview by splitting it into individual character spans or word spans, each
tagged with `data-start` and `data-end` attributes. Then
`window.getSelection()` can read the `data-start` of the first selected
node and `data-end` of the last to get the source offsets. This is more
complex but gives a better UX. Worth prototyping.

### Sample document

Pre-loaded sample for demonstration (medical record with fake PII):

```
# Patient Intake Note

**Patient:** Jane Smith (jane.smith@hospital.org)
**DOB:** 03/15/1987 **SSN:** 123-45-6789
**Phone:** (555) 867-5309

## Chief Complaint

Stage II hypertension. BP reading 145/92.
Prescribed lisinopril 10mg daily.

## Billing

Visa ending 4111-1111-1111-1111
Submitted from clinic terminal 192.168.1.42

## Follow-up

Contact john.doe@clinic.net or call +1 555.123.4567 to confirm.
```

### Open questions

1. **Manual redaction UX**: Substring input field (simple, reliable) vs.
   visual selection in preview (better UX, harder to implement). Start with
   substring input; add visual selection as an enhancement.

2. **Re-scan after edits**: If the user edits the textarea after scanning,
   the findings are stale. Should we auto-clear findings and require a
   re-scan? Or re-scan automatically on input? Recommend: show a warning
   "Source changed since last scan" and require manual re-scan.

3. **Markdown rendering in preview after redaction**: After submitting,
   placeholders like `[EMAIL]` appear in the markdown source. These render
   fine in markdown (they're just text). But should we style them
   distinctly in the final preview? Recommend: yes, wrap them in a
   `<code>` style for visual clarity.

4. **What if the same PII appears multiple times?** The `re.finditer()`
   approach finds all occurrences. Each one gets its own entry in the
   findings list. The user can uncheck individual occurrences.

### Enhancement: Ollama-assisted PII detection

Regex catches structured PII (emails, SSNs, phone numbers), but it cannot
catch contextual PII -- names ("Jane Smith", "Dr. Rodriguez"), locations
("the clinic on 5th Ave"), relationships ("the patient's mother"), ages,
job titles, or any other identifying detail that requires language
understanding.

A local LLM running in Ollama solves this. The data flow stays private:

```
Browser (Pyodide)                   Ollama (localhost:11434)
┌─────────────────────────┐         ┌────────────────────────┐
│                         │  fetch  │                        │
│  Raw text ──────────────────────> │  LLM identifies PII:   │
│                         │         │  names, locations,     │
│                         │         │  relationships, etc.   │
│  <────────────────────────────── │                        │
│  LLM findings added to  │         └────────────────────────┘
│  the same checkbox list  │
│  alongside regex hits    │
│                         │
│  User reviews all        │
│  findings (regex + LLM)  │
│                         │    traitlet
│  Submit ─────────────────────────────────> Kernel
└─────────────────────────┘
```

The sensitive text goes from browser to `localhost:11434` and back. It
never leaves the machine. No API key, no cloud.

#### How it works

Phase 2 (auto-detect) gains an additional "Scan with LLM" button alongside
the existing regex "Scan for PII" button. Clicking it:

1. Reads the raw text from the textarea.
2. Calls Ollama via `pyodide.http.pyfetch`:

   ```python
   from pyodide.http import pyfetch
   import json

   response = await pyfetch(
       "http://localhost:11434/api/generate",
       method="POST",
       headers={"Content-Type": "application/json"},
       body=json.dumps({
           "model": "llama3.2",
           "prompt": (
               "Identify all personally identifiable information (PII) in "
               "the following text. Return a JSON array of objects, each "
               "with 'type' (e.g. PERSON, LOCATION, ORGANIZATION, AGE, "
               "RELATIONSHIP) and 'value' (the exact text span).\n\n"
               f"Text:\n{raw_text}\n\nJSON:"
           ),
           "stream": False,
           "format": "json",
       }),
   )
   result = await response.json()
   ```

3. Parses the LLM's JSON response into findings.
4. For each LLM finding, locates the `value` substring in the raw text
   (using `str.find()` or `re.finditer(re.escape(value))`) to get
   `start`/`end` offsets.
5. Adds the LLM findings to the same `current_findings` list, tagged with
   their LLM-provided type (PERSON, LOCATION, etc.) and marked with a
   different color/style to distinguish from regex hits.
6. The findings list (checkboxes) and preview update to show both regex
   and LLM detections.

#### CORS configuration

Ollama's `OLLAMA_ORIGINS` defaults allow `localhost` origins. If the
notebook is served from a different origin (e.g. `notebook.link`,
`marimo.app`), the user must configure Ollama to allow it:

```bash
# macOS
launchctl setenv OLLAMA_ORIGINS "*"

# Linux (systemd)
sudo systemctl edit ollama
# Add: Environment="OLLAMA_ORIGINS=*"
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

The widget should detect CORS failures and show a helpful error message
with these instructions instead of a raw network error.

#### When Ollama is not running

This is an optional enhancement, not a requirement. The widget should
gracefully handle:

- Ollama not installed: "Scan with LLM" button shows a tooltip explaining
  the requirement. Regex scanning works independently.
- Ollama running but model not pulled: show the error from Ollama's
  response and suggest `ollama pull llama3.2`.
- CORS rejection: show configuration instructions (see above).
- Network timeout: show a retry option.

The regex-only flow must always work standalone. Ollama is additive.

#### Open questions (Ollama-specific)

1. **Which model?** `llama3.2` (3B) is a good default -- small, fast,
   capable enough for NER-style tasks. Should we allow the user to pick a
   model from a dropdown (populated by `GET /api/tags`)? Or keep it
   simple with a hardcoded default?

2. **Structured output reliability**: LLMs don't always return valid JSON.
   Ollama's `"format": "json"` helps but isn't bulletproof. Need a
   fallback parser that extracts findings even from malformed responses.

3. **Latency**: A 3B model on CPU may take 5-15 seconds for a page of
   text. Show a spinner/progress indicator. Consider streaming the
   response to show partial results.

4. **Async in event handler**: The pyfetch call is async. The "Scan with
   LLM" button handler needs `asyncio.ensure_future()` to schedule the
   coroutine from a sync click callback. This is the same pattern as
   the OpenAI example (documented in Open Questions / Risks). Needs
   testing in pywidget.

---

## Example 6: Interactive OpenCV Playground (webcam + browser-side CV)

### Concept

A teaching tool for computer vision. The widget accesses the webcam
directly in the browser, applies OpenCV filters in real-time via Pyodide,
and displays the processed feed in a single panel. Students see the effect
of `cv2.Canny`, `cv2.GaussianBlur`, `cv2.threshold`, etc. on their own
camera feed instantly. A snapshot button captures the current processed
frame and sends it to the kernel as a NumPy array for further exploration
in subsequent notebook cells.

**Use case**: You're writing a CV course or tutorial. Instead of loading
static images, students point their camera and see each OpenCV operation
live. They experiment with the filter bar, then snapshot a frame to
continue working with it as a regular NumPy array in the next cell --
histogram analysis, feature extraction, cascade classifiers, feeding into
sklearn, saving to disk, etc.

This is a direct evolution of [this 2018 blog post](https://medium.com/@kostal91/displaying-real-time-webcam-stream-in-ipython-at-relatively-high-framerate-8e67428ac522)
which fought IPython's display pipeline to show webcam frames at ~36 FPS
using a kernel-side `cv2.VideoCapture` -> PIL JPEG encode ->
`IPython.display` -> `clear_output` loop. pywidget eliminates the entire
kernel round trip:

```
2018 (kernel-side):
  webcam -> kernel (cv2.VideoCapture) -> PIL JPEG -> IPython.display -> clear -> repeat
  bottleneck: kernel <-> frontend network hop per frame

pywidget (browser-side):
  webcam -> <video> element (getUserMedia, browser-native)
       -> canvas.drawImage() captures a frame
       -> NumPy array (in Pyodide WASM)
       -> cv2 processing (in Pyodide WASM)
       -> render result to <img>
  bottleneck: WASM processing only. Zero network hops.
```

### Pyodide packages

- `opencv-python` (4.11.0, available in Pyodide)
- `numpy`
- `Pillow` (for JPEG encoding of processed frames)

### Traitlets (synced to kernel)

The live video stream stays browser-only. Only explicit user actions push
data to the kernel.

- `snapshot_b64 = Unicode("")` -- base64-encoded JPEG of the last captured
  processed frame, synced only when the user clicks "Snapshot"
- `filter_name = Unicode("none")` -- currently selected filter, synced so
  kernel can read which filter is active

### Browser APIs used

All accessed from Python via `from js import navigator, document`:

- `navigator.mediaDevices.getUserMedia({"video": True})` -- request webcam
  access (requires HTTPS or localhost; user sees a browser permission
  prompt)
- `HTMLVideoElement` -- receives the live camera stream (hidden element)
- `HTMLCanvasElement` + `getContext("2d")` -- captures individual frames
  from the video via `drawImage()`, provides `getImageData()` to read
  pixel data
- `setInterval` -- drives the processing loop at a target FPS

### Data flow

```
Browser (Pyodide WASM)
┌──────────────────────────────────────────────────────┐
│  getUserMedia()                                      │
│       │                                              │
│       v                                              │
│  <video> element (hidden, receives live stream)      │
│       │                                              │
│       v  (on each setInterval tick)                  │
│  <canvas>.drawImage(video) -- capture frame          │
│       │                                              │
│       v                                              │
│  getImageData() -> Uint8ClampedArray                 │
│       │                                              │
│       v                                              │
│  np.frombuffer(...).reshape(H, W, 4) -- RGBA array   │
│       │                                              │
│       v                                              │
│  cv2 filter (selected by user)                       │
│       │                                              │
│       v                                              │
│  PIL JPEG encode -> data:image/jpeg;base64 -> <img>  │
│                                                      │
│  [Snapshot] button ──> model.set("snapshot_b64")     │
│                        model.save_changes() ───────> │ Kernel
└──────────────────────────────────────────────────────┘
```

### Frame capture: getting pixels from video to NumPy

The critical path from `<video>` to a NumPy array:

```python
from js import navigator, document
import numpy as np

# One-time setup (in async render)
video = document.createElement("video")
stream = await navigator.mediaDevices.getUserMedia(to_js({"video": True}))
video.srcObject = stream
await video.play()

# Per-frame capture (in setInterval callback)
canvas = document.createElement("canvas")
canvas.width = video.videoWidth
canvas.height = video.videoHeight
ctx = canvas.getContext("2d")
ctx.drawImage(video, 0, 0)
image_data = ctx.getImageData(0, 0, canvas.width, canvas.height)

# Convert to numpy -- image_data.data is a Uint8ClampedArray (RGBA)
rgba = np.frombuffer(image_data.data.to_py(), dtype=np.uint8)
rgba = rgba.reshape((canvas.height, canvas.width, 4))
rgb = rgba[:, :, :3]  # drop alpha for OpenCV
```

**Performance concern**: `image_data.data.to_py()` copies pixel data from
JS to WASM memory. For a 640x480 frame that's ~1.2 MB per copy. This may
limit framerate. Possible mitigations:
- Default to 320x240 (300 KB per frame)
- When filter is "None" (passthrough), skip the NumPy path entirely and
  just draw the `<video>` element directly to a visible canvas with
  `drawImage()` -- no pixel copy needed
- Only enter the NumPy/OpenCV path when a filter is selected

### Processing filters

Button bar to select a filter. Each filter is a Python function taking an
RGB NumPy array and returning a processed array:

| Filter             | OpenCV call                                        | Visual effect                |
|--------------------|----------------------------------------------------|------------------------------|
| None (passthrough) | skip NumPy entirely, direct canvas draw             | Raw webcam feed              |
| Grayscale          | `cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)`          | Black & white                |
| Edge detection     | `cv2.Canny(gray, 100, 200)`                        | White edges on black         |
| Gaussian blur      | `cv2.GaussianBlur(frame, (15, 15), 0)`             | Soft focus                   |
| Threshold          | `cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)` | High-contrast B&W            |
| Cartoon            | bilateral filter + adaptive threshold + edges      | Cartoon/illustration look    |

### Rendering processed frames

Use JPEG encode + data URL (same proven pattern as Mandelbrot example and
the 2018 blog -- JPEG encoding is ~10x faster than PNG):

```python
from PIL import Image
import io, base64

img = Image.fromarray(processed_rgb)
buf = io.BytesIO()
img.save(buf, format="JPEG", quality=80)
data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
display_img.src = data_url
```

### UI layout

Single panel -- the feed with the effect applied. No side-by-side.

```
┌─────────────────────────────────────────────┐
│  Interactive OpenCV Playground               │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │                                     │    │
│  │   Camera feed with active filter    │    │
│  │   (single <img> or <canvas>)        │    │
│  │                                     │    │
│  │                                     │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  [None] [Gray] [Edges] [Blur] [Threshold]   │
│  [Cartoon]                                  │
│                                             │
│  [Start Camera]  [Snapshot to kernel]       │
│                                             │
│  FPS: 14.2  |  320x240                      │
└─────────────────────────────────────────────┘
```

### Interaction flow

1. Widget renders with a "Start Camera" button and the filter bar
   (disabled). No webcam access until user clicks (browsers require a
   user gesture for `getUserMedia`).
2. User clicks Start. Browser shows permission prompt. On approval, the
   live feed appears. Filter bar enables.
3. Processing loop begins via `setInterval`. Each tick: capture frame,
   apply selected filter, display result. FPS counter updates.
4. User clicks different filter buttons. The active filter changes
   immediately. The `filter_name` traitlet syncs to the kernel.
5. User clicks "Snapshot to kernel":
   - The current processed frame is encoded as base64 JPEG.
   - `model.set("snapshot_b64", data)` + `model.save_changes()`.
   - A brief flash/border effect confirms the capture.
6. On widget destroy, the stream is stopped (`stream.getTracks()` ->
   `track.stop()`) to release the camera.

### Kernel-side usage (the teaching payoff)

The widget gives you a frame. What you do with it is your notebook:

```python
# Cell 1: the widget
w = WebcamWidget()
w

# Cell 2: after clicking Snapshot
import numpy as np
from PIL import Image
import base64, io

img_bytes = base64.b64decode(w.snapshot_b64)
img = Image.open(io.BytesIO(img_bytes))
frame = np.array(img)

print(f"Captured: {frame.shape}")  # e.g. (240, 320, 3)

# Cell 3: continue with any CV/ML workflow
import cv2

# Histogram of color channels
for i, color in enumerate(("b", "g", "r")):
    hist = cv2.calcHist([frame], [i], None, [256], [0, 256])
    # ... plot with matplotlib, analyze, etc.

# Or: face detection, contour finding, color segmentation,
#     feeding into sklearn, saving to disk, etc.
```

### Async architecture

`getUserMedia()` returns a Promise, so the render function must be async:

```python
async def render(self, el, model):
    from js import navigator, document
    # ...
    stream = await navigator.mediaDevices.getUserMedia(...)
```

This works because the bridge (`_bridge.js:168-169`) awaits thenables
returned by render.

The frame processing loop uses `setInterval` with a `create_proxy`'d
callback. The callback is a regular sync function (captures one frame,
processes, displays -- no async needed per tick).

### Open questions

1. **Performance of `to_py()` / `to_js()` for pixel data**: The JS<->WASM
   memory copy is the likely bottleneck. Benchmark at 320x240 to
   determine achievable FPS. Passthrough mode (filter=None) should skip
   NumPy entirely and just use `drawImage` for maximum FPS.

2. **Default resolution**: Start at 320x240 for safety. Optionally offer a
   resolution toggle (320x240 / 640x480) if performance allows.

3. **HTTPS requirement**: `getUserMedia` requires a secure context (HTTPS
   or localhost). This works on notebook.link and marimo.app (both HTTPS)
   and on local Jupyter (localhost). Won't work on plain HTTP. The widget
   should detect `window.isSecureContext` and show a clear error.

4. **Permission denial**: If the user denies camera access, show a
   friendly message ("Camera access denied. Click the camera icon in your
   browser's address bar to allow it.") instead of a raw error.

5. **Cleanup on destroy**: The bridge's cleanup function
   (`_bridge.js:203`) destroys the Python namespace but the camera stream
   needs explicit stopping (`track.stop()`). Need to ensure this happens.
   Options: store the interval ID and stream reference, clear/stop in the
   cleanup return function. Verify the bridge cleanup runs reliably.

---

## Example 7: Interactive Matplotlib (SVG click interaction)

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
