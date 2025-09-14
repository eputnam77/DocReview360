from __future__ import annotations

import json
import numbers
import re
from pathlib import Path


def run_checks(file_path: str | Path) -> dict[str, object]:
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")

    grammar = []
    # ``re.split`` on whitespace leaves punctuation attached to tokens which
    # meant sequences like "word, word" were missed by the repeated word
    # detector.  Extract plain word tokens instead so adjacent words separated
    # only by punctuation are also compared.
    words = re.findall(r"[A-Za-z0-9']+", text)
    for i in range(len(words) - 1):
        if words[i].lower() == words[i + 1].lower():
            grammar.append(f"repeated word '{words[i]}'")

    accessibility = []
    # ``<img>`` tags may appear without any attributes (e.g. ``<img>``).  The
    # previous regular expression required at least one space after ``<img``
    # which meant such tags were silently ignored and missing ``alt`` text was
    # not reported.  Match a word boundary instead so tags with or without
    # attributes are captured.
    img_tag = re.compile(r"<img\b[^>]*>", re.I)
    # Accept attributes with optional whitespace around the equals sign and
    # support single, double quoted or unquoted ``alt`` values.
    # Capture the ``alt`` value so we can verify it contains meaningful text.
    # Merely checking for the attribute's presence previously treated values like
    # ``alt=""`` or ``alt="   "`` as valid even though they provide no
    # descriptive alternative.  Optional capture groups allow us to extract the
    # quoted or unquoted value and ensure it isn't empty or just whitespace.
    alt_attr = re.compile(
        r"alt\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>/]+))",
        re.I,
    )
    button_tag = re.compile(r"<button([^>]*)>(.*?)</button>", re.I | re.S)
    # ``aria-label`` attributes may also include surrounding whitespace. Allow
    # both quoting styles while normalizing incidental spaces.
    # ``aria-label`` values can legally be unquoted provided they contain no
    # whitespace or special characters.  Limiting the expression to quoted
    # values incorrectly flagged buttons using the unquoted form as missing a
    # label.  Support an additional unquoted capture group so all valid
    # syntaxes are handled.
    aria_label = re.compile(
        r"aria-label\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>/\'\"]+))",
        re.I,
    )

    for match in img_tag.finditer(text):
        m = alt_attr.search(match.group(0))
        # Treat the attribute as missing when absent or when it contains only
        # whitespace which fails to convey any meaning to assistive technology.
        if not m or not (m.group(1) or m.group(2) or m.group(3) or "").strip():
            accessibility.append("image missing alt text")

    for match in button_tag.finditer(text):
        attrs = match.group(1)
        body = match.group(2)
        # Remove nested tags when checking for visible text. Without this,
        # buttons containing only empty markup like ``<span></span>`` were not
        # flagged as missing labels.
        text_only = re.sub(r"<[^>]+>", "", body).strip()
        m = aria_label.search(attrs)
        label = ""
        if m:
            label = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if (not label) and text_only == "":
            accessibility.append("button missing label")

    style_ok = not detect_anomalies(text)

    return {"grammar": grammar, "accessibility": accessibility, "styleOk": style_ok}


def detect_anomalies(text: str, threshold: float = 0.7) -> bool:
    # ``threshold`` represents a probability and therefore must fall within the
    # inclusive range ``[0, 1]``.  Non-numeric inputs previously surfaced a
    # cryptic ``TypeError`` from the comparison operators.  Validate the type
    # explicitly so callers receive a clear message.
    if not isinstance(threshold, numbers.Real):
        raise TypeError("threshold must be a real number")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    # ``re.split`` left punctuation attached to tokens so sequences like
    # ``"bad, bad"`` were treated as different words and missed by the
    # repetition counter.  Extract plain word tokens instead so punctuation
    # does not shield repeated words from detection.
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    repeated = sum(1 for i in range(len(words) - 1) if words[i] == words[i + 1])
    # ``unique_ratio`` was previously calculated using the set of raw
    # characters which drastically underestimated diversity for inputs that
    # reused characters across different words (e.g. ``"aaaa bbbb"``).  This
    # skewed the anomaly score and could flip the result around the threshold.
    # Measuring uniqueness at the token level instead yields a stable metric
    # aligned with the repeated word detector above.
    unique_ratio = len(set(words)) / max(len(words), 1)
    features = [len(text) / 1000, unique_ratio, repeated]
    weights = [0.0, -0.1, 1.2]
    linear = sum(w * f for w, f in zip(weights, features))
    score = 1 / (1 + pow(2.718281828, -linear))
    return score >= threshold


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run document checks")
    parser.add_argument("file", help="path to document")
    args = parser.parse_args()

    result = run_checks(args.file)
    print(json.dumps(result))
