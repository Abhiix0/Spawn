"""Prove absent script attributes in explicitly packaged simple modules."""

import ast
import re

from ..models import Evidence
from ..rules import RuleContext
from ._common import OUTSIDE_SCOPE, Unclear, check, kind, read, table

_SCRIPT_KEY = "project.scripts"
_REFERENCE = re.compile(r"([A-Za-z][A-Za-z0-9_]*):([A-Za-z][A-Za-z0-9_]*)")


def _console_target(context: RuleContext, doc: dict):
    project = table(doc["project"])
    if project.get("dynamic"):
        raise Unclear()
    scripts = table(project.get("scripts", {}))
    if not scripts:
        return OUTSIDE_SCOPE
    if table(doc.get("build-system", {})) != {
        "requires": ["setuptools"],
        "build-backend": "setuptools.build_meta",
    } or any(kind(context, name) != "missing" for name in ("setup.py", "setup.cfg")):
        raise Unclear()
    setuptools = table(table(doc.get("tool", {})).get("setuptools", {}))
    if set(setuptools) != {"py-modules"} or not isinstance(
        setuptools["py-modules"], list
    ):
        raise Unclear()
    declared = setuptools["py-modules"]
    if not all(
        isinstance(item, str) and item.isascii() and item.isidentifier()
        for item in declared
    ):
        raise Unclear()

    missing = set()
    modules = {}
    for ref in scripts.values():
        context.spend()
        match = _REFERENCE.fullmatch(ref) if isinstance(ref, str) else None
        if not match:
            raise Unclear()
        module, attribute = match.groups()
        context.spend(1 + len(declared))
        if module not in declared:
            raise Unclear()
        path = module + ".py"
        if path not in modules:
            if (
                kind(context, path) != "file"
                or kind(context, module) != "missing"
                or kind(context, module + ".pyi") != "missing"
            ):
                raise Unclear()
            source = read(context, path)
            if "\x00" in source:
                raise Unclear()
            tree = ast.parse(source)
            # Compile validates scope-sensitive syntax without executing code.
            compile(tree, "<diagnostic-module>", "exec", dont_inherit=True)
            names = set()
            for index, node in enumerate(tree.body):
                context.spend()
                if (
                    index == 0
                    and isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    continue
                if (
                    not isinstance(node, ast.FunctionDef)
                    or node.name in names | {"__getattr__"}
                    or node.decorator_list
                    or node.type_params
                    or node.returns
                    or node.args.defaults
                    or any(node.args.kw_defaults)
                    or any(
                        isinstance(child, ast.arg) and child.annotation
                        for child in ast.walk(node.args)
                    )
                ):
                    raise Unclear()
                names.add(node.name)
            modules[path] = names
        if attribute not in modules[path]:
            missing.add(path)
    return tuple(
        (Evidence("pyproject.toml", key=_SCRIPT_KEY), Evidence(path))
        for path in sorted(missing)
    )


CONSOLE_TARGET = check(
    "py-entry-001",
    "entry-point",
    "Console script target is absent from its module",
    "A declared console script names an attribute absent from this explicitly packaged module.",
    "Correct the script target in project.scripts or define the intended top-level function.",
    _console_target,
    keys=(_SCRIPT_KEY,),
)
