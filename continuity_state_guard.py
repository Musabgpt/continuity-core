"""Pure validation primitive for persisted Continuity Core state payloads."""

SUPPORTED_STATE_SCHEMAS = {1, 2}


def validate_state_payload(state, prefix="Transaction state"):
    """Validate a state payload without reading or mutating filesystem state.

    Raises ValueError with a stable diagnostic on the first invalid boundary.
    Returns None for a valid payload.
    """
    if not isinstance(state, dict):
        raise ValueError(f"{prefix} invalid: state must be object.")
    required = {
        "schema_version": int,
        "project": str,
        "goal": str,
        "status": str,
        "constraints": list,
        "decisions": list,
        "next_action": (str, type(None)),
        "updated_at": str,
    }
    for key, expected in required.items():
        if key not in state:
            raise ValueError(f"{prefix} invalid: missing field {key}.")
        value = state[key]
        valid_type = (
            isinstance(value, expected)
            if isinstance(expected, tuple)
            else isinstance(value, expected) and not (expected is int and isinstance(value, bool))
        )
        if not valid_type:
            expected_name = "string or null" if key == "next_action" else expected.__name__
            raise ValueError(f"{prefix} invalid: {key} must be {expected_name}.")
    if state["schema_version"] not in SUPPORTED_STATE_SCHEMAS:
        raise ValueError(f"{prefix} invalid: unsupported schema_version.")
    if not state["project"].strip():
        raise ValueError(f"{prefix} invalid: project is empty.")
    if not state["goal"].strip():
        raise ValueError(f"{prefix} invalid: goal is empty.")
    if not all(isinstance(value, str) and value.strip() for value in state["constraints"]):
        raise ValueError(f"{prefix} invalid: constraints must be non-empty strings.")
    if not all(isinstance(value, str) and value.strip() for value in state["decisions"]):
        raise ValueError(f"{prefix} invalid: decisions must be non-empty strings.")
    if state["schema_version"] == 2:
        revision = state.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            raise ValueError(f"{prefix} invalid: schema v2 requires non-negative integer revision.")
