"""Offline eval runner CLI: load golden fixtures, score, emit a report."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from .formatters import FORMATS, render_report
from .metrics import list_metrics as registered_metrics
from .metrics import score as score_metrics
from .metrics import validate_thresholds
from .report import build_report, format_summary


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


class FixtureError(ValueError):
    """Invalid fixture metadata."""


def _normalize_tags(raw: Any, case_name: str) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list) or not all(isinstance(t, str) for t in raw):
        raise FixtureError(f"{case_name}/meta.json: tags must be a string or list of strings")
    return [t.strip() for t in raw if t.strip()]


def _load_case(case_dir: Path, case_name: str) -> dict[str, Any] | None:
    expected_path = case_dir / "expected.txt"
    actual_path = case_dir / "actual.txt"
    meta_path = case_dir / "meta.json"

    if not expected_path.is_file():
        return None

    expected = _read_text(expected_path)
    actual: str | None = None
    skipped = False
    if actual_path.is_file():
        actual = _read_text(actual_path)
    else:
        skipped = True

    meta: dict[str, Any] = {"id": case_name, "metrics": ["exact_match"]}
    if meta_path.is_file():
        try:
            raw = json.loads(_read_text(meta_path))
        except json.JSONDecodeError as exc:
            raise FixtureError(f"{case_name}/meta.json: invalid JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise FixtureError(f"{case_name}/meta.json: expected a JSON object")
        try:
            thresholds = validate_thresholds(raw.get("thresholds"))
        except ValueError as exc:
            raise FixtureError(f"{case_name}/meta.json: {exc}") from exc
        meta = {
            **raw,
            "id": raw.get("id") or case_name,
            "metrics": raw.get("metrics") or ["exact_match"],
            "tags": _normalize_tags(raw.get("tags"), case_name),
            "thresholds": thresholds,
        }
    meta.setdefault("tags", [])
    meta.setdefault("thresholds", {})

    return {
        "case_dir": case_dir,
        "case_name": case_name,
        "expected": expected,
        "actual": actual,
        "skipped": skipped,
        "meta": meta,
    }


def _discover_cases(
    fixtures_dir: Path,
    only: set[str] | None = None,
    tags: set[str] | None = None,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for ent in fixtures_dir.iterdir():
        if not ent.is_dir() or ent.name.startswith("."):
            continue
        if only is not None and ent.name not in only:
            continue
        loaded = _load_case(ent, ent.name)
        if loaded is None:
            continue
        if tags is not None and not tags.intersection(loaded["meta"]["tags"]):
            continue
        cases.append(loaded)
    cases.sort(key=lambda c: c["case_name"])
    return cases


@click.command("llm-eval")
@click.option(
    "--fixtures",
    "fixtures_dir",
    default="fixtures",
    show_default=True,
    type=click.Path(),
    help="Directory containing fixture case subdirectories.",
)
@click.option(
    "--out",
    "out_path",
    default=None,
    type=click.Path(),
    help="Write the report to this path (stdout if omitted).",
)
@click.option(
    "--format",
    "-f",
    "report_format",
    default="json",
    show_default=True,
    type=click.Choice(FORMATS),
    help="Report format: json, markdown, or junit (JUnit XML for CI test reporters).",
)
@click.option(
    "--require-actual",
    is_flag=True,
    default=False,
    help="Fail cases that are missing actual.txt instead of skipping.",
)
@click.option(
    "--case",
    "-c",
    "case_ids",
    multiple=True,
    help="Only run named case ids (directory names). Repeatable.",
)
@click.option(
    "--tag",
    "-t",
    "tag_filters",
    multiple=True,
    help="Only run cases whose meta.json tags include this tag. Repeatable (any match).",
)
@click.option(
    "--list-metrics",
    "list_metrics_flag",
    is_flag=True,
    default=False,
    help="Print registered metric names one per line and exit.",
)
@click.option(
    "--fail-under",
    "fail_under",
    default=None,
    type=float,
    help="Exit 1 if summary pass_rate is below this threshold (0.0-1.0).",
)
def main(
    fixtures_dir: str,
    out_path: str | None,
    report_format: str,
    require_actual: bool,
    case_ids: tuple[str, ...],
    tag_filters: tuple[str, ...],
    list_metrics_flag: bool,
    fail_under: float | None,
) -> None:
    """Score fixture actual.txt against expected.txt; emit a report."""
    if list_metrics_flag:
        for name in registered_metrics():
            click.echo(name)
        sys.exit(0)

    fixtures = Path(fixtures_dir).resolve()
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if not fixtures.is_dir():
        click.echo(f"Fixtures directory not found: {fixtures}", err=True)
        sys.exit(2)

    only = set(case_ids) if case_ids else None
    tags = {t.strip() for t in tag_filters if t.strip()} or None
    try:
        loaded = _discover_cases(fixtures, only=only, tags=tags)
    except FixtureError as exc:
        click.echo(f"Invalid fixture: {exc}", err=True)
        sys.exit(2)
    if not loaded:
        if tags:
            click.echo(
                f"No fixture cases under {fixtures} match tags: {', '.join(sorted(tags))}",
                err=True,
            )
        else:
            click.echo(
                f"No fixture cases with expected.txt under {fixtures}",
                err=True,
            )
        sys.exit(2)

    case_results: list[dict[str, Any]] = []
    for c in loaded:
        base: dict[str, Any] = {"id": c["meta"]["id"], "path": c["case_name"]}
        if c["meta"]["tags"]:
            base["tags"] = c["meta"]["tags"]
        if c["skipped"]:
            if require_actual:
                case_results.append(
                    {
                        **base,
                        "pass": False,
                        "skipped": False,
                        "error": "missing actual.txt",
                        "metrics": [],
                    }
                )
            else:
                case_results.append(
                    {**base, "pass": True, "skipped": True, "metrics": []}
                )
            continue

        metrics = score_metrics(
            c["actual"],
            c["expected"],
            c["meta"]["metrics"],
            thresholds=c["meta"]["thresholds"],
        )
        passed = all(m["pass"] for m in metrics)
        case_results.append(
            {**base, "pass": passed, "skipped": False, "metrics": metrics}
        )

    finished_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    report = build_report(
        cases=case_results,
        fixtures_dir=fixtures_dir,
        started_at=started_at,
        finished_at=finished_at,
    )

    payload = render_report(report, report_format)
    if out_path:
        Path(out_path).write_text(payload, encoding="utf-8")
        click.echo(f"Wrote {out_path}", err=True)
    else:
        click.echo(payload, nl=False)

    click.echo(format_summary(report), err=True)

    failed_hard = any(not c["pass"] and not c.get("skipped") for c in case_results)
    below_threshold = (
        fail_under is not None
        and float(report["summary"]["pass_rate"]) < float(fail_under)
    )
    sys.exit(1 if (failed_hard or below_threshold) else 0)


if __name__ == "__main__":
    main()
