# Execution guide

## Run tests locally

```bash
source .venv/bin/activate
pytest -q
```

## Run the FastAPI scaffold (optional, not wired into any workflow)

```bash
uvicorn src.api.main:app --reload
curl http://127.0.0.1:8000/health
```

## Run the patch-proposal CLI directly

```bash
export GITHUB_TOKEN=...        # a token with repo scope
export REPO_OWNER=<owner>
export REPO_NAME=<repo>
export BASE_BRANCH=main
export NEW_BRANCH=patch-proposal/manual-test
export PR_TITLE="test: manual patch proposal"
export PR_BODY_FILE=/tmp/pr-body.md
export PATCH_FILE_PATH=docs/incidents/manual-test.md
export PATCH_CONTENT_FILE=/tmp/patch-note.md
python tools/patch_proposal_runner.py
```

## Verifying the GitHub Actions workflows end to end

1. **PR review**: open a small real PR against `main`.
   ```bash
   gh run list --workflow "Claude PR Review"
   gh pr view <n> --comments
   ```
   Confirm the run reaches `completed`/`success` and Claude's comment has real content.

2. **CI triage + patch proposal**: push a branch with a deliberately broken test
   (e.g. `assert False`) and open a PR so `build-and-test.yml` fails, then watch:
   ```bash
   gh run list --workflow "Claude CI Failure Triage"
   gh issue list --label "triage:ci-failure"
   gh pr list --draft
   ```
   Confirm a real issue and a real draft PR referencing it both appear.

3. On any failure, read the actual log before changing anything:
   ```bash
   gh run view <run-id> --log-failed
   ```

4. Clean up: revert the intentionally broken test and close/delete any demo
   branches/PRs/issues used purely for verification.
