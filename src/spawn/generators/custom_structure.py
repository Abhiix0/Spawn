"""
Parse pasted folder-structure text into a flat list of (path, is_file) entries,
and generate the filesystem structure from parsed entries.

Supported input formats:
  tree      — uses ├──, └──, │ connectors (standard Unix tree output)
  markdown  — lines starting with optional whitespace + "- " or "* "
  indented  — plain indentation (tabs or spaces), no bullets or tree chars
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from spawn.core.exceptions import SpawnError, StructureParseError
from spawn.utils.console import console
from spawn.utils.git import initialize_git
from spawn.utils.uv import initialize_uv, install_packages

# Tree connector characters
_TREE_CHARS = {"├", "└", "│"}
_TREE_CONNECTOR_RE = re.compile(r"^[\s│]*[├└]──\s*")
_MARKDOWN_LINE_RE = re.compile(r"^(\s*)[-*]\s+")


@dataclass
class ParsedEntry:
    path: str       # relative path, forward-slash separated
    is_file: bool   # True if entry has a file extension or no trailing "/"


# ─── Helpers ──────────────────────────────────────────────────────────────


def _is_file_entry(name: str) -> bool:
    """
    Decide whether a name represents a file or a folder.

    Rules (in priority order):
    1. Trailing "/" → always folder.
    2. Starts with "." (dotfile like .env, .gitignore) → file.
    3. Contains a "." after the last "/" segment → file.
    4. Anything else → folder.
    """
    if name.endswith("/"):
        return False
    segment = name.rsplit("/", 1)[-1]
    if segment.startswith("."):
        return True
    if "." in segment:
        return True
    return False


def _strip_name(name: str) -> str:
    """Remove trailing slash and inline comments."""
    name = re.sub(r"\s*#.*$", "", name).strip()
    return name.rstrip("/")


# ─── Format detection ─────────────────────────────────────────────────────


def detect_format(raw: str) -> str:
    """Return 'tree', 'markdown', or 'indented'."""
    for line in raw.splitlines():
        if any(c in line for c in _TREE_CHARS):
            return "tree"
    for line in raw.splitlines():
        if _MARKDOWN_LINE_RE.match(line):
            return "markdown"
    return "indented"


# ─── Per-format depth extraction ──────────────────────────────────────────


def _tree_depth_and_name(line: str) -> tuple[int, str] | None:
    stripped = line.rstrip()
    if not stripped:
        return None

    # Root line: no tree characters
    if not any(c in stripped for c in _TREE_CHARS):
        name = _strip_name(stripped.lstrip())
        if not name:
            return None
        return (0, name)

    match = re.match(r"^([\s│]*)[├└]──\s*(.+)$", stripped)
    if not match:
        return None
    prefix, name = match.group(1), match.group(2).rstrip()
    name = _strip_name(name)
    if not name:
        return None
    depth = len(prefix) // 4 + 1
    return (depth, name)


def _markdown_depth_and_name(line: str, indent_unit: int) -> tuple[int, str] | None:
    match = _MARKDOWN_LINE_RE.match(line)
    if not match:
        stripped = line.strip()
        if not stripped:
            return None
        return (0, _strip_name(stripped))
    spaces = len(match.group(1))
    name = _strip_name(line[match.end():].strip())
    if not name:
        return None
    depth = (spaces // indent_unit + 1) if indent_unit > 0 else 1
    return (depth, name)


def _indented_depth_and_name(
    line: str, indent_unit: int | None
) -> tuple[int, str, int | None]:
    stripped = line.rstrip()
    if not stripped or not stripped.strip():
        return (-1, "", indent_unit)

    leading = len(stripped) - len(stripped.lstrip())
    name = _strip_name(stripped.strip())
    if not name:
        return (-1, "", indent_unit)

    if leading == 0:
        return (0, name, indent_unit)

    if indent_unit is None:
        indent_unit = leading

    depth = leading // indent_unit
    return (depth, name, indent_unit)


# ─── Main parser ──────────────────────────────────────────────────────────


def parse_structure(raw: str) -> list[ParsedEntry]:
    """
    Parse raw pasted text into a flat list of ParsedEntry with full
    relative paths.

    Raises StructureParseError for empty input, malformed indentation,
    or duplicate paths.
    """
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        raise StructureParseError("Input is empty — no structure to parse.")

    fmt = detect_format(raw)

    if fmt == "tree":
        depth_name_pairs = _parse_tree_lines(lines)
    elif fmt == "markdown":
        depth_name_pairs = _parse_markdown_lines(lines)
    else:
        depth_name_pairs = _parse_indented_lines(lines)

    return _build_entries(depth_name_pairs)


def _parse_tree_lines(lines: list[str]) -> list[tuple[int, str]]:
    result = []
    for line in lines:
        parsed = _tree_depth_and_name(line)
        if parsed is None:
            continue
        result.append(parsed)
    return result


def _parse_markdown_lines(lines: list[str]) -> list[tuple[int, str]]:
    indent_unit = 2
    space_counts = []
    for line in lines:
        m = _MARKDOWN_LINE_RE.match(line)
        if m:
            spaces = len(m.group(1))
            if spaces > 0:
                space_counts.append(spaces)
    if space_counts:
        indent_unit = min(space_counts)

    result = []
    for line in lines:
        parsed = _markdown_depth_and_name(line, indent_unit)
        if parsed is None:
            continue
        result.append(parsed)
    return result


def _parse_indented_lines(lines: list[str]) -> list[tuple[int, str]]:
    indent_unit: int | None = None
    result = []
    for line in lines:
        depth, name, indent_unit = _indented_depth_and_name(line, indent_unit)
        if depth < 0 or not name:
            continue
        result.append((depth, name))
    return result


def _build_entries(
    depth_name_pairs: list[tuple[int, str]],
) -> list[ParsedEntry]:
    if not depth_name_pairs:
        raise StructureParseError("No parseable entries found in input.")

    # Normalise so the shallowest entry is always at depth 0
    min_depth = min(d for d, _ in depth_name_pairs)
    if min_depth != 0:
        depth_name_pairs = [(d - min_depth, n) for d, n in depth_name_pairs]

    entries: list[ParsedEntry] = []
    seen: set[str] = set()
    stack: list[str] = [""]
    prev_depth = -1

    for depth, name in depth_name_pairs:
        if depth > prev_depth + 1:
            raise StructureParseError(
                f"Entry '{name}' is indented {depth} level(s) deep but the "
                f"previous depth was {prev_depth} — missing intermediate parent."
            )

        del stack[depth + 1:]

        parent = stack[depth] if depth < len(stack) else stack[-1]
        full_path = f"{parent}/{name}".lstrip("/") if parent else name

        is_file = _is_file_entry(name)

        if full_path in seen:
            raise StructureParseError(
                f"Duplicate path '{full_path}' declared more than once."
            )
        seen.add(full_path)

        entries.append(ParsedEntry(path=full_path, is_file=is_file))

        if not is_file:
            if depth + 1 >= len(stack):
                stack.append(full_path)
            else:
                stack[depth + 1] = full_path

        prev_depth = depth

    return entries


# ─── README helpers ───────────────────────────────────────────────────────


def _render_tree(entries: list[ParsedEntry]) -> str:
    """Render parsed entries as a normalised indented tree string."""
    lines = []
    for entry in entries:
        depth = entry.path.count("/")
        indent = "  " * depth
        name = entry.path.rsplit("/", 1)[-1]
        suffix = "" if entry.is_file else "/"
        lines.append(f"{indent}{name}{suffix}")
    return "\n".join(lines)


def _build_readme_content(
    project_name: str, entries: list[ParsedEntry], use_uv: bool
) -> str:
    """Return generated README.md content for a custom-structure project."""
    tree_lines = _render_tree(entries)
    setup_line = "uv sync" if use_uv else "# Set up your environment"
    return (
        f"# {project_name}\n\n"
        "Generated by Spawn\n\n"
        "## Project Structure\n\n"
        "```\n"
        f"{tree_lines}\n"
        "```\n\n"
        "## Setup\n\n"
        "```bash\n"
        f"{setup_line}\n"
        "```\n\n"
        "## Run\n\n"
        "Add project run instructions here.\n"
    )


# ─── Filesystem generator ─────────────────────────────────────────────────


class CustomStructureGenerator:
    def generate(
        self,
        project_name: str,
        entries: list[ParsedEntry],
        use_git: bool = False,
        use_uv: bool = True,
        dependencies: list[str] | None = None,
        dev_setup: list[str] | None = None,
    ) -> Path:
        """
        Create the folder/file structure described by *entries* under a new
        directory named *project_name* in the current working directory.

        Raises SpawnError if the directory already exists or an OS error
        occurs.  Rolls back on any failure.
        """
        project_path = Path(project_name)

        if project_path.exists():
            raise SpawnError(f"Directory '{project_name}' already exists.")

        try:
            project_path.mkdir()

            for entry in entries:
                full_path = project_path / entry.path
                if entry.is_file:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.touch()
                else:
                    full_path.mkdir(parents=True, exist_ok=True)

            readme_entry = next(
                (
                    e for e in entries
                    if e.path == "README.md" or e.path.endswith("/README.md")
                ),
                None,
            )
            if readme_entry is not None:
                readme_path = project_path / readme_entry.path
                readme_path.write_text(
                    _build_readme_content(project_name, entries, use_uv),
                    encoding="utf-8",
                )

            if use_git:
                console.print("[yellow]Initializing Git...[/yellow]")
                initialize_git(project_path)

            if use_uv:
                initialize_uv(project_path)

            if use_uv and dependencies:
                console.print("[yellow]Installing dependencies...[/yellow]")
                install_packages(project_path, dependencies)

            if use_uv and dev_setup:
                self._apply_dev_setup(project_path, dev_setup)

        except OSError as e:
            shutil.rmtree(project_path, ignore_errors=True)
            raise SpawnError(str(e)) from e

        except BaseException:
            shutil.rmtree(project_path, ignore_errors=True)
            raise

        return project_path

    def _apply_dev_setup(self, project_path: Path, dev_setup: list[str]) -> None:
        """Install dev tools and generate their config files."""
        dev_deps: list[str] = []
        if "ruff" in dev_setup:
            dev_deps.append("ruff")
        if "pytest" in dev_setup:
            dev_deps.append("pytest")
        if "precommit" in dev_setup:
            dev_deps.append("pre-commit")

        if dev_deps:
            console.print("[yellow]Installing dev tools...[/yellow]")
            install_packages(project_path, dev_deps, dev=True)

        if "ruff" in dev_setup:
            (project_path / "ruff.toml").write_text(
                'line-length = 88\ntarget-version = "py312"\n',
                encoding="utf-8",
            )

        if "pytest" in dev_setup:
            tests_dir = project_path / "tests"
            tests_dir.mkdir(exist_ok=True)
            (tests_dir / "__init__.py").touch()

        if "precommit" in dev_setup:
            (project_path / ".pre-commit-config.yaml").write_text(
                "repos:\n"
                "  - repo: https://github.com/astral-sh/ruff-pre-commit\n"
                "    rev: v0.15.16\n"
                "    hooks:\n"
                "      - id: ruff\n",
                encoding="utf-8",
            )

        if "dockerfile" in dev_setup:
            (project_path / "Dockerfile").write_text(
                "FROM python:3.12-slim\n"
                "WORKDIR /app\n"
                "COPY . .\n"
                "RUN pip install uv && uv sync\n"
                'CMD ["python", "-m", "src.main"]\n',
                encoding="utf-8",
            )
