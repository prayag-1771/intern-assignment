"""Text clean-up for the exact-duplicate check.

Two questions are exact duplicates when their cleaned text is identical. Cleaning
removes what is presentation only: letter case, spacing, sentence punctuation, a
leading question number, and bold or italic marks. It keeps anything that can
change the meaning of a question: digits, decimal points, quote and prime marks,
and symbols such as + - * / = < > ! % and the degree sign. "What is 5 + 3?" and
"What is 5 - 3?" must never clean to the same text, nor "5!" and "5".

Cleaning is deliberately cautious. A copy it misses is still caught later by
the meaning-based layers; a wrong match here would be final.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

# A question number or bullet in front: "1)", "1.", "(a)", "Q3.", "Q.", "Question 2:", "-", "•".
_LEADING_MARKER = re.compile(
    r"^\s*(?:\(?\d{1,3}[.)]|\(?[a-z][.)]|q(?:uestion)?\s*\d*\s*[.:)]|[-•])\s+",
    re.IGNORECASE,
)

# Markdown bold and italic, as LLMs often add. The stars must hug the words they wrap,
# start after a space and end before a space or punctuation, so "2*3*4", "a * b * c",
# "2**3" and "(a)*(b)*(c)" are left alone.
_BOLD = re.compile(r"(?:(?<=\s)|^)\*\*(?=\S)(.+?)(?<=\S)\*\*(?=\s|$|[.,;:!?])")
_ITALIC = re.compile(r"(?:(?<=\s)|^)\*(?=\S)(.+?)(?<=\S)\*(?=\s|$|[.,;:!?])")

# Fill-in-the-blank lines come in every length; they all mean the same blank.
_BLANK = re.compile(r"_{3,}")

_TYPOGRAPHY = str.maketrans(
    {
        "‘": "'", "’": "'", "“": '"', "”": '"',  # curly quotes
        "–": "-", "—": "-", "−": "-",  # long dashes and the minus sign
        "​": None, "‌": None, "‍": None, "﻿": None,  # invisible characters
    }
)

# A full stop, comma or colon directly before a digit is part of a number (2.5, 1,000, 10:30) and stays.
_SENTENCE_PUNCTUATION = re.compile(r"[.,:](?!\d)|[;?]")
_SPACE_BEFORE_UNIT = re.compile(r"\s+(?=[°%])")
_SPACES = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Return the text with presentation removed, for comparing two questions exactly."""
    cleaned = unicodedata.normalize("NFKC", text).translate(_TYPOGRAPHY).strip()
    cleaned = _LEADING_MARKER.sub("", cleaned)
    cleaned = _ITALIC.sub(r"\1", _BOLD.sub(r"\1", cleaned))
    cleaned = _BLANK.sub("____", cleaned)
    cleaned = _SENTENCE_PUNCTUATION.sub(" ", cleaned.casefold())
    cleaned = _SPACE_BEFORE_UNIT.sub("", cleaned)
    return _SPACES.sub(" ", cleaned).strip()


def fingerprint(text: str) -> str:
    """A fixed-length code for the cleaned text, so an exact duplicate is found with one lookup."""
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()
