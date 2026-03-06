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
