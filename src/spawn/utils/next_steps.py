# ── next_steps.py ──────────────────────────────────────────────────────────────
# Returns template-specific commands shown after project creation.
# ADD the JS entries below to your existing next_steps.py — don't replace the
# whole file, just append the JS block and update get_next_steps if needed.
# ───────────────────────────────────────────────────────────────────────────────

# ── ADD these entries to your existing NEXT_STEPS dict ────────────────────────

JS_NEXT_STEPS: dict[int, list[str]] = {
    9: [                          # Vanilla JS
        "cd {project_name}",
        "npx serve .",
    ],
    10: [                         # Node.js / Express API
        "cd {project_name}",
        "npm install express",
        "node src/index.js",
    ],
    11: [                         # React (Vite)
        "cd {project_name}",
        "npm install react react-dom",
        "npm install --save-dev vite @vitejs/plugin-react",
        "npx vite",
    ],
    12: [                         # Next.js
        "cd {project_name}",
        "npm install next react react-dom",
        "npm run dev",
    ],
}


def get_next_steps(template_id: int, project_name: str) -> list[str]:
    """
    Return next-step commands for the given template with project_name interpolated.
    Checks JS steps first, then falls back to your existing Python steps dict.
    """
    steps = JS_NEXT_STEPS.get(template_id, [])
    # If your existing code has a NEXT_STEPS dict for Python templates,
    # merge it here: steps = {**EXISTING_NEXT_STEPS, **JS_NEXT_STEPS}.get(template_id, [])
    return [step.replace("{project_name}", project_name) for step in steps]
