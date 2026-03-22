import subprocess
import pytest
from unittest.mock import MagicMock, patch, call
from src.coach.sync import RepoSync
from src.coach.config import Config


def make_config(progress_repo=None, skills_repo=None, write_back=False):
    return Config(
        checkin_frequency="daily",
        write_back=write_back,
        model_id="claude-sonnet-4-6",
        progress_repo=progress_repo,
        skills_repo=skills_repo,
    )


def make_sync(tmp_path, config):
    memory = MagicMock()
    skills = MagicMock()
    skills._dir = tmp_path / "skills"
    return RepoSync(memory, skills, config, base_path=tmp_path)


# ---------------------------------------------------------------------------
# sync_progress
# ---------------------------------------------------------------------------

def test_sync_progress_runs_correct_git_commands(tmp_path):
    config = make_config(progress_repo="github.com/user/progress")
    sync = make_sync(tmp_path, config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        sync.sync_progress()

    commands = [c[0][0] for c in mock_run.call_args_list]
    # Should have add, commit, push
    flat = [" ".join(cmd) for cmd in commands]
    assert any("git add" in c for c in flat)
    assert any("git commit" in c for c in flat)
    assert any("git push" in c for c in flat)


def test_sync_progress_skips_when_no_repo_configured(tmp_path):
    config = make_config(progress_repo=None)
    sync = make_sync(tmp_path, config)

    with patch("subprocess.run") as mock_run:
        sync.sync_progress()

    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# sync_skills
# ---------------------------------------------------------------------------

def test_sync_skills_pushes_before_pulling_when_write_back_enabled(tmp_path):
    config = make_config(skills_repo="github.com/user/skills", write_back=True)
    sync = make_sync(tmp_path, config)

    push_order = []

    def record_run(cmd, **kwargs):
        flat = " ".join(cmd)
        if "push" in flat:
            push_order.append("push")
        elif "pull" in flat or "fetch" in flat:
            push_order.append("pull")
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=record_run):
        sync.sync_skills()

    assert "push" in push_order
    assert "pull" in push_order
    assert push_order.index("push") < push_order.index("pull")


def test_sync_skills_only_pulls_when_write_back_disabled(tmp_path):
    config = make_config(skills_repo="github.com/user/skills", write_back=False)
    sync = make_sync(tmp_path, config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        sync.sync_skills()

    commands = [" ".join(c[0][0]) for c in mock_run.call_args_list]
    assert not any("push" in c for c in commands)
    assert any("pull" in c or "fetch" in c for c in commands)


def test_sync_skills_skips_when_no_repo_configured(tmp_path):
    config = make_config(skills_repo=None)
    sync = make_sync(tmp_path, config)

    with patch("subprocess.run") as mock_run:
        sync.sync_skills()

    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Retry / error handling
# ---------------------------------------------------------------------------

def test_transient_failure_triggers_retry(tmp_path):
    config = make_config(progress_repo="github.com/user/progress")
    sync = make_sync(tmp_path, config)

    call_count = 0

    def flaky_run(cmd, **kwargs):
        nonlocal call_count
        flat = " ".join(cmd)
        if "push" in flat:
            call_count += 1
            if call_count < 2:
                raise subprocess.CalledProcessError(1, cmd)
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=flaky_run):
        with patch("time.sleep"):  # don't actually sleep in tests
            sync.sync_progress()

    assert call_count >= 2


def test_permanent_failure_gives_up_and_does_not_raise(tmp_path):
    config = make_config(progress_repo="github.com/user/progress")
    sync = make_sync(tmp_path, config)

    def always_fail(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    with patch("subprocess.run", side_effect=always_fail):
        with patch("time.sleep"):
            # Should not raise — log and exit cleanly
            sync.sync_progress()
