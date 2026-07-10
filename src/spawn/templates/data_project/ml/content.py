ML_SAMPLE_CSV = """\
feature_1,feature_2,feature_3,feature_4,target
2.5,1.4,0.3,0.1,0
4.7,3.2,1.3,0.2,0
4.6,3.1,1.5,0.2,0
5.0,3.6,1.4,0.2,0
5.4,3.9,1.7,0.4,0
4.6,3.4,1.4,0.3,0
5.0,3.4,1.5,0.2,0
4.4,2.9,1.4,0.2,0
4.9,3.1,1.5,0.1,0
5.4,3.7,1.5,0.2,0
4.8,3.4,1.6,0.2,0
4.8,3.0,1.4,0.1,0
4.3,3.0,1.1,0.1,0
5.8,4.0,1.2,0.2,0
5.7,4.4,1.5,0.4,0
5.4,3.9,1.3,0.4,0
5.1,3.5,1.4,0.3,0
5.7,3.8,1.7,0.3,0
5.1,3.8,1.5,0.3,0
5.4,3.4,1.7,0.2,0
7.0,3.2,4.7,1.4,1
6.4,3.2,4.5,1.5,1
6.9,3.1,4.9,1.5,1
5.5,2.3,4.0,1.3,1
6.5,2.8,4.6,1.5,1
5.7,2.8,4.5,1.3,1
6.3,3.3,4.7,1.6,1
4.9,2.4,3.3,1.0,1
6.6,2.9,4.6,1.3,1
5.2,2.7,3.9,1.4,1
5.0,2.0,3.5,1.0,1
5.9,3.0,4.2,1.5,1
6.0,2.2,4.0,1.0,1
6.1,2.9,4.7,1.4,1
5.6,2.9,3.6,1.3,1
6.7,3.1,4.4,1.4,1
5.6,3.0,4.5,1.5,1
5.8,2.7,4.1,1.0,1
6.2,2.2,4.5,1.5,1
5.6,2.5,3.9,1.1,1
"""

ML_TRAIN_CONTENT = """\
import json
import os
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


def train() -> None:
    data_path = Path("data/dataset.csv")
    if not data_path.exists():
        print(f"Dataset not found at {{data_path}}. Ensure data/dataset.csv exists.")
        return

    df = pd.read_csv(data_path)
    feature_cols = [c for c in df.columns if c != "target"]
    X = df[feature_cols].values
    y = df["target"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    print(f"Test accuracy: {{accuracy:.4f}}")

    Path("models").mkdir(exist_ok=True)
    model_path = Path("models/model.joblib")
    joblib.dump(clf, model_path)
    print(f"Model saved to {{model_path}}")

    Path("experiments").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment = {{
        "timestamp": timestamp,
        "accuracy": accuracy,
        "model_type": "RandomForestClassifier",
        "n_train": len(X_train),
        "n_test": len(X_test),
    }}
    exp_path = Path(f"experiments/{{timestamp}}.json")
    exp_path.write_text(json.dumps(experiment, indent=2), encoding="utf-8")
    print(f"Experiment logged to {{exp_path}}")


if __name__ == "__main__":
    train()
"""

ML_TEST_CONTENT = """\
import json
from pathlib import Path

import pytest


def test_train_produces_model(tmp_path, monkeypatch):
    import shutil

    monkeypatch.chdir(tmp_path)
    # Copy the bundled dataset into the tmp working directory
    src_dataset = Path(__file__).parent.parent / "data" / "dataset.csv"
    (tmp_path / "data").mkdir()
    shutil.copy(src_dataset, tmp_path / "data" / "dataset.csv")

    from src.train import train
    train()

    model_path = tmp_path / "models" / "model.joblib"
    assert model_path.exists(), "models/model.joblib was not created"


def test_train_accuracy_is_valid(tmp_path, monkeypatch):
    import shutil

    monkeypatch.chdir(tmp_path)
    src_dataset = Path(__file__).parent.parent / "data" / "dataset.csv"
    (tmp_path / "data").mkdir()
    shutil.copy(src_dataset, tmp_path / "data" / "dataset.csv")

    from src.train import train
    train()

    exp_files = list((tmp_path / "experiments").glob("*.json"))
    assert exp_files, "No experiment file written"
    experiment = json.loads(exp_files[0].read_text(encoding="utf-8"))
    accuracy = experiment["accuracy"]
    assert isinstance(accuracy, float)
    assert 0.0 <= accuracy <= 1.0, f"Accuracy out of range: {{accuracy}}"


def test_dataset_csv_exists():
    assert Path("data/dataset.csv").exists(), "data/dataset.csv must exist"
"""


def make_readme() -> str:
    return (
        "# {project_name}\n\n"
        "A Machine Learning project generated with Spawn using scikit-learn.\n\n"
        "## Getting Started\n\n"
        "1. Install dependencies:\n\n"
        "```bash\n"
        "uv sync\n"
        "```\n\n"
        "2. Train the model:\n\n"
        "```bash\n"
        "uv run python src/train.py\n"
        "```\n\n"
        "Each run trains a `RandomForestClassifier` on `data/dataset.csv`, saves\n"
        "the model to `models/model.joblib`, and writes a timestamped JSON to\n"
        "`experiments/` with accuracy and metadata.\n\n"
        "## Example\n\n"
        "```\n"
        "$ uv run python src/train.py\n"
        "Test accuracy: 0.9750\n"
        "Model saved to models/model.joblib\n"
        "Experiment logged to experiments/20240101_120000.json\n"
        "```\n\n"
        "## Experiment Tracking\n\n"
        "Every training run appends a new file to `experiments/`:\n\n"
        "```json\n"
        "{{\n"
        '  "timestamp": "20240101_120000",\n'
        '  "accuracy": 0.975,\n'
        '  "model_type": "RandomForestClassifier",\n'
        '  "n_train": 32,\n'
        '  "n_test": 8\n'
        "}}\n"
        "```\n\n"
        "## Project Structure\n\n"
        "```\n"
        "{project_name}/\n"
        "├── data/\n"
        "│   └── dataset.csv         # Labeled training data\n"
        "├── models/\n"
        "│   └── model.joblib        # Saved model (created on first run)\n"
        "├── experiments/            # Per-run JSON metrics\n"
        "├── src/\n"
        "│   └── train.py            # Training script\n"
        "├── tests/\n"
        "│   └── test_ml.py\n"
        "└── README.md\n"
        "```\n\n"
        "## Running Tests\n\n"
        "```bash\n"
        "uv run pytest\n"
        "```\n"
    )
