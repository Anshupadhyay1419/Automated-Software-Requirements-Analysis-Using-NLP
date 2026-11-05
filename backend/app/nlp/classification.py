"""Requirement classification with TF-IDF and Logistic Regression. No LLM is used here.

  TF-IDF turns text into numbers: words that are common in this requirement
  but rare overall get a high score.
  Logistic Regression learns which words point to each class.

Two models are used:
  type model     : functional or non_functional
  category model : which kind of non-functional (only used for non_functional)

Train them with:  python backend/training/train.py
"""
from functools import lru_cache

import joblib

from ..config import SAVED_MODELS_DIR


class ModelNotTrained(Exception):
    pass


@lru_cache(maxsize=1)
def load_models():
    try:
        return (
            joblib.load(SAVED_MODELS_DIR / "tfidf_vectorizer.joblib"),
            joblib.load(SAVED_MODELS_DIR / "type_model.joblib"),
            joblib.load(SAVED_MODELS_DIR / "category_model.joblib"),
        )
    except FileNotFoundError as error:
        raise ModelNotTrained("Classifier not found. Run: python backend/training/train.py") from error


def classify(texts: list[str]) -> list[dict]:
    """Example result: {"type": "non_functional", "category": "performance", "confidence": 0.91}"""
    if not texts:
        return []
    vectorizer, type_model, category_model = load_models()
    vectors = vectorizer.transform(texts)
    types = type_model.predict(vectors)
    confidences = type_model.predict_proba(vectors).max(axis=1)
    categories = category_model.predict(vectors)
    return [
        {
            "type": str(req_type),
            "category": str(category) if req_type == "non_functional" else None,
            "confidence": round(float(confidence), 3),
        }
        for req_type, category, confidence in zip(types, categories, confidences)
    ]
