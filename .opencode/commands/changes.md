List and explain current uncommitted changes for `/changes $ARGUMENTS` without modifying the working tree.

Load and apply these skills: `code-quality-policy`, `commit-policy`, `dependency-policy`.

Before acting, inspect project-level specifications and repository nuances, including `AGENTS.md`, README files, package scripts, CI/config files, and project-local `.opencode` skills.

Read-only workflow:

1. Inspect short status, full status, staged diff, unstaged diff, and untracked files.
2. Separate staged, unstaged, and untracked changes.
3. Summarize each changed file or logical group with what changed, why it appears relevant, and any risks or follow-up verification.
4. Identify dependency manifest or lockfile changes and note whether installation or lockfile review may be needed. Do not run installs.
5. Identify generated files, secrets risk, local-only files, and unrelated-looking changes when visible.
6. Do not stage, commit, stash, clean, delete, format, generate, or run write commands.
