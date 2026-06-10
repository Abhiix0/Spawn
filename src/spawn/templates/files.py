PYTHON_MAIN_CONTENT = """\
def main():
    print("Hello from {project_name}!")


if __name__ == "__main__":
    main()
"""

FASTAPI_MAIN_CONTENT = """\
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {{"message": "Hello from {project_name}!"}}
"""

DATA_SCIENCE_MAIN_CONTENT = """\
import os


def main():
    print("Starting {project_name} analysis...")


if __name__ == "__main__":
    main()
"""

ML_MAIN_CONTENT = """\
import os


def main():
    print("Starting {project_name} ML pipeline...")


if __name__ == "__main__":
    main()
"""

README_CONTENT = """# {project_name}

Project generated with Spawn.
"""

GITIGNORE_CONTENT = """# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.pyc

# Virtual environments
.venv/
venv/
env/

# Distribution / packaging
dist/
build/
*.egg-info/
*.egg

# uv
.uv/
uv.lock

# Environment variables
.env
.env.*

# IDEs
.vscode/
.idea/
*.iml

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Mypy
.mypy_cache/
"""