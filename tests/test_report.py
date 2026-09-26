"""Tests for report aggregation and formatting."""

from llm_eval_harness import __version__
from llm_eval_harness.report import build_report, format_summary


def test_build_report_uses_package_version():
    report = build_report(cases=[])
    assert report["version"] == __version__
    assert report["version"] == "1.0.0"


def test_build_report_accepts_version_override():
    report = build_report(cases=[], version="9.9.9")
    assert report["version"] == "9.9.9"


def test_build_report_counts_skipped_separately():
    cases = [
        {"id": "a", "pass": True, "skipped": False, "metrics": []},
        {"id": "b", "pass": False, "skipped": False, "metrics": []},
        {"id": "c", "pass": True, "skipped": True, "metrics": []},
    ]
    report = build_report(cases=cases)
    summary = report["summary"]
    assert summary["total"] == 3
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["skipped"] == 1
    assert summary["pass_rate"] == 0.5


def test_build_report_all_skipped_pass_rate_is_one():
    cases = [
        {"id": "a", "pass": True, "skipped": True, "metrics": []},
        {"id": "b", "pass": True, "skipped": True, "metrics": []},
    ]
    report = build_report(cases=cases)
    summary = report["summary"]
    assert summary["total"] == 2
    assert summary["passed"] == 0
    assert summary["failed"] == 0
    assert summary["skipped"] == 2
    assert summary["pass_rate"] == 1.0


def test_format_summary_mentions_skipped():
    report = build_report(
        cases=[
            {"id": "a", "pass": True, "skipped": False, "metrics": []},
            {"id": "b", "pass": True, "skipped": True, "metrics": []},
        ]
    )
    text = format_summary(report)
    assert "skipped" in text
    assert "1 skipped" in text


def test_format_summary_omits_skipped_when_zero():
    report = build_report(
        cases=[
            {"id": "a", "pass": True, "skipped": False, "metrics": []},
        ]
    )
    text = format_summary(report)
    assert "skipped" not in text


def test_package_version_matches_pyproject():
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert data["project"]["version"] == __version__
