Prepare a GitLab merge request using `$ARGUMENTS`.

Apply these project skills before proceeding:

- `code-quality-policy`
- `commit-policy`

Before performing any GitLab or Git operations, review the project guidance in `AGENTS.md`, repository documentation, configuration files, and project-local OpenCode skills.

Workflow:

1. Ensure the working tree is clean. If uncommitted changes exist, stop and explain that the branch must be committed before creating a merge request.
2. Use `glab` for all GitLab operations. If `glab` is unavailable or authentication fails, stop and report the blocker.
3. Determine the merge request target branch from GitLab or repository configuration. Never assume the target branch.
4. Inspect:
   - the current branch;
   - upstream tracking;
   - commits unique to the current branch;
   - the diff against the target branch.
5. Check whether an open merge request already exists for the current branch. If one exists, update it instead of creating a duplicate.
6. Analyze the branch changes and generate:
   - a concise title following the repository convention;
   - a structured merge request description based on the actual code changes, not only commit messages.
7. The description should include:
   - Summary
   - Why this change was made
   - Implementation details (only noteworthy changes)
   - Validation performed (only categories, not command output)
   - Breaking changes (if any)
   - New dependencies (or explicitly state "None")
8. If the branch name contains a Jira issue key, include it in the merge request title and reference it naturally in the description.
9. Before creating or updating the merge request, present the generated title and description to the user. Allow both to be edited before continuing.
10. If the user declines or does not explicitly approve the final version, stop without pushing or modifying the merge request.
11. After approval, re-check the repository state to ensure nothing changed while waiting for confirmation.
12. Push the current branch if needed. Never force-push unless explicitly requested.
13. Create or update the GitLab merge request using `glab`.
14. Return the merge request URL.