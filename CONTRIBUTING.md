# Contributing

Thanks for improving the harness.

## Setup

- Python >= 3.11
- `pip install -e ".[dev]"`

## Workflow

1. Branch from `main`.
2. Add or adjust fixtures under `fixtures/`.
3. Extend metrics in `src/llm_eval_harness/metrics.py` and cover them in `tests/`.
4. Run `pytest` and `llm-eval` locally.
5. Open a PR; CI runs unit tests and a sample eval.

## Style

- Python 3.11+, prefer the standard library plus Click unless a dependency is clearly justified.
- No company names, personal contacts, or AI authorship comments in committed files.
- Keep agent stubs (`AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`) brief and portable.
