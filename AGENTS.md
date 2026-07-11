# AGENTS.md

## Purpose

This repository is maintained with Codex. Complete one coherent outcome per task and keep changes reviewable.

## Before changing files

1. Read the relevant Issue and repository documentation.
2. Inspect the existing structure before choosing an implementation.
3. Identify the validation commands already used by the project.
4. State assumptions when requirements are ambiguous.

## Implementation rules

- Make the smallest complete change that satisfies the task.
- Preserve existing behavior unless the task explicitly changes it.
- Do not add dependencies without a concrete need.
- Never commit secrets, credentials, tokens, private keys, or `.env` files.
- Do not modify unrelated files.
- Use a separate branch or worktree for parallel work.
- Do not let multiple agents write to the same branch or worktree concurrently.

## Validation

Before declaring completion:

1. Run the relevant tests, linters, type checks, or build commands.
2. Inspect the final diff for unrelated or generated changes.
3. Report which checks passed and which could not be run.
4. Update documentation when behavior or setup changes.

## Pull requests

A pull request must include:

- the problem and intended outcome;
- a concise summary of the implementation;
- validation evidence;
- risks, limitations, or follow-up work;
- the related Issue when one exists.

## Project-specific commands

This section must be updated when the first application is added.

- Install: not configured
- Run: not configured
- Test: not configured
- Lint: not configured
- Build: not configured
