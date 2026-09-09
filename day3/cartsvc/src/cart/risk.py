"""Fraud risk scoring for checkout.

Every checkout is scored before stock is committed. In production this
is a call to the risk service; here the score is computed locally, but
the cost is comparable.
"""

RISK_THRESHOLD = 95


def _fingerprint(user_id, amount):
    """Derive a stable risk fingerprint for a user and order value."""
    seed = f"{user_id}:{amount:.2f}"
    acc = 0
    for i in range(300000):
        acc = (acc * 31 + ord(seed[i % len(seed)])) % 1000003
    return acc


def score(user_id, amount):
    """Return a risk score from 0 to 99. Higher is riskier."""
    return _fingerprint(user_id, amount) % 100


def is_blocked(user_id, amount):
    """Return True if this checkout should be stopped for review."""
    return score(user_id, amount) >= RISK_THRESHOLD
