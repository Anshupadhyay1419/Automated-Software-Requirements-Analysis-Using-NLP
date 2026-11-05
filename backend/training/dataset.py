"""Loads the training data and makes one fixed train/test split.

train.py and evaluate.py both use this file, so test rows are never used for training.

Data files (see data/README.md):
  PROMISE_exp.csv     real, published requirements (split into train and test)
  app_style_train.csv hand-written short examples, used for training only
  app_style_test.csv  hand-written short examples, used for testing only
"""
import csv
from pathlib import Path

from sklearn.model_selection import train_test_split

DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "PROMISE_exp.csv"
RANDOM_SEED = 42
TEST_SIZE = 0.2

# The dataset has 11 non-functional labels. We group them into the project's categories.
# This grouping is our own design decision, not part of the dataset.
CATEGORY_OF_LABEL = {
    "PE": "performance", "SC": "performance",        # performance, scalability
    "SE": "security",
    "US": "usability", "LF": "usability",            # usability, look and feel
    "A": "reliability", "FT": "reliability",         # availability, fault tolerance
    "MN": "maintainability", "PO": "maintainability",  # maintainability, portability
    "O": "other", "L": "other",                      # operational, legal
}


def load_rows() -> list[dict]:
    """Each row: text, type, category, project. Exact repeats are removed so that the
    same sentence cannot appear in both the training and the test set."""
    rows, seen = [], set()
    with open(DATA_FILE, encoding="utf-8") as file:
        for row in csv.DictReader(file):
            text = " ".join(row["RequirementText"].split())
            label = row["_class_"].strip()
            if text.lower() in seen:
                continue
            seen.add(text.lower())
            rows.append({
                "text": text,
                "type": "functional" if label == "F" else "non_functional",
                "category": CATEGORY_OF_LABEL.get(label),
                "project": row["ProjectID"],
            })
    return rows


def load_app_style(filename: str) -> list[dict]:
    """Short sentences in the style the LLM writes, such as "Users can log in."."""
    with open(DATA_DIR / filename, encoding="utf-8") as file:
        return [
            {"text": row["text"], "type": row["type"], "category": row.get("category") or None}
            for row in csv.DictReader(file)
        ]


def load_split():
    """Returns (train_rows, test_rows), 80/20, keeping the class balance in both."""
    rows = load_rows()
    return train_test_split(
        rows, test_size=TEST_SIZE, random_state=RANDOM_SEED, stratify=[row["type"] for row in rows]
    )
