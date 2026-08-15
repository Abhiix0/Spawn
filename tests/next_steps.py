# ── next_steps.py ──────────────────────────────────────────────────────────────
# Returns the template-specific commands to show after project creation.
# Keys match the template numbers defined in registry.py.
# ───────────────────────────────────────────────────────────────────────────────

NEXT_STEPS: dict[int, list[str]] = {
    # ── Python ──────────────────────────────────────────────────────────────────
    1: [
        "cd {project_name}",
        "uv run python main.py",
    ],
    2: [
        "cd {project_name}",
        "uv add fastapi uvicorn",
        "uv run uvicorn app.main:app --reload",
    ],
    3: [
        "cd {project_name}",
        "uv add pandas numpy matplotlib",
        "uv run jupyter notebook",
    ],
    4: [
        "cd {project_name}",
        "uv add pandas numpy scikit-learn",
        "uv run python src/train.py",
    ],
    # ── JavaScript ──────────────────────────────────────────────────────────────
    5: [
        "cd {project_name}",
        "# Open index.html in your browser, or:",
        "npx serve .",
    ],
    6: [
        "cd {project_name}",
        "npm install express",
        "node src/index.js",
        "# or for auto-reload:",
        "npx nodemon src/index.js",
    ],
    7: [
        "cd {project_name}",
        "npm install react react-dom",
        "npm install --save-dev vite @vitejs/plugin-react",
        "npx vite",
    ],
    8: [
        "cd {project_name}",
        "npm install next react react-dom",
        "npm run dev",
    ],
}


def get_next_steps(template_id: int, project_name: str) -> list[str]:
    """Return next-step commands for the given template, with project_name interpolated."""
    steps = NEXT_STEPS.get(template_id, [])
    return [step.replace("{project_name}", project_name) for step in steps]
