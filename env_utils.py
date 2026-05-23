import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(ROOT_DIR, ".env")


def load_env_file(path=ENV_PATH):
    """Load simple KEY=VALUE pairs from .env without overriding real env vars."""
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
