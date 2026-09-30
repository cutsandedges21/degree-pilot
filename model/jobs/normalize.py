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


def contains_words(haystack: str, needle: str, match_case_if_short: bool = False) -> bool:
    """True if `needle` appears in `haystack` as whole words once both are normalized, so
    "Git" is not found in "Digital". With match_case_if_short, values of three characters
    or fewer (grades, credits) keep their case, so a grade "A" isn't found in the word "a"."""
    if match_case_if_short and len(needle.strip()) <= 3:
        hay = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", haystack))
        pin = unicodedata.normalize("NFKC", needle).strip()
    else:
        hay, pin = norm(haystack), norm(needle)
    if not pin:
        return True
    return re.search(rf"(?<![\w+#]){re.escape(pin)}(?![\w+#])", hay) is not None
