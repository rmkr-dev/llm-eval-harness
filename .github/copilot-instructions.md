# Copilot instructions

- This is an offline eval harness template (Copilot / Claude Code / Codex workflows only).
- Fixture cases live under `fixtures/<id>/` with `input.txt`, `expected.txt`, `actual.txt`, optional `meta.json`.
- Metrics: `exact_match`, `case_insensitive_match`, `contains`, `token_overlap` in `src/llm_eval_harness/metrics.py`.
- Run unit tests via `pytest`; score fixtures via `llm-eval`.
- Keep changes focused; do not add unrelated agent platforms.
