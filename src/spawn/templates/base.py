from dataclasses import dataclass


@dataclass
class BaseTemplate:
    name: str
    folders: list[str]