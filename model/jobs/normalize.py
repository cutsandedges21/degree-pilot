"""Text normalization shared by the copy rule and the scorers.

Two values are the same when they match after NFKC, casefolding, collapsing whitespace
and trimming punctuation from the ends. Inner punctuation stays: it carries meaning in
course codes (603-101-MQ) and grades (A-), so "-" and "+" are never trimmed.
"""
import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_EDGE = " .,;:!?\"'()[]{}*•·"


def norm(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    return _WHITESPACE.sub(" ", text).strip(_EDGE)


def contains(haystack: str, needle: str) -> bool:
    """True if `needle` appears in `haystack` once both are normalized."""
    return norm(needle) in norm(haystack)
