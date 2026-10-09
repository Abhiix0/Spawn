import ast
from pathlib import Path

SRC = Path(__file__).parent.parent / "src" / "spawn"
GUARDED = ("core", "generators", "templates", "utils", "github")


def _imports_cli(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                a.name == "spawn.cli" or a.name.startswith("spawn.cli.")
                for a in node.names
            ):
                return True
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level == 0 and (
                mod == "spawn.cli"
                or mod.startswith("spawn.cli.")
                or (mod == "spawn" and any(a.name == "cli" for a in node.names))
            ):
                return True
            if node.level > 0 and (mod == "cli" or mod.startswith("cli.")):
                return True
    return False


def test_no_module_outside_cli_imports_cli():
    offenders = []
    for pkg in GUARDED:
        for py in (SRC / pkg).rglob("*.py"):
            if _imports_cli(ast.parse(py.read_text(encoding="utf-8"))):
                offenders.append(py.relative_to(SRC).as_posix())
    assert not offenders, f"these modules import spawn.cli: {offenders}"
