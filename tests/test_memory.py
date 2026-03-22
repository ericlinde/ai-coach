import json
import pytest
from src.coach.memory import MemoryStore


def test_load_agent_state_returns_empty_when_absent(tmp_path):
    store = MemoryStore(tmp_path)
    assert store.load_agent_state() == ""


def test_agent_state_round_trip(tmp_path):
    store = MemoryStore(tmp_path)
    store.save_agent_state("# Agent State\nsome content")
    assert store.load_agent_state() == "# Agent State\nsome content"


def test_load_progress_returns_empty_when_absent(tmp_path):
    store = MemoryStore(tmp_path)
    assert store.load_progress() == ""


def test_progress_round_trip(tmp_path):
    store = MemoryStore(tmp_path)
    store.save_progress("# Progress\nweek 1 done")
    assert store.load_progress() == "# Progress\nweek 1 done"


def test_append_session_turn_creates_file_on_first_call(tmp_path):
    store = MemoryStore(tmp_path)
    store.append_session_turn("2026-03-22", "user", "hello")
    log_file = tmp_path / "sessions" / "2026-03-22.jsonl"
    assert log_file.exists()


def test_append_session_turn_writes_valid_jsonl(tmp_path):
    store = MemoryStore(tmp_path)
    store.append_session_turn("2026-03-22", "user", "hello")
    log_file = tmp_path / "sessions" / "2026-03-22.jsonl"
    line = log_file.read_text().strip()
    obj = json.loads(line)
    assert obj["role"] == "user"
    assert obj["content"] == "hello"
    assert obj["date"] == "2026-03-22"


def test_append_session_turn_appends_multiple(tmp_path):
    store = MemoryStore(tmp_path)
    store.append_session_turn("2026-03-22", "user", "hello")
    store.append_session_turn("2026-03-22", "assistant", "world")
    log_file = tmp_path / "sessions" / "2026-03-22.jsonl"
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["role"] == "user"
    assert json.loads(lines[1])["role"] == "assistant"


def test_load_pending_checkins_empty_when_absent(tmp_path):
    store = MemoryStore(tmp_path)
    assert store.load_pending_checkins() == []


def test_pending_checkins_enqueue_load_clear(tmp_path):
    store = MemoryStore(tmp_path)
    store.enqueue_checkin("Time to check in!")
    store.enqueue_checkin("Another check-in")
    items = store.load_pending_checkins()
    assert items == ["Time to check in!", "Another check-in"]
    store.clear_pending_checkins()
    assert store.load_pending_checkins() == []


def test_pending_checkins_persist_across_instances(tmp_path):
    store1 = MemoryStore(tmp_path)
    store1.enqueue_checkin("persisted item")
    store2 = MemoryStore(tmp_path)
    assert store2.load_pending_checkins() == ["persisted item"]
