"""The dangerous-error rule lives in app/safety.py (the app's guards use it too); re-exported here
for the evaluation."""
from app.safety import NOT_YET, RANK, STRICTNESS, error_kind, is_dangerous  # noqa: F401
