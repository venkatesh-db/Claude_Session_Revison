import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from github_integration.github_client import create_client_from_token
from github_integration.github_operations import GitHubOperations


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")
    return value


def main() -> None:
    token = require_env("GITHUB_TOKEN")
    owner = require_env("REPO_OWNER")
    repo = require_env("REPO_NAME")
    base_branch = require_env("BASE_BRANCH")
    new_branch = require_env("NEW_BRANCH")
    title = require_env("PR_TITLE")
    body = Path(require_env("PR_BODY_FILE")).read_text(encoding="utf-8")
    patch_path = require_env("PATCH_FILE_PATH")
    patch_content = Path(require_env("PATCH_CONTENT_FILE")).read_text(encoding="utf-8")

    client = create_client_from_token(token)
    ops = GitHubOperations(client)
    pr_url = ops.create_draft_pull_request(
        owner, repo, base_branch, new_branch, title, body, {patch_path: patch_content}
    )
    print(f"Draft PR created: {pr_url}")


if __name__ == "__main__":
    main()
