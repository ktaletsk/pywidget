from __future__ import annotations

import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import nbformat


REPO_OWNER = "ktaletsk"
REPO_NAME = "pywidget"
REPO_REF = "main"

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
README_PATH = EXAMPLES_DIR / "README.md"
MARIMO_BADGE_URL = "https://marimo.io/shield.svg"
NOTEBOOK_LINK_BADGE_URL = (
    "https://img.shields.io/badge/notebook-link-e2d610?logo=jupyter&logoColor=white"
)
COLAB_BADGE_URL = "https://colab.research.google.com/assets/colab-badge.svg"
CODESPACES_BADGE_URL = (
    "https://github.com/codespaces/badge.svg"
)


@dataclass(frozen=True)
class ExampleSpec:
    title: str
    marimo_source: Path
    notebook_path: Path
    colab_path: Path


def iter_marimo_sources() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*_mo.py"))


def notebook_path_for(source_path: Path) -> Path:
    stem = source_path.stem.removesuffix("_mo")
    return source_path.with_name(f"{stem}.ipynb")


def colab_path_for(source_path: Path) -> Path:
    stem = source_path.stem.removesuffix("_mo")
    return source_path.with_name(f"{stem}_colab.ipynb")


def parse_pep723_deps(header: str) -> list[str]:
    """Extract dependency names from a PEP 723 inline script metadata header."""
    deps: list[str] = []
    in_deps = False
    for line in header.splitlines():
        text = line.lstrip("# ").strip()
        if text.startswith("dependencies"):
            # Handle single-line: dependencies = ["pywidget", "anywidget"]
            match = re.search(r"\[(.+)\]", text)
            if match:
                for item in match.group(1).split(","):
                    name = item.strip().strip('"').strip("'").strip()
                    if name:
                        deps.append(name)
                break
            in_deps = True
            continue
        if in_deps:
            if text.startswith("]") or text.startswith("# ///"):
                break
            name = text.strip(' ",')
            if name:
                deps.append(name)
    return deps


def generate_colab_notebook(notebook_path: Path, colab_path: Path) -> None:
    """Copy *notebook_path* to *colab_path* with a ``!pip install`` cell prepended."""
    notebook = nbformat.read(notebook_path, as_version=4)

    header = notebook.metadata.get("marimo", {}).get("header", "")
    deps = parse_pep723_deps(header) if header else []

    # Keep only packages that a Colab user actually needs to install.
    skip = {"marimo", "anywidget"}
    install_deps = [d for d in deps if re.split(r"[><=!]", d)[0] not in skip]
    if not install_deps:
        install_deps = ["pywidget"]
    elif not any(re.split(r"[><=!]", d)[0] == "pywidget" for d in install_deps):
        install_deps.insert(0, "pywidget")

    pip_line = "!pip install " + " ".join(install_deps)

    install_cell = nbformat.v4.new_code_cell(source=pip_line)
    install_cell.metadata["id"] = "colab-install"
    notebook.cells.insert(0, install_cell)

    # Strip marimo-specific metadata that is irrelevant in Colab.
    notebook.metadata.pop("marimo", None)

    nbformat.write(notebook, colab_path)


def extract_title(source_path: Path) -> str:
    source = source_path.read_text()
    match = re.search(
        r"mo\.md\(\s*(?:r)?(?P<quote>\"\"\"|''')(?P<body>.*?)(?P=quote)\s*\)",
        source,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(f"Could not find a markdown cell in {source_path}")

    for line in match.group("body").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()

    raise ValueError(
        f"Could not find an H1 heading in the first markdown cell of {source_path}"
    )


def export_notebook(source_path: Path, notebook_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "marimo",
            "export",
            "ipynb",
            str(source_path),
            "-o",
            str(notebook_path),
        ],
        check=True,
        cwd=REPO_ROOT,
    )


