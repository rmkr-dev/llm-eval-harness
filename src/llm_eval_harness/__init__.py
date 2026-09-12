"""Lightweight offline LLM eval harness."""

from .metrics import (
    case_insensitive_match,
    contains,
    ends_with,
    exact_match,
    length_ratio,
    list_metrics,
    regex_match,
    score,
    starts_with,
    token_overlap,
    whitespace_normalized_match,
)
from .report import build_report, format_summary

__all__ = [
    "exact_match",
    "case_insensitive_match",
    "contains",
    "token_overlap",
    "starts_with",
    "ends_with",
    "regex_match",
    "whitespace_normalized_match",
    "length_ratio",
    "score",
    "list_metrics",
    "build_report",
    "format_summary",
]

__version__ = "0.2.0"
