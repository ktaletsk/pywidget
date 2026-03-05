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
│   ├── __init__.py     # public exports
│   ├── pywidget.py     # PyWidget class + method extraction
│   └── _bridge.js      # JS bridge ESM (loaded by anywidget via _esm)
├── tests/
│   └── test_pywidget.py
├── examples/
│   └── pywidget_demo.ipynb
└── pyproject.toml
```

The JS bridge (`_bridge.js`) is the only JavaScript in this project. It is read
at import time and delivered to the browser through anywidget's standard `_esm`
traitlet mechanism. No JS build step is required.

## Making changes to the bridge

Edit `pywidget/_bridge.js` directly. Changes take effect on the next Python
import (or kernel restart in JupyterLab). There is no bundling or compilation.

## Running the demo notebook

```bash
conda activate pywidget
jupyter lab
# open examples/pywidget_demo.ipynb
```
