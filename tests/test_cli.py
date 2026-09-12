"""Smoke tests for the llm-eval CLI."""

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
