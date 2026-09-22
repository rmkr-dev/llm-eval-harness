"""Aggregate case results into a JSON-serializable report."""

from __future__ import annotations

from typing import Any


def build_report(
    *,
    cases: list[dict[str, Any]],
    fixtures_dir: str = "fixtures",
    started_at: str | None = None,
    finished_at: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    """Build an eval report from per-case results."""
    if version is None:
        from . import __version__ as version

    total = len(cases)
    skipped = sum(1 for c in cases if c.get("skipped"))
    scored = [c for c in cases if not c.get("skipped")]
    passed = sum(1 for c in scored if c.get("pass"))
    failed = sum(1 for c in scored if not c.get("pass"))
    scored_n = passed + failed
    if scored_n > 0:
        pass_rate = float(f"{(passed / scored_n):.4f}")
    elif total == 0:
        pass_rate = 0.0
    else:
        # all skipped
        pass_rate = 1.0

    metric_totals: dict[str, dict[str, float | int]] = {}
    for c in scored:
        for m in c.get("metrics") or []:
            name = m["name"]
            if name not in metric_totals:
                metric_totals[name] = {"sum": 0.0, "count": 0, "passes": 0}
            t = metric_totals[name]
            t["sum"] = float(t["sum"]) + (float(m.get("score") or 0))
            t["count"] = int(t["count"]) + 1
            if m.get("pass"):
                t["passes"] = int(t["passes"]) + 1

    metrics_summary: dict[str, dict[str, float | int]] = {}
    for name, t in metric_totals.items():
        count = int(t["count"])
        metrics_summary[name] = {
            "mean_score": float(f"{(float(t['sum']) / count):.4f}") if count else 0,
            "pass_rate": float(f"{(int(t['passes']) / count):.4f}") if count else 0,
            "n": count,
        }

    return {
        "harness": "llm-eval-harness",
        "version": version,
        "fixturesDir": fixtures_dir,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": pass_rate,
        },
        "metrics": metrics_summary,
        "cases": cases,
    }


def format_summary(report: dict[str, Any]) -> str:
    """Human-readable one-line-per-metric summary."""
    summary = report["summary"]
    metrics = report.get("metrics") or {}
    skipped = int(summary.get("skipped") or 0)
    if skipped > 0:
        head = (
            f"Eval: {summary['passed']}/{summary['total']} passed "
            f"({summary['pass_rate'] * 100:.1f}%), "
            f"{skipped} skipped"
        )
    else:
        head = (
            f"Eval: {summary['passed']}/{summary['total']} passed "
            f"({summary['pass_rate'] * 100:.1f}%)"
        )
    lines = [head]
    for name, m in metrics.items():
        lines.append(
            f"  {name}: mean={m['mean_score']} "
            f"pass_rate={m['pass_rate'] * 100:.1f}% (n={m['n']})"
        )
    return "\n".join(lines)
