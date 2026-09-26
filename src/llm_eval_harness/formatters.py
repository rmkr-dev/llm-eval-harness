"""Render an eval report as JSON, Markdown, or JUnit XML."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any

FORMATS = ("json", "markdown", "junit")


def to_json(report: dict[str, Any]) -> str:
    """Pretty-printed JSON (the original report format)."""
    return json.dumps(report, indent=2) + "\n"


def _status(case: dict[str, Any]) -> str:
    if case.get("skipped"):
        return "SKIP"
    return "PASS" if case.get("pass") else "FAIL"


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _metric_detail(m: dict[str, Any]) -> str:
    text = f"{m.get('name')}={m.get('score')}"
    if "threshold" in m:
        text += f" (>= {m['threshold']})"
    if not m.get("pass"):
        text += " FAIL"
    if m.get("error"):
        text += f" [{m['error']}]"
    return text


def to_markdown(report: dict[str, Any]) -> str:
    """GitHub-flavored Markdown summary, suitable for PR comments or job summaries."""
    summary = report["summary"]
    lines = [
        f"# Eval report ({report.get('harness', 'llm-eval-harness')} "
        f"{report.get('version', '')})".rstrip(),
        "",
        f"Fixtures: `{report.get('fixturesDir', '')}`",
        "",
        "| Total | Passed | Failed | Skipped | Pass rate |",
        "|------:|-------:|-------:|--------:|----------:|",
        f"| {summary['total']} | {summary['passed']} | {summary['failed']} "
        f"| {summary['skipped']} | {summary['pass_rate'] * 100:.1f}% |",
    ]

    metrics = report.get("metrics") or {}
    if metrics:
        lines += [
            "",
            "## Metrics",
            "",
            "| Metric | Mean score | Pass rate | n |",
            "|--------|-----------:|----------:|--:|",
        ]
        for name, m in metrics.items():
            lines.append(
                f"| `{name}` | {m['mean_score']} | {m['pass_rate'] * 100:.1f}% | {m['n']} |"
            )

    cases = report.get("cases") or []
    if cases:
        lines += [
            "",
            "## Cases",
            "",
            "| Case | Status | Details |",
            "|------|--------|---------|",
        ]
        for c in cases:
            details = [_metric_detail(m) for m in c.get("metrics") or []]
            if c.get("error"):
                details.insert(0, c["error"])
            lines.append(
                f"| `{_md_cell(c.get('id'))}` | {_status(c)} "
                f"| {_md_cell('; '.join(details) or '-')} |"
            )
    return "\n".join(lines) + "\n"


def to_junit(report: dict[str, Any], suite_name: str = "llm-eval") -> str:
    """JUnit XML: one <testcase> per fixture case.

    Failed metrics become <failure>, case-level errors (e.g. missing
    actual.txt with --require-actual) become <error>, skipped cases <skipped>.
    """
    cases = report.get("cases") or []
    failures = sum(
        1 for c in cases if not c.get("skipped") and not c.get("pass") and not c.get("error")
    )
    errors = sum(1 for c in cases if not c.get("skipped") and c.get("error"))
    skipped = sum(1 for c in cases if c.get("skipped"))
    counts = {
        "tests": str(len(cases)),
        "failures": str(failures),
        "errors": str(errors),
        "skipped": str(skipped),
        "time": "0",
    }

    root = ET.Element("testsuites", {"name": report.get("harness", "llm-eval-harness"), **counts})
    suite_attrs = {"name": suite_name, **counts}
    if report.get("startedAt"):
        suite_attrs["timestamp"] = str(report["startedAt"])
    suite = ET.SubElement(root, "testsuite", suite_attrs)

    props = ET.SubElement(suite, "properties")
    for key in ("version", "fixturesDir"):
        if report.get(key) is not None:
            ET.SubElement(props, "property", {"name": key, "value": str(report[key])})

    for c in cases:
        tc = ET.SubElement(
            suite,
            "testcase",
            {
                "classname": f"{suite_name}.{c.get('path') or c.get('id')}",
                "name": str(c.get("id")),
                "time": "0",
            },
        )
        metric_lines = [_metric_detail(m) for m in c.get("metrics") or []]
        if c.get("skipped"):
            ET.SubElement(tc, "skipped", {"message": "missing actual.txt"})
        elif c.get("error"):
            el = ET.SubElement(tc, "error", {"message": str(c["error"]), "type": "CaseError"})
            el.text = str(c["error"])
        elif not c.get("pass"):
            failed = [m.get("name") for m in c.get("metrics") or [] if not m.get("pass")]
            el = ET.SubElement(
                tc,
                "failure",
                {"message": "failed metrics: " + ", ".join(map(str, failed)), "type": "MetricFailure"},
            )
            el.text = "\n".join(metric_lines)
        if metric_lines:
            out = ET.SubElement(tc, "system-out")
            out.text = "\n".join(metric_lines)

    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def render_report(report: dict[str, Any], fmt: str = "json") -> str:
    """Render ``report`` in one of FORMATS."""
    if fmt == "json":
        return to_json(report)
    if fmt == "markdown":
        return to_markdown(report)
    if fmt == "junit":
        return to_junit(report)
    raise ValueError(f"unknown report format: {fmt}")
