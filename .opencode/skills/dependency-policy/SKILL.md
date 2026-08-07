---
name: 'dependency-policy'
description: "Use when Python dependencies, virtual environments, installs, branch switches, pulls, merges, or worktree starts may affect the project's dependency state."
---

# Dependencies Policy

Use this skill when dependency files, virtual environments, package installs, branch switches, pulls, merges, or worktree starts may affect project dependencies.

## Paired State

- Treat `requirements.txt` and the active Python environment as paired state.
- If `requirements.txt` changes, assume the virtual environment may need to be updated.
- Do not modify `requirements.txt` unless it is required by the requested work.
- If dependency changes are detected but the environment has not been updated, inform the user and ask whether dependencies should be installed.

## Installs

- Ask before running dependency installation commands after branch changes, pulls, merges, or worktree starts.
- Install dependencies from the repository root using:
  - `pip install -r requirements.txt`
- Do not upgrade unrelated packages or regenerate dependency files unless explicitly requested.

## Reporting

- Mention dependency changes in reviews, commits, merge requests, branch switches, pulls, merges, and worktree starts.
- Note when dependency installation may be required, but do not install packages without user approval.
