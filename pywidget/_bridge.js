/**
 * pywidget bridge ESM
 *
 * This module is loaded by anywidget's standard ESM machinery. It routes the
 * anywidget lifecycle hooks (initialize, render) through a shared Pyodide
 * instance, executing the user's Python rendering code in the browser.
 *
 * Architecture:
 * - One Pyodide instance per page (singleton, ~11 MB WASM download)
 * - One isolated Python namespace (dict) per widget view
 * - Model API proxied from JS to Python with automatic type conversion
 */

// ---------------------------------------------------------------------------
// Pyodide singleton
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
			// Convert JS values to Python-native types. Primitives (int, str, bool)
			// pass through transparently; complex types (arrays, objects) are
			// deep-converted so Python code gets list/dict, not JsProxy.
			try {
				return pyodide.toPy(val);
			} catch {
				return val;
			}
		},
		set(key, value) {
			// Convert Python objects back to JS. PyProxy objects have .toJs();
			// primitives are auto-converted by Pyodide FFI.
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
		send(msg) {
			const jsMsg = msg && typeof msg.toJs === "function" ? msg.toJs() : msg;
			model.send(jsMsg);
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
// Lifecycle hooks (consumed by anywidget Runtime)
// ---------------------------------------------------------------------------

export default {
	async initialize({ model }) {
		// Kick off Pyodide loading without awaiting. CRITICAL: anywidget's
		// Runtime has a 2-second timeout on initialize() (widget.js:372).
		// Pyodide cold-start takes 3-5 seconds, so we must not block here.
		ensurePyodide();
	},

	async render({ model, el }) {
		const pyodide = await ensurePyodide();

		// --- Install packages (idempotent; cached by micropip after first install) ---
		const packages = model.get("_py_packages") || [];
		if (packages.length > 0) {
			el.innerHTML =
				'<div style="padding:8px;color:#666;font-style:italic">' +
				"Installing packages: " +
				packages.join(", ") +
				"...</div>";
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
			el.innerHTML =
				'<div style="padding:8px;color:#999">No <code>_py_render</code> code provided.</div>';
			return;
		}

		// --- Create isolated namespace for this widget view ---
		// Each view gets its own Python dict as globals, preventing pollution
		// between multiple widget instances or multiple views of the same widget.
		const ns = pyodide.toPy({});

		// Inject helpers into the namespace:
		// - create_proxy: prevents GC of Python callbacks passed to JS (e.g., addEventListener)
		// - to_js: explicit conversion of Python objects to JS when needed
		// - console: access to browser console from Python
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

		// --- Execute user's Python code (defines render/update functions) ---
		try {
			await pyodide.runPythonAsync(pyCode, { globals: ns });
		} catch (err) {
			showError(el, "Error in _py_render code", err.message);
			ns.destroy();
			return;
		}

		// Clear any loading indicators
		el.innerHTML = "";

		// --- Create the model proxy ---
		const proxy = createModelProxy(model, pyodide);

		// --- Call the user's render(el, model) function ---
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

		// --- Wire up the optional update(el, model) function ---
		const updateFn = ns.get("update");
		if (updateFn) {
			// Listen for any model state change. The listener inherits the view's
			// context from model_proxy (set in widget.js create_view), so it is
			// automatically cleaned up when the view is destroyed.
			model.on("change", () => {
				try {
					const result = updateFn(el, proxy);
					if (result && typeof result.then === "function") {
						result.catch((e) => console.error("[pywidget] update() error:", e));
					}
				} catch (err) {
					console.error("[pywidget] update() error:", err);
				}
			});
		}

		// --- Return cleanup function (called on view destroy or ESM hot update) ---
		return () => {
			ns.destroy();
		};
	},
};
