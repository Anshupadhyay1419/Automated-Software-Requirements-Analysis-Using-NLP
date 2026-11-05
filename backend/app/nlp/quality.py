"""Quality analysis: find vague or incomplete requirements and possible contradictions.

Two sources work together:
  Rules (check_rules, rule_contradiction): predictable, easy to explain, only catch known patterns.
  LLM (llm_review, llm_contradiction): can catch other problems, but may be wrong.

Every result is only a suggestion for a person to review. This cannot find every problem.
Questions are inferred by this tool. The client did not say them.
"""
from typing import Literal

from pydantic import BaseModel

from .llm import ask_llm
from .preprocess import get_nlp, has_negation, numbers_in, subject_head, subject_of

# Vague word -> (what is unclear, the question to ask). {subject} is filled in later.
VAGUE_WORDS = {
    "fast": ("performance", "What response-time target should {subject} meet?"),
    "quick": ("performance", "What response-time target should {subject} meet?"),
    "quickly": ("performance", "What response-time target should {subject} meet?"),
    "efficient": ("performance", "What measurable performance target should {subject} meet?"),
    "scalable": ("performance", "How many users or how much data should {subject} support?"),
    "easy": ("usability", "How will we measure that {subject} is easy to use?"),
    "simple": ("usability", "How will we measure that {subject} is simple to use?"),
    "user-friendly": ("usability", "How will we measure that {subject} is user-friendly?"),
    "intuitive": ("usability", "How will we measure that {subject} is intuitive?"),
    "nice": ("usability", "What specific design qualities are expected from {subject}?"),
    "modern": ("usability", "What specific design qualities are expected from {subject}?"),
    "secure": ("security", "Which specific threats or security standards should {subject} address?"),
    "reliable": ("reliability", "What availability target should {subject} meet?"),
    "robust": ("reliability", "What failures should {subject} be able to handle?"),
    "appropriate": ("behaviour", "What exactly counts as appropriate here?"),
    "adequate": ("behaviour", "What exactly counts as adequate here?"),
    "several": ("quantity", "What exact number is meant?"),
    "many": ("quantity", "What exact number is meant?"),
    "various": ("quantity", "Which specific items are included?"),
}
# Phrases that leave the behaviour undefined.
UNSPECIFIED_PHRASES = ["tbd", "to be decided", "to be determined", "etc", "and so on", "as needed", "if necessary"]
GENERIC_VERBS = {"handle", "manage", "process", "deal"}
UNCLEAR_SUBJECTS = {"it", "they", "this", "that", "these", "those", "someone", "somebody", "we"}
NEEDS_NUMBER = {"performance", "reliability"}


def issue(kind, evidence, message, question):
    return {"kind": kind, "evidence": evidence, "message": message, "question": question}


def check_rules(text: str, category: str | None = None) -> list[dict]:
    """Run all the rules on one requirement. "category" comes from the classifier."""
    doc = get_nlp()(text)
    subject = subject_of(text)
    issues = []

    # Rule 1: vague words.
    for token in doc:
        word = token.lower_
        if word == "user" and token.i + 2 < len(doc) and doc[token.i + 1].text == "-":
            word = "user-friendly"
        if word in VAGUE_WORDS:
            area, question = VAGUE_WORDS[word]
            issues.append(issue(
                "vague_expression", token.text if word != "user-friendly" else "user-friendly",
                f"Ambiguous {area} requirement.", question.format(subject=subject),
            ))

    # Rule 2: the actor is unclear. Only the main clause counts, so the "it" in
    # "after it has been shipped" is ignored.
    root_verbs = [token for token in doc if token.dep_ == "ROOT"]
    subjects = [token for token in doc if token.dep_ in ("nsubj", "nsubjpass") and token.head.dep_ == "ROOT"]
    if not subjects and root_verbs and root_verbs[0].pos_ in ("VERB", "AUX"):
        issues.append(issue("unclear_actor", "", "No actor is stated.", "Who or what should perform this action?"))
    for token in subjects:
        if token.lower_ in UNCLEAR_SUBJECTS:
            issues.append(issue(
                "unclear_actor", token.text, f'The actor "{token.text}" is unclear.',
                f'What does "{token.text}" refer to?',
            ))

    # Passive voice hides who acts: "Reports are generated". Only checked for functional
    # requirements, because "Passwords must be encrypted" is fine as a quality rule.
    is_passive = any(token.dep_ == "nsubjpass" for token in subjects)
    has_agent = any(token.dep_ == "agent" for token in doc)
    if category is None and is_passive and not has_agent:
        issues.append(issue(
            "unclear_actor", "", "The passive wording does not say who or what performs this action.",
            "Who or what should perform this action?",
        ))

    # Rule 3: the behaviour is not specified.
    lowered = text.lower()
    for phrase in UNSPECIFIED_PHRASES:
        if f" {phrase}" in f" {lowered}".replace(".", " ").replace(",", " "):
            issues.append(issue(
                "unspecified_behavior", phrase, f'"{phrase}" leaves the behaviour undefined.',
                "What exactly should be included or done here?",
            ))
    for token in root_verbs:
        if token.lemma_.lower() in GENERIC_VERBS and not numbers_in(text):
            issues.append(issue(
                "unspecified_behavior", token.text, f'"{token.text}" does not say what should actually happen.',
                f'What exact steps does "{token.text}" involve?',
            ))

    # Rule 4: a performance or reliability requirement needs a number. This runs last
    # and is skipped if another issue already covers the requirement.
    if category in NEEDS_NUMBER and not numbers_in(text) and not issues:
        issues.append(issue(
            "missing_measure", "", f"This {category} requirement has no measurable target.",
            f"What measurable {category} target should {subject} meet?",
        ))
    return issues