def unwrap_anywidget_calls(source: str) -> str:
    token = "mo.ui.anywidget("
    parts: list[str] = []
    start = 0

    while True:
        index = source.find(token, start)
        if index == -1:
            parts.append(source[start:])
            return "".join(parts)

        parts.append(source[start:index])
        cursor = index + len(token)
        depth = 1

        while cursor < len(source) and depth > 0:
            char = source[cursor]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            cursor += 1

        if depth != 0:
            raise ValueError(
                "Unbalanced parentheses while unwrapping mo.ui.anywidget(...)"
            )

        parts.append(source[index + len(token) : cursor - 1])
        start = cursor


def parse_control_assignment(stripped_line: str) -> tuple[str, str | None] | None:
    if " = mo.ui." not in stripped_line:
        return None

    name, expr = stripped_line.split("=", maxsplit=1)
    name = name.strip()
    expr = expr.strip()
    call = ast.parse(expr, mode="eval").body

    if not isinstance(call, ast.Call):
        return None
    if not isinstance(call.func, ast.Attribute):
        return None
    if not isinstance(call.func.value, ast.Attribute):
        return None
    if not isinstance(call.func.value.value, ast.Name):
        return None
    if call.func.value.value.id != "mo" or call.func.value.attr != "ui":
        return None

    control_kind = call.func.attr
    if control_kind in {"text", "slider"}:
        for keyword in call.keywords:
            if keyword.arg == "value":
                return name, ast.unparse(keyword.value)
        raise ValueError(
            f"Missing default value for mo.ui.{control_kind} in line: {stripped_line}"
        )

    if control_kind == "button":
        return name, None

    return None


def _replace_mo_md(source: str) -> str:
    """Replace ``mo.md(...)`` calls with ``print(...)``."""
    token = "mo.md("
    parts: list[str] = []
    start = 0

    while True:
        index = source.find(token, start)
        if index == -1:
            parts.append(source[start:])
            return "".join(parts)

        parts.append(source[start:index])
        parts.append("print(")
        cursor = index + len(token)
        depth = 1

        while cursor < len(source) and depth > 0:
            char = source[cursor]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            cursor += 1

        if depth != 0:
            raise ValueError("Unbalanced parentheses while replacing mo.md(...)")

        parts.append(source[index + len(token) : cursor])
        start = cursor

    return "".join(parts)


def clean_code_cell(
    source: str,
    control_defaults: dict[str, str | None],
    anywidget_names: set[str],
) -> str:
    # Detect anywidget wrapper names before unwrapping strips the mo.ui prefix.
    for line in source.splitlines():
        m = re.match(r"(\w+)\s*=\s*mo\.ui\.anywidget\(", line.strip())
        if m:
            anywidget_names.add(m.group(1))

    source = unwrap_anywidget_calls(source)
    cleaned_lines: list[str] = []

    for line in source.splitlines():
        stripped = line.strip()
        is_top_level = line == line.lstrip()

        if is_top_level and stripped in {"import marimo", "import marimo as mo"}:
            continue
        if is_top_level and stripped.startswith("return"):
            continue
        if is_top_level and stripped in {
            'if __name__ == "__main__":',
            "if __name__ == '__main__':",
        }:
            continue
        if is_top_level and stripped == "app.run()":
            continue

        parsed_assignment = parse_control_assignment(stripped) if is_top_level else None
        if parsed_assignment is not None:
            name, default_expr = parsed_assignment
            control_defaults[name] = default_expr
            if default_expr is not None:
                cleaned_lines.append(f"{name} = {default_expr}")
            continue

        if is_top_level and stripped in control_defaults:
            continue

        cleaned_lines.append(line)

    cleaned_source = "\n".join(cleaned_lines)

    for name, default_expr in control_defaults.items():
        replacement = name if default_expr is not None else "None"
        cleaned_source = re.sub(rf"\b{name}\.value\b", replacement, cleaned_source)

    # Convert anywidget .value access to direct trait access:
    #   wrapper.value.get("key", default) → wrapper.key
    #   wrapper.value["key"]              → wrapper.key
    for name in anywidget_names:
        cleaned_source = re.sub(
            rf'\b{re.escape(name)}\.value\.get\(\s*"(\w+)"(?:\s*,\s*[^)]+)?\)',
            rf"{name}.\1",
            cleaned_source,
        )
        cleaned_source = re.sub(
            rf'\b{re.escape(name)}\.value\[\s*"(\w+)"\s*\]',
            rf"{name}.\1",
            cleaned_source,
        )

    # Convert mo.md(...) calls to print(...) so the cell survives the mo. check.
    cleaned_source = _replace_mo_md(cleaned_source)

    cleaned_source = re.sub(r"^\s*\n", "", cleaned_source, flags=re.MULTILINE)
    cleaned_source = cleaned_source.strip()

    if not cleaned_source:
        return ""
    if "mo." in cleaned_source:
        return ""

    return f"{cleaned_source}\n"


