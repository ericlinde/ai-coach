import logging
import subprocess
import time
from pathlib import Path

from .config import Config
from .memory import MemoryStore
from .skills import SkillsCache

log = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2  # seconds; doubles each attempt


def _run_git(args: list[str], cwd: Path, retries: int = _MAX_RETRIES) -> bool:
    """Run a git command with exponential backoff retry.

    Returns True on success, False after exhausting retries.
    """
    delay = _RETRY_BASE_DELAY
    for attempt in range(retries + 1):
        try:
            subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as exc:
            if attempt == retries:
                log.error("git command failed after %d attempts: %s\n%s",
                          retries + 1, " ".join(args), exc.stderr)
                return False
            log.warning("git command failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1, retries + 1, delay, " ".join(args))
            time.sleep(delay)
            delay *= 2


class RepoSync:
    def __init__(
        self,
        memory: MemoryStore,
        skills: SkillsCache,
        config: Config,
        base_path: Path,
    ):
        self._memory = memory
        self._skills = skills
        self._config = config
        self._base = Path(base_path)

    def sync_progress(self) -> None:
        """Commit and push memory/progress.md to the configured remote."""
        if not self._config.progress_repo:
            log.info("sync_progress: no progress_repo configured, skipping")
            return

        memory_dir = self._base / "memory"
        _run_git(["git", "add", "progress.md"], cwd=memory_dir)
        _run_git(
            ["git", "commit", "--allow-empty", "-m", "chore: update progress"],
            cwd=memory_dir,
        )
        _run_git(["git", "push"], cwd=memory_dir)

    def sync_skills(self) -> None:
        """Push modified skills (if write-back enabled) then pull latest from remote."""
        if not self._config.skills_repo:
            log.info("sync_skills: no skills_repo configured, skipping")
            return

        skills_dir = self._skills._dir

        if self._config.write_back:
            _run_git(["git", "add", "-A"], cwd=skills_dir)
            _run_git(
                ["git", "commit", "--allow-empty", "-m", "chore: update skills"],
                cwd=skills_dir,
            )
            _run_git(["git", "push"], cwd=skills_dir)

        _run_git(["git", "pull"], cwd=skills_dir)
