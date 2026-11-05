"""Measures the saved models on the held-out test set. Run:  python backend/training/evaluate.py

Results are printed and saved to saved_models/metrics.json, which the app shows.
"""
import json
from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline

from dataset import load_app_style, load_rows, load_split
from train import make_model, make_vectorizer

MODEL_DIR = Path(__file__).parents[1] / "saved_models"


def score(true_labels, predicted, labels, positive=None):
    """Accuracy, precision, recall, F1 and confusion matrix for one model."""
    precision, recall, f1, _ = precision_recall_fscore_support(
        true_labels, predicted, labels=labels, average="macro", zero_division=0
    )
    return {
        "test_rows": len(true_labels),
        "labels": labels,
        "accuracy": round(accuracy_score(true_labels, predicted), 3),
        "precision_macro": round(precision, 3),
        "recall_macro": round(recall, 3),
        "f1_macro": round(f1, 3),
        "confusion_matrix": confusion_matrix(true_labels, predicted, labels=labels).tolist(),
    }


def cross_project_f1(rows, folds=5):
    """A harder test: train on some projects and test on completely different ones.
    This is closer to real use, because a new client's wording is new to the model."""
    texts = [row["text"] for row in rows]
    labels = [row["type"] for row in rows]
    groups = [row["project"] for row in rows]
    extra = load_app_style("app_style_train.csv")
    predictions = [None] * len(rows)
    for train_index, test_index in GroupKFold(n_splits=folds).split(texts, labels, groups):
        model = make_pipeline(make_vectorizer(), make_model())
        model.fit(
            [texts[i] for i in train_index] + [row["text"] for row in extra],
            [labels[i] for i in train_index] + [row["type"] for row in extra],
        )
        for i, prediction in zip(test_index, model.predict([texts[i] for i in test_index])):
            predictions[i] = prediction
    return score(labels, predictions, ["functional", "non_functional"])


def main():
    vectorizer = joblib.load(MODEL_DIR / "tfidf_vectorizer.joblib")
    type_model = joblib.load(MODEL_DIR / "type_model.joblib")
    category_model = joblib.load(MODEL_DIR / "category_model.joblib")
    train_rows, test_rows = load_split()
    train_rows = train_rows + load_app_style("app_style_train.csv")

    predicted_types = type_model.predict(vectorizer.transform([row["text"] for row in test_rows]))
    type_scores = score([row["type"] for row in test_rows], predicted_types.tolist(), ["functional", "non_functional"])

    nfr_test = [row for row in test_rows if row["type"] == "non_functional"]
    predicted_categories = category_model.predict(vectorizer.transform([row["text"] for row in nfr_test]))
    category_labels = sorted({row["category"] for row in nfr_test})
    category_scores = score([row["category"] for row in nfr_test], predicted_categories.tolist(), category_labels)

    # Second test: short sentences like the ones this app actually classifies.
    app_test = load_app_style("app_style_test.csv")
    predicted_app = type_model.predict(vectorizer.transform([row["text"] for row in app_test]))
    app_scores = score([row["type"] for row in app_test], predicted_app.tolist(), ["functional", "non_functional"])

    metrics = {
        "dataset": "PROMISE_exp (Lima et al., 2019) plus hand-written app-style examples",
        "train_rows": len(train_rows),
        "type_model": type_scores,
        "category_model": category_scores,
        "type_model_cross_project": cross_project_f1(load_rows()),
        "type_model_app_style": app_scores,
    }
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
