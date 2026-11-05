"""User stories: draft "As a [role], I want [feature], so that [benefit]." from one requirement.

Everything here is a draft. The benefit and acceptance criteria are suggestions that the client
did not state, so simple checks reject drafts that add facts or reverse the meaning.
"""
import re

from pydantic import BaseModel, Field

from .extraction import ExtractionFailed
from .llm import LLMBadOutput, ask_llm
from .preprocess import content_words, has_negation, numbers_in

NOT_A_PERSON = {"system", "website", "application", "app", "software", "platform"}

SYSTEM_PROMPT = """You draft an agile user story from one software requirement.

Rules:
- role: the actor in the requirement, in singular form. If no person is named, use "user".
- feature: what the role wants, starting with a verb. Keep the meaning, including any "not".
- benefit: one short and general reason. Do not invent business rules.
- acceptance_criteria: 1 to 3 short, testable checks based only on the requirement.
  Reuse the requirement's own words. Do not add numbers, limits, roles, screens, fields or
  technologies that the requirement does not state. Do not describe the opposite case.

Example requirement: "Users can reset their password."
{"role":"user","feature":"reset my password","benefit":"I can regain access to my account","acceptance_criteria":["A user can start a password reset.","After a reset, the user can log in with the new password."]}"""


class StoryDraft(BaseModel):
    role: str = Field(min_length=2)
    feature: str = Field(min_length=3)
    benefit: str = Field(min_length=3)
    acceptance_criteria: list[str]


def find_problems(requirement: str, draft: StoryDraft) -> list[str]:
    problems = []
    if has_negation(requirement) and not has_negation(draft.feature):
        problems.append('The requirement has a negation, so the feature must keep it (for example "not").')
    words = content_words(requirement)
    if words and not (content_words(draft.feature) & words):
        problems.append("The feature must use the requirement's own words.")
    return problems


def keep_safe_criteria(requirement: str, criteria: list[str]) -> list[str]:
    """Drop criteria that add facts the requirement never stated:
      - a new number, such as "within 5 seconds"
      - a new negation, such as "smaller refunds do not need approval"
      - mostly new words, such as "the review includes a rating and a comment"
    """
    allowed_words = content_words(requirement)
    safe = []
    for item in criteria:
        words = content_words(item)
        adds_number = not numbers_in(item) <= numbers_in(requirement)
        adds_negation = has_negation(item) and not has_negation(requirement)
        mostly_new = bool(words) and len(words & allowed_words) / len(words) < 0.6
        if not (adds_number or adds_negation or mostly_new):
            safe.append(item)
    # If nothing is safe, restating the requirement is always a valid check.
    return safe[:3] or [requirement]


def tidy(text: str) -> str:
    """Remove trailing full stops, and lowercase the first letter unless it is "I"."""
    text = text.strip().rstrip(".").strip()
    return text if text.startswith("I ") or not text else text[0].lower() + text[1:]


def clean_feature(feature: str) -> str:
    """The story adds "I want to", so remove words that would repeat or clash with it.
    "must not cancel an order" becomes "not cancel an order"."""
    return re.sub(r"^(to|must|should|shall|can|may|will)\s+", "", tidy(feature), flags=re.I)


def story_sentence(role: str, feature: str, benefit: str) -> str:
    # "u" is left out on purpose, because we say "a user".
    article = "an" if role[:1].lower() in "aeio" else "a"
    return f"As {article} {role}, I want to {feature}, so that {benefit}."


def generate_story(requirement: str) -> dict:
    """Returns a story, or raises ExtractionFailed if no draft passes the checks."""
    prompt = f'Requirement: "{requirement}"'
    problems = []
    for _attempt in range(2):
        try:
            draft = ask_llm(SYSTEM_PROMPT, prompt, StoryDraft)
        except LLMBadOutput as error:
            problems = [str(error)]
            continue
        problems = find_problems(requirement, draft)
        if not problems:
            # A system cannot want something, so stories about one use "user".
            role = "user" if draft.role.lower() in NOT_A_PERSON else tidy(draft.role)
            return {
                "role": role,
                "role_inferred": not (content_words(role) & content_words(requirement)),
                "feature": clean_feature(draft.feature),
                "benefit": tidy(draft.benefit),
                "acceptance_criteria": keep_safe_criteria(requirement, draft.acceptance_criteria),
            }
        prompt += "\nYour last answer had these problems, please fix them: " + " ".join(problems)
    raise ExtractionFailed(" ".join(problems))
