"""Extraction checks. These tests use made-up LLM answers to test OUR validation code.
The real model is tested in test_real_llm.py."""
import pytest

from app.nlp import extraction
from app.nlp.extraction import ExtractedRequirement as Item
from app.nlp.extraction import ExtractionFailed, ExtractionResult, extract_requirements, find_problems
from app.nlp.llm import LLMBadOutput
from app.nlp.preprocess import split_into_sentences


def items(*texts):
    return [Item(text=text) for text in texts]


def test_compound_sentence_passes():
    sentence = "Users should register, log in, search products, and place orders."
    answer = items("Users can register.", "Users can log in.", "Users can search products.", "Users can place orders.")
    assert find_problems(sentence, "", answer) == []


def test_lost_negation_is_caught():
    problems = find_problems("Admins must not delete logs.", "", items("Admins must delete logs."))
    assert any("negation" in problem for problem in problems)


def test_added_negation_is_caught():
    problems = find_problems("Admins can delete logs.", "", items("Admins must not delete logs."))
    assert any("negation" in problem for problem in problems)


def test_one_negated_part_is_enough_when_sentence_has_two_parts():
    sentence = "Guests can browse products but must not place orders."
    assert find_problems(sentence, "", items("Guests can browse products.", "Guests must not place orders.")) == []


def test_lost_number_is_caught():
    problems = find_problems("Pages must load within 2 seconds.", "", items("Pages must load quickly within seconds."))
    assert any("Numbers were lost" in problem for problem in problems)


def test_invented_number_is_caught():
    problems = find_problems("Pages must load quickly.", "", items("Pages must load quickly within 2 seconds."))
    assert any("invented" in problem for problem in problems)


def test_invented_feature_is_caught():
    problems = find_problems("Users can log in.", "", items("Users can log in.", "Users can purchase premium subscriptions."))
    assert any("not in the source" in problem for problem in problems)


def test_dropped_part_is_caught():
    sentence = "Customers can cancel orders at any time from their account page."
    problems = find_problems(sentence, "", items("Customers can cancel orders."))
    assert any("missing" in problem for problem in problems)


def test_lost_condition_is_caught():
    problems = find_problems("If payment fails, the system cancels the order.", "", items("Payment fails, the system cancels the order."))
    assert any("Condition" in problem for problem in problems)


def test_empty_answer_is_fine_for_non_requirement():
    assert find_problems("Our company sells furniture.", "", []) == []


def test_empty_answer_is_caught_for_real_requirement():
    assert find_problems("The system must send invoices.", "", []) != []


def test_pronoun_may_be_resolved_from_previous_sentence():
    problems = find_problems("They can export reports.", "Admins can view reports.", items("Admins can export reports."))
    assert problems == []


def test_able_to_wording_does_not_count_as_missing():
    problems = find_problems("Customers must also be able to track deliveries.", "", items("Customers can track deliveries."))
    assert problems == []


def test_bad_answer_is_retried_with_feedback(monkeypatch):
    prompts = []
    answers = [ExtractionResult(requirements=items("Admins must delete logs.")),
               ExtractionResult(requirements=items("Admins must not delete logs."))]

    def fake_llm(_system, prompt, _schema):
        prompts.append(prompt)
        return answers.pop(0)

    monkeypatch.setattr(extraction, "ask_llm", fake_llm)
    result = extract_requirements("Admins must not delete logs.")
    assert [item.text for item in result] == ["Admins must not delete logs."]
    assert "negation" in prompts[1]


def test_repeated_bad_answers_fail_instead_of_saving(monkeypatch):
    monkeypatch.setattr(extraction, "ask_llm", lambda *_: ExtractionResult(requirements=items("Admins must delete logs.")))
    with pytest.raises(ExtractionFailed):
        extract_requirements("Admins must not delete logs.")


def test_invalid_json_fails_instead_of_saving(monkeypatch):
    def broken(*_):
        raise LLMBadOutput("not JSON")
    monkeypatch.setattr(extraction, "ask_llm", broken)
    with pytest.raises(ExtractionFailed):
        extract_requirements("Users can log in.")


def test_guessed_actor_is_removed(monkeypatch):
    answer = ExtractionResult(requirements=[Item(text="Passwords must be encrypted.", actor="system")])
    monkeypatch.setattr(extraction, "ask_llm", lambda *_: answer)
    assert extract_requirements("Passwords must be encrypted.")[0].actor == ""


def test_exact_repeats_in_one_sentence_are_removed(monkeypatch):
    answer = ExtractionResult(requirements=items("Users can log in.", "users can log in."))
    monkeypatch.setattr(extraction, "ask_llm", lambda *_: answer)
    assert len(extract_requirements("Users can log in.")) == 1


def test_sentences_keep_correct_positions():
    text = "Project Overview\n\nUsers can log in. Admins can export data.\n- Guests can browse items\n2. Staff can edit items"
    sentences = split_into_sentences(text)
    assert [s["text"] for s in sentences] == [
        "Users can log in.", "Admins can export data.", "Guests can browse items", "Staff can edit items",
    ]
    for sentence in sentences:
        assert text[sentence["start"]:sentence["end"]] == sentence["text"]
