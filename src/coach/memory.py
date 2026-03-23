import json
from pathlib import Path


class MemoryStore:
    def __init__(self, base_path: Path):
        self._base = Path(base_path)

    def load_agent_state(self) -> str:
        path = self._base / "agent_state.md"
        return path.read_text() if path.exists() else ""

    def save_agent_state(self, content: str) -> None:
        (self._base / "agent_state.md").write_text(content)

    def load_progress(self) -> str:
        path = self._base / "progress.md"
        return path.read_text() if path.exists() else ""

    def save_progress(self, content: str) -> None:
        (self._base / "progress.md").write_text(content)

    def append_session_turn(self, date: str, role: str, content: str) -> None:
        sessions_dir = self._base / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        log_file = sessions_dir / f"{date}.jsonl"
        record = json.dumps({"date": date, "role": role, "content": content})
        with log_file.open("a") as f:
            f.write(record + "\n")

    def _pending_checkins_path(self) -> Path:
        return self._base / "pending_checkins.json"

    def load_pending_checkins(self) -> list[str]:
        path = self._pending_checkins_path()
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def enqueue_checkin(self, message: str) -> None:
        items = self.load_pending_checkins()
        items.append(message)
        self._pending_checkins_path().write_text(json.dumps(items))

    def clear_pending_checkins(self) -> None:
        self._pending_checkins_path().write_text(json.dumps([]))
