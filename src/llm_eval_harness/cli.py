"""Offline eval runner CLI: load golden fixtures, score, emit JSON."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from .metrics import list_metrics as registered_metrics
from .metrics import score as score_metrics
from .report import build_report, format_summary


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


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
        raw = json.loads(_read_text(meta_path))
        meta = {
            **raw,
            "id": raw.get("id") or case_name,
            "metrics": raw.get("metrics") or ["exact_match"],
        }

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
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for ent in fixtures_dir.iterdir():
        if not ent.is_dir() or ent.name.startswith("."):
            continue
        if only is not None and ent.name not in only:
            continue
        loaded = _load_case(ent, ent.name)
        if loaded is not None:
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
    help="Write JSON report to this path (stdout if omitted).",
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
    "--list-metrics",
    "list_metrics_flag",
    is_flag=True,
    default=False,
    help="Print registered metric names one per line and exit.",
)
def main(
    fixtures_dir: str,
    out_path: str | None,
    require_actual: bool,
    case_ids: tuple[str, ...],
    list_metrics_flag: bool,
) -> None:
    """Score fixture actual.txt against expected.txt; emit a JSON report."""
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
    loaded = _discover_cases(fixtures, only=only)
    if not loaded:
        click.echo(
            f"No fixture cases with expected.txt under {fixtures}",
            err=True,
        )
        sys.exit(2)

    case_results: list[dict[str, Any]] = []
    for c in loaded:
        if c["skipped"]:
            if require_actual:
                case_results.append(
                    {
                        "id": c["meta"]["id"],
                        "path": c["case_name"],
                        "pass": False,
                        "skipped": False,
                        "error": "missing actual.txt",
                        "metrics": [],
                    }
                )
            else:
                case_results.append(
                    {
                        "id": c["meta"]["id"],
                        "path": c["case_name"],
                        "pass": True,
                        "skipped": True,
                        "metrics": [],
                    }
                )
            continue

        metrics = score_metrics(c["actual"], c["expected"], c["meta"]["metrics"])
        passed = all(m["pass"] for m in metrics)
        case_results.append(
            {
                "id": c["meta"]["id"],
                "path": c["case_name"],
                "pass": passed,
                "skipped": False,
                "metrics": metrics,
            }
        )

    finished_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    report = build_report(
        cases=case_results,
        fixtures_dir=fixtures_dir,
        started_at=started_at,
        finished_at=finished_at,
    )

    payload = json.dumps(report, indent=2) + "\n"
    if out_path:
        Path(out_path).write_text(payload, encoding="utf-8")
        click.echo(f"Wrote {out_path}", err=True)
    else:
        click.echo(payload, nl=False)

    click.echo(format_summary(report), err=True)

    failed_hard = any(not c["pass"] and not c.get("skipped") for c in case_results)
    sys.exit(1 if failed_hard else 0)


if __name__ == "__main__":
    main()
