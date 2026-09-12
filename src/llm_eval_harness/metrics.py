"""Simple offline metrics for comparing actual vs expected strings."""

from __future__ import annotations

import re
from typing import Any


def exact_match(actual: str | None, expected: str | None) -> dict[str, Any]:
    """Exact string equality (trimmed)."""
    a = str(actual or "").strip()
    e = str(expected or "").strip()
    passed = a == e
    return {"name": "exact_match", "pass": passed, "score": 1 if passed else 0}


def case_insensitive_match(actual: str | None, expected: str | None) -> dict[str, Any]:
    """Case-insensitive equality (trimmed)."""
    a = str(actual or "").strip().lower()
    e = str(expected or "").strip().lower()
    passed = a == e
    return {
        "name": "case_insensitive_match",
        "pass": passed,
        "score": 1 if passed else 0,
    }


def contains(actual: str | None, expected: str | None) -> dict[str, Any]:
    """Whether expected is a substring of actual (trimmed, case-sensitive)."""
    a = str(actual or "")
    e = str(expected or "").strip()
    passed = (len(a) == 0) if len(e) == 0 else (e in a)
    return {"name": "contains", "pass": passed, "score": 1 if passed else 0}


def token_overlap(
    actual: str | None,
    expected: str | None,
    threshold: float = 0.8,
) -> dict[str, Any]:
    """Token Jaccard similarity over whitespace-split tokens (lowercased).

    Score in [0, 1]; pass when score >= threshold (default 0.8).
    """

    def tokenize(s: str | None) -> set[str]:
        return {t for t in str(s or "").lower().strip().split() if t}

    a_toks = tokenize(actual)
    e_toks = tokenize(expected)

    if not a_toks and not e_toks:
        return {
            "name": "token_overlap",
            "pass": True,
            "score": 1,
            "threshold": threshold,
        }
    if not a_toks or not e_toks:
        return {
            "name": "token_overlap",
            "pass": False,
            "score": 0,
            "threshold": threshold,
        }

    inter = len(a_toks & e_toks)
    union = len(a_toks) + len(e_toks) - inter
    sim = 0.0 if union == 0 else inter / union
    score_val = float(f"{sim:.4f}")
    return {
        "name": "token_overlap",
        "pass": score_val >= threshold,
        "score": score_val,
        "threshold": threshold,
    }


def starts_with(actual: str | None, expected: str | None) -> dict[str, Any]:
    """Whether trimmed actual starts with trimmed expected."""
    a = str(actual or "").strip()
    e = str(expected or "").strip()
    passed = a.startswith(e)
    return {"name": "starts_with", "pass": passed, "score": 1 if passed else 0}


def ends_with(actual: str | None, expected: str | None) -> dict[str, Any]:
    """Whether trimmed actual ends with trimmed expected."""
    a = str(actual or "").strip()
    e = str(expected or "").strip()
    passed = a.endswith(e)
    return {"name": "ends_with", "pass": passed, "score": 1 if passed else 0}


def regex_match(actual: str | None, expected: str | None) -> dict[str, Any]:
    """Treat expected as a regex; search against actual with re.search.

    Invalid regex patterns return pass=False with an error field.
    """
    a = str(actual or "")
    e = str(expected or "")
    try:
        matched = re.search(e, a) is not None
    except re.error as exc:
        return {
            "name": "regex_match",
            "pass": False,
            "score": 0,
            "error": f"invalid regex: {exc}",
        }
    return {"name": "regex_match", "pass": matched, "score": 1 if matched else 0}


def whitespace_normalized_match(
    actual: str | None,
    expected: str | None,
) -> dict[str, Any]:
    """Collapse all whitespace to single spaces, trim, then exact equality."""

    def normalize(s: str | None) -> str:
        return re.sub(r"\s+", " ", str(s or "").strip())

    a = normalize(actual)
    e = normalize(expected)
    passed = a == e
    return {
        "name": "whitespace_normalized_match",
        "pass": passed,
        "score": 1 if passed else 0,
    }


def length_ratio(
    actual: str | None,
    expected: str | None,
    threshold: float = 0.9,
) -> dict[str, Any]:
    """Ratio of shorter to longer string length; pass when score >= threshold.

    When both are empty (max length 0), score is 1.
    """
    a = str(actual or "")
    e = str(expected or "")
    len_a = len(a)
    len_e = len(e)
    max_len = max(len_a, len_e)
    if max_len == 0:
        score_val = 1.0
    else:
        score_val = min(len_a, len_e) / max_len
    score_val = float(f"{score_val:.4f}") if max_len > 0 else 1.0
    return {
        "name": "length_ratio",
        "pass": score_val >= threshold,
        "score": score_val,
        "threshold": threshold,
    }


REGISTRY: dict[str, Any] = {
    "exact_match": exact_match,
    "case_insensitive_match": case_insensitive_match,
    "contains": contains,
    "token_overlap": token_overlap,
    "starts_with": starts_with,
    "ends_with": ends_with,
    "regex_match": regex_match,
    "whitespace_normalized_match": whitespace_normalized_match,
    "length_ratio": length_ratio,
}


def score(
    actual: str | None,
    expected: str | None,
    metric_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Run named metrics against actual/expected."""
    if metric_names is None:
        metric_names = ["exact_match"]
    results: list[dict[str, Any]] = []
    for name in metric_names:
        fn = REGISTRY.get(name)
        if fn is None:
            results.append(
                {
                    "name": name,
                    "pass": False,
                    "score": 0,
                    "error": f"unknown metric: {name}",
                }
            )
            continue
        results.append(fn(actual, expected))
    return results


def list_metrics() -> list[str]:
    """Return registered metric names."""
    return list(REGISTRY.keys())
