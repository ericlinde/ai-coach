import json
import pytest
from src.coach.config import load_config, ConfigError


def write_config(tmp_path, data):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))
    return config_file


def test_valid_config_loads(tmp_path):
    cfg_path = write_config(tmp_path, {
        "checkin_frequency": "daily",
        "progress_repo": "github.com/user/progress",
        "skills_repo": "github.com/user/skills",
        "write_back": True,
        "model_id": "claude-sonnet-4-6",
    })
    config = load_config(cfg_path)
    assert config.checkin_frequency == "daily"
    assert config.progress_repo == "github.com/user/progress"
    assert config.skills_repo == "github.com/user/skills"
    assert config.write_back is True
    assert config.model_id == "claude-sonnet-4-6"


def test_missing_required_field_raises(tmp_path):
    # Missing checkin_frequency
    cfg_path = write_config(tmp_path, {
        "progress_repo": "github.com/user/progress",
        "skills_repo": "github.com/user/skills",
        "write_back": False,
        "model_id": "claude-sonnet-4-6",
    })
    with pytest.raises(ConfigError, match="checkin_frequency"):
        load_config(cfg_path)


def test_missing_model_id_raises(tmp_path):
    cfg_path = write_config(tmp_path, {
        "checkin_frequency": "daily",
        "progress_repo": "github.com/user/progress",
        "skills_repo": "github.com/user/skills",
        "write_back": False,
    })
    with pytest.raises(ConfigError, match="model_id"):
        load_config(cfg_path)


def test_unknown_fields_are_ignored(tmp_path):
    cfg_path = write_config(tmp_path, {
        "checkin_frequency": "daily",
        "progress_repo": "github.com/user/progress",
        "skills_repo": "github.com/user/skills",
        "write_back": False,
        "model_id": "claude-sonnet-4-6",
        "unknown_field": "ignored",
    })
    config = load_config(cfg_path)
    assert config.checkin_frequency == "daily"


def test_missing_config_file_raises(tmp_path):
    missing = tmp_path / "config.json"
    with pytest.raises(ConfigError, match="not found"):
        load_config(missing)


def test_optional_repos_can_be_absent(tmp_path):
    cfg_path = write_config(tmp_path, {
        "checkin_frequency": "daily",
        "write_back": False,
        "model_id": "claude-sonnet-4-6",
    })
    config = load_config(cfg_path)
    assert config.progress_repo is None
    assert config.skills_repo is None
