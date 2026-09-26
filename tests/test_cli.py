"""Smoke tests for the llm-eval CLI."""

import json

from click.testing import CliRunner

from llm_eval_harness.cli import main
from llm_eval_harness.metrics import list_metrics


def test_list_metrics_prints_names_and_exits_zero():
    runner = CliRunner()
    result = runner.invoke(main, ["--list-metrics"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.strip().splitlines() if ln]
    assert lines == list_metrics()
    assert "exact_match" in lines
    assert "length_ratio" in lines
    assert "contains_all" in lines
    assert "contains_any" in lines
    assert "json_equal" in lines


def test_case_filter_runs_only_named_fixture(tmp_path):
    fixtures = tmp_path / "fixtures"
    for name, expected, actual in [
        ("keep-me", "hello", "hello"),
        ("skip-me", "other", "other"),
    ]:
        case = fixtures / name
        case.mkdir(parents=True)
        (case / "expected.txt").write_text(expected, encoding="utf-8")
        (case / "actual.txt").write_text(actual, encoding="utf-8")
        (case / "meta.json").write_text(
            '{"id": "%s", "metrics": ["exact_match"]}' % name,
            encoding="utf-8",
        )

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--fixtures", str(fixtures), "--case", "keep-me", "--out", str(tmp_path / "out.json")],
    )
    assert result.exit_code == 0
    report = (tmp_path / "out.json").read_text(encoding="utf-8")
    assert "keep-me" in report
    assert "skip-me" not in report


def test_case_filter_repeatable(tmp_path):
    fixtures = tmp_path / "fixtures"
    for name in ("alpha", "beta", "gamma"):
        case = fixtures / name
        case.mkdir(parents=True)
        (case / "expected.txt").write_text("x", encoding="utf-8")
        (case / "actual.txt").write_text("x", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--fixtures",
            str(fixtures),
            "-c",
            "alpha",
            "-c",
            "gamma",
            "--out",
            str(tmp_path / "out.json"),
        ],
    )
    assert result.exit_code == 0
    report = (tmp_path / "out.json").read_text(encoding="utf-8")
    assert "alpha" in report
    assert "gamma" in report
    assert "beta" not in report


def _make_fixtures(tmp_path, cases):
    fixtures = tmp_path / "fixtures"
    for name, expected, actual in cases:
        case = fixtures / name
        case.mkdir(parents=True)
        (case / "expected.txt").write_text(expected, encoding="utf-8")
        if actual is not None:
            (case / "actual.txt").write_text(actual, encoding="utf-8")
        (case / "meta.json").write_text(
            '{"id": "%s", "metrics": ["exact_match"]}' % name,
            encoding="utf-8",
        )
    return fixtures


def test_fail_under_exits_one_when_below_threshold(tmp_path):
    fixtures = _make_fixtures(
        tmp_path,
        [
            ("ok", "hello", "hello"),
            ("bad", "hello", "goodbye"),
        ],
    )
    runner = CliRunner()
    out = tmp_path / "out.json"
    result = runner.invoke(
        main,
        ["--fixtures", str(fixtures), "--out", str(out), "--fail-under", "0.9"],
    )
    # also fails hard because one case failed
    assert result.exit_code == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["pass_rate"] == 0.5
    assert report["summary"]["skipped"] == 0


def test_fail_under_exits_zero_when_above_threshold(tmp_path):
    fixtures = _make_fixtures(
        tmp_path,
        [
            ("ok1", "hello", "hello"),
            ("ok2", "world", "world"),
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--fixtures",
            str(fixtures),
            "--out",
            str(tmp_path / "out.json"),
            "--fail-under",
            "0.9",
        ],
    )
    assert result.exit_code == 0


def test_fail_under_triggers_even_when_all_cases_pass_but_rate_low(tmp_path):
    """With mixed pass via skip-aware rate: two pass one fail → rate 0.666 < 0.8."""
    fixtures = _make_fixtures(
        tmp_path,
        [
            ("a", "x", "x"),
            ("b", "y", "y"),
            ("c", "z", "nope"),
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--fixtures",
            str(fixtures),
            "--out",
            str(tmp_path / "out.json"),
            "--fail-under",
            "0.8",
        ],
    )
    assert result.exit_code == 1


