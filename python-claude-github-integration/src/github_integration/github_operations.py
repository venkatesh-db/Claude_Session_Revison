from github import Github, GithubException


class GitHubOperations:
    def __init__(self, client: Github):
        self._client = client

    def create_issue(
        self, owner: str, repo: str, title: str, body: str, labels: list[str] | None = None
    ) -> int:
        gh_repo = self._client.get_repo(f"{owner}/{repo}")
        issue = gh_repo.create_issue(title=title, body=body, labels=labels or [])
        return issue.number

    def comment_on_pull_request(self, owner: str, repo: str, pr_number: int, body: str) -> None:
        gh_repo = self._client.get_repo(f"{owner}/{repo}")
        pr = gh_repo.get_pull(pr_number)
        pr.create_issue_comment(body)

    def get_failed_job_logs(self, owner: str, repo: str, workflow_run_id: int) -> str:
        gh_repo = self._client.get_repo(f"{owner}/{repo}")
        run = gh_repo.get_workflow_run(workflow_run_id)
        failed_job_names = [job.name for job in run.jobs() if job.conclusion == "failure"]
        return "\n".join(failed_job_names)

    def create_draft_pull_request(
        self,
        owner: str,
        repo: str,
        base_branch: str,
        new_branch: str,
        title: str,
        body: str,
        file_changes: dict[str, str],
    ) -> str:
        gh_repo = self._client.get_repo(f"{owner}/{repo}")
        base_ref = gh_repo.get_git_ref(f"heads/{base_branch}")
        base_sha = base_ref.object.sha

        try:
            gh_repo.get_git_ref(f"heads/{new_branch}")
        except GithubException:
            gh_repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_sha)

        for path, content in file_changes.items():
            try:
                existing = gh_repo.get_contents(path, ref=new_branch)
                gh_repo.update_file(
                    path, f"chore: update {path}", content, existing.sha, branch=new_branch
                )
            except GithubException:
                gh_repo.create_file(
                    path, f"chore: add {path}", content, branch=new_branch
                )

        pr = gh_repo.create_pull(
            title=title, body=body, head=new_branch, base=base_branch, draft=True
        )
        return pr.html_url
