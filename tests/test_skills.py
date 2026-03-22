import pytest
from src.coach.skills import SkillsCache, SkillNotFoundError


def write_skill(skills_dir, name, content):
    (skills_dir / f"{name}.md").write_text(content)


def test_all_topics_returns_stems(tmp_path):
    write_skill(tmp_path, "mcp", "# MCP\ncontent")
    write_skill(tmp_path, "software-factory", "# Software Factory\ncontent")
    cache = SkillsCache(tmp_path)
    assert sorted(cache.all_topics()) == ["mcp", "software-factory"]


def test_all_topics_empty_when_directory_is_empty(tmp_path):
    cache = SkillsCache(tmp_path)
    assert cache.all_topics() == []


def test_load_returns_content(tmp_path):
    write_skill(tmp_path, "mcp", "# MCP\nsome guidance")
    cache = SkillsCache(tmp_path)
    assert cache.load("mcp") == "# MCP\nsome guidance"


def test_load_raises_on_unknown_topic(tmp_path):
    cache = SkillsCache(tmp_path)
    with pytest.raises(SkillNotFoundError, match="unknown-topic"):
        cache.load("unknown-topic")


def test_select_matches_on_filename(tmp_path):
    write_skill(tmp_path, "mcp", "# Model Context Protocol\nguidance here")
    write_skill(tmp_path, "code-review", "# Code Review\nreview tips")
    cache = SkillsCache(tmp_path)
    results = cache.select(["mcp"])
    assert len(results) == 1
    assert "Model Context Protocol" in results[0]


def test_select_matches_on_first_line_heading(tmp_path):
    write_skill(tmp_path, "software-factory", "# Safe Factories\ncontent")
    cache = SkillsCache(tmp_path)
    results = cache.select(["safe"])
    assert len(results) == 1
    assert "Safe Factories" in results[0]


def test_select_returns_empty_list_when_no_match(tmp_path):
    write_skill(tmp_path, "mcp", "# MCP\ncontent")
    cache = SkillsCache(tmp_path)
    assert cache.select(["nonexistent"]) == []


def test_select_returns_empty_list_when_directory_empty(tmp_path):
    cache = SkillsCache(tmp_path)
    assert cache.select(["anything"]) == []


def test_select_matches_multiple_keywords(tmp_path):
    write_skill(tmp_path, "mcp", "# MCP\ncontent")
    write_skill(tmp_path, "code-review", "# Code Review\ncontent")
    cache = SkillsCache(tmp_path)
    results = cache.select(["mcp", "review"])
    assert len(results) == 2


def test_update_creates_new_file(tmp_path):
    cache = SkillsCache(tmp_path)
    cache.update("new-topic", "# New Topic\nfresh content")
    assert (tmp_path / "new-topic.md").read_text() == "# New Topic\nfresh content"


def test_update_overwrites_existing_file(tmp_path):
    write_skill(tmp_path, "mcp", "# MCP\nold content")
    cache = SkillsCache(tmp_path)
    cache.update("mcp", "# MCP\nimproved content")
    assert cache.load("mcp") == "# MCP\nimproved content"
