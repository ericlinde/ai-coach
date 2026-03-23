import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ConfigError(Exception):
    pass


@dataclass
class Config:
    checkin_frequency: str
    write_back: bool
    model_id: str
    progress_repo: Optional[str] = None
    skills_repo: Optional[str] = None


REQUIRED_FIELDS = ("checkin_frequency", "write_back", "model_id")


def load_config(path: Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file: {e}") from e

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ConfigError(f"Missing required config field: {field}")

    return Config(
        checkin_frequency=data["checkin_frequency"],
        write_back=data["write_back"],
        model_id=data["model_id"],
        progress_repo=data.get("progress_repo"),
        skills_repo=data.get("skills_repo"),
    )


def update_cadence(config_path: Path, new_interval: str) -> None:
    """Validate new_interval then atomically update checkin_frequency in config.json.

    Raises InvalidCadenceError (imported from scheduler) if the interval is invalid.
    The file is never modified if validation fails.
    """
    from .scheduler import parse_interval  # avoid circular import at module level

    parse_interval(new_interval)  # raises InvalidCadenceError on bad value

    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        data = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file: {e}") from e

    data["checkin_frequency"] = new_interval

    tmp_path = config_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    os.replace(tmp_path, config_path)
