# llm-eval-harness

Lightweight **offline** LLM eval harness template for **GitHub Copilot**, **Claude Code**, and **Codex** workflows. Score prompt/model outputs against golden fixtures with simple metrics and emit a JSON, Markdown, or JUnit XML report. No network calls; no model API keys required at eval time.

**Version:** 1.0.0

## Requirements

- Python >= 3.11

## Install

```bash
pip install -e ".[dev]"
```

## Quick start

```bash
pytest
llm-eval --fixtures fixtures --out eval-report.json --require-actual
```

Flags:

| Flag | Description |
|------|-------------|
| `--fixtures` | Directory of fixture case subdirectories (default: `fixtures`) |
| `--out` | Write the report to this path (stdout if omitted) |
| `--format` / `-f` | Report format: `json` (default), `markdown`, or `junit` |
| `--require-actual` | Fail cases missing `actual.txt` instead of skipping |
| `--case` / `-c` | Only run named case ids (directory names); repeatable |
| `--tag` / `-t` | Only run cases whose `meta.json` `tags` include this tag; repeatable (any match) |
| `--list-metrics` | Print registered metric names one per line and exit |
| `--fail-under` | Exit 1 if summary `pass_rate` is below this float (0.0–1.0) |

Examples:

```bash
llm-eval --list-metrics
llm-eval --fixtures fixtures -c greeting -c summarize-bullets
llm-eval --fixtures fixtures --fail-under 0.9
llm-eval --fixtures fixtures --tag smoke
llm-eval --fixtures fixtures -t smoke -t summarization -c greeting
llm-eval --fixtures fixtures --format markdown >> "$GITHUB_STEP_SUMMARY"
llm-eval --fixtures fixtures --format junit --out eval-junit.xml
```

`--case` and `--tag` combine: a case must match both filters when both are given. If no case matches, the CLI exits `2`.

### Report formats

- `json` (default): the full report object, unchanged from earlier versions.
- `markdown`: summary, per-metric, and per-case tables (GitHub-flavored), handy for PR comments or `$GITHUB_STEP_SUMMARY`.
- `junit`: JUnit XML with one `<testcase>` per fixture. Failed metrics become `<failure>`, missing `actual.txt` under `--require-actual` becomes `<error>`, and skipped cases become `<skipped>`. Works with CI test reporters (GitHub Actions test-report actions, GitLab `artifacts:reports:junit`, Jenkins JUnit plugin).

The one-line-per-metric summary always goes to stderr regardless of format.

Exit codes: `0` when all scored cases pass (and pass_rate meets `--fail-under` if set); `1` when any scored case fails or pass_rate is below `--fail-under`; `2` for usage/fixture errors.

## Fixture layout

Each subdirectory under `fixtures/` is one case:

```
fixtures/
  my-case/
    input.txt      # prompt / inputs (informational; not scored)
    expected.txt   # golden expected output (required)
    actual.txt     # model or agent output to score
    meta.json      # optional: id, metrics, thresholds, tags, description
```

Example `meta.json`:

```json
{
  "id": "my-case",
  "description": "Short description",
  "metrics": ["exact_match", "token_overlap", "edit_ratio"],
  "thresholds": { "token_overlap": 0.6, "edit_ratio": 0.9 },
  "tags": ["smoke", "summarization"]
}
```

- `thresholds` (optional): per-metric pass threshold in `[0.0, 1.0]`. A metric with a threshold passes when its `score >= threshold`, and the threshold is recorded on the metric result. This overrides built-in defaults (`token_overlap` 0.8, `edit_ratio` 0.8, `length_ratio` 0.9) and also works for fractional metrics such as `contains_all` (e.g. `0.75` = at least three quarters of lines found). Metrics that error (invalid regex, bad JSON, unknown metric) always fail. Out-of-range or non-numeric values exit `2`.
- `tags` (optional): a string or list of strings used by `--tag`. Tags are copied onto the case in the report.

### Adding a fixture

1. Create `fixtures/<case-id>/`.
2. Add `input.txt` (what you asked the model) and `expected.txt` (golden answer).
3. After a Copilot / Claude Code / Codex run, save the response as `actual.txt`.
4. Set `metrics` in `meta.json` (default is `exact_match`).
5. Run `llm-eval` and inspect the JSON report.

## Metrics

| Name | Behavior |
|------|----------|
| `exact_match` | Trimmed string equality |
| `case_insensitive_match` | Trimmed, case-insensitive equality |
| `contains` | Expected is a substring of actual |
| `contains_all` | Each non-empty expected line must appear as a substring of actual (case-sensitive); score = fraction found; empty expected → pass |
| `contains_any` | At least one non-empty expected line is a substring of actual; empty expected → pass; score 1/0 |
| `json_equal` | Parse both as JSON (`json.loads`) and deep-compare; parse errors → fail + `error`; score 1/0 |
| `token_overlap` | Jaccard similarity over whitespace tokens (pass if score >= 0.8) |
| `starts_with` | Trimmed actual starts with trimmed expected |
| `ends_with` | Trimmed actual ends with trimmed expected |
| `regex_match` | Treat expected as a regex; `re.search` against actual (invalid regex → fail + error) |
| `whitespace_normalized_match` | Collapse whitespace to single spaces, trim, then exact equality |
| `length_ratio` | `min(len)/max(len)` (1 if both empty); pass if score >= 0.9 |
| `edit_ratio` | Normalized Levenshtein similarity on trimmed strings: `1 - distance / max(len)` (1 if both empty); pass if score >= 0.8. Pure Python, O(n·m), best for short-to-medium outputs |

Thresholds shown above are defaults; override them per case with `thresholds` in `meta.json`.

A case **passes** only when every listed metric passes. Missing `actual.txt` is skipped (exit 0) unless `--require-actual` is set.

Report summary fields: `total` (all cases), `passed` / `failed` (non-skipped only), `skipped`, and `pass_rate` = `passed / (passed + failed)` (or `1.0` if everything was skipped).

## Using with Copilot / Claude Code / Codex

This repo is aimed at agent-assisted coding loops:

1. Point the agent at `AGENTS.md`, `.github/copilot-instructions.md`, or `CLAUDE.md`.
2. Ask it to implement or refine prompts against `fixtures/*/input.txt`.
3. Have it write outputs to `fixtures/*/actual.txt`.
4. Run `llm-eval` (or CI) to score against goldens; use `--tag` to focus on a subset.
5. Iterate on prompts or code until the report is green.

Do not invent new agent runtimes here—keep the loop to Copilot, Claude Code, and Codex.

## Library API

```python
from llm_eval_harness import (
    build_report,
    contains_all,
    edit_ratio,
    json_equal,
    list_metrics,
    render_report,
    score,
)

results = score("Hello World", "hello world", ["exact_match", "contains"])
print(list_metrics())
print(contains_all("a b c", "a\nc"))
print(json_equal('{"x": 1}', '{"x": 1}'))
print(edit_ratio("Hello, wrold!", "Hello, world!"))
print(score("a b c", "a b c d e", ["token_overlap"], thresholds={"token_overlap": 0.6}))

report = build_report(
    cases=[{"id": "demo", "pass": all(m["pass"] for m in results), "skipped": False, "metrics": results}]
)
print(render_report(report, "markdown"))
```

## License

MIT
