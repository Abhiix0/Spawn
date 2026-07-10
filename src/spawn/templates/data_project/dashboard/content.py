from spawn.templates.data_project.analysis.content import SAMPLE_CSV

# Reuse the same sample dataset — date/category/value fits both use cases
DASHBOARD_SAMPLE_CSV = SAMPLE_CSV

DASHBOARD_APP_CONTENT = """\
import pandas as pd
import plotly.express as px
import streamlit as st

df = pd.read_csv("data/sample.csv", parse_dates=["date"])

st.title("{project_name} Dashboard")

# ── Sidebar filters ───────────────────────────────────────────────────────
st.sidebar.header("Filters")
all_categories = sorted(df["category"].unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Category",
    options=all_categories,
    default=all_categories,
)

filtered = df[df["category"].isin(selected_categories)]

# ── Raw data ──────────────────────────────────────────────────────────────
st.subheader("Raw Data")
st.dataframe(filtered, use_container_width=True)

# ── Chart ─────────────────────────────────────────────────────────────────
st.subheader("Total Value by Category")
summary = filtered.groupby("category")["value"].sum().reset_index()
fig = px.bar(
    summary,
    x="category",
    y="value",
    color="category",
    title="Total Value by Category",
    labels={{"category": "Category", "value": "Total Value"}},
)
st.plotly_chart(fig, use_container_width=True)
"""

DASHBOARD_TEST_CONTENT = """\
def test_sample_csv_loads_with_expected_columns():
    import pandas as pd

    df = pd.read_csv("data/sample.csv")
    assert len(df) > 0, "data/sample.csv is empty"
    assert "date" in df.columns
    assert "category" in df.columns
    assert "value" in df.columns


def test_dashboard_app_exists():
    from pathlib import Path

    assert Path("dashboard/app.py").exists(), "dashboard/app.py is missing"
"""


def make_readme() -> str:
    return (
        "# {project_name}\n\n"
        "An interactive Dashboard generated with Spawn using Streamlit and Plotly.\n\n"
        "## Getting Started\n\n"
        "1. Install dependencies:\n\n"
        "```bash\n"
        "uv sync\n"
        "```\n\n"
        "2. Launch the dashboard:\n\n"
        "```bash\n"
        "uv run streamlit run dashboard/app.py\n"
        "```\n\n"
        "3. Open the URL shown in the terminal (usually http://localhost:8501).\n\n"
        "## Example\n\n"
        "```\n"
        "$ uv run streamlit run dashboard/app.py\n"
        "  Local URL: http://localhost:8501\n"
        "# Use the sidebar to filter by category\n"
        "```\n\n"
        "## Adding Data\n\n"
        "Replace `data/sample.csv` with your own CSV that has `date`, `category`,\n"
        "and `value` columns (or update `dashboard/app.py` to match your schema).\n\n"
        "## Project Structure\n\n"
        "```\n"
        "{project_name}/\n"
        "├── data/\n"
        "│   └── sample.csv          # Sample sales data\n"
        "├── dashboard/\n"
        "│   └── app.py              # Streamlit application\n"
        "├── src/\n"
        "├── tests/\n"
        "│   └── test_dashboard.py\n"
        "└── README.md\n"
        "```\n\n"
        "## Running Tests\n\n"
        "```bash\n"
        "uv run pytest\n"
        "```\n"
    )
