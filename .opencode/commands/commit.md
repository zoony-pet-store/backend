The `/commit $ARGUMENTS` command is considered explicit permission to create a Git commit, but only after all required policy and quality checks have completed successfully.

Apply the following project skills before proceeding:

- `code-quality-policy`
- `commit-policy`

Before performing any Git operations, review the repository-specific guidance. This includes `AGENTS.md`, in root directory, relevant README documentation, package or build scripts, CI and configuration files, and any project-local skills located under `.agents`.

Workflow:

1. Review the current repository state using `git status`, `git diff`, and `git log --oneline -10`.
2. If a `/review` command has already been executed during this session, reuse its results. Only perform any additional quality checks required for files that have changed since that review.
3. Otherwise, execute the verification appropriate for the modified files, including `git diff --check` before preparing the commit.
4. Do not stage any files until the user has approved the proposed commit message.
5. Abort the commit process if there are failing quality checks, unresolved review comments, exposed secrets, unintended modifications, or any remaining issues that must be addressed.
6. If the commit cannot proceed, clearly describe every blocking issue, including the affected files, recommended fixes, and any verification still required.
7. Prepare a commit message that follows the repository's conventions. Use the format `feat|fix|chore|hotfix|etc: short description`, and include a descriptive body whenever the changes are significant. Reference specifications or documentation where helpful.
8. Present the proposed commit subject and body to the user for confirmation, allowing both to be edited before continuing. If no body is needed, explicitly indicate `(empty body)`.
9. If the user declines, dismisses the confirmation, edits are still pending, or confirmation cannot be obtained, stop the workflow without staging or committing.
10. Once the final commit message has been explicitly approved, stage only the intended files.
11. Review the staged changes one final time to ensure there are no unrelated modifications or sensitive information before creating the commit.
12. Create the commit using the confirmed message. Do not amend an existing commit unless the user explicitly requests it.