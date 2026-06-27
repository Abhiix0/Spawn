INIT_CONTENT = ""

MAIN_CONTENT = """\
import logging

from src.utils.logger import setup_logger
from src.workflows.report_workflow import run_report_workflow


def main() -> None:
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("Starting {project_name}")
    run_report_workflow()
    logger.info("{project_name} finished")


if __name__ == "__main__":
    main()
"""

LOGGER_CONTENT = """\
import logging
from pathlib import Path


def setup_logger(log_file: str = "logs/app.log") -> None:
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
"""

REPORT_WORKFLOW_CONTENT = """\
import logging

from src.tasks.data_task import load_sample_data
from src.tasks.report_task import generate_report

logger = logging.getLogger(__name__)


def run_report_workflow() -> None:
    logger.info("Workflow started")
    data = load_sample_data()
    report = generate_report(data)
    logger.info("Report: %s", report)
    logger.info("Workflow complete")
"""

DATA_TASK_CONTENT = """\
import logging

logger = logging.getLogger(__name__)


def load_sample_data() -> dict:
    logger.info("Loading sample data")
    return {{"records": 42, "source": "local"}}
"""

REPORT_TASK_CONTENT = """\
import logging

logger = logging.getLogger(__name__)


def generate_report(data: dict) -> str:
    logger.info("Generating report")
    return f"Records processed: {{data['records']}}"
"""

TEST_CONTENT = """\
from src.tasks.data_task import load_sample_data
from src.tasks.report_task import generate_report


def test_load_sample_data():
    data = load_sample_data()
    assert isinstance(data, dict)
    assert "records" in data


def test_generate_report():
    data = {{"records": 10, "source": "test"}}
    report = generate_report(data)
    assert "10" in report
"""

ENV_EXAMPLE_CONTENT = """\
APP_NAME={project_name}
DEBUG=True
"""

README_CONTENT = """\
# {project_name}

An automation project generated with Spawn.

## Getting Started

```bash
uv run python src/main.py
```

## Project Structure

```
{project_name}/
├── src/
│   ├── workflows/      # Business workflows
│   ├── tasks/          # Reusable task modules
│   ├── integrations/   # External service connectors
│   ├── utils/          # Shared helpers
│   └── main.py         # Entry point
├── logs/               # Application logs
├── tests/
├── .env.example
└── README.md
```

## Running Tests

```bash
uv run pytest
```

## Logs

Logs are written to `logs/app.log` and printed to the console.

## Workflow Overview

Load sample data → Generate report → Log output → Workflow complete

## Future Expansions

```bash
spawn add scheduler
spawn add openai
spawn add slack
spawn add database
```
"""

GITHUB_ACTIONS_CI_BASE = """\
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5

      - run: uv sync --all-extras --dev
"""

GITHUB_ACTIONS_CI_RUFF_STEP = """\
      - name: Lint
        run: uv run ruff check .
"""

GITHUB_ACTIONS_CI_PYTEST_STEP = """\
      - name: Test
        run: uv run pytest
"""
