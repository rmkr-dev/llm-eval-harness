"""Tests for JSON / Markdown / JUnit report rendering."""

import json
import xml.etree.ElementTree as ET

import pytest

from llm_eval_harness.formatters import FORMATS, render_report, to_junit, to_markdown
from llm_eval_harness.report import build_report


def _report():
    cases = [
        {
            "id": "good",
            "path": "good",
            "pass": True,
            "skipped": False,
            "metrics": [{"name": "exact_match", "pass": True, "score": 1}],
        },
        {
            "id": "bad|pipe",
            "path": "bad",
            "pass": False,
            "skipped": False,
            "metrics": [
                {"name": "exact_match", "pass": False, "score": 0},
                {"name": "edit_ratio", "pass": False, "score": 0.5, "threshold": 0.8},
            ],
        },
        {"id": "pending", "path": "pending", "pass": True, "skipped": True, "metrics": []},
        {
            "id": "missing",
            "path": "missing",
            "pass": False,
            "skipped": False,
            "error": "missing actual.txt",
            "metrics": [],
        },
    ]
    return build_report(
        cases=cases,
        fixtures_dir="fixtures",
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        version="1.2.3",
    )


def test_formats_constant():
    assert FORMATS == ("json", "markdown", "junit")


def test_render_json_matches_plain_dump():
    report = _report()
    assert render_report(report, "json") == json.dumps(report, indent=2) + "\n"
    assert render_report(report) == render_report(report, "json")


def test_render_unknown_format_raises():
    with pytest.raises(ValueError):
        render_report(_report(), "yaml")


def test_markdown_contains_summary_metrics_and_cases():
    md = to_markdown(_report())
    assert md.startswith("# Eval report (llm-eval-harness 1.2.3)")
    assert "| 4 | 1 | 2 | 1 | 33.3% |" in md
    assert "## Metrics" in md
    assert "| `exact_match` |" in md
    assert "| `good` | PASS |" in md
    assert "| `pending` | SKIP |" in md
    assert "| `missing` | FAIL | missing actual.txt |" in md
    assert "edit_ratio=0.5 (>= 0.8) FAIL" in md
    # pipes in ids are escaped so the table stays intact
    assert "`bad\\|pipe`" in md


def test_markdown_empty_report():
    md = to_markdown(build_report(cases=[], version="1.0.0"))
    assert "## Cases" not in md
    assert "| 0 | 0 | 0 | 0 | 0.0% |" in md


def test_junit_is_well_formed_with_counts():
    xml_text = to_junit(_report())
    assert xml_text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    root = ET.fromstring(xml_text.split("\n", 1)[1])
    assert root.tag == "testsuites"
    suite = root.find("testsuite")
    assert suite is not None
    assert suite.get("tests") == "4"
    assert suite.get("failures") == "1"
    assert suite.get("errors") == "1"
    assert suite.get("skipped") == "1"
    assert suite.get("timestamp") == "2026-01-01T00:00:00Z"

    by_name = {tc.get("name"): tc for tc in suite.findall("testcase")}
    assert set(by_name) == {"good", "bad|pipe", "pending", "missing"}
    assert list(by_name["good"]) == [by_name["good"].find("system-out")]
    failure = by_name["bad|pipe"].find("failure")
    assert failure is not None
    assert failure.get("message") == "failed metrics: exact_match, edit_ratio"
    assert "edit_ratio=0.5" in failure.text
    assert by_name["pending"].find("skipped") is not None
    assert by_name["missing"].find("error").get("message") == "missing actual.txt"

    props = {p.get("name"): p.get("value") for p in suite.find("properties")}
    assert props == {"version": "1.2.3", "fixturesDir": "fixtures"}


def test_junit_escapes_special_characters():
    report = build_report(
        cases=[
            {
                "id": "<a & b>",
                "path": "x",
                "pass": False,
                "skipped": False,
                "metrics": [{"name": "regex_match", "pass": False, "score": 0, "error": "bad <re>"}],
            }
        ],
        version="1.0.0",
    )
    root = ET.fromstring(to_junit(report).split("\n", 1)[1])
    tc = root.find("testsuite/testcase")
    assert tc.get("name") == "<a & b>"
    assert "bad <re>" in tc.find("failure").text
