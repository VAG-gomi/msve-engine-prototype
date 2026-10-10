"""MSVE prototype CLI."""
import json
import sys

from msve.capacity import load_config
from msve.errors import MSVEError
from msve.pipeline import run_text


def main(argv):
    if len(argv) != 2:
        print("usage: msve-run <input.json>", file=sys.stderr)
        return 2
    try:
        with open(argv[1]) as f:
            text = f.read()
    except OSError as e:
        print(json.dumps({"error": "INPUT_READ_FAILED", "message": str(e)}))
        return 2
    try:
        cfg = load_config()
    except MSVEError as e:
        print(json.dumps({"error": e.code, "message": str(e)}))
        return 2
    try:
        result = run_text(text, cfg)
    except MSVEError as e:
        print(json.dumps({"error": e.code, "message": str(e), "details": e.details,
                          "experimental": True}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
