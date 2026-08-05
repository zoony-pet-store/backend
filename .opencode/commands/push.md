Push the current branch using `$ARGUMENTS`.

Before proceeding, apply this project skill:

- `commit-policy`

Review the project guidance before making any changes. This includes `AGENTS.md`, repository documentation, configuration files, and project-local OpenCode skills.

Workflow:

1. Accept an optional synchronization strategy: `rebase` or `merge`.
2. Inspect the current repository state, including:
   - working tree status;
   - current branch;
   - recent commit history;
   - upstream tracking configuration.
3. If no synchronization strategy is provided:
   - default to `rebase` when the working tree is clean;
   - if uncommitted changes exist, ask the user which strategy to use before continuing.
4. Fetch the latest remote changes.
5. If the current branch tracks a remote branch, synchronize it using the selected strategy before pushing.
6. For the `rebase` strategy:
   - require a clean working tree;
   - update the branch using a rebase before pushing.
7. For the `merge` strategy:
   - update the branch using a merge;
   - require a clean working tree unless the user has explicitly approved continuing with local uncommitted changes.
8. If the current branch does not yet have an upstream branch, ask the user to confirm the target remote before publishing it.
9. Push the branch to the confirmed remote.
10. Never perform force pushes, create commits, amend commits, stash changes, or use any other history-rewriting operations unless the user explicitly requests them.