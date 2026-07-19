from dataclasses import dataclass, field


@dataclass
class ProjectConfig:
    name: str
    template: str
    use_git: bool
    framework: str | None = None
    extras: list[str] = field(default_factory=list)
    cli_type: str | None = None
    data_type: str | None = None
    provider: str | None = None
    use_uv: bool = True
    custom_entries: list | None = None   # list[ParsedEntry] when template == "custom"
    custom_dependencies: list[str] = field(default_factory=list)
