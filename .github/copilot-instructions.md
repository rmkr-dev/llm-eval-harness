# Copilot instructions

- This is an offline eval harness template (Copilot / Claude Code / Codex workflows only).
- Fixture cases live under `fixtures/<id>/` with `input.txt`, `expected.txt`, `actual.txt`, optional `meta.json`.
- Metrics: `exact_match`, `case_insensitive_match`, `contains`, `token_overlap` in `src/metrics.js`.
- Run unit tests via the `test` script; score fixtures via the `eval` script.
- Keep changes focused; do not add unrelated agent platforms.
