"""Unit tests for offline eval metrics."""

from llm_eval_harness.metrics import (
    case_insensitive_match,
    contains,
    contains_all,
    contains_any,
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


def test_starts_with_passes():
    r = starts_with("  Hello World  ", "Hello")
    assert r["pass"] is True
    assert r["score"] == 1
    assert r["name"] == "starts_with"


def test_starts_with_fails():
    r = starts_with("Hello World", "World")
    assert r["pass"] is False
    assert r["score"] == 0


def test_ends_with_passes():
    r = ends_with("  Hello World  ", "World")
    assert r["pass"] is True
    assert r["score"] == 1
    assert r["name"] == "ends_with"


def test_ends_with_fails():
    r = ends_with("Hello World", "Hello")
    assert r["pass"] is False
    assert r["score"] == 0


def test_regex_match_passes():
    r = regex_match("order-12345-done", r"order-\d+-done")
    assert r["pass"] is True
    assert r["score"] == 1
    assert r["name"] == "regex_match"


def test_regex_match_fails():
    r = regex_match("plain text", r"^\d+$")
    assert r["pass"] is False
    assert r["score"] == 0


def test_regex_match_invalid_pattern():
    r = regex_match("anything", r"[unclosed")
    assert r["pass"] is False
    assert r["score"] == 0
    assert "invalid regex" in r["error"]


def test_whitespace_normalized_match_passes():
    r = whitespace_normalized_match("hello   world\n\t!", "hello world !")
    assert r["pass"] is True
    assert r["score"] == 1
    assert r["name"] == "whitespace_normalized_match"


def test_whitespace_normalized_match_fails():
    r = whitespace_normalized_match("hello world", "hello  there")
    assert r["pass"] is False
    assert r["score"] == 0


def test_length_ratio_passes_near_equal():
    r = length_ratio("abcdefghij", "abcdefghi")
    assert r["pass"] is True
    assert r["score"] >= 0.9
    assert r["threshold"] == 0.9
    assert r["name"] == "length_ratio"


def test_length_ratio_fails_when_far_apart():
    r = length_ratio("short", "a much longer expected string")
    assert r["pass"] is False
    assert r["score"] < 0.9
    assert r["threshold"] == 0.9


def test_length_ratio_empty_vs_empty():
    r = length_ratio("", "")
    assert r["pass"] is True
    assert r["score"] == 1
    assert r["threshold"] == 0.9


def test_length_ratio_empty_vs_nonempty():
    r = length_ratio("", "hello")
    assert r["pass"] is False
    assert r["score"] == 0


def test_contains_all_passes_when_all_lines_found():
    r = contains_all("alpha beta gamma delta", "beta\ngamma")
    assert r["pass"] is True
    assert r["score"] == 1
    assert r["name"] == "contains_all"


def test_contains_all_partial_score():
    r = contains_all("alpha beta", "beta\ngamma\ndelta")
    assert r["pass"] is False
    assert r["score"] == 0.3333
    assert r["name"] == "contains_all"


def test_contains_all_fails_when_none_found():
    r = contains_all("alpha", "beta\ngamma")
    assert r["pass"] is False
    assert r["score"] == 0


def test_contains_all_empty_expected_passes():
    r = contains_all("anything", "")
    assert r["pass"] is True
    assert r["score"] == 1


def test_contains_all_blank_lines_ignored():
    r = contains_all("hello world", "\nhello\n\n")
    assert r["pass"] is True
    assert r["score"] == 1


def test_contains_all_case_sensitive():
    r = contains_all("Hello World", "hello")
    assert r["pass"] is False
    assert r["score"] == 0


def test_contains_any_passes_on_one_hit():
    r = contains_any("alpha beta", "gamma\nbeta")
    assert r["pass"] is True
    assert r["score"] == 1
    assert r["name"] == "contains_any"


def test_contains_any_fails_when_none_hit():
    r = contains_any("alpha", "beta\ngamma")
    assert r["pass"] is False
    assert r["score"] == 0


def test_contains_any_empty_expected_passes():
    r = contains_any("anything", "\n\n")
    assert r["pass"] is True
    assert r["score"] == 1


def test_json_equal_passes_on_deep_equal():
    r = json_equal('{"a": 1, "b": [2, 3]}', '{"b": [2, 3], "a": 1}')
    assert r["pass"] is True
    assert r["score"] == 1
    assert r["name"] == "json_equal"


def test_json_equal_fails_on_mismatch():
    r = json_equal('{"a": 1}', '{"a": 2}')
    assert r["pass"] is False
    assert r["score"] == 0


def test_json_equal_parse_error_on_actual():
    r = json_equal("not-json", '{"a": 1}')
    assert r["pass"] is False
    assert r["score"] == 0
    assert "actual not valid JSON" in r["error"]


def test_json_equal_parse_error_on_expected():
    r = json_equal('{"a": 1}', "not-json")
    assert r["pass"] is False
    assert r["score"] == 0
    assert "expected not valid JSON" in r["error"]


def test_json_equal_scalars():
    r = json_equal("42", "42")
    assert r["pass"] is True
    assert r["score"] == 1


def test_list_metrics_includes_known_metrics():
    names = list_metrics()
    assert "exact_match" in names
    assert "token_overlap" in names
    assert "starts_with" in names
    assert "ends_with" in names
    assert "regex_match" in names
    assert "whitespace_normalized_match" in names
    assert "length_ratio" in names
    assert "contains_all" in names
    assert "contains_any" in names
    assert "json_equal" in names


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
