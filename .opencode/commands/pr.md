Prepare a GitLab merge request using `$ARGUMENTS`.

Apply these project skills before proceeding:

- `code-quality-policy`
- `commit-policy`

Before performing any GitLab or Git operations, review the project guidance in `AGENTS.md`, repository documentation, configuration files, and project-local OpenCode skills.

Workflow:

1. Ensure the working tree is clean. If uncommitted changes exist, stop and explain that the branch must be committed before creating a merge request.
2. Use glab for GitLab operations such as merge request lookup, creation, updates, and GitLab metadata. If glab is unavailable or authentication fails, stop and report the blocker.
3. Determine the merge request target branch from GitLab or repository configuration. Never assume the target branch.
4. Inspect:
   - the current branch;
   - upstream tracking;
   - commits unique to the current branch;
   - the diff against the target branch.
5. Check whether an open merge request already exists for the current branch. If one exists, update it instead of creating a duplicate.
6. Generate the merge request title and description entirely in Ukrainian.
   All user-facing text must be written in Ukrainian, including section headings,
   labels, explanations, and descriptions. Do not use English section headings.

7. Analyze the branch changes and generate:
   - a concise title following the repository convention;
   - a structured merge request description based on the actual code changes,
     not only commit messages.

8. The description should include the following sections, with headings written
   in Ukrainian:
   - Коротко — brief summary of the changes;
   - Чому це зроблено — explain the reason or problem being addressed;
   - Деталі реалізації — only noteworthy implementation details;
   - Перевірка — validation categories that were actually performed, without
     command output;
   - Критичні зміни — breaking changes, if any;
   - Нові залежності — newly introduced dependencies, or explicitly state
     "Немає".
9. If the branch name contains a Jira issue key, include it in the merge request title and reference it naturally in the description.
10. Before creating or updating the merge request, present the generated title and description to the user. Allow both to be edited before continuing.
11. If the user declines or does not explicitly approve the final version, stop without pushing or modifying the merge request.
12. After approval, re-check the repository state to ensure nothing changed while waiting for confirmation.
13. Push the current branch if needed using the repository's configured Git remote and its existing transport and authentication method, whether SSH or HTTPS. Never change the remote URL or force-push unless explicitly requested.
14. Create or update the GitLab merge request using `glab`.
15. Return the merge request URL.