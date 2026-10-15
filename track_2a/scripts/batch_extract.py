"""Compatibility entry point for the manifest-driven Skony batch command."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Keep the function imports used by callers of the original user-added script.
from skony.batch import load_manifest, main, run_batch  # noqa: E402,F401


if __name__ == "__main__":
    raise SystemExit(main())
