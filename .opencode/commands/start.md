Create and switch to a new Git branch using `$ARGUMENTS`.

Apply these project skills before proceeding:

* `commit-policy`
* `dependencies-policy`

Do not use worktrees.

Before making repository changes, inspect project-level specifications and repository-specific guidance, including:

* `AGENTS.md`
* relevant nested `AGENTS.md`
* README files
* package and build scripts
* CI/configuration files
* project-local OpenCode skills in `.opencode`

## Branch naming convention

Generate branch names using exactly:

`<type>/<issue-number-if-any>-<short-description>`

Examples:

* `feature/123-add-login`
* `bugfix/456-fix-mobile-header`
* `hotfix/789-payment-timeout`
* `chore/update-opencode-commands`
* `ci/123-update-pipeline`

If no Jira issue number is provided, omit it:

* `feature/add-login`
* `chore/update-opencode-commands`

The following parts are determined automatically:

* `<type>` — inferred from the actual changes;
* `<short-description>` — generated from the actual changes.

The user only provides or confirms the optional Jira issue number and confirms the generated branch name.

## Workflow

### 1. Inspect the current repository state

Before asking for branch information, inspect:

* `git status --short`
* current branch
* `git diff`
* `git diff --cached`
* untracked files
* recent commit history
* upstream tracking configuration

Consider all relevant work in the repository:

* staged changes;
* unstaged changes;
* untracked files.

Read changed files when necessary to understand the purpose of the work.

Do not assume that only staged or only unstaged changes represent the current task.

### 2. Analyze the current work

Use the repository changes as the primary source of truth for the branch name.

Determine:

* what the changes accomplish;
* which files belong to the current work;
* whether the work is a feature, bug fix, maintenance task, CI change, refactor, documentation change, test change, performance change, or another appropriate category.

Do not ask the user to describe the work if it can be understood from the repository state.

### 3. Determine the branch type automatically

Choose the most appropriate type based on the actual changes and repository conventions.

Prefer:

* `feature` — new functionality or capability;
* `bugfix` — non-urgent bug fix;
* `hotfix` — urgent production fix;
* `chore` — maintenance, tooling, configuration, or repository housekeeping;
* `ci` — CI/CD changes;
* `refactor` — restructuring without intended behavior changes;
* `docs` — documentation-only changes;
* `test` — test-only changes;
* `perf` — performance improvements.

Use the project's established branch types when documented.

Do not ask the user to select the type unless the changes are genuinely impossible to classify automatically.

### 4. Ask for the optional Jira issue number

Ask the user whether to include a Jira issue number.

The question must provide:

* a choice to continue without a Jira number;
* a choice to provide a Jira number.

If `$ARGUMENTS` already contains a Jira issue number, use it as the initial value instead of asking the user to repeat it.

Never invent a Jira issue number.

If the user chooses no issue number, omit it from the branch name.

### 5. Generate the short description automatically

Generate `<short-description>` from the actual repository changes.

Use:

* staged diff;
* unstaged diff;
* untracked files;
* changed file names;
* recent commits;
* repository terminology;
* `$ARGUMENTS`, if provided.

The description must:

* be concise;
* use lowercase;
* use hyphens;
* describe the purpose of the work;
* reflect the actual changes;
* avoid implementation-level noise;
* avoid generic text such as `update-code`, `make-changes`, or `fix-stuff`;
* not include the Jira issue number;
* not invent functionality.

Examples:

* `add-dependency-policy`
* `update-opencode-start-workflow`
* `fix-login-redirect`
* `add-model-diagram-sync`
* `refactor-auth-flow`

### 6. Generate the complete branch name

Combine the automatically determined type, optional Jira number, and generated description:

`<type>/<issue-number-if-any>-<short-description>`

Validate that the result:

* is a valid Git branch name;
* contains no spaces;
* follows repository conventions;
* does not contain duplicate separators;
* does not contain the Jira number more than once.

If the generated branch already exists, report that and generate a safe alternative.

### 7. Handle existing changes safely

If the working tree contains changes:

* summarize them;
* distinguish staged, unstaged, and untracked changes when useful;
* use them to generate the branch name;
* do not stash them;
* do not reset them;
* do not discard them;
* do not commit them;
* do not pull;
* do not switch to another branch;
* do not otherwise modify the working tree before confirmation.

The purpose of `/start` is to place the **existing work onto the newly created branch**.

### 8. Present the proposed branch

Show the user:

* detected branch type;
* Jira issue number, if any;
* generated short description;
* complete proposed branch name;
* brief summary of the changes used to generate the name.

Then ask for confirmation:

**Create this branch?**

Allow:

* **Yes** — create the proposed branch;
* **Edit** — provide either a complete branch name or a description of what the branch should represent;
* **No** — cancel.

If the user chooses **Edit** and provides a description rather than a complete branch name:

* use the description as additional context;
* regenerate the branch type if necessary;
* regenerate the short description;
* produce a new branch name using the same naming convention;
* ask for confirmation again.

Do not require the user to manually choose the branch type.

### 9. Create the branch

Only after the final branch name has been explicitly confirmed:

* create the branch from the current `HEAD`;
* switch to it immediately.

Use the equivalent of:

`git switch -c <final-branch-name>`

Do not:

* fetch remotes;
* switch to the default branch;
* pull;
* rebase;
* merge;
* stash;
* reset;
* commit;
* create a worktree.

Existing staged, unstaged, and untracked changes must remain intact.

### 10. Verify the result

After creating the branch, verify:

* the active branch is the new branch;
* the branch was created successfully;
* staged changes remain staged;
* unstaged changes remain unstaged;
* untracked files remain present.

If the branch creation would overwrite or lose local work, stop instead of forcing the operation.

### 11. Dependency handling

After creating the branch, inspect dependency-related files involved in the current work.

If dependency manifests or lockfiles are affected:

* apply `dependencies-policy`;
* determine whether dependency installation is actually required;
* ask before running installation commands.

If installation is approved, prefer:

`pnpm install --frozen-lockfile`

from the repository root when the project uses pnpm.

Do not install dependencies unnecessarily.

### 12. Final result

Report:

* final branch name;
* detected branch type;
* Jira issue number, if any;
* generated short description;
* confirmation that the branch was created and checked out;
* confirmation that existing changes were preserved;
* any dependency-policy follow-up required.

## Safety rules

Never:

* invent a Jira issue number;
* ask the user to describe work that can already be inferred from the repository changes;
* silently discard or stash changes;
* commit changes;
* reset the working tree;
* force checkout over local changes;
* fetch or pull merely to create the branch;
* switch to another branch before confirmation;
* create a worktree;
* create the branch before the final name is confirmed.
