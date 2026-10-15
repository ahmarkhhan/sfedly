"""Bounded CSCS connectivity check. Never print headers, keys or error bodies."""

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skony.__main__ import load_env
from skony.client import Settings


def main():
    load_env(ROOT / ".env")
    try:
        settings = Settings.from_environment()
        if settings.base_url != "https://api.inference.cscs.ch/v1":
            raise ValueError("This check is restricted to the user-supplied CSCS endpoint")
        if not settings.api_key:
            raise ValueError("The local CSCS key is missing")
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get(settings.base_url + "/models",
                                  headers={"Authorization": f"Bearer {settings.api_key}"})
        print("CSCS models endpoint HTTP", response.status_code)
        if response.status_code != 200:
            return 3
        models = [item["id"] for item in response.json()["data"]
                  if "Apertus-v1.5" in item.get("id", "")]
        print(json.dumps({"apertus_1_5_models": models, "configured_model": settings.model,
                          "configured_model_available": settings.model in models}))
        output = ROOT / "output" / "cscs_models.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"provider": "CSCS", "apertus_1_5_models": models}, indent=2), encoding="utf-8")
        return 0
    except httpx.HTTPError as error:
        print("CSCS network failure:", type(error).__name__)
        return 10
    except (ValueError, KeyError, TypeError):
        print("CSCS configuration or models response is invalid; no credentials displayed")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
