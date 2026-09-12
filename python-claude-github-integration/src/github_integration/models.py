from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class PullRequestReviewComment:
    file_path: str
    line: int
    body: str


@dataclass(frozen=True)
class PullRequestReview:
    repo_owner: str
    repo_name: str
    pull_request_number: int
    summary: str
    comments: Sequence[PullRequestReviewComment]


@dataclass(frozen=True)
class CiFailureTriage:
    repo_owner: str
    repo_name: str
    workflow_run_id: int
    workflow_name: str
    root_cause_summary: str
    labels: Sequence[str]
