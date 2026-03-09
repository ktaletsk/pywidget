# /// script
# requires-python = ">=3.10"
# dependencies = ["pywidget", "anywidget", "marimo>=0.20.4"]
# ///

import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(r"""
    # PII Scrubber

    A privacy-preserving widget for detecting and redacting Personally
    Identifiable Information (PII) from text documents.

    **Privacy guarantee:** Raw text lives _only_ in the browser (DOM / Pyodide
    WASM memory). The traitlet sync boundary **is** the privacy boundary —
    only sanitized text crosses to the Python kernel after you explicitly
    click **Submit**.

    ## How to use

    1. Edit or paste text into the left pane. A live Markdown preview appears on
       the right.
    2. Click **Scan for PII** to detect emails, phone numbers, SSNs, credit
       cards, and IP addresses with regex.
    3. _(Optional)_ Click **Scan with LLM** to ask a local Ollama model for
       additional PII (requires Ollama running on your machine — see below).
    4. _(Optional)_ Select text in the editor and click **Redact Selection** to
       manually flag all occurrences of that text.
    5. Uncheck any findings you want to keep.
    6. Click **Submit** — only the redacted text and a PII summary are sent to
       the kernel.

    ## LLM scan setup (Ollama)

    > **Important:** You must start Ollama with CORS origins enabled.
    > A normal `ollama serve` will **not** work — the browser blocks
    > cross-origin requests without the correct headers.
    >
    > ```bash
    > OLLAMA_ORIGINS=* ollama serve
    > ```
    >
    > This allows the widget (running in your browser) to reach the Ollama
    > API on `localhost:11434`. Your data never leaves your machine.

    ### Browser compatibility

    > If widget fails to find your ollama API, you need to disable adblocker or Brave Shields for the page
    """)
    return


@app.cell
def _():
    import json

    import marimo as mo
    import traitlets
    from pywidget import PyWidget

    return PyWidget, json, mo, traitlets


