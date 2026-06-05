from dataclasses import dataclass


@dataclass
class ProjectConfig:
    name: str
    template: str
    use_git: bool