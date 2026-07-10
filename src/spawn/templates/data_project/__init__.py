from spawn.templates.base import BaseTemplate
from spawn.templates.data_project.analysis import DataAnalysisTemplate
from spawn.templates.data_project.dashboard import DashboardTemplate
from spawn.templates.data_project.etl import ETLPipelineTemplate
from spawn.templates.data_project.ml import MLProjectTemplate

_SUBTEMPLATE_MAP = {
    "Data Analysis":    DataAnalysisTemplate,
    "Dashboard":        DashboardTemplate,
    "ETL Pipeline":     ETLPipelineTemplate,
    "Machine Learning": MLProjectTemplate,
}


class DataProjectTemplate(BaseTemplate):
    """
    Dispatcher that returns the appropriate per-data_type subtemplate.

    Uses __new__ so the returned object IS the subtemplate — the registry,
    generator, and prompts.py never need to know about the subtemplates.
    """

    def __new__(
        cls,
        data_type: str = "Data Analysis",
        extras: list[str] | None = None,
    ) -> BaseTemplate:  # type: ignore[misc]
        klass = _SUBTEMPLATE_MAP.get(data_type)
        if klass is not None:
            return klass(extras=extras)
        # Unknown data_type — return a no-op skeleton so the CLI doesn't crash
        instance = super().__new__(cls)
        return instance

    def __init__(
        self,
        data_type: str = "Data Analysis",
        extras: list[str] | None = None,
    ) -> None:
        # Only reached for unrecognised data_types
        if isinstance(self, tuple(_SUBTEMPLATE_MAP.values())):
            return
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
