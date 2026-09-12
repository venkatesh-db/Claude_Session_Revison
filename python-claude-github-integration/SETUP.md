# Setup log

Literal record of tools installed and repo settings configured, in order.

1. Verified `python` on PATH: `3.12.7` (matches `python-version: "3.12"` pinned in
   `.github/workflows/*.yml` via `actions/setup-python@v5`).
2. `gh` CLI was not present and no package manager (`winget`/`choco`) was available on
   this Windows host. Downloaded the CLI release zip directly from
   `https://github.com/cli/cli/releases/download/v2.63.2/gh_2.63.2_windows_amd64.zip`
   and extracted it to `C:\Users\Administrator\tools\gh-cli`.
3. Ran `gh auth login --hostname github.com --git-protocol https --web --scopes "repo,workflow"`
   — this requires the user to complete a browser device-code login; it cannot be
   completed non-interactively.
4. (Pending user confirmation) `gh repo create <owner>/github-claude-integration-py --public`
5. (Pending) `gh secret set ANTHROPIC_API_KEY --repo <owner>/github-claude-integration-py`
6. (Pending) `gh api -X PUT repos/<owner>/github-claude-integration-py/actions/permissions/workflow -f default_workflow_permissions=write -F can_approve_pull_request_reviews=true`
7. (Pending) Label creation loop — see README.md "Required repository setup" step 3.
8. Created Python virtual environment at `.venv/` and installed `requirements.txt`.
9. Ran `pytest -q` locally: 11/11 tests passed.
