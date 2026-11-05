"""User story checks, using made-up LLM answers."""
import pytest

from app.nlp import user_stories
from app.nlp.extraction import ExtractionFailed
from app.nlp.user_stories import StoryDraft, generate_story, keep_safe_criteria, story_sentence


def draft(**changes):
    fields = {"role": "user", "feature": "reset my password", "benefit": "I can regain access.",
              "acceptance_criteria": ["A user can reset a password."]}
    return StoryDraft(**{**fields, **changes})


def test_story_format_and_article():
    assert story_sentence("admin", "export data", "I can share it") == "As an admin, I want to export data, so that I can share it."
    assert story_sentence("user", "log in", "I can work").startswith("As a user,")


def test_benefit_is_tidied(monkeypatch):
    monkeypatch.setattr(user_stories, "ask_llm", lambda *_: draft(benefit="Users can regain access."))
    assert generate_story("Users can reset their password.")["benefit"] == "users can regain access"


@pytest.mark.parametrize("feature, expected", [
    ("must not cancel an order", "not cancel an order"),
    ("to reset my password", "reset my password"),
    ("Reset my password.", "reset my password"),
])
def test_feature_fits_after_i_want_to(monkeypatch, feature, expected):
    monkeypatch.setattr(user_stories, "ask_llm", lambda *_: draft(feature=feature))
    requirement = "Customers must not cancel an order." if "not" in feature else "Users can reset their password."
    assert generate_story(requirement)["feature"] == expected


def test_invented_number_in_criteria_is_dropped():
    criteria = ["A user can reset a password.", "The user can reset a password within 5 minutes."]
    assert keep_safe_criteria("Users can reset their password.", criteria) == criteria[:1]


def test_invented_opposite_rule_is_dropped():
    criteria = ["Refunds of 500 dollars must not need managers."]
    result = keep_safe_criteria("Managers can approve refunds above 500 dollars.", criteria)
    assert criteria[0] not in result


def test_mostly_new_words_are_dropped():
    criteria = ["The review includes a rating, photos and a comment."]
    assert criteria[0] not in keep_safe_criteria("Customers can leave a review.", criteria)


def test_requirement_is_used_when_no_criterion_is_safe():
    assert keep_safe_criteria("Users can log in.", ["Dashboards show charts in 5 seconds."]) == ["Users can log in."]


def test_lost_negation_in_feature_is_rejected(monkeypatch):
    monkeypatch.setattr(user_stories, "ask_llm", lambda *_: draft(feature="delete logs"))
    with pytest.raises(ExtractionFailed):
        generate_story("Admins must not delete logs.")


def test_role_not_in_requirement_is_marked_inferred(monkeypatch):
    monkeypatch.setattr(user_stories, "ask_llm", lambda *_: draft(role="manager", feature="send invoices"))
    assert generate_story("The system must send invoices.")["role_inferred"] is True


def test_system_is_not_used_as_a_role(monkeypatch):
    monkeypatch.setattr(user_stories, "ask_llm", lambda *_: draft(role="system", feature="send invoices"))
    story = generate_story("The system must send invoices.")
    assert story["role"] == "user"
    assert story["role_inferred"] is True
