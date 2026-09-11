"""Unit tests for offline eval metrics."""

from llm_eval_harness.metrics import (
    case_insensitive_match,
    contains,
    exact_match,
    list_metrics,
    score,
    token_overlap,
)


def test_exact_match_passes_on_identical_trimmed_strings():
    r = exact_match("  hello  ", "hello")
    assert r["pass"] is True
    assert r["score"] == 1
    assert r["name"] == "exact_match"


def test_exact_match_fails_on_mismatch():
    r = exact_match("hello", "Hello")
    assert r["pass"] is False
    assert r["score"] == 0


def test_case_insensitive_match_ignores_case():
    r = case_insensitive_match("Hello", "hello")
    assert r["pass"] is True
    assert r["score"] == 1


def test_contains_passes_when_expected_is_substring():
    r = contains("alpha beta gamma", "beta")
    assert r["pass"] is True


def test_contains_fails_when_missing():
    r = contains("alpha beta", "gamma")
    assert r["pass"] is False


def test_token_overlap_scores_full_overlap_as_1():
    r = token_overlap("one two three", "three one two")
    assert r["score"] == 1
    assert r["pass"] is True


def test_token_overlap_fails_below_threshold():
    r = token_overlap("one two", "three four", 0.8)
    assert r["pass"] is False
    assert r["score"] < 0.8


def test_token_overlap_handles_empty_vs_empty():
    r = token_overlap("", "")
    assert r["pass"] is True
    assert r["score"] == 1


def test_list_metrics_includes_known_metrics():
    names = list_metrics()
    assert "exact_match" in names
    assert "token_overlap" in names


def test_score_runs_multiple_metrics():
    results = score(
        "Hello World",
        "hello world",
        ["exact_match", "case_insensitive_match"],
    )
    assert len(results) == 2
    assert results[0]["pass"] is False
    assert results[1]["pass"] is True


def test_score_flags_unknown_metrics():
    results = score("a", "a", ["not_a_metric"])
    assert results[0]["pass"] is False
    assert "unknown metric" in results[0]["error"]
