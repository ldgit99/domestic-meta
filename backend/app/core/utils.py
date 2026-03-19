import re
import uuid
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def normalize_title(value: str) -> str:
    compact = re.sub(r"\s+", " ", value.strip().lower())
    return re.sub(r"[^0-9a-zA-Z가-힣 ]", "", compact)
