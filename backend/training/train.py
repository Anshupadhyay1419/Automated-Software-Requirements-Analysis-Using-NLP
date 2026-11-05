"""Trains the classifier and saves it. Run:  python backend/training/train.py"""
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from dataset import load_app_style, load_split

OUTPUT_DIR = Path(__file__).parents[1] / "saved_models"


def make_vectorizer():
    # ngram_range=(1, 2) uses single words and word pairs, such as "response time".
    # min_df=2 ignores anything that appears in only one requirement.
    return TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, sublinear_tf=True)


def make_model():
    # class_weight="balanced" stops the larger classes from dominating.
    return LogisticRegression(max_iter=2000, class_weight="balanced")


def main():
    promise_train, test_rows = load_split()
    # PROMISE is formal ("The system shall..."), but the LLM writes short sentences
    # ("Users can log in."), so we also train on examples written in that style.
    train_rows = promise_train + load_app_style("app_style_train.csv")
    train_texts = [row["text"] for row in train_rows]
    print(f"Training rows: {len(train_rows)}, held-out PROMISE test rows: {len(test_rows)}")

    # Step 1: learn the vocabulary from training text only.
    vectorizer = make_vectorizer()
    vectors = vectorizer.fit_transform(train_texts)

    # Step 2: learn functional vs non-functional.
    type_model = make_model().fit(vectors, [row["type"] for row in train_rows])

    # Step 3: learn the category, using only the non-functional rows.
    nfr_rows = [row for row in train_rows if row["type"] == "non_functional"]
    nfr_vectors = vectorizer.transform([row["text"] for row in nfr_rows])
    category_model = make_model().fit(nfr_vectors, [row["category"] for row in nfr_rows])

    # Step 4: save everything.
    OUTPUT_DIR.mkdir(exist_ok=True)
    joblib.dump(vectorizer, OUTPUT_DIR / "tfidf_vectorizer.joblib")
    joblib.dump(type_model, OUTPUT_DIR / "type_model.joblib")
    joblib.dump(category_model, OUTPUT_DIR / "category_model.joblib")
    print(f"Saved vectorizer and models to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
