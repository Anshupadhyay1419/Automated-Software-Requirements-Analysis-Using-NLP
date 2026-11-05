"""Tests with the REAL Ollama model. Run with:  python -m pytest -m llm -o addopts="" -v
LLM output can vary, so a failure here may mean the model made a mistake, not the code."""
import pytest

from app.nlp.extraction import extract_requirements
from app.nlp.llm import LLMUnavailable, active_model
from app.nlp.preprocess import has_negation
from app.nlp.quality import llm_contradiction
from app.nlp.user_stories import generate_story

pytestmark = pytest.mark.llm


@pytest.fixture(autouse=True)
def need_ollama():
    try:
        active_model()
    except LLMUnavailable as error:
        pytest.skip(str(error))


def texts(sentence, context=""):
    return [item.text for item in extract_requirements(sentence, context)]


def test_brief_example_gives_four_requirements():
    assert len(texts("Users should register, log in, search products, and place orders.")) == 4


def test_negation_is_kept():
    result = texts("Guests can browse products but must not place orders.")
    assert len(result) == 2
    assert sum(has_negation(text) for text in result) == 1


def test_condition_is_repeated():
    result = texts("If a payment fails, the system shall notify the customer and cancel the order.")
    assert len(result) == 2
    assert all("if a payment fails" in text.lower() for text in result)


def test_limit_stays_with_action():
    result = texts("Only managers can approve refunds above 500 dollars.")
    assert len(result) == 1
    assert "500" in result[0]


def test_non_requirement_gives_nothing():
    assert texts("Our company was founded in 2009 and sells furniture.") == []


def test_pronoun_uses_previous_sentence():
    assert "admin" in texts("They can also export reports to PDF.", "Admins can add users and view reports.")[0].lower()


def test_real_contradiction_is_noticed():
    assert llm_contradiction("All users must be able to delete their account.", "Users are never allowed to delete their account.")


def test_compatible_requirements_are_not_a_contradiction():
    assert llm_contradiction("Users can upload a photo.", "Users can view their order history.") is None


def test_story_keeps_negation():
    assert has_negation(generate_story("Guests must not place orders.")["feature"])
