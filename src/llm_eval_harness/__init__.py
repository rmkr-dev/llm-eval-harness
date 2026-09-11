"""Lightweight offline LLM eval harness."""

from .metrics import (
    case_insensitive_match,
    contains,
    exact_match,
    list_metrics,
    score,
    token_overlap,
)
from .report import build_report, format_summary

__all__ = [
    "exact_match",
    "case_insensitive_match",
    "contains",
    "token_overlap",
    "score",
    "list_metrics",
    "build_report",
    "format_summary",
]

__version__ = "0.1.0"
