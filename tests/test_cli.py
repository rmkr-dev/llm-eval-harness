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
    assert report["version"] == "0.3.0"
    assert report["summary"]["total"] == 2
    assert report["summary"]["passed"] == 1
    assert report["summary"]["failed"] == 0
    assert report["summary"]["skipped"] == 1
    assert report["summary"]["pass_rate"] == 1.0
    assert "1 skipped" in result.output or "1 skipped" in (result.stderr or "")