def test_report_includes_version_and_skipped(tmp_path):
    fixtures = _make_fixtures(
        tmp_path,
        [
            ("scored", "hello", "hello"),
            ("pending", "hello", None),
        ],
    )
    runner = CliRunner()
    out = tmp_path / "out.json"
    result = runner.invoke(
        main,
        ["--fixtures", str(fixtures), "--out", str(out)],
    )
    assert result.exit_code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["version"] == "1.0.0"
    assert report["summary"]["total"] == 2
    assert report["summary"]["passed"] == 1
    assert report["summary"]["failed"] == 0
    assert report["summary"]["skipped"] == 1
    assert report["summary"]["pass_rate"] == 1.0
    assert "1 skipped" in result.output or "1 skipped" in (result.stderr or "")


def _write_case(fixtures, name, expected, actual, meta=None):
    case = fixtures / name
    case.mkdir(parents=True)
    (case / "expected.txt").write_text(expected, encoding="utf-8")
    if actual is not None:
        (case / "actual.txt").write_text(actual, encoding="utf-8")
    if meta is not None:
        (case / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _run(tmp_path, fixtures, *args):
    """Invoke the CLI writing the report to a file; return (result, report text)."""
    out = tmp_path / "report.out"
    result = CliRunner().invoke(main, ["--fixtures", str(fixtures), "--out", str(out), *args])
    text = out.read_text(encoding="utf-8") if out.exists() else ""
    return result, text


def _ids(text):
    return [c["id"] for c in json.loads(text)["cases"]]


def test_edit_ratio_listed():
    result = CliRunner().invoke(main, ["--list-metrics"])
    assert "edit_ratio" in result.output.splitlines()


def test_format_markdown(tmp_path):
    fixtures = _make_fixtures(tmp_path, [("ok", "hello", "hello")])
    result, text = _run(tmp_path, fixtures, "--format", "markdown")
    assert result.exit_code == 0
    assert "# Eval report (llm-eval-harness 1.0.0)" in text
    assert "| `ok` | PASS |" in text


def test_format_junit_to_file(tmp_path):
    import xml.etree.ElementTree as ET

    fixtures = _make_fixtures(
        tmp_path,
        [("ok", "hello", "hello"), ("bad", "hello", "bye"), ("todo", "hello", None)],
    )
    out = tmp_path / "junit.xml"
    result = CliRunner().invoke(
        main, ["--fixtures", str(fixtures), "-f", "junit", "--out", str(out)]
    )
    assert result.exit_code == 1
    suite = ET.parse(out).getroot().find("testsuite")
    assert suite.get("tests") == "3"
    assert suite.get("failures") == "1"
    assert suite.get("skipped") == "1"


def test_format_default_is_json(tmp_path):
    fixtures = _make_fixtures(tmp_path, [("ok", "hello", "hello")])
    result, text = _run(tmp_path, fixtures)
    assert result.exit_code == 0
    assert json.loads(text)["summary"]["passed"] == 1


def test_format_rejects_unknown_value(tmp_path):
    fixtures = _make_fixtures(tmp_path, [("ok", "hello", "hello")])
    result = CliRunner().invoke(main, ["--fixtures", str(fixtures), "--format", "yaml"])
    assert result.exit_code == 2


def _tagged_fixtures(tmp_path):
    fixtures = tmp_path / "fixtures"
    _write_case(fixtures, "smoke-a", "x", "x", {"metrics": ["exact_match"], "tags": ["smoke", "fast"]})
    _write_case(fixtures, "slow-b", "y", "y", {"metrics": ["exact_match"], "tags": "slow"})
    _write_case(fixtures, "untagged", "z", "z", {"metrics": ["exact_match"]})
    _write_case(fixtures, "no-meta", "w", "w")
    return fixtures


def test_tag_filter_runs_only_matching_cases(tmp_path):
    fixtures = _tagged_fixtures(tmp_path)
    result, text = _run(tmp_path, fixtures, "--tag", "smoke")
    assert result.exit_code == 0
    assert _ids(text) == ["smoke-a"]
    case = json.loads(text)["cases"][0]
    assert case["tags"] == ["smoke", "fast"]


def test_tag_filter_repeatable_is_any_match(tmp_path):
    fixtures = _tagged_fixtures(tmp_path)
    result, text = _run(tmp_path, fixtures, "-t", "fast", "-t", "slow")
    assert result.exit_code == 0
    assert _ids(text) == ["slow-b", "smoke-a"]


def test_tag_filter_combines_with_case_filter(tmp_path):
    fixtures = _tagged_fixtures(tmp_path)
    result, text = _run(tmp_path, fixtures, "-t", "smoke", "-t", "slow", "-c", "slow-b")
    assert result.exit_code == 0
    assert _ids(text) == ["slow-b"]


def test_no_tag_filter_runs_everything(tmp_path):
    fixtures = _tagged_fixtures(tmp_path)
    result, text = _run(tmp_path, fixtures)
    assert result.exit_code == 0
    assert _ids(text) == ["no-meta", "slow-b", "smoke-a", "untagged"]
    untagged = json.loads(text)["cases"][-1]
    assert "tags" not in untagged


def test_tag_filter_with_no_matches_exits_two(tmp_path):
    fixtures = _tagged_fixtures(tmp_path)
    result, text = _run(tmp_path, fixtures, "--tag", "nope")
    assert result.exit_code == 2
    assert "match tags: nope" in result.output


def test_invalid_tags_type_exits_two(tmp_path):
    fixtures = tmp_path / "fixtures"
    _write_case(fixtures, "bad", "x", "x", {"tags": [1, 2]})
    result, text = _run(tmp_path, fixtures)
    assert result.exit_code == 2
    assert "tags must be" in result.output


def test_meta_thresholds_relax_metric(tmp_path):
    fixtures = tmp_path / "fixtures"
    _write_case(
        fixtures,
        "fuzzy",
        "The quick brown fox jumps",
        "The quick brown fox leaps",
        {"metrics": ["edit_ratio", "token_overlap"], "thresholds": {"token_overlap": 0.6}},
    )
    result, text = _run(tmp_path, fixtures)
    assert result.exit_code == 0
    metrics = {m["name"]: m for m in json.loads(text)["cases"][0]["metrics"]}
    assert metrics["token_overlap"]["threshold"] == 0.6
    assert metrics["token_overlap"]["pass"] is True
    assert metrics["edit_ratio"]["threshold"] == 0.8
    assert metrics["edit_ratio"]["pass"] is True


def test_meta_thresholds_tighten_metric(tmp_path):
    fixtures = tmp_path / "fixtures"
    _write_case(
        fixtures,
        "strict",
        "Hello, world!",
        "Hello, wrold!",
        {"metrics": ["edit_ratio"], "thresholds": {"edit_ratio": 0.95}},
    )
    result, text = _run(tmp_path, fixtures)
    assert result.exit_code == 1
    metric = json.loads(text)["cases"][0]["metrics"][0]
    assert metric["threshold"] == 0.95
    assert metric["pass"] is False


def test_meta_invalid_threshold_exits_two(tmp_path):
    fixtures = tmp_path / "fixtures"
    _write_case(fixtures, "bad", "x", "x", {"thresholds": {"edit_ratio": 2}})
    result, text = _run(tmp_path, fixtures)
    assert result.exit_code == 2
    assert "between 0.0 and 1.0" in result.output


def test_bundled_fixtures_pass_in_all_formats():
    from pathlib import Path

    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    for fmt in ("json", "markdown", "junit"):
        result = CliRunner().invoke(
            main, ["--fixtures", str(fixtures), "--require-actual", "--format", fmt]
        )
        assert result.exit_code == 0, (fmt, result.output)
