def show_next_steps(project_name: str, template: str, framework: str | None = None) -> str:
    if template == "backend-api":
        if framework == "flask":
            steps = [
                f"cd {project_name}",
                "uv run python run.py",
            ]
        elif framework == "django":
            steps = [
                f"cd {project_name}",
                "uv run python manage.py runserver",
            ]
        else:
            steps = [
                f"cd {project_name}",
                "uv run uvicorn app.main:app --reload",
            ]
        return "\n".join(steps)

    commands = {
        "python": [
            f"cd {project_name}",
            "uv run python main.py",
        ],
        "data-science": [
            f"cd {project_name}",
            "uv add pandas numpy matplotlib",
        ],
        "ml": [
            f"cd {project_name}",
            "uv add pandas numpy scikit-learn",
        ],
    }

    steps = commands.get(template, [])
    return "\n".join(steps)
