/**
 * pywidget bridge for MyST Markdown
 *
 * This is an anywidget-compatible ESM that loads Pyodide in the browser and
 * executes user-supplied Python rendering code. It enables pywidget-style
 * "pure Python" widgets inside static MyST sites — no kernel required.
 *
 * Usage in MyST Markdown:
 *
 *   ```{anywidget} ./pywidget-bridge.mjs
 *   {
 *     "_py_render": "def render(el, model):\n    el.innerHTML = '<h1>Hello from Pyodide!</h1>'"
 *   }
 *   ```
 *
 * Model keys consumed:
 *   _py_render    — Python source defining render(el, model) and optionally update(el, model)
 *   _py_packages  — (optional) list of package names to install via micropip
 */

// ---------------------------------------------------------------------------
// Pyodide singleton (one per page, ~11 MB WASM download on first load)
// ---------------------------------------------------------------------------

let _pyodideReady = null;

function ensurePyodide() {
  if (!_pyodideReady) {
    _pyodideReady = (async () => {
      const { loadPyodide } = await import(
        /* webpackIgnore: true */
        /* @vite-ignore */
        "https://cdn.jsdelivr.net/pyodide/v0.27.5/full/pyodide.mjs"
      );
      const pyodide = await loadPyodide();
      await pyodide.loadPackage("micropip");
      return pyodide;
    })();
  }
  return _pyodideReady;
}

// ---------------------------------------------------------------------------
// Model proxy: bridges anywidget model API to Python-friendly interface
// ---------------------------------------------------------------------------

function createModelProxy(model, pyodide) {
  return {
    get(key) {
      const val = model.get(key);
      try {
        return pyodide.toPy(val);
      } catch {
        return val;
      }
    },
    set(key, value) {
      const jsVal =
        value && typeof value.toJs === "function" ? value.toJs() : value;
      model.set(key, jsVal);
    },
    save_changes() {
      model.save_changes();
    },
    on(event, callback) {
      model.on(event, callback);
    },
    off(event, callback) {
      model.off(event, callback);
    },
  };
}

// ---------------------------------------------------------------------------
// Error display helper
// ---------------------------------------------------------------------------

const ERROR_STYLE =
  "color:#c00;white-space:pre-wrap;font-family:monospace;font-size:13px;" +
  "padding:12px;margin:0;background:#fff0f0;border:1px solid #fcc;" +
  "border-radius:4px;overflow-x:auto;";

function showError(el, title, message) {
  el.innerHTML = `<pre style="${ERROR_STYLE}"><strong>${title}</strong>\n${message}</pre>`;
}

// ---------------------------------------------------------------------------
// Lifecycle hooks (anywidget spec, consumed by MyST widget runtime)
// ---------------------------------------------------------------------------

export default {
  async render({ model, el }) {
    // Show a loading indicator while Pyodide boots
    el.innerHTML =
      '<div style="padding:12px;color:#666;font-family:sans-serif;font-style:italic">' +
      "Loading Pyodide (~11 MB)…</div>";

    const pyodide = await ensurePyodide();

    // --- Install packages ---
    const packages = model.get("_py_packages") || [];
    if (packages.length > 0) {
      el.innerHTML =
        '<div style="padding:8px;color:#666;font-style:italic">' +
        "Installing packages: " +
        packages.join(", ") +
        "…</div>";
      try {
        const micropip = pyodide.pyimport("micropip");
        await micropip.install(packages);
      } catch (err) {
        showError(el, "Package install error", err.message);
        return;
      }
    }

    // --- Get user's Python code ---
    const pyCode = model.get("_py_render");
    if (!pyCode) {
      showError(
        el,
        "Missing _py_render",
        'Provide a "_py_render" key in the widget JSON body containing Python code ' +
          "that defines render(el, model).",
      );
      return;
    }

    // --- Create isolated namespace ---
    const ns = pyodide.toPy({});

    try {
      await pyodide.runPythonAsync(
        "from pyodide.ffi import create_proxy, to_js\nfrom js import console, document",
        { globals: ns },
      );
    } catch (err) {
      showError(el, "pywidget setup error", err.message);
      ns.destroy();
      return;
    }

    // --- Execute user's Python code ---
    try {
      await pyodide.runPythonAsync(pyCode, { globals: ns });
    } catch (err) {
      showError(el, "Error in _py_render code", err.message);
      ns.destroy();
      return;
    }

    // Clear loading indicator
    el.innerHTML = "";

    // --- Create the model proxy ---
    const proxy = createModelProxy(model, pyodide);

    // --- Call render(el, model) ---
    const renderFn = ns.get("render");
    if (renderFn) {
      try {
        const result = renderFn(el, proxy);
        if (result && typeof result.then === "function") await result;
      } catch (err) {
        showError(el, "render() error", err.message);
        return;
      }
    } else {
      showError(
        el,
        "Missing render function",
        '_py_render code must define a "render(el, model)" function.',
      );
      ns.destroy();
      return;
    }

    // --- Wire up optional update(el, model) ---
    const updateFn = ns.get("update");
    if (updateFn) {
      model.on("change", () => {
        try {
          const result = updateFn(el, proxy);
          if (result && typeof result.then === "function") {
            result.catch((e) =>
              console.error("[pywidget] update() error:", e),
            );
          }
        } catch (err) {
          console.error("[pywidget] update() error:", err);
        }
      });
    }

    // --- Cleanup ---
    return () => {
      ns.destroy();
    };
  },
};
