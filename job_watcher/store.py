"""Remembers which postings were already evaluated so each job is reported once."""
import json
from datetime import date, timedelta
from pathlib import Path


class SeenStore:
    def __init__(self, path: Path, keep_days: int = 90):
        self.path = path
        self.keep_days = keep_days
        self.seen: dict[str, str] = json.loads(path.read_text()) if path.exists() else {}

    def __contains__(self, key: str) -> bool:
        return key in self.seen

    def add(self, key: str) -> None:
        self.seen.setdefault(key, date.today().isoformat())

    def save(self) -> None:
        cutoff = (date.today() - timedelta(days=self.keep_days)).isoformat()
        self.seen = {k: v for k, v in self.seen.items() if v >= cutoff}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.seen, indent=0, sort_keys=True))
