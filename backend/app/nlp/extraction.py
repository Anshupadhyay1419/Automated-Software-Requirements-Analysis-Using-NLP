"""Requirement extraction: turn one sentence into small, single-idea requirements.

How it works:
  1. Send the sentence to the local LLM and ask for JSON.
  2. Check the answer with simple rules (find_problems).
  3. If a rule fails, ask once more and say what was wrong.
  4. If it still fails, report the sentence instead of saving a doubtful result.
"""
from pydantic import BaseModel, Field

from .llm import LLMBadOutput, ask_llm
from .preprocess import content_words, has_negation, numbers_in

CONDITION_WORDS = {"if", "when", "unless", "until", "only", "after", "before", "while"}
REQUIREMENT_WORDS = {"shall", "must", "should", "will", "need", "needs", "require", "required"}

SYSTEM_PROMPT = """You extract software requirements from client text.
Split the sentence into atomic requirements, with one capability or constraint in each.

Rules:
- Use only the information in the sentence. Never add features, numbers or details.
- Repeat the actor in every requirement.
- Keep every negation, condition, limit and number exactly.
- If a condition applies to several actions, repeat it in each requirement.
- Keep a limit in the same requirement as its action. Do not split one action into two.
- Replace a pronoun such as "they" using the previous sentence. If you cannot tell what it
  refers to, keep the pronoun. Never change the actor to "we".
- Keep "etc." attached to the last listed item. Never make a requirement only about "etc.".
- If the sentence states no software requirement, return an empty list.
- "actor" is who or what performs the action, copied from the text.

Examples:
"Users should register, log in, and place orders." ->
{"requirements":[{"text":"Users can register.","actor":"Users"},{"text":"Users can log in.","actor":"Users"},{"text":"Users can place orders.","actor":"Users"}]}

"If payment fails, the system must notify the user and cancel the order." ->
{"requirements":[{"text":"If payment fails, the system must notify the user.","actor":"system"},{"text":"If payment fails, the system must cancel the order.","actor":"system"}]}

"Guests can browse products but must not place orders." ->
{"requirements":[{"text":"Guests can browse products.","actor":"Guests"},{"text":"Guests must not place orders.","actor":"Guests"}]}

Previous sentence: "Admins can add users and view reports." Sentence: "They can also export reports." ->
{"requirements":[{"text":"Admins can export reports.","actor":"Admins"}]}

"Staff can view orders at any time." ->
{"requirements":[{"text":"Staff can view orders at any time.","actor":"Staff"}]}

"Only managers can approve refunds above 500 dollars." ->
{"requirements":[{"text":"Only managers can approve refunds above 500 dollars.","actor":"managers"}]}

"We want a report page and it should load in 3 seconds." ->
{"requirements":[{"text":"We want a report page.","actor":""},{"text":"It should load in 3 seconds.","actor":""}]}

"Our company was founded in 2010." ->
{"requirements":[]}"""


class ExtractedRequirement(BaseModel):
    text: str = Field(min_length=3)
    actor: str = ""


class ExtractionResult(BaseModel):
    requirements: list[ExtractedRequirement]


class ExtractionFailed(Exception):
    """The LLM answer failed our checks, so nothing was saved for this sentence."""


def find_problems(sentence: str, context: str, items: list[ExtractedRequirement]) -> list[str]:
    """Compare the LLM answer with the source sentence. An empty list means it passed."""
    problems = []
    texts = [item.text for item in items]
    joined = " ".join(texts)
    source_words = content_words(sentence)
    allowed_words = source_words | content_words(context)  # pronouns may come from context

    # Empty answer: fine, unless the sentence clearly states a requirement.
    if not items:
        if REQUIREMENT_WORDS & set(sentence.lower().split()):
            problems.append("The sentence seems to state a requirement, but nothing was extracted.")
        return problems

    # No invented words: at least 80% of each item's words must come from the source.
    for text in texts:
        words = content_words(text)
        if words and len(words - allowed_words) / len(words) > 0.2:
            problems.append(f'"{text}" uses words that are not in the source: {sorted(words - allowed_words)}.')

    # Nothing dropped: at least 80% of the sentence's words must appear in the result.
    missing = source_words - content_words(joined)
    if source_words and len(missing) / len(source_words) > 0.2:
        problems.append(f"These words from the sentence are missing: {sorted(missing)}.")

    # "etc." cannot be a requirement by itself.
    for text in texts:
        if "etc" in text.lower() and "," not in text:
            problems.append(f'"{text}" is not a real requirement. Keep "etc." with the listed items.')

    # Numbers must be kept, and none may be added.
    if numbers_in(sentence) - numbers_in(joined):
        problems.append(f"Numbers were lost: {sorted(numbers_in(sentence) - numbers_in(joined))}.")
    if numbers_in(joined) - numbers_in(sentence + " " + context):
        problems.append(f"Numbers were invented: {sorted(numbers_in(joined) - numbers_in(sentence))}.")

    # Negation must not be lost or added ("must not delete" is opposite to "must delete").
    if has_negation(sentence) and not has_negation(joined):
        problems.append("The negation in the sentence was lost.")
    if has_negation(joined) and not has_negation(sentence):
        problems.append("A negation was added that is not in the sentence.")

    # Conditions must be kept.
    lost = (CONDITION_WORDS & set(sentence.lower().split())) - set(joined.lower().split())
    if lost:
        problems.append(f"Condition words were lost: {sorted(lost)}.")
    return problems


def extract_requirements(sentence: str, context: str = "") -> list[ExtractedRequirement]:
    """Return checked requirements for one sentence, or raise ExtractionFailed."""
    prompt = f'Previous sentence: "{context}"\nSentence: "{sentence}"'
    problems = []
    for _attempt in range(2):
        try:
            items = ask_llm(SYSTEM_PROMPT, prompt, ExtractionResult).requirements
        except LLMBadOutput as error:
            problems = [str(error)]
            continue
        problems = find_problems(sentence, context, items)
        if not problems:
            return clean_actors(remove_exact_repeats(items))
        prompt += "\nYour last answer had these problems, please fix them: " + " ".join(problems)
    raise ExtractionFailed(" ".join(problems))


def clean_actors(items: list[ExtractedRequirement]) -> list[ExtractedRequirement]:
    """The actor must appear in the requirement. If the LLM guessed one, leave it blank."""
    for item in items:
        if item.actor.lower() not in item.text.lower():
            item.actor = ""
    return items


def remove_exact_repeats(items: list[ExtractedRequirement]) -> list[ExtractedRequirement]:
    """Removes identical items within one sentence. Repeats across sentences are kept
    on purpose, so the duplicate detector can show them to the reviewer."""
    seen = set()
    unique = []
    for item in items:
        key = item.text.strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
