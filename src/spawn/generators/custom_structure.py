"""
Parse pasted folder-structure text into a flat list of (path, is_file) entries.

Supported input formats:
  tree      — uses ├──, └──, │ connectors (standard Unix tree output)
  markdown  — lines starting with optional whitespace + "- " or "* "
  indented  — plain indentation (tabs or spaces), no bullets or tree chars
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from spawn.core.exceptions import StructureParseError

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
    2. Starts with "." and has no further dot after the leading dot
       (e.g. ".env", ".gitignore") → file.
    3. Contains a "." after the last "/" segment → file.
    4. Anything else → folder.
    """
    if name.endswith("/"):
        return False
    segment = name.rsplit("/", 1)[-1]
    # dotfiles like ".env.example", ".gitignore", ".env"
    if segment.startswith("."):
        return True
    # names containing a dot are files (e.g. "main.py", "README.md")
    if "." in segment:
        return True
    return False


def _strip_name(name: str) -> str:
    """Remove trailing slash and inline comments."""
    # strip inline comments like "# some note"
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
    """
    Parse one line of tree output.

    Depth is determined by counting tree-prefix segments before the name.
    Each "│   " or "    " (4-char block) counts as one level, plus the
    final connector (├── or └──) counts as one more level.

    Returns (depth, name) or None if the line is blank / unparseable.
    """
    stripped = line.rstrip()
    if not stripped:
        return None

    # Root line: no tree characters at all
    if not any(c in stripped for c in _TREE_CHARS):
        name = _strip_name(stripped.lstrip())
        if not name:
            return None
        return (0, name)

    # Count prefix width before the connector
    # prefix chars: │, space
    match = re.match(r"^([\s│]*)[├└]──\s*(.+)$", stripped)
    if not match:
        return None
    prefix, name = match.group(1), match.group(2).rstrip()
    name = _strip_name(name)
    if not name:
        return None
    # Each "│   " or "    " block in prefix is 4 chars → one indent level
    # connector itself adds one more level
    depth = len(prefix) // 4 + 1
    return (depth, name)


def _markdown_depth_and_name(line: str, indent_unit: int) -> tuple[int, str] | None:
    match = _MARKDOWN_LINE_RE.match(line)
    if not match:
        stripped = line.strip()
        if not stripped:
            return None
        # non-bullet root line
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
    """
    Returns (depth, name, updated_indent_unit).
    indent_unit is None until the first indented line establishes it.
    """
    stripped = line.rstrip()
    if not stripped or not stripped.strip():
        return (-1, "", indent_unit)

    leading = len(stripped) - len(stripped.lstrip())
    name = _strip_name(stripped.strip())
    if not name:
        return (-1, "", indent_unit)

    if leading == 0:
        return (0, name, indent_unit)

    # Establish indent unit from first indented line
    if indent_unit is None:
        indent_unit = leading

    depth = leading // indent_unit
    return (depth, name, indent_unit)


# ─── Main parser ──────────────────────────────────────────────────────────


def parse_structure(raw: str) -> list[ParsedEntry]:
    """
    Parse raw pasted text into a flat list of ParsedEntry with full
    relative paths.  See module docstring for format details.

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
    # Detect indent unit: smallest non-zero leading-space count on bullet lines
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
    """
    Convert (depth, name) pairs to ParsedEntry with full paths.

    Uses a stack where stack[depth] = current folder path at that depth.
    Raises StructureParseError for depth jumps > 1 and duplicate paths.
    """
    if not depth_name_pairs:
        raise StructureParseError("No parseable entries found in input.")

    # Normalise so the shallowest entry is always at depth 0
    min_depth = min(d for d, _ in depth_name_pairs)
    if min_depth != 0:
        depth_name_pairs = [(d - min_depth, n) for d, n in depth_name_pairs]

    entries: list[ParsedEntry] = []
    seen: set[str] = set()

    # stack[i] = the folder path that acts as parent for depth i+1
    # stack[0] = "" means top-level entries have no parent prefix
    stack: list[str] = [""]

    prev_depth = -1

    for depth, name in depth_name_pairs:
        # Validate depth jump
        if depth > prev_depth + 1:
            raise StructureParseError(
                f"Entry '{name}' is indented {depth} level(s) deep but the "
                f"previous depth was {prev_depth} — missing intermediate parent."
            )

        # Trim stack to current depth
        # stack has entries for depths 0..prev_depth
        # After trim, stack[depth] is the parent folder for this entry
        del stack[depth + 1 :]

        parent = stack[depth] if depth < len(stack) else stack[-1]
        full_path = f"{parent}/{name}".lstrip("/") if parent else name

        # Detect file vs folder (use original name including trailing slash)
        original_line_name = name  # already stripped of comments
        is_file = _is_file_entry(original_line_name)

        if full_path in seen:
            raise StructureParseError(
                f"Duplicate path '{full_path}' declared more than once."
            )
        seen.add(full_path)

        entries.append(ParsedEntry(path=full_path, is_file=is_file))

        # If this is a folder, push it as the parent for the next depth level
        if not is_file:
            if depth + 1 >= len(stack):
                stack.append(full_path)
            else:
                stack[depth + 1] = full_path

        prev_depth = depth

    return entries
