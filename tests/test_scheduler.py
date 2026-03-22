import json
import pytest
from unittest.mock import MagicMock, patch, call
from src.coach.scheduler import Scheduler, parse_interval, InvalidCadenceError
from src.coach.config import update_cadence, ConfigError


# ---------------------------------------------------------------------------
# parse_interval
# ---------------------------------------------------------------------------

def test_parse_interval_daily():
    assert parse_interval("daily") == 86400


def test_parse_interval_hourly():
    assert parse_interval("hourly") == 3600


def test_parse_interval_minutes_suffix():
    assert parse_interval("30m") == 1800


def test_parse_interval_hours_suffix():
    assert parse_interval("2h") == 7200


def test_parse_interval_days_suffix():
    assert parse_interval("1d") == 86400


def test_parse_interval_bare_integer_is_minutes():
    assert parse_interval("60") == 3600


def test_parse_interval_rejects_too_short():
    with pytest.raises(InvalidCadenceError):
        parse_interval("1m")  # less than 5 minutes


def test_parse_interval_rejects_too_long():
    with pytest.raises(InvalidCadenceError):
        parse_interval("8d")  # more than 7 days


def test_parse_interval_rejects_unknown_string():
    with pytest.raises(InvalidCadenceError):
        parse_interval("weekly")


# ---------------------------------------------------------------------------
# config.update_cadence (atomic write)
# ---------------------------------------------------------------------------

def test_config_update_cadence_persists(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({
        "checkin_frequency": "daily",
        "write_back": False,
        "model_id": "claude-sonnet-4-6",
    }))
    update_cadence(cfg_path, "2h")
    data = json.loads(cfg_path.read_text())
    assert data["checkin_frequency"] == "2h"


def test_config_update_cadence_rejects_invalid(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({
        "checkin_frequency": "daily",
        "write_back": False,
        "model_id": "claude-sonnet-4-6",
    }))
    with pytest.raises(InvalidCadenceError):
        update_cadence(cfg_path, "8d")
    # Original file must be unchanged
    data = json.loads(cfg_path.read_text())
    assert data["checkin_frequency"] == "daily"


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

def make_scheduler():
    mock_aps = MagicMock()
    mock_job = MagicMock()
    mock_aps.add_job.return_value = mock_job
    scheduler = Scheduler(apscheduler=mock_aps)
    return scheduler, mock_aps, mock_job


def test_job_scheduled_with_correct_interval():
    scheduler, mock_aps, _ = make_scheduler()
    agent = MagicMock()
    send_message = MagicMock()

    scheduler.start(agent, send_message, interval_seconds=3600)

    mock_aps.add_job.assert_called_once()
    _, kwargs = mock_aps.add_job.call_args
    assert kwargs["seconds"] == 3600


def test_job_calls_checkin_and_forwards_to_send_message():
    scheduler, mock_aps, _ = make_scheduler()
    agent = MagicMock()
    agent.checkin.return_value = "time to check in!"
    send_message = MagicMock()

    scheduler.start(agent, send_message, interval_seconds=3600)

    # Extract the job function and invoke it directly
    job_fn = mock_aps.add_job.call_args[0][0]
    job_fn()

    agent.checkin.assert_called_once()
    send_message.assert_called_once_with("time to check in!")


def test_update_cadence_reschedules_job():
    scheduler, mock_aps, mock_job = make_scheduler()
    agent = MagicMock()
    send_message = MagicMock()

    scheduler.start(agent, send_message, interval_seconds=3600)
    scheduler.update_cadence("30m")  # 1800 seconds

    mock_job.reschedule.assert_called_once()
    trigger_arg = mock_job.reschedule.call_args[0][0]
    # Check it's an interval trigger with correct seconds
    assert trigger_arg.interval.seconds == 1800 or trigger_arg.interval.total_seconds() == 1800


def test_update_cadence_noop_when_interval_unchanged():
    scheduler, mock_aps, mock_job = make_scheduler()
    agent = MagicMock()
    send_message = MagicMock()

    scheduler.start(agent, send_message, interval_seconds=3600)
    scheduler.update_cadence("hourly")  # still 3600s

    mock_job.reschedule.assert_not_called()


def test_invalid_cadence_rejected_does_not_reschedule():
    scheduler, mock_aps, mock_job = make_scheduler()
    agent = MagicMock()
    send_message = MagicMock()

    scheduler.start(agent, send_message, interval_seconds=3600)

    with pytest.raises(InvalidCadenceError):
        scheduler.update_cadence("8d")

    mock_job.reschedule.assert_not_called()
