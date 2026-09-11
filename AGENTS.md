# Agent notes

Scope: offline LLM eval harness for Copilot / Claude Code / Codex only.

## Goals

- Add or update golden fixtures under `fixtures/`.
- Keep metrics simple (`src/llm_eval_harness/metrics.py`); prefer extending the registry over new frameworks.
- After producing model output, write `actual.txt` next to `expected.txt`, then run `llm-eval`.
- Emit JSON reports only—no dashboards or remote callers.

## Do not

- Add other agent runtimes or cloud eval services.
- Commit secrets or live API keys.
- Change license or remove fixture goldens without updating tests.

## Checks

- `pytest` (unit tests for metrics)
- `llm-eval` (sample fixtures; use `--require-actual` in CI)
