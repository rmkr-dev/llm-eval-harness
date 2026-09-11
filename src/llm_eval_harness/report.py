"""Aggregate case results into a JSON-serializable report."""

from __future__ import annotations

from typing import Any


def build_report(
    *,
    cases: list[dict[str, Any]],
    fixtures_dir: str = "fixtures",
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    """Build an eval report from per-case results."""
    total = len(cases)
    passed = sum(1 for c in cases if c.get("pass"))
    failed = total - passed

    metric_totals: dict[str, dict[str, float | int]] = {}
    for c in cases:
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
        "version": "0.1.0",
        "fixturesDir": fixtures_dir,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": float(f"{(passed / total):.4f}") if total else 0,
        },
        "metrics": metrics_summary,
        "cases": cases,
    }


def format_summary(report: dict[str, Any]) -> str:
    """Human-readable one-line-per-metric summary."""
    summary = report["summary"]
    metrics = report.get("metrics") or {}
    lines = [
        f"Eval: {summary['passed']}/{summary['total']} passed "
        f"({summary['pass_rate'] * 100:.1f}%)"
    ]
    for name, m in metrics.items():
        lines.append(
            f"  {name}: mean={m['mean_score']} "
            f"pass_rate={m['pass_rate'] * 100:.1f}% (n={m['n']})"
        )
    return "\n".join(lines)
