"""Classifier tests. These use the real saved model and data files."""
import json

from dataset import load_app_style, load_split

from app.config import SAVED_MODELS_DIR
from app.nlp.classification import classify


def test_result_shape_and_confidence():
    result = classify(["Users can log in."])[0]
    assert result["type"] in ("functional", "non_functional")
    assert 0 <= result["confidence"] <= 1


def test_empty_input():
    assert classify([]) == []


def test_clear_functional_examples():
    texts = ["Users can register.", "Admins can export reports to PDF.", "Users can search products."]
    assert [row["type"] for row in classify(texts)] == ["functional"] * 3


def test_clear_non_functional_examples():
    texts = ["All passwords must be encrypted.", "The website must be available 99.9% of the time."]
    assert [row["type"] for row in classify(texts)] == ["non_functional"] * 2


def test_functional_has_no_category():
    assert classify(["Users can register."])[0]["category"] is None


def test_test_rows_never_appear_in_training_data():
    train, test = load_split()
    train_texts = {row["text"].lower() for row in train}
    train_texts |= {row["text"].lower() for row in load_app_style("app_style_train.csv")}
    assert not train_texts & {row["text"].lower() for row in test}
    assert not train_texts & {row["text"].lower() for row in load_app_style("app_style_test.csv")}


def test_saved_metrics_have_every_required_measure():
    metrics = json.loads((SAVED_MODELS_DIR / "metrics.json").read_text())
    for section in ("type_model", "category_model", "type_model_cross_project", "type_model_app_style"):
        for measure in ("accuracy", "precision_macro", "recall_macro", "f1_macro", "confusion_matrix"):
            assert measure in metrics[section]
