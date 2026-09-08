# llm-eval-harness

Lightweight **offline** LLM eval harness template for **GitHub Copilot**, **Claude Code**, and **Codex** workflows. Score prompt/model outputs against golden fixtures with simple metrics and emit a JSON report. No network calls; no model API keys required at eval time.

## Requirements

- Node.js >= 20

## Quick start

Use the package scripts `test` and `eval` (see package.json). For flags, pass `--fixtures`, `--out`, and `--require-actual` to the eval entrypoint under `src/`.

## Fixture layout

Each subdirectory under `fixtures/` is one case:

```
fixtures/
  my-case/
    input.txt      # prompt / inputs (informational; not scored)
    expected.txt   # golden expected output (required)
    actual.txt     # model or agent output to score
    meta.json      # optional: id, metrics list, description
```

Example `meta.json`:

```json
{
  "id": "my-case",
  "description": "Short description",
  "metrics": ["exact_match", "token_overlap"]
}
```

### Adding a fixture

1. Create `fixtures/<case-id>/`.
2. Add `input.txt` (what you asked the model) and `expected.txt` (golden answer).
3. After a Copilot / Claude Code / Codex run, save the response as `actual.txt`.
4. Set `metrics` in `meta.json` (default is `exact_match`).
5. Run the `eval` script and inspect the JSON report.

## Metrics

| Name | Behavior |
|------|----------|
| `exact_match` | Trimmed string equality |
| `case_insensitive_match` | Trimmed, case-insensitive equality |
| `contains` | Expected is a substring of actual |
| `token_overlap` | Jaccard similarity over whitespace tokens (pass if score >= 0.8) |

A case **passes** only when every listed metric passes. Missing `actual.txt` is skipped (exit 0) unless `--require-actual` is set.

## Using with Copilot / Claude Code / Codex

This repo is aimed at agent-assisted coding loops:

1. Point the agent at `AGENTS.md`, `.github/copilot-instructions.md`, or `CLAUDE.md`.
2. Ask it to implement or refine prompts against `fixtures/*/input.txt`.
3. Have it write outputs to `fixtures/*/actual.txt`.
4. Run the `eval` script (or CI) to score against goldens.
5. Iterate on prompts or code until the report is green.

Do not invent new agent runtimes here—keep the loop to Copilot, Claude Code, and Codex.

## Library API

Import `score`, `listMetrics`, and `buildReport` from the package entry (`src/index.js`). Call `score(actual, expected, ["exact_match", "contains"])` to obtain per-metric results.

## License

MIT
