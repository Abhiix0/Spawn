from spawn.templates.base import BaseTemplate


class DataProjectTemplate(BaseTemplate):
    def __init__(
        self,
        data_type: str = "Data Analysis",
        extras: list[str] | None = None,
    ) -> None:
        self.data_type = data_type
        self.extras = extras or []

        super().__init__(
            name="Data Project",
            folders=[],
            starter_files=[],
        )

    def get_dependencies(self) -> list[str]:
        return []
