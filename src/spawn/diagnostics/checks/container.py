"""Identify an explicit root USER in an unambiguous Python runtime stage."""

import json
import re

from ..models import Evidence
from ..rules import RuleContext
from ._common import OUTSIDE_SCOPE, Unclear, check, kind, read, table

_BACKENDS = {"fastapi", "starlette", "flask", "django"}
_FROM = re.compile(r"([a-z0-9][a-z0-9._:/-]*)(?: AS ([a-z][a-z0-9_-]*))?", re.I)
_PYTHON = re.compile(r"(?:docker\.io/library/)?python:[0-9][a-z0-9.-]*")
_USER = re.compile(r"[a-z_][a-z0-9_-]*|[0-9]+")
_OPERANDS = re.compile(r"[A-Za-z0-9_./:+-]+(?:[ \t]+[A-Za-z0-9_./:+-]+)*")


def _operands_supported(instruction: str, value: str) -> bool:
    if instruction in {"CMD", "ENTRYPOINT"}:
        try:
            args = json.loads(value)
        except json.JSONDecodeError:
            return False
        return (
            isinstance(args, list)
            and bool(args)
            and all(isinstance(argument, str) for argument in args)
        )
    if not _OPERANDS.fullmatch(value):
        return False
    args = value.split()
    match instruction:
        case "RUN":
            return not args[0].startswith("-")
        case "COPY":
            return len(args) >= 2 and not any(arg.startswith("-") for arg in args)
        case "WORKDIR":
            return len(args) == 1 and args[0].startswith("/")
        case "EXPOSE":
            return all(re.fullmatch(r"[0-9]+(?:/tcp|/udp)?", arg) for arg in args)
        case _:
            return False


def _docker_user(context: RuleContext, doc: dict):
    path = "Dockerfile"
    if kind(context, path) == "missing":
        return OUTSIDE_SCOPE
    dependencies = table(doc["project"]).get("dependencies")
    if (
        not isinstance(dependencies, list)
        or not all(isinstance(item, str) for item in dependencies)
        or not any(item.lower() in _BACKENDS for item in dependencies)
    ):
        raise Unclear()
    aliases = set()
    image = None
    user = None
    for number, raw in enumerate(read(context, path).split("\n"), 1):
        context.spend()
        line = raw.removesuffix("\r").strip(" \t")
        if (
            "\\" in line
            or "<<" in line
            or any(ord(char) < 32 and char != "\t" for char in line)
        ):
            raise Unclear()
        if not line:
            continue
        if line.startswith("#"):
            if re.match(r"#\s*(?:syntax|escape|check)\s*=", line, re.I):
                raise Unclear()
            continue
        tokens = line.split(None, 1)
        if len(tokens) != 2:
            raise Unclear()
        instruction, value = tokens[0].upper(), tokens[1]
        if instruction == "FROM":
            match = _FROM.fullmatch(value)
            if not match:
                raise Unclear()
            image, alias = match.groups()
            if alias:
                alias = alias.lower()
                if alias in aliases:
                    raise Unclear()
                aliases.add(alias)
            if image.lower() in aliases:
                raise Unclear()
            user = None
        elif image is None:
            raise Unclear()
        elif instruction == "USER":
            if not _USER.fullmatch(value):
                raise Unclear()
            user = (value, number)
        elif not _operands_supported(instruction, value):
            raise Unclear()

    if image is None or not _PYTHON.fullmatch(image) or "onbuild" in image:
        raise Unclear()
    if user is not None and user[0] in {"root", "0"}:
        return ((Evidence(path, line=user[1]),),)
    if user is not None and user[0].isdigit() and not user[0].lstrip("0"):
        raise Unclear()
    return ()


DOCKER_USER = check(
    "py-container-001",
    "container",
    "Final Python Docker stage selects root",
    "The last USER in the final Python stage explicitly selects root or UID zero.",
    "Set the final USER to a suitable unprivileged account and grant it the required file access.",
    _docker_user,
)
