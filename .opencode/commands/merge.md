Merge a source branch into the current branch using `$ARGUMENTS`.

Before proceeding, apply these project skills:

- `code-quality-policy`
- `commit-policy`
- `dependency-policy`

Review the project guidance before making any changes. This includes `AGENTS.md`, repository documentation, configuration files, and project-local OpenCode skills.

Workflow:

1. Require the source branch name. Never assume which branch should be merged.
2. If no branch name is provided, ask the user for it before performing any Git operations.
3. Ensure the working tree is clean before starting the merge.
4. Update remote references.
5. Verify that the specified source branch exists.
6. Merge the source branch into the currently checked out branch.
7. Automatically resolve only simple, low-risk merge conflicts. If manual conflict resolution is required, stop the workflow and explain what needs to be resolved.
8. After a successful merge, check whether dependency-related files have changed and, if necessary, follow the project's `dependency-policy`.
9. Run the appropriate verification for the affected files.
10. Do not push the merge unless the user explicitly requests it.