def rule_contradiction(a: str, b: str) -> str | None:
    """Two very similar requirements may conflict if negation or numbers differ.
    Both must be about the same subject: "Guests must not order" and "Customers can order"
    do not conflict. Call this only for similar pairs. Returns a reason, or None."""
    if subject_head(a) != subject_head(b):
        return None
    if has_negation(a) != has_negation(b):
        return "One requirement is negated and the other is not."
    if numbers_in(a) and numbers_in(b) and numbers_in(a) != numbers_in(b):
        return f"They state different numbers: {sorted(numbers_in(a))} and {sorted(numbers_in(b))}."
    return None


# ----- LLM checks -----

REVIEW_PROMPT = """You review one software requirement for quality problems.
Report a problem only if it is clearly present. Most clear requirements have no problems.
Do not suggest new features.

Kinds of problem:
- vague_expression: a word with no clear meaning, such as "fast"
- missing_measure: a quality goal with no measurable target
- unclear_actor: it is not clear who performs the action
- unspecified_behavior: it does not say what should actually happen

For each problem give:
- kind
- evidence: words copied exactly from the requirement
- message: one short sentence
- question: one short question to ask the client

Example: "Users can log in." -> {"issues":[]}
Example: "The app should look good." ->
{"issues":[{"kind":"vague_expression","evidence":"look good","message":"Ambiguous appearance requirement.","question":"What design qualities are expected?"}]}"""

CONTRADICTION_PROMPT = """You compare two software requirements.
Answer contradiction=true only if both cannot be true at the same time.
Requirements about different things, or that only add detail, are not contradictions.
Give a one-sentence explanation."""


class LLMIssue(BaseModel):
    kind: Literal["vague_expression", "missing_measure", "unclear_actor", "unspecified_behavior"]
    evidence: str
    message: str
    question: str


class LLMReview(BaseModel):
    issues: list[LLMIssue]


class ContradictionCheck(BaseModel):
    contradiction: bool
    explanation: str


def llm_review(text: str) -> list[dict]:
    """Ask the LLM for problems, then throw away answers that cannot be right:
    evidence must be copied from the requirement, and a requirement that contains
    a number cannot be missing a measure."""
    result = ask_llm(REVIEW_PROMPT, f'Requirement: "{text}"', LLMReview)
    return [
        item.model_dump() for item in result.issues
        if item.evidence and item.evidence.lower() in text.lower()
        and not (item.kind == "missing_measure" and numbers_in(text))
    ]


def llm_contradiction(a: str, b: str) -> str | None:
    """Returns the LLM's explanation if it thinks they conflict, otherwise None."""
    result = ask_llm(CONTRADICTION_PROMPT, f'Requirement A: "{a}"\nRequirement B: "{b}"', ContradictionCheck)
    return result.explanation if result.contradiction else None
