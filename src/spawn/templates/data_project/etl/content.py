ETL_RAW_CSV = """\
date,category,amount,notes
2024-01-05,Sales,1200,Q1 kickoff
2024-01-12,sales,430,
2024-01-18,SALES,980,follow-up
2024-01-25,Marketing,210,campaign
2024-02-03,marketing,560,
2024-02-10,MARKETING,1450,conference
2024-02-14,Operations,330,
2024-02-22,operations,390,routine
2024-03-01,OPERATIONS,1100,audit
2024-03-08,Sales,270,
2024-03-15,sales,620,Q2 push
2024-03-21,,870,unknown category
2024-03-28,Marketing,190,
2024-04-04,MARKETING,710,Q2 end
2024-04-11,Operations,1340,
2024-04-18,Sales,250,follow-up
"""

ETL_CLEAN_CONTENT = """\
import os
import sys

import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def run() -> None:
    input_path = os.getenv("INPUT_PATH", "data/raw.csv")
    output_path = os.getenv("OUTPUT_PATH", "data/cleaned.csv")

    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"Input file not found at {{input_path}}. Check INPUT_PATH in .env.")
        sys.exit(1)

    original_count = len(df)

    # Normalise category: lowercase and strip whitespace
    df["category"] = df["category"].str.lower().str.strip()

    # Drop rows with missing values in required columns
    required_cols = ["date", "category", "amount"]
    df = df.dropna(subset=required_cols)

    cleaned_count = len(df)
    dropped = original_count - cleaned_count

    df.to_csv(output_path, index=False)

    print(f"Cleaned {{cleaned_count}} rows (dropped {{dropped}} with missing values).")
    print(f"Output written to {{output_path}}")


if __name__ == "__main__":
    run()
"""

ETL_RUN_CONTENT = """\
import os

from dotenv import load_dotenv

from pipelines.clean_data import run as clean

load_dotenv()


def main() -> None:
    output_path = os.getenv("OUTPUT_PATH", "data/cleaned.csv")
    clean()
    print(f"Pipeline complete. Output written to {{output_path}}")


if __name__ == "__main__":
    main()
"""

ETL_ENV_CONTENT = """\
APP_NAME={project_name}
INPUT_PATH=data/raw.csv
OUTPUT_PATH=data/cleaned.csv
"""

ETL_TEST_CONTENT = """\
import os
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture()
def raw_csv(tmp_path: Path) -> Path:
    content = (
        "date,category,amount,notes\\n"
        "2024-01-05,Sales,100,ok\\n"
        "2024-01-06,SALES,200,\\n"
        "2024-01-07,marketing,300,ok\\n"
        "2024-01-08,,400,missing category\\n"
        "2024-01-09,operations,,missing amount\\n"
    )
    p = tmp_path / "raw.csv"
    p.write_text(content, encoding="utf-8")
    return p


def test_clean_produces_lowercase_categories(raw_csv: Path, tmp_path: Path):
    out = tmp_path / "cleaned.csv"
    os.environ["INPUT_PATH"] = str(raw_csv)
    os.environ["OUTPUT_PATH"] = str(out)

    from pipelines.clean_data import run
    run()

    df = pd.read_csv(out)
    assert all(df["category"] == df["category"].str.lower().str.strip()), (
        "category values are not all lowercase"
    )


def test_clean_drops_rows_with_missing_required_values(raw_csv: Path, tmp_path: Path):
    out = tmp_path / "cleaned.csv"
    os.environ["INPUT_PATH"] = str(raw_csv)
    os.environ["OUTPUT_PATH"] = str(out)

    from pipelines.clean_data import run
    run()

    df = pd.read_csv(out)
    # Rows with missing category or amount should be gone
    assert df["category"].notna().all(), "cleaned CSV still has missing category"
    assert df["amount"].notna().all(), "cleaned CSV still has missing amount"


def test_clean_missing_input_exits(tmp_path: Path):
    os.environ["INPUT_PATH"] = str(tmp_path / "nonexistent.csv")
    os.environ["OUTPUT_PATH"] = str(tmp_path / "out.csv")

    from pipelines.clean_data import run
    with pytest.raises(SystemExit) as exc_info:
        run()
    assert exc_info.value.code == 1


def test_raw_csv_exists():
    assert Path("data/raw.csv").exists(), "data/raw.csv must exist"
"""


def make_readme() -> str:
    return (
        "# {project_name}\n\n"
        "An ETL Pipeline generated with Spawn using pandas and python-dotenv.\n\n"
        "## Getting Started\n\n"
        "1. Rename `.env.example` to `.env` (optional — defaults work out of the box):\n\n"
        "```bash\n"
        "# .env\n"
        "INPUT_PATH=data/raw.csv\n"
        "OUTPUT_PATH=data/cleaned.csv\n"
        "```\n\n"
        "2. Install dependencies:\n\n"
        "```bash\n"
        "uv sync\n"
        "```\n\n"
        "3. Run the pipeline:\n\n"
        "```bash\n"
        "uv run python pipelines/run.py\n"
        "```\n\n"
        "## Configuration\n\n"
        "`INPUT_PATH` and `OUTPUT_PATH` are read from `.env` (via python-dotenv).\n"
        "Override them to point at any CSV file without editing code:\n\n"
        "```env\n"
        "INPUT_PATH=data/my_data.csv\n"
        "OUTPUT_PATH=data/my_data_clean.csv\n"
        "```\n\n"
        "## What the Pipeline Does\n\n"
        "1. Reads the raw CSV from `INPUT_PATH`\n"
        "2. Normalises the `category` column (lowercase + strip whitespace)\n"
        "3. Drops rows with missing values in required columns\n"
        "4. Writes the cleaned CSV to `OUTPUT_PATH`\n\n"
        "## Project Structure\n\n"
        "```\n"
        "{project_name}/\n"
        "├── data/\n"
        "│   ├── raw.csv             # Source data\n"
        "│   └── cleaned.csv         # Output (created on first run)\n"
        "├── pipelines/\n"
        "│   ├── clean_data.py       # Cleaning logic\n"
        "│   └── run.py              # Pipeline entry point\n"
        "├── src/\n"
        "├── tests/\n"
        "│   └── test_etl.py\n"
        "├── .env.example\n"
        "└── README.md\n"
        "```\n\n"
        "## Running Tests\n\n"
        "```bash\n"
        "uv run pytest\n"
        "```\n"
    )
