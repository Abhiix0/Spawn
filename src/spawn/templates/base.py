from dataclasses import dataclass, field


@dataclass
class BaseTemplate:
    name: str
    folders: list[str]
    starter_files: list[tuple[str, str]] = field(default_factory=list)
    # Each tuple: (relative_path_string, content_template_string)
