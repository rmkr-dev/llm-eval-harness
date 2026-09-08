# Contributing

Thanks for improving the harness.

## Setup

- Node.js >= 20
- No install step required for the default scaffold (stdlib only)

## Workflow

1. Branch from `main`.
2. Add or adjust fixtures under `fixtures/`.
3. Extend metrics in `src/metrics.js` and cover them in `test/`.
4. Run the `test` and `eval` scripts locally.
5. Open a PR; CI runs unit tests and a sample eval.

## Style

- ES modules, Node built-ins only unless a dependency is clearly justified.
- No company names, personal contacts, or AI authorship comments in committed files.
- Keep agent stubs (`AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`) brief and portable.
