# OpenClaw → Codex → GitHub

## 1. Intake in OpenClaw

OpenClaw converts a Telegram request into a compact task contract:

- objective;
- repository;
- constraints;
- acceptance criteria;
- validation requirements;
- actions that require confirmation.

Do not copy an entire Telegram history into the engineering task.

## 2. Record the task in GitHub

Create one Issue per coherent outcome. The Issue is the source of truth for scope and acceptance criteria.

Split unrelated outcomes into separate Issues.

## 3. Execute in Codex

Use:

- **Local** for small, immediate changes in the current checkout;
- **Worktree** for substantial, background, or parallel work;
- **Cloud** when the task should run remotely in a configured environment.

Codex owns implementation, tests, diff inspection, and the proposed pull request.

## 4. Review

Before merging:

- compare the result with the Issue acceptance criteria;
- inspect the diff;
- confirm validation results;
- review security and migration risks;
- keep unresolved work explicit.

## 5. Report

After completion, OpenClaw may summarize the PR status in Telegram. GitHub remains the canonical record of code, review, and decisions.

## Ownership rule

Only one agent may write to a branch or worktree at a time. Other agents may analyze or review it read-only.
