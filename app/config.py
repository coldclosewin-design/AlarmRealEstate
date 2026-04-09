import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
MOLIT_API_KEY = os.environ.get("MOLIT_API_KEY", "")


def load_properties() -> list[dict]:
    path = PROJECT_ROOT / "config" / "properties.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)
