"""Lightweight offline LLM eval harness."""

from .metrics import (
    case_insensitive_match,
    contains,
    contains_all,
    contains_any,
    edit_ratio,
    ends_with,
    exact_match,
    json_equal,
    length_ratio,
    list_metrics,
    regex_match,
    score,
    starts_with,
    token_overlap,
    whitespace_normalized_match,
)
from .formatters import render_report, to_junit, to_markdown
from .report import build_report, format_summary

__all__ = [
    "exact_match",
    "case_insensitive_match",
    "contains",
    "contains_all",
    "contains_any",
    "json_equal",
    "token_overlap",
    "starts_with",
    "ends_with",
    "regex_match",
    "whitespace_normalized_match",
    "length_ratio",
    "edit_ratio",
    "score",
    "list_metrics",
    "build_report",
    "format_summary",
    "render_report",
    "to_markdown",
    "to_junit",
]

__version__ = "1.0.0"
