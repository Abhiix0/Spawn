import json

SAMPLE_CSV = """\
date,category,value
2024-01-05,Electronics,1200
2024-01-12,Clothing,430
2024-01-18,Electronics,980
2024-01-25,Food,210
2024-02-03,Clothing,560
2024-02-10,Electronics,1450
2024-02-14,Food,330
2024-02-22,Clothing,390
2024-03-01,Electronics,1100
2024-03-08,Food,270
2024-03-15,Clothing,620
2024-03-21,Electronics,870
2024-03-28,Food,190
2024-04-04,Clothing,710
2024-04-11,Electronics,1340
2024-04-18,Food,250
2024-04-25,Clothing,480
"""

NOTEBOOK_CONTENT = json.dumps(
    {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12.0"},
        },
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\n",
                    "import matplotlib.pyplot as plt\n",
                    "\n",
                    'df = pd.read_csv("data/sample.csv", parse_dates=["date"])\n',
                    "df.head()",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "print(df.describe())\n",
                    "print()\n",
                    'summary = df.groupby("category")["value"].sum().reset_index()\n',
                    "print(summary)",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import os\n",
                    'os.makedirs("reports", exist_ok=True)\n',
                    "\n",
                    "fig, ax = plt.subplots(figsize=(8, 5))\n",
                    'ax.bar(summary["category"], summary["value"], color="steelblue")\n',
                    'ax.set_title("Total Value by Category")\n',
                    'ax.set_xlabel("Category")\n',
                    'ax.set_ylabel("Total Value")\n',
                    "plt.tight_layout()\n",
                    'plt.savefig("reports/summary.png", dpi=150)\n',
                    "plt.show()\n",
                    'print("Chart saved to reports/summary.png")',
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## Insights\n",
                    "\n",
                    "_Fill in your observations here after reviewing the chart above._",
                ],
            },
        ],
    },
    indent=2,
)

TEST_CONTENT = """\
import os
from pathlib import Path


def test_sample_csv_exists_and_nonempty():
    import pandas as pd

    df = pd.read_csv("data/sample.csv")
    assert len(df) > 0, "data/sample.csv is empty"
    assert "category" in df.columns
    assert "value" in df.columns


def test_reports_directory_exists():
    reports_path = Path("reports")
    assert reports_path.exists(), (
        "reports/ directory missing — run the notebook first to generate it"
    )
"""


def make_readme() -> str:
    return (
        "# {project_name}\n\n"
        "A Data Analysis project generated with Spawn using pandas, matplotlib, and Jupyter.\n\n"
        "## Getting Started\n\n"
        "1. Install dependencies:\n\n"
        "```bash\n"
        "uv sync\n"
        "```\n\n"
        "2. Launch the notebook:\n\n"
        "```bash\n"
        "uv run jupyter notebook\n"
        "```\n\n"
        "3. Open `notebooks/analysis.ipynb` and run all cells.\n"
        "   A bar chart is saved to `reports/summary.png` automatically.\n\n"
        "## Example\n\n"
        "```\n"
        "$ uv run jupyter notebook\n"
        "# Open notebooks/analysis.ipynb\n"
        "# Run all cells → reports/summary.png is generated\n"
        "```\n\n"
        "## Project Structure\n\n"
        "```\n"
        "{project_name}/\n"
        "├── data/\n"
        "│   └── sample.csv          # Sample sales data\n"
        "├── notebooks/\n"
        "│   └── analysis.ipynb      # Main analysis notebook\n"
        "├── reports/                # Generated charts and outputs\n"
        "├── src/\n"
        "├── tests/\n"
        "│   └── test_analysis.py\n"
        "└── README.md\n"
        "```\n\n"
        "## Running Tests\n\n"
        "```bash\n"
        "uv run pytest\n"
        "```\n"
    )


# ─── GitHub Actions ───────────────────────────────────────────────────────

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

      - name: Install dependencies
        run: uv sync
"""

GITHUB_ACTIONS_CI_RUFF_STEP = """\
      - name: Lint
        run: uv run ruff check .
"""

GITHUB_ACTIONS_CI_PYTEST_STEP = """\
      - name: Test
        run: uv run pytest
"""
