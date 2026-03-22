from pathlib import Path


class SkillNotFoundError(Exception):
    pass


class SkillsCache:
    def __init__(self, skills_dir: Path):
        self._dir = Path(skills_dir)

    def all_topics(self) -> list[str]:
        return [p.stem for p in self._dir.glob("*.md")]

    def load(self, topic: str) -> str:
        path = self._dir / f"{topic}.md"
        if not path.exists():
            raise SkillNotFoundError(f"Skill not found: {topic}")
        return path.read_text()

    def select(self, keywords: list[str]) -> list[str]:
        results = []
        for path in self._dir.glob("*.md"):
            content = path.read_text()
            first_line = content.splitlines()[0] if content.strip() else ""
            if any(
                kw.lower() in path.stem.lower() or kw.lower() in first_line.lower()
                for kw in keywords
            ):
                results.append(content)
        return results

    def update(self, topic: str, content: str) -> None:
        (self._dir / f"{topic}.md").write_text(content)
