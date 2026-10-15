"""Import pinned corpus PDFs and optional cached batch suggestions; no model calls."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skony.cache import ResponseCache
from skony.corpus import import_corpus
from skony.review import ReviewStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-dir", type=Path, default=ROOT / "data/private/gold")
    parser.add_argument("--store", type=Path, default=ROOT / "output/workbench")
    parser.add_argument("--batch-run", type=Path, help="directory containing run_ledger.json")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "output/cache")
    args = parser.parse_args()
    try:
        counts = import_corpus(args.fetch_dir, ReviewStore(args.store), run_dir=args.batch_run,
                               cache=ResponseCache(args.cache_dir) if args.batch_run else None)
    except (ValueError, OSError, KeyError):
        print("Import could not start. Check the source manifest, batch ledger and cache.", file=sys.stderr)
        return 2
    print(json.dumps(counts, indent=2))
    print(f"Review store: {args.store}")
    return 1 if counts["source_failed"] or counts["result_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
