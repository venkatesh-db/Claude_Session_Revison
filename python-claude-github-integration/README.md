# github-claude-integration-py

Wires Claude into the GitHub development lifecycle: PR review, CI-failure triage, and
automated draft-patch proposals — running as real GitHub Actions workflows.

This is the Python port of the .NET version of this project. Same mechanism, same
guardrails, different language.

## Project layout

```
src/
  github_integration/
    models.py            # PullRequestReview, CiFailureTriage dataclasses
    triage_rules.py       # pattern -> label mapping (pure, unit-tested)
    github_operations.py  # PyGithub wrapper: issues, PR comments, logs, draft PRs
    github_client.py      # token-auth client factory
  api/
    main.py                # FastAPI scaffold (not wired into any workflow yet)
tools/
  patch_proposal_runner.py  # CLI invoked by the CI-triage / patch-proposal workflows
tests/
  test_triage_rules.py
.github/workflows/
  build-and-test.yml          # pytest on every PR/push to main
  claude-pr-review.yml         # Claude reviews every PR diff, posts a comment
  claude-ci-triage.yml         # on build-and-test failure: triage job -> patch-proposal job (chained)
  claude-patch-proposal.yml    # manual-label fallback (issues:labeled, human-applied only)
```

## Required repository setup

These are **not** in any workflow YAML — they must be configured on the repo directly:

1. **Secret**: `ANTHROPIC_API_KEY`
   ```bash
   gh secret set ANTHROPIC_API_KEY --repo <owner>/<repo>
   ```
   Pipe the key directly from your own terminal/password manager — never paste it into
   a chat session.

2. **Actions token permissions** (two independently-gated settings; both required):
   ```bash
   gh api -X PUT repos/<owner>/<repo>/actions/permissions/workflow \
     -f default_workflow_permissions=write \
     -F can_approve_pull_request_reviews=true
   ```

3. **Labels** referenced by the triage rules and workflows:
   ```bash
   for l in "triage:ci-failure" "triage:needs-manual-review" "bug:null-reference" \
            "bug:timeout" "build:dependency" "build:compile-error" \
            "test:assertion-failure" "infra:resource-limit" "auth:credential-issue"; do
     gh label create "$l" --repo <owner>/<repo> --color "5319e7" --force
   done
   ```

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest -q
```

## Safety rails

- Claude-authored changes never push directly to `main` and never auto-merge — every
  patch proposal lands as a **draft** PR requiring human review.
- No API key, token, or password is ever entered or persisted on the user's behalf.
- Creating repos, pushing to shared branches, and changing repo-wide security settings
  are treated as side-effecting actions requiring explicit confirmation.

See [SETUP.md](SETUP.md) for the literal setup log and [EXECUTION.md](EXECUTION.md) for
how to run and verify everything end to end.
