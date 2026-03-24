import os
from pathlib import Path

from app.core import config


def test_load_env_file_reads_backend_env(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        """
# comment
RISS_LIVE_ENABLED=true
RISS_API_URL=https://example.org/riss
CORS_ALLOW_ORIGINS=http://localhost:3000, http://127.0.0.1:5500
QUOTED_VALUE='hello world'
""".strip(),
        encoding="utf-8",
    )

    keys = [
        "RISS_LIVE_ENABLED",
        "RISS_API_URL",
        "CORS_ALLOW_ORIGINS",
        "QUOTED_VALUE",
    ]
    previous_values = {key: os.environ.get(key) for key in keys}

    try:
        for key in keys:
            os.environ.pop(key, None)
        config.load_env_file(env_path)
        assert os.environ["RISS_LIVE_ENABLED"] == "true"
        assert os.environ["RISS_API_URL"] == "https://example.org/riss"
        assert os.environ["CORS_ALLOW_ORIGINS"] == "http://localhost:3000, http://127.0.0.1:5500"
        assert os.environ["QUOTED_VALUE"] == "hello world"
    finally:
        for key, value in previous_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
