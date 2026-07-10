from spawn.templates.base import BaseTemplate
from spawn.templates.data_project.analysis import DataAnalysisTemplate
from spawn.templates.data_project.dashboard import DashboardTemplate


class DataProjectTemplate(BaseTemplate):
    """
    Dispatcher that delegates to a per-data_type subtemplate.

    Behaves like any other BaseTemplate from the outside — the registry,
    generator, and prompts.py never need to know about the subtemplates.
    """

    def __new__(
        cls,
        data_type: str = "Data Analysis",
        extras: list[str] | None = None,
    ) -> BaseTemplate:  # type: ignore[misc]
        _map = {
            "Data Analysis": DataAnalysisTemplate,
            "Dashboard":     DashboardTemplate,
        }
        klass = _map.get(data_type)
        if klass is not None:
            return klass(extras=extras)
        # Unimplemented types — return a no-op skeleton so the CLI
        # doesn't crash while other data_types are still in progress.
        instance = super().__new__(cls)
        return instance

    def __init__(
        self,
        data_type: str = "Data Analysis",
        extras: list[str] | None = None,
    ) -> None:
        # Only reached for unimplemented data_types (ETL, ML)
        if isinstance(self, (DataAnalysisTemplate, DashboardTemplate)):
            return  # already fully initialised by subclass __init__
        self.data_type = data_type
        self.extras = extras or []
        super().__init__(
            name="Data Project",
            folders=[],
            starter_files=[],
            next_steps=["cd {project_name}"],
        )

    def get_dependencies(self) -> list[str]:
        return []
