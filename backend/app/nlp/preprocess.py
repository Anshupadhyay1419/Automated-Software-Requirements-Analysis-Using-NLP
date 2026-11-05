"""spaCy helpers: split text into sentences and pull out simple language facts.

Every other NLP step uses these small functions.
"""
import re
from functools import lru_cache

NEGATION_WORDS = {"not", "n't", "no", "never", "none", "neither", "nor", "without", "cannot"}
# Phrasing words that carry no feature meaning, so they should not count as content.
PHRASING_WORDS = {"able", "also", "want", "like", "need", "really", "please"}
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
# A new block starts after a blank line, or on a line that begins with a bullet or number.
BLOCK_BREAK = re.compile(r"\n\s*\n|\n(?=\s*(?:[-*•]|\d+[.)])\s)")


@lru_cache(maxsize=1)
def get_nlp():
    """Load spaCy only once, the first time it is needed."""
    import spacy
    return spacy.load("en_core_web_sm")


def split_into_sentences(text: str) -> list[dict]:
    """Return sentences with their position in the text, so we can link back to the source.

    Example: "Users log in. Admins export." gives two items:
      {"text": "Users log in.", "start": 0, "end": 13}
      {"text": "Admins export.", "start": 14, "end": 28}
    """
    sentences = []
    block_start = 0
    breaks = list(BLOCK_BREAK.finditer(text)) + [None]
    for match in breaks:
        block_end = match.start() if match else len(text)
        # Newlines become spaces. The length stays the same, so positions stay correct.
        block = text[block_start:block_end].replace("\n", " ")
        for sent in get_nlp()(block).sents:
            sentence = sent.text.strip()
            bullet = BULLET.match(sentence)
            if bullet:
                sentence = sentence[bullet.end():]
            if len(sentence.split()) < 3:  # headings like "Project Overview"
                continue
            start = block_start + block.index(sentence, sent.start_char)
            sentences.append({"text": sentence, "start": start, "end": start + len(sentence)})
        if match:
            block_start = match.end()
    return sentences


def content_words(text: str) -> set[str]:
    """Important words in base form. "Users placed orders" gives {"user", "place", "order"}."""
    return {
        token.lemma_.lower()
        for token in get_nlp()(text)
        if token.is_alpha and not token.is_stop and token.lower_ not in PHRASING_WORDS
    }


def has_negation(text: str) -> bool:
    return any(token.lower_ in NEGATION_WORDS for token in get_nlp()(text))


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def subject_of(text: str) -> str:
    """The grammatical subject. "The website should be fast" gives "the website"."""
    for chunk in get_nlp()(text).noun_chunks:
        if chunk.root.dep_ in ("nsubj", "nsubjpass"):
            return chunk.text.lower()
    return "the system"


def subject_head(text: str) -> str:
    """The main word of the subject. "Product search results" gives "result"."""
    for chunk in get_nlp()(text).noun_chunks:
        if chunk.root.dep_ in ("nsubj", "nsubjpass"):
            return chunk.root.lemma_.lower()
    return ""
