"""D5 capacity: explicit configuration with validation and failure behaviour."""
import json
from .errors import MSVEError

BOUNDS = {
    "max_assumptions": (0, 1024),
    "max_assertions": (1, 4096),
    "max_declarations": (0, 256),
    "max_verification_records": (0, 16),
    "max_descriptors": (1, 16),
    "max_invocations": (0, 16),
    "solver_timeout_ms": (1, 600000),
    "checker_enumeration_bound": (1, 12),
}

DEFAULTS = {
    "max_assumptions": 16,
    "max_assertions": 64,
    "max_declarations": 16,
    "max_verification_records": 2,
    "max_descriptors": 2,
    "max_invocations": 2,
    "solver_timeout_ms": 5000,
    "checker_enumeration_bound": 5,
}


def load_config(path=None, overrides=None):
    cfg = dict(DEFAULTS)
    if path:
        with open(path) as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict):
            raise MSVEError("INVALID_CONFIG", "config file must be a JSON object")
        cfg.update(loaded)
    if overrides:
        if not isinstance(overrides, dict):
            raise MSVEError("INVALID_CONFIG", "config overrides must be an object")
        cfg.update(overrides)
    for key, (lo, hi) in BOUNDS.items():
        if key not in cfg:
            raise MSVEError("INVALID_CONFIG", f"missing capacity key: {key}")
        v = cfg[key]
        if not isinstance(v, int) or isinstance(v, bool) or not (lo <= v <= hi):
            raise MSVEError(
                "INVALID_CONFIG",
                f"capacity key {key}={v!r} outside permitted range [{lo}, {hi}]",
            )
    return cfg


def check_limit(cfg, key, actual, what):
    limit = cfg[key]
    if actual > limit:
        raise MSVEError(
            "CAPACITY_EXCEEDED",
            f"{what}: {actual} exceeds configured {key}={limit}",
            {"key": key, "limit": limit, "actual": actual, "what": what},
        )
