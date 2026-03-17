---
title: pywidget in MyST
subtitle: Pure Python widgets running in the browser via Pyodide
---

# pywidget + MyST

This page demonstrates **pywidget** rendering logic running inside a MyST
site — no Python kernel required. The Python code executes in the browser
via [Pyodide](https://pyodide.org/) (CPython compiled to WebAssembly).

:::{note}
First load takes 3-5 seconds while Pyodide downloads (~11 MB WASM).
Subsequent widgets on the same page render instantly.
:::

## Example 1: Hello World

A minimal widget that renders static HTML from Python.

```{code-block} python
def render(el, model):
    el.innerHTML = """
    <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px; color: white; font-family: sans-serif;">
        <h2 style="margin: 0 0 8px 0;">Hello from Pyodide!</h2>
        <p style="margin: 0; opacity: 0.9;">
            This HTML was rendered by Python running in your browser via WebAssembly.
        </p>
    </div>
    """
```

```{anywidget} https://cdn.jsdelivr.net/npm/pywidget-bridge@0.1.1/pywidget-bridge.mjs
{
  "_py_render": "def render(el, model):\n    el.innerHTML = \"\"\"\n    <div style=\"padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n                border-radius: 12px; color: white; font-family: sans-serif;\">\n        <h2 style=\"margin: 0 0 8px 0;\">Hello from Pyodide!</h2>\n        <p style=\"margin: 0; opacity: 0.9;\">\n            This HTML was rendered by Python running in your browser via WebAssembly.\n        </p>\n    </div>\n    \"\"\""
}
```

## Example 2: Interactive Counter

A button that tracks clicks using the widget model for state.

```{code-block} python
def render(el, model):
    from js import document

    container = document.createElement('div')
    container.style.fontFamily = 'sans-serif'
    container.style.padding = '16px'

    btn = document.createElement('button')
    btn.style.cssText = (
        'padding: 10px 24px; font-size: 16px; cursor: pointer;'
        ' border: 2px solid #6366f1; border-radius: 8px;'
        ' background: #eef2ff; color: #4338ca;'
    )
    btn.textContent = 'Count: 0'

    count = 0
    def on_click(event):
        nonlocal count
        count += 1
        btn.textContent = f'Count: {count}'
    btn.addEventListener('click', create_proxy(on_click))

    container.appendChild(btn)
    el.appendChild(container)
```

```{anywidget} https://cdn.jsdelivr.net/npm/pywidget-bridge@0.1.1/pywidget-bridge.mjs
{
  "_py_render": "def render(el, model):\n    from js import document\n    container = document.createElement('div')\n    container.style.fontFamily = 'sans-serif'\n    container.style.padding = '16px'\n\n    btn = document.createElement('button')\n    btn.style.cssText = 'padding: 10px 24px; font-size: 16px; cursor: pointer; border: 2px solid #6366f1; border-radius: 8px; background: #eef2ff; color: #4338ca;'\n    btn.textContent = 'Count: 0'\n\n    count = 0\n    def on_click(event):\n        nonlocal count\n        count += 1\n        btn.textContent = f'Count: {count}'\n    btn.addEventListener('click', create_proxy(on_click))\n\n    container.appendChild(btn)\n    el.appendChild(container)",
  "count": 0
}
```

## Example 3: Python Computation

Using Python's standard library to compute and display results.

```{code-block} python
def render(el, model):
    import math
    import sys

    rows = ''
    for n in range(1, 11):
        rows += (
            f'<tr><td>{n}</td><td>{n**2}</td>'
            f'<td>{math.factorial(n):,}</td><td>{math.sqrt(n):.4f}</td></tr>'
        )

    el.innerHTML = f"""
    <div style="font-family: sans-serif; padding: 16px;">
        <p style="color: #666; margin-bottom: 12px;">
            Computed by Python {sys.version.split()[0]} (Pyodide) in your browser
        </p>
        <table style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr style="background: #f1f5f9;">
                    <th style="padding: 8px 12px; border: 1px solid #e2e8f0;">n</th>
                    <th style="padding: 8px 12px; border: 1px solid #e2e8f0;">n²</th>
                    <th style="padding: 8px 12px; border: 1px solid #e2e8f0;">n!</th>
                    <th style="padding: 8px 12px; border: 1px solid #e2e8f0;">√n</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """
```

```{anywidget} https://cdn.jsdelivr.net/npm/pywidget-bridge@0.1.1/pywidget-bridge.mjs
{
  "_py_render": "def render(el, model):\n    import math\n    import sys\n\n    rows = ''\n    for n in range(1, 11):\n        rows += f'<tr><td>{n}</td><td>{n**2}</td><td>{math.factorial(n):,}</td><td>{math.sqrt(n):.4f}</td></tr>'\n\n    el.innerHTML = f\"\"\"\n    <div style=\"font-family: sans-serif; padding: 16px;\">\n        <p style=\"color: #666; margin-bottom: 12px;\">Computed by Python {sys.version.split()[0]} (Pyodide) in your browser</p>\n        <table style=\"border-collapse: collapse; width: 100%;\">\n            <thead>\n                <tr style=\"background: #f1f5f9;\">\n                    <th style=\"padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;\">n</th>\n                    <th style=\"padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;\">n&sup2;</th>\n                    <th style=\"padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;\">n!</th>\n                    <th style=\"padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;\">&radic;n</th>\n                </tr>\n            </thead>\n            <tbody>{rows}</tbody>\n        </table>\n    </div>\n    \"\"\""
}
```
