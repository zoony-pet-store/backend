---
name: 'commit-policy'
description: 'Use when committing, preparing branches, merging, pushing, or creating GitLab merge requests; enforces explicit commit authorization and safe git workflow.'
---

# Commit Policy

## Project Workflows

The project defines reusable Git workflows under `.agents/command-prompts/`.

When the user requests a Git workflow in natural language, use the corresponding project workflow instead of improvising a custom Git sequence.

## Authorization

- Use the project-local custom slash commands for matching git workflows: `/commit`, `/changes`, `/pr`, `/pull`, `/push`, `/start`, and `/merge`.
- When the user asks for one of those workflows in natural language, follow the matching custom command workflow rather than improvising an ad-hoc git sequence.
- Never create commits automatically during normal tasks.
- Only run `git commit` when the user invokes `/commit` or directly asks to commit in the current turn.
- Treat phrases such as "finish", "complete", "save", "done", or "ship it" as insufficient authorization to commit.
- Do not stage changes until after the commit-message confirmation gate passes.

## Pre-Commit Inspection

- Always inspect `git status`, `git diff`, and `git log --oneline -10` before committing.
- Stage only intended changes.
- Re-check the staged diff before committing for unrelated changes, secrets, generated artifacts, and accidental broad formatting.
- Do not commit when quality issues, failing checks, unresolved review findings, secrets, unrelated changes, or required corrective actions remain.
- In commit result summaries, describe verification very briefly by check category only, for example "formatting, JSON validation, whitespace, and secret scan"; do not list exact commands, command output, or detailed check logs.

## Safety Rules

- Never amend, force-push, delete unmerged branches, delete remote branches, or change remotes unless explicitly requested.
- Use `glab` for GitLab access, including merge request lookup, creation, updates, and GitLab metadata; if `glab` is unavailable, stop and report the blocker.
- Do not use interactive git commands.
- Do not autostash, commit, amend, or force operations during pull, push, switch, merge, clean, or start workflows unless explicitly requested.
- Preserve unrelated user changes in dirty worktrees.

## Merge Request Descriptions

- For `/pr`, keep commit co-author trailers distinct from MR attribution: mention trailers only when commits contain them.
- The MR `authors` section should list the unique authors of commits included in the same target-branch diff range used for `Branch Commits`, even when no commits contain `Co-authored-by` trailers.

## Commit Messages

- Use the subject format `feat|fix|chore|hotfix|etc: short message of changes`, choosing the best type for the actual changes.
- Keep message style consistent with repository history.
- For non-trivial changes, include a detailed body explaining what changed, why, important implementation or verification details, and useful references such as spec documents or documentation links.
