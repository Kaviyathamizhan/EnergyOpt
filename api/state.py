from typing import Dict, Any

# Global state container populated during FastAPI lifespan
_global_state: Dict[str, Any] = {}

def set_state(key: str, value: Any):
    _global_state[key] = value

def get_state() -> Dict[str, Any]:
    """FastAPI dependency for accessing loaded models, buffer, and config."""
    return _global_state
