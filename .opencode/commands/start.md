Create a new Git branch using `$ARGUMENTS`.

Apply these project skills before proceeding:

- `commit-policy`
- `dependency-policy`

Before making any repository changes, review the project guidance in `AGENTS.md`, relevant documentation, configuration files, and project-local OpenCode skills.

Workflow:

1. Review the current repository state using `git status --short` and determine the active branch.
2. If the user already supplied a complete branch name, use it as the initial proposal.
3. Otherwise, follow the project's Jira workflow:
   - If a Jira issue key or issue number is available, use it.
   - If not, ask the user for the Jira issue number (optional).
   - Ask the user for a short description of the work.
4. Generate the branch name using the project's naming convention:

   `<type>/<issue-number-if-any>-<short-description>`

   Examples:

   - `feature/123-user-profile`
   - `bugfix/456-fix-login`
   - `hotfix/789-payment-timeout`
   - `chore/update-opencode-skills`

5. If the repository contains uncommitted changes, summarize them. Do not switch branches or modify the repository until the user explicitly confirms continuing.
6. Ask for all required confirmations in a single interaction:
   - whether to continue with any uncommitted changes;
   - the final branch name.
7. Allow the user to edit the proposed branch name before proceeding.
8. Continue only after explicit confirmation.
9. Fetch the latest remote references.
10. Determine the repository's default branch from the remote configuration. If it cannot be resolved, ask the user instead of guessing.
11. Verify that the default branch exists.
12. Switch to the default branch and update it using fast-forward only.
If a fast-forward update is not possible, stop and report the divergence.
13. Create and switch to the new branch.
14. If dependency-related files changed while updating the default branch, follow the project's `dependency-policy`.
