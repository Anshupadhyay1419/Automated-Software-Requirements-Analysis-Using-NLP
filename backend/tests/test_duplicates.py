"""Duplicate detection tests. These use the real embedding model."""
from app.nlp.duplicates import review_reason, similar_pairs


def test_identical_requirements_score_one():
    pairs = similar_pairs(["Users can log in.", "Users can log in."], 0.9)
    assert pairs[0][:2] == (0, 1)
    assert pairs[0][2] > 0.99


def test_paraphrase_is_found():
    assert similar_pairs(["Users can log in.", "Users are able to sign in."], 0.6)


def test_unrelated_requirements_are_not_found():
    assert not similar_pairs(["Users can upload a profile photo.", "The database must be backed up nightly."], 0.6)


def test_threshold_is_respected():
    texts = ["Users can log in.", "Users are able to sign in."]
    assert similar_pairs(texts, 0.5)
    assert not similar_pairs(texts, 0.999)


def test_single_requirement_has_no_pairs():
    assert similar_pairs(["Users can log in."], 0.5) == []


def test_highest_score_comes_first():
    pairs = similar_pairs(["Users can log in.", "Users can sign in.", "Users can log in."], 0.3)
    assert pairs == sorted(pairs, key=lambda pair: -pair[2])


def test_negated_pair_gets_a_warning_not_a_duplicate_claim():
    reason = review_reason("Users can delete posts.", "Users must not delete posts.", 0.9)
    assert "contradiction" in reason


def test_different_numbers_get_a_warning():
    assert "numbers differ" in review_reason("Load in 2 seconds.", "Load in 5 seconds.", 0.9)