def clean_notebook(notebook_path: Path) -> None:
    notebook = nbformat.read(notebook_path, as_version=4)
    cleaned_cells = []
    control_defaults: dict[str, str | None] = {}
    anywidget_names: set[str] = set()

    for cell in notebook.cells:
        if cell.cell_type == "code":
            cleaned_source = clean_code_cell(cell.source, control_defaults, anywidget_names)
            if not cleaned_source:
                continue
            cell.source = cleaned_source
            cleaned_cells.append(cell)
            continue

        if cell.cell_type == "markdown" and cell.source.strip():
            cleaned_cells.append(cell)

    for index, cell in enumerate(cleaned_cells):
        if cell.cell_type != "markdown":
            continue
        first_line = cell.source.strip().splitlines()[0]
        if first_line.startswith("# "):
            cleaned_cells.insert(0, cleaned_cells.pop(index))
            break

    notebook.cells = cleaned_cells
    nbformat.write(notebook, notebook_path)


def marimo_url_for(source_path: Path) -> str:
    raw_url = (
        f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/refs/heads/"
        f"{REPO_REF}/examples/{source_path.name}"
    )
    return f"https://marimo.app/?src={quote(raw_url, safe='')}"


def notebook_link_url_for(notebook_path: Path) -> str:
    path = quote(f"examples/{notebook_path.name}", safe="")
    return f"https://notebook.link/github.com/{REPO_OWNER}/{REPO_NAME}/?path={path}"


def colab_url_for(colab_path: Path) -> str:
    return (
        f"https://colab.research.google.com/github/{REPO_OWNER}/{REPO_NAME}"
        f"/blob/{REPO_REF}/examples/{colab_path.name}"
    )


def codespaces_url_for() -> str:
    return f"https://codespaces.new/{REPO_OWNER}/{REPO_NAME}?quickstart=1"


def write_gallery_readme(example_specs: list[ExampleSpec]) -> None:
    lines = [
        "# gallery",
        "",
        "| Example | marimo.app | notebook.link | Google Colab | GitHub Codespaces |",
        "| --- | --- | --- | --- | --- |",
    ]

    codespaces_url = codespaces_url_for()
    for spec in example_specs:
        marimo_url = marimo_url_for(spec.marimo_source)
        notebook_url = notebook_link_url_for(spec.notebook_path)
        colab_url = colab_url_for(spec.colab_path)
        lines.append(
            f"| {spec.title} | "
            f"[![Open in marimo]({MARIMO_BADGE_URL})]({marimo_url}) | "
            f"[![Open on notebook.link]({NOTEBOOK_LINK_BADGE_URL})]({notebook_url}) | "
            f"[![Open in Colab]({COLAB_BADGE_URL})]({colab_url}) | "
            f"[![Open in GitHub Codespaces]({CODESPACES_BADGE_URL})]({codespaces_url}) |"
        )

    README_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    sources = iter_marimo_sources()
    example_specs: list[ExampleSpec] = []

    for source_path in sources:
        notebook_path = notebook_path_for(source_path)
        colab_path = colab_path_for(source_path)
        export_notebook(source_path, notebook_path)
        clean_notebook(notebook_path)
        generate_colab_notebook(notebook_path, colab_path)
        example_specs.append(
            ExampleSpec(
                title=extract_title(source_path),
                marimo_source=source_path,
                notebook_path=notebook_path,
                colab_path=colab_path,
            )
        )

    write_gallery_readme(example_specs)


if __name__ == "__main__":
    main()
