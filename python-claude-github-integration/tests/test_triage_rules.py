import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from github_integration.triage_rules import build_triage, labels_for


def test_null_reference_signature():
    assert labels_for("System threw NullReferenceException at line 42") == ["bug:null-reference"]


def test_timeout_signature():
    assert labels_for("Operation Timeout after 30s") == ["bug:timeout"]


def test_pip_install_signature():
    assert labels_for("ERROR: pip install failed for package foo") == ["build:dependency"]


def test_syntax_error_signature():
    assert labels_for("SyntaxError: invalid syntax") == ["build:compile-error"]


def test_assertion_failure_signature():
    assert labels_for("AssertionError: expected 1 got 2") == ["test:assertion-failure"]


def test_memory_error_signature():
    assert labels_for("MemoryError: out of memory") == ["infra:resource-limit"]


def test_unauthorized_signature():
    assert labels_for("401 Unauthorized: bad token") == ["auth:credential-issue"]


def test_unrecognized_log_falls_back():
    assert labels_for("some totally unrelated failure text") == ["triage:needs-manual-review"]


def test_empty_log_falls_back():
    assert labels_for("") == ["triage:needs-manual-review"]
    assert labels_for("   ") == ["triage:needs-manual-review"]


def test_multiple_simultaneous_signatures():
    log = "SyntaxError happened, then AssertionError was also raised"
    assert labels_for(log) == ["build:compile-error", "test:assertion-failure"]


def test_build_triage():
    triage = build_triage(
        "octocat", "hello-world", 123, "build-and-test",
        "Timeout while running tests", "Test suite exceeded the timeout limit"
    )
    assert triage.repo_owner == "octocat"
    assert triage.repo_name == "hello-world"
    assert triage.workflow_run_id == 123
    assert triage.workflow_name == "build-and-test"
    assert triage.root_cause_summary == "Test suite exceeded the timeout limit"
    assert triage.labels == ["bug:timeout"]
