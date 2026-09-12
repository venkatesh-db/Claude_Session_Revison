from .models import CiFailureTriage

SIGNATURE_LABELS: list[tuple[str, str]] = [
    ("NullReferenceException", "bug:null-reference"),
    ("Timeout", "bug:timeout"),
    ("pip install", "build:dependency"),
    ("SyntaxError", "build:compile-error"),
    ("AssertionError", "test:assertion-failure"),
    ("MemoryError", "infra:resource-limit"),
    ("Unauthorized", "auth:credential-issue"),
]


def labels_for(failure_log: str) -> list[str]:
    if not failure_log or not failure_log.strip():
        return ["triage:needs-manual-review"]
    matched = [
        label for pattern, label in SIGNATURE_LABELS
        if pattern.lower() in failure_log.lower()
    ]
    return matched or ["triage:needs-manual-review"]


def build_triage(
    owner: str,
    repo: str,
    run_id: int,
    workflow_name: str,
    failure_log: str,
    root_cause_summary: str,
) -> CiFailureTriage:
    return CiFailureTriage(
        owner, repo, run_id, workflow_name, root_cause_summary, labels_for(failure_log)
    )
