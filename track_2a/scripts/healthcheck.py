"""Container liveness check; deliberately bypasses any HTTP proxy settings."""

import json
from urllib.request import ProxyHandler, build_opener


def main():
    try:
        with build_opener(ProxyHandler({})).open("http://127.0.0.1:8765/healthz", timeout=2) as response:
            return 0 if json.load(response).get("status") == "ok" else 1
    except (OSError, ValueError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