@app.cell
def _(PyWidget, create_proxy, mo, traitlets):
    class PIIScrubberWidget(PyWidget):
        _py_packages = ["markdown"]
        sanitized_text = traitlets.Unicode("").tag(sync=True)
        pii_summary_json = traitlets.Unicode("{}").tag(sync=True)

        async def render(self, el, model):
            import re, json, markdown, asyncio, textwrap
            from js import Blob, URL, Worker, Object, Promise

            # ----- Constants -----
            PII_PATTERNS = [
                {
                    "type": "EMAIL",
                    "pattern": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
                    "color": "#FFD700",
                    "placeholder": "[EMAIL]",
                },
                {
                    "type": "PHONE",
                    "pattern": r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
                    "color": "#87CEEB",
                    "placeholder": "[PHONE]",
                },
                {
                    "type": "SSN",
                    "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
                    "color": "#FF6B6B",
                    "placeholder": "[SSN]",
                },
                {
                    "type": "CREDIT_CARD",
                    "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
                    "color": "#DDA0DD",
                    "placeholder": "[CREDIT_CARD]",
                },
                {
                    "type": "IP_ADDR",
                    "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                    "color": "#98FB98",
                    "placeholder": "[IP_ADDRESS]",
                },
            ]

            MANUAL_COLOR = "#D3D3D3"
            MANUAL_PLACEHOLDER = "[REDACTED]"

            SAMPLE_DOCUMENT = textwrap.dedent("""\
                # Patient Intake Form

                **Patient:** John Smith
                **DOB:** 03/15/1985
                **SSN:** 123-45-6789

                ## Contact Information

                - Email: john.smith@example.com
                - Phone: (555) 867-5309
                - Secondary Phone: +1-555-123-4567
                - Address: 742 Evergreen Terrace, Springfield, IL 62704

                ## Insurance

                - Provider: BlueCross BlueShield
                - Policy Number: BCB-9876543
                - Credit Card on File: 4532 1234 5678 9012

                ## Medical History

                Patient was referred by Dr. Sarah Johnson (sarah.johnson@hospital.org)
                from Memorial Hospital (IP: 192.168.1.100).

                Previous records transferred from clinic at 10.0.0.42.

                Emergency contact: Jane Smith, (555) 234-5678, jane.smith@email.com

                ## Notes

                Patient SSN verified: 123-45-6789. Secondary ID credit card:
                4111-1111-1111-1111. Billing sent to john.smith@example.com.
            """)

            # ----- Helper: ollama_fetch (Web Worker bypass for Colab SW) -----
            async def ollama_fetch(url, method="GET", body=None):
                """Fetch via a disposable Web Worker.

                Google Colab's service worker intercepts all localhost HTTP
                requests from the main thread and returns a fake 500.  A
                blob-URL Web Worker is not controlled by that SW, so fetch()
                inside it reaches the real localhost Ollama server.
                """
                worker_code = (
                    "self.onmessage = async function(e) {\n"
                    "  try {\n"
                    "    const opts = {method: e.data.method || 'GET'};\n"
                    "    if (e.data.body) {\n"
                    "      opts.body = e.data.body;\n"
                    "      opts.headers = {'Content-Type': 'application/json'};\n"
                    "    }\n"
                    "    const resp = await fetch(e.data.url, opts);\n"
                    "    const text = await resp.text();\n"
                    "    self.postMessage({ok: true, status: resp.status, body: text});\n"
                    "  } catch(err) {\n"
                    "    self.postMessage({ok: false, error: err.message});\n"
                    "  }\n"
                    "};\n"
                )
                blob = Blob.new(
                    to_js([worker_code]),
                    to_js({"type": "application/javascript"}, dict_converter=Object.fromEntries),
                )
                wurl = URL.createObjectURL(blob)
                worker = Worker.new(wurl)
                try:
                    def executor(resolve, reject):
                        def on_msg(e):
                            resolve(e.data)
                        def on_err(e):
                            reject(e)
                        worker.onmessage = create_proxy(on_msg)
                        worker.onerror = create_proxy(on_err)
                        msg = {"url": url, "method": method}
                        if body is not None:
                            msg["body"] = body
                        worker.postMessage(to_js(msg, dict_converter=Object.fromEntries))
                    result = await Promise.new(create_proxy(executor))
                    if not result.ok:
                        raise Exception(str(result.error))
                    return json.loads(str(result.body))
                finally:
                    worker.terminate()
                    URL.revokeObjectURL(wurl)

            # ----- Closure State -----
            state = {
                "phase": "edit",
                "current_findings": [],
                "scan_text_snapshot": "",
            }

            # ----- Color lookup -----
            def color_for_type(t):
                for p in PII_PATTERNS:
                    if p["type"] == t:
                        return p["color"]
                if t == "MANUAL":
                    return MANUAL_COLOR
                return "#ccc"

            def placeholder_for_type(t):
                for p in PII_PATTERNS:
                    if p["type"] == t:
                        return p["placeholder"]
                if t == "MANUAL":
                    return MANUAL_PLACEHOLDER
                return "[REDACTED]"

            # ----- Build initial DOM -----
            legend_items = "".join(
                f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px;">'
                f'<span style="display:inline-block;width:14px;height:14px;background:{p["color"]};'
                f'border-radius:2px;border:1px solid #aaa;"></span>'
                f'<span style="font-size:12px;">{p["type"]}</span></span>'
                for p in PII_PATTERNS
            )
            legend_items += (
                f'<span style="display:inline-flex;align-items:center;gap:4px;">'
                f'<span style="display:inline-block;width:14px;height:14px;background:{MANUAL_COLOR};'
                f'border-radius:2px;border:1px solid #aaa;"></span>'
                f'<span style="font-size:12px;">MANUAL</span></span>'
            )

            el.innerHTML = f"""
            <div style="font-family:sans-serif;">
                <div style="background:#2d5016;color:white;padding:8px 14px;border-radius:6px;
                            margin-bottom:10px;font-size:13px;">
                    🔒 <strong>Privacy mode:</strong> Raw text stays in the browser.
                    Only redacted output is sent to the kernel on Submit.
                </div>

                <div style="display:flex;flex-wrap:wrap;align-items:center;gap:4px;
                            margin-bottom:10px;padding:6px 10px;background:#f8f8f8;
                            border-radius:4px;border:1px solid #e0e0e0;">
                    {legend_items}
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:10px;">
                    <div>
                        <div style="font-size:12px;font-weight:600;margin-bottom:4px;color:#555;">
                            INPUT
                            <span id="input-hint" style="font-weight:400;color:#999;margin-left:6px;">
                                select text + click Redact
                            </span>
                        </div>
                        <textarea id="pii-textarea"
                            style="width:100%;height:400px;font-family:monospace;font-size:13px;
                                   padding:10px;border:1px solid #ccc;border-radius:4px;
                                   resize:vertical;box-sizing:border-box;"
                        ></textarea>
                    </div>
                    <div>
                        <div style="font-size:12px;font-weight:600;margin-bottom:4px;color:#555;">
                            PREVIEW
                        </div>
                        <div id="pii-preview"
                            style="width:100%;height:400px;overflow-y:auto;padding:10px;
                                   border:1px solid #ccc;border-radius:4px;font-size:13px;
                                   box-sizing:border-box;background:#fafafa;">
                        </div>
                    </div>
                </div>

                <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px;">
                    <button id="scan-btn"
                        style="padding:8px 16px;font-size:13px;cursor:pointer;border:1px solid #ccc;
                               border-radius:4px;background:#e8f0fe;font-weight:600;">
                        Scan for PII
                    </button>
                    <button id="scan-llm-btn"
                        style="padding:8px 16px;font-size:13px;cursor:pointer;border:1px solid #ccc;
                               border-radius:4px;background:#f0e8fe;">
                        Scan with LLM
                    </button>
                    <select id="ollama-model"
                        style="padding:7px 10px;font-size:13px;border:1px solid #ccc;
                               border-radius:4px;background:white;">
                        <option value="">Loading models...</option>
                    </select>
                    <span style="color:#999;">|</span>
                    <button id="redact-btn"
                        style="padding:8px 16px;font-size:13px;cursor:pointer;border:1px solid #ccc;
                               border-radius:4px;background:#fff3e0;">
                        Redact Selection
                    </button>
                    <span style="color:#999;">|</span>
                    <button id="submit-btn"
                        style="padding:8px 16px;font-size:13px;cursor:pointer;border:1px solid #ccc;
                               border-radius:4px;background:#c8e6c9;font-weight:600;">
                        Submit
                    </button>
                </div>

                <div id="stale-warning"
                    style="display:none;background:#fff3cd;border:1px solid #ffc107;color:#856404;
                           padding:8px 12px;border-radius:4px;margin-bottom:10px;font-size:13px;">
                    ⚠️ Text has changed since last scan. Please re-scan before submitting.
                </div>

                <div id="findings-list" style="margin-bottom:10px;"></div>

                <div id="report-summary" style="margin-bottom:10px;"></div>

                <div id="status-msg" style="font-size:13px;color:#555;"></div>
            </div>
            """

            # Set sample text
            textarea = el.querySelector("#pii-textarea")
            textarea.value = SAMPLE_DOCUMENT

            # ----- Helper: render_preview -----
            def render_preview():
                preview = el.querySelector("#pii-preview")
                raw_text = el.querySelector("#pii-textarea").value

                if state["phase"] == "edit":
                    # Markdown preview
                    html = markdown.markdown(raw_text)
                    preview.innerHTML = f'<div style="line-height:1.5;">{html}</div>'

                elif state["phase"] == "scanned":
                    # Highlighted preview with <mark> tags
                    # Collect checked findings sorted by start
                    checked = [f for f in state["current_findings"] if f["checked"]]
                    checked.sort(key=lambda f: f["start"])

                    # Merge overlapping spans
                    merged = []
                    for f in checked:
                        if merged and f["start"] <= merged[-1]["end"]:
                            last = merged[-1]
                            if f["end"] > last["end"]:
                                last["end"] = f["end"]
                                last["type"] = f["type"]
                                last["color"] = f["color"]
                        else:
                            merged.append({
                                "start": f["start"],
                                "end": f["end"],
                                "type": f["type"],
                                "color": f["color"],
                            })

                    # Build highlighted text
                    parts = []
                    last_end = 0
                    for m in merged:
                        if m["start"] > last_end:
                            # Escape HTML in plain text segments
                            seg = raw_text[last_end:m["start"]]
                            seg = seg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            parts.append(seg)
                        marked = raw_text[m["start"]:m["end"]]
                        marked = marked.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        parts.append(
                            f'<mark style="background:{m["color"]};padding:1px 3px;'
                            f'border-radius:2px;" title="{m["type"]}">{marked}</mark>'
                        )
                        last_end = m["end"]
                    if last_end < len(raw_text):
                        seg = raw_text[last_end:]
                        seg = seg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        parts.append(seg)

                    preview.innerHTML = (
                        '<div style="white-space:pre-wrap;font-family:monospace;'
                        'font-size:13px;line-height:1.5;">'
                        + "".join(parts)
                        + "</div>"
                    )

                elif state["phase"] == "submitted":
                    # Show sanitized text with styled placeholders
                    sanitized = model.get("sanitized_text")
                    # Style placeholder tokens
                    display = sanitized
                    for p in PII_PATTERNS:
                        escaped = p["placeholder"].replace("[", "\\[").replace("]", "\\]")
                        display = re.sub(
                            escaped,
                            f'<code style="background:{p["color"]};padding:1px 4px;'
                            f'border-radius:3px;font-size:12px;">{p["placeholder"]}</code>',
                            display,
                        )
                    manual_escaped = MANUAL_PLACEHOLDER.replace("[", "\\[").replace("]", "\\]")
                    display = re.sub(
                        manual_escaped,
                        f'<code style="background:{MANUAL_COLOR};padding:1px 4px;'
                        f'border-radius:3px;font-size:12px;">{MANUAL_PLACEHOLDER}</code>',
                        display,
                    )
                    html = markdown.markdown(display)
                    preview.innerHTML = f'<div style="line-height:1.5;">{html}</div>'

            # ----- Helper: render_findings_list -----
            def render_findings_list():
                container = el.querySelector("#findings-list")
                findings = state["current_findings"]
                if not findings:
                    container.innerHTML = ""
                    return

                items = []
                for i, f in enumerate(findings):
                    checked_attr = "checked" if f["checked"] else ""
                    val_display = f["value"]
                    if len(val_display) > 40:
                        val_display = val_display[:37] + "..."
                    val_display = val_display.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    items.append(
                        f'<label style="display:flex;align-items:center;gap:6px;padding:3px 0;'
                        f'font-size:13px;cursor:pointer;">'
                        f'<input type="checkbox" data-idx="{i}" {checked_attr} '
                        f'style="cursor:pointer;" />'
                        f'<span style="display:inline-block;padding:1px 6px;border-radius:3px;'
                        f'font-size:11px;font-weight:600;background:{f["color"]};'
                        f'color:#333;">{f["type"]}</span>'
                        f'<span style="font-family:monospace;">{val_display}</span>'
                        f'</label>'
                    )

                container.innerHTML = (
                    '<div style="border:1px solid #e0e0e0;border-radius:4px;padding:8px 12px;'
                    'max-height:200px;overflow-y:auto;">'
                    f'<div style="font-size:12px;font-weight:600;color:#555;margin-bottom:6px;">'
                    f'Findings ({len(findings)})</div>'
                    + "".join(items)
                    + "</div>"
                )

                # Re-attach checkbox listeners
                for cb in container.querySelectorAll("input[type=checkbox]"):
                    def on_check(event, _cb=cb):
                        idx = int(_cb.getAttribute("data-idx"))
                        state["current_findings"][idx]["checked"] = _cb.checked
                        render_preview()
                    cb.addEventListener("change", create_proxy(on_check))

            # ----- Helper: update_button_states -----
            def update_button_states():
                scan_btn = el.querySelector("#scan-btn")
                llm_btn = el.querySelector("#scan-llm-btn")
                redact_btn = el.querySelector("#redact-btn")
                submit_btn = el.querySelector("#submit-btn")

                phase = state["phase"]
                if phase == "edit":
                    scan_btn.disabled = False
                    llm_btn.disabled = False
                    redact_btn.disabled = False
                    submit_btn.disabled = True
                elif phase == "scanned":
                    scan_btn.disabled = False
                    llm_btn.disabled = False
                    redact_btn.disabled = False
                    submit_btn.disabled = len(state["current_findings"]) == 0
                elif phase == "submitted":
                    scan_btn.disabled = True
                    llm_btn.disabled = True
                    redact_btn.disabled = True
                    submit_btn.disabled = True

                # Visual disabled style
                for btn in [scan_btn, llm_btn, redact_btn, submit_btn]:
                    if btn.disabled:
                        btn.style.opacity = "0.5"
                        btn.style.cursor = "not-allowed"
                    else:
                        btn.style.opacity = "1"
                        btn.style.cursor = "pointer"

            # ----- Helper: perform_scan -----
            def perform_scan():
                raw_text = el.querySelector("#pii-textarea").value
                new_findings = []

                for pat in PII_PATTERNS:
                    for m in re.finditer(pat["pattern"], raw_text):
                        # Skip if duplicate of existing finding
                        dup = False
                        for existing in state["current_findings"]:
                            if m.start() == existing["start"] and m.end() == existing["end"]:
                                dup = True
                                break
                        if not dup:
                            new_findings.append({
                                "type": pat["type"],
                                "value": m.group(),
                                "start": m.start(),
                                "end": m.end(),
                                "color": pat["color"],
                                "checked": True,
                            })

                if new_findings:
                    state["current_findings"].extend(new_findings)
                    state["current_findings"].sort(key=lambda f: f["start"])

                state["phase"] = "scanned"
                state["scan_text_snapshot"] = raw_text

                el.querySelector("#stale-warning").style.display = "none"
                el.querySelector("#status-msg").innerHTML = (
                    f'<span style="color:#2e7d32;">Regex scan: {len(new_findings)} new item(s) '
                    f'({len(state["current_findings"])} total).</span>'
                )

                render_preview()
                render_findings_list()
                update_button_states()

            # ----- Helper: perform_manual_redact -----
            def perform_manual_redact():
                ta = el.querySelector("#pii-textarea")
                sel_start = ta.selectionStart
                sel_end = ta.selectionEnd

                if sel_start is None or sel_end is None or sel_start == sel_end:
                    el.querySelector("#status-msg").innerHTML = (
                        '<span style="color:#e65100;">Select text in the editor first, then click Redact Selection.</span>'
                    )
                    return

                raw_text = ta.value
                selected_text = raw_text[sel_start:sel_end]

                # Find all occurrences of the selected text
                new_findings = []
                for m in re.finditer(re.escape(selected_text), raw_text):
                    dup = False
                    for existing in state["current_findings"]:
                        if m.start() == existing["start"] and m.end() == existing["end"]:
                            dup = True
                            break
                    if not dup:
                        new_findings.append({
                            "type": "MANUAL",
                            "value": m.group(),
                            "start": m.start(),
                            "end": m.end(),
                            "color": MANUAL_COLOR,
                            "checked": True,
                        })

                if new_findings:
                    state["current_findings"].extend(new_findings)
                    state["current_findings"].sort(key=lambda f: f["start"])
                    display = selected_text if len(selected_text) <= 30 else selected_text[:27] + "..."
                    el.querySelector("#status-msg").innerHTML = (
                        f'<span style="color:#2e7d32;">Redacted "{display}" '
                        f'({len(new_findings)} occurrence(s), '
                        f'{len(state["current_findings"])} total).</span>'
                    )
                else:
                    el.querySelector("#status-msg").innerHTML = (
                        '<span style="color:#e65100;">Selection already flagged.</span>'
                    )

                state["phase"] = "scanned"
                state["scan_text_snapshot"] = raw_text

                render_preview()
                render_findings_list()
                update_button_states()

            # ----- Helper: perform_submit -----
            def perform_submit():
                raw_text = el.querySelector("#pii-textarea").value
                checked = [f for f in state["current_findings"] if f["checked"]]

                # Merge overlapping spans
                checked.sort(key=lambda f: f["start"])
                merged = []
                for f in checked:
                    if merged and f["start"] <= merged[-1]["end"]:
                        last = merged[-1]
                        if f["end"] > last["end"]:
                            last["end"] = f["end"]
                            last["type"] = f["type"]
                    else:
                        merged.append(dict(f))

                # Apply replacements in reverse order
                result = raw_text
                counts = {}
                for f in reversed(merged):
                    ph = placeholder_for_type(f["type"])
                    result = result[:f["start"]] + ph + result[f["end"]:]
                    counts[f["type"]] = counts.get(f["type"], 0) + 1

                model.set("sanitized_text", result)
                model.set("pii_summary_json", json.dumps(counts))
                model.save_changes()

                state["phase"] = "submitted"

                el.querySelector("#status-msg").innerHTML = (
                    '<span style="color:#2e7d32;font-weight:600;">'
                    '✓ Submitted! Sanitized text sent to kernel.</span>'
                )
                el.querySelector("#report-summary").innerHTML = (
                    '<div style="padding:8px 12px;background:#e8f5e9;border-radius:4px;'
                    'border:1px solid #a5d6a7;font-size:13px;">'
                    f'<strong>Redacted:</strong> {json.dumps(counts)}</div>'
                )

                render_preview()
                render_findings_list()
                update_button_states()

            # ----- Helper: fetch_ollama_models -----
            async def fetch_ollama_models():
                select = el.querySelector("#ollama-model")
                try:
                    data = await ollama_fetch("http://localhost:11434/api/tags")
                    models = data.get("models", [])
                    if not models:
                        select.innerHTML = '<option value="">No models found</option>'
                        return
                    options = ""
                    for m in models:
                        name = m.get("name", "")
                        options += f'<option value="{name}">{name}</option>'
                    select.innerHTML = options
                except Exception:
                    select.innerHTML = '<option value="">Ollama not available</option>'

            # ----- Helper: ollama_scan -----
            async def ollama_scan():
                raw_text = el.querySelector("#pii-textarea").value
                status = el.querySelector("#status-msg")

                selected_model = el.querySelector("#ollama-model").value
                if not selected_model:
                    status.innerHTML = (
                        '<span style="color:#e65100;">No Ollama model selected.</span>'
                    )
                    return

                status.innerHTML = (
                    f'<span style="color:#1565c0;">⏳ Querying {selected_model}...</span>'
                )

                try:
                    prompt = (
                        "Analyze the following text and return ONLY a JSON array of PII items found. "
                        "Each item should have 'type' (one of: NAME, ADDRESS, DATE_OF_BIRTH, "
                        "MEDICAL_INFO, POLICY_NUMBER, or OTHER) and 'value' (the exact text). "
                        "Do not include emails, phones, SSNs, credit cards, or IP addresses "
                        "(those are handled separately). Return ONLY the JSON array, no other text.\n\n"
                        f"Text:\n{raw_text}"
                    )

                    data = await ollama_fetch(
                        "http://localhost:11434/api/generate",
                        method="POST",
                        body=json.dumps({
                            "model": selected_model,
                            "prompt": prompt,
                            "stream": False,
                        }),
                    )

                    response_text = data.get("response", "")

                    # Extract JSON array from response
                    array_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                    if not array_match:
                        status.innerHTML = (
                            '<span style="color:#e65100;">LLM returned no structured findings.</span>'
                        )
                        return

                    items = json.loads(array_match.group())

                    new_findings = []
                    for item in items:
                        val = item.get("value", "")
                        pii_type = item.get("type", "OTHER")
                        # Find all occurrences in raw text
                        for m in re.finditer(re.escape(val), raw_text):
                            # Skip if overlapping with existing finding
                            dup = False
                            for existing in state["current_findings"]:
                                if (m.start() < existing["end"] and m.end() > existing["start"]):
                                    dup = True
                                    break
                            if not dup:
                                new_findings.append({
                                    "type": pii_type,
                                    "value": val,
                                    "start": m.start(),
                                    "end": m.end(),
                                    "color": "#FFA726",
                                    "checked": True,
                                })

                    if new_findings:
                        state["current_findings"].extend(new_findings)
                        state["current_findings"].sort(key=lambda f: f["start"])

                    state["phase"] = "scanned"
                    state["scan_text_snapshot"] = raw_text

                    if new_findings:
                        status.innerHTML = (
                            f'<span style="color:#2e7d32;">LLM scan: {len(new_findings)} new item(s) '
                            f'({len(state["current_findings"])} total).</span>'
                        )
                    else:
                        status.innerHTML = (
                            '<span style="color:#555;">LLM found no additional PII.</span>'
                        )

                    render_preview()
                    render_findings_list()
                    update_button_states()

                except Exception as e:
                    err = str(e)
                    if "Failed to fetch" in err or "NetworkError" in err:
                        status.innerHTML = (
                            '<span style="color:#c62828;">'
                            'Could not connect to Ollama. Make sure it is running: '
                            '<code>OLLAMA_ORIGINS=* ollama serve</code></span>'
                        )
                    elif "CORS" in err:
                        status.innerHTML = (
                            '<span style="color:#c62828;">'
                            'CORS error. Set <code>OLLAMA_ORIGINS=*</code> when starting Ollama.</span>'
                        )
                    elif "model" in err.lower() and "not found" in err.lower():
                        status.innerHTML = (
                            '<span style="color:#c62828;">'
                            f'Model not found. Run: <code>ollama pull {selected_model}</code></span>'
                        )
                    else:
                        status.innerHTML = (
                            f'<span style="color:#c62828;">LLM error: {err}</span>'
                        )

            # ----- Event Listeners -----

            # Textarea input: live preview + stale detection
            def on_textarea_input(event):
                render_preview()
                if state["phase"] == "scanned":
                    current_text = el.querySelector("#pii-textarea").value
                    if current_text != state["scan_text_snapshot"]:
                        el.querySelector("#stale-warning").style.display = "block"
                        state["phase"] = "edit"
                        state["current_findings"] = []
                        el.querySelector("#findings-list").innerHTML = ""
                        update_button_states()

            textarea.addEventListener("input", create_proxy(on_textarea_input))

            # Scan button
            def on_scan(event):
                perform_scan()
            el.querySelector("#scan-btn").addEventListener("click", create_proxy(on_scan))

            # LLM scan button
            def on_llm_scan(event):
                asyncio.ensure_future(ollama_scan())
            el.querySelector("#scan-llm-btn").addEventListener("click", create_proxy(on_llm_scan))

            # Manual redact button
            def on_redact(event):
                perform_manual_redact()
            el.querySelector("#redact-btn").addEventListener("click", create_proxy(on_redact))

            # Submit button
            def on_submit(event):
                perform_submit()
            el.querySelector("#submit-btn").addEventListener("click", create_proxy(on_submit))

            # ----- Initial render -----
            render_preview()
            update_button_states()
            asyncio.ensure_future(fetch_ollama_models())

    w = mo.ui.anywidget(PIIScrubberWidget())
    w
    return (w,)


@app.cell
def _(json, mo, w):
    mo.stop(not w.widget.sanitized_text)
    summary = json.loads(w.widget.pii_summary_json)
    summary_parts = [f"**{k}:** {v}" for k, v in summary.items()]
    mo.md(f"""
    ## Sanitized Output

    **PII Summary:** {", ".join(summary_parts) if summary_parts else "None"}

    ```
    {w.widget.sanitized_text}
    ```
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
