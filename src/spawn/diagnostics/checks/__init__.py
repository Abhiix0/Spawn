"""Explicit catalog of static Python configuration checks."""

from .configuration import MAKE_CONFIG, PYTEST_PATHS, REQUIREMENTS
from .container import DOCKER_USER
from .entry import CONSOLE_TARGET

RULES = (CONSOLE_TARGET, PYTEST_PATHS, MAKE_CONFIG, REQUIREMENTS, DOCKER_USER)
