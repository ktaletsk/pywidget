# Contributing

## Setup

Clone the repo and create a fresh environment:

```bash
git clone https://github.com/ktaletsk/pywidget
cd pywidget
conda create -n pywidget python=3.14
conda activate pywidget
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Project structure

```
pywidget/
├── pywidget/
│   ├── __init__.py          # public exports
│   ├── pywidget.py          # PyWidget class + method extraction
│   └── _bridge.js           # JS bridge ESM (loaded by anywidget via _esm)
├── js/
│   ├── package.json         # npm package: pywidget-bridge
│   └── pywidget-bridge.mjs  # Pyodide bridge for static MyST pages (canonical source)
├── tests/
│   └── test_pywidget.py
├── examples/
│   ├── myst/                # MyST Markdown examples (reference js/ bridge locally)
│   └── *.ipynb              # Jupyter/Colab notebooks
└── pyproject.toml
```

There are two JavaScript files in this project:

- **`pywidget/_bridge.js`** — kernel-side bridge, delivered via anywidget's `_esm`
  traitlet. Has an `initialize()` hook for eager Pyodide loading. No build step.
- **`js/pywidget-bridge.mjs`** — static MyST bridge (npm package `pywidget-bridge`).
  Referenced as a local path during development; users reference it via CDN once
  published. No build step.

## Making changes to the kernel bridge

Edit `pywidget/_bridge.js` directly. Changes take effect on the next Python
import (or kernel restart in JupyterLab).

## Making changes to the MyST bridge

Edit `js/pywidget-bridge.mjs` directly. Test locally by running the MyST example:

```bash
cd examples/myst
npx mystmd start
```

`examples/myst/` references the bridge as `../../js/pywidget-bridge.mjs` (local path) for
development of the bridge itself. The deployed docs site uses the jsDelivr CDN URL.

> **Note:** Use `cdn.jsdelivr.net/npm` (not `esm.sh`) for CDN references. esm.sh serves a shim
> that re-exports from a relative `/`-path, which `myst start` resolves against `localhost`
> and 404s. jsDelivr serves the raw file directly and works in both dev and production.

## Releasing a new Python version (PyPI)

1. Bump `version` in `pyproject.toml`.
2. Tag the commit: `git tag vX.Y.Z && git push --tags`.
3. Build and upload:
   ```bash
   python -m build
   twine upload dist/*
   ```

## Releasing the npm package (`pywidget-bridge`)

The npm package lives in `js/`. Its version should stay in sync with `pyproject.toml`.

### First-time setup

Create an npm account at <https://www.npmjs.com> if you don't have one, then:

```bash
npm login
```

### Publishing

1. Bump `version` in `js/package.json` to match `pyproject.toml`.
2. Publish:
   ```bash
   cd js
   npm publish --access public
   ```

### After publishing

Once published, users can reference the bridge by CDN URL instead of a local path.
Use the **jsDelivr npm CDN** — it serves the raw file without transformation:

```markdown
```{anywidget} https://cdn.jsdelivr.net/npm/pywidget-bridge@0.1.1/pywidget-bridge.mjs
{ "_py_render": "def render(el, model): ..." }
```
```

Update the docs site to use the jsDelivr URL after each release.

## Running the demo notebook

```bash
conda activate pywidget
jupyter lab
# open examples/pywidget_demo.ipynb
```
