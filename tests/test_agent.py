import pytest
from unittest.mock import MagicMock, call
from src.coach.agent import CoachAgent
from src.coach.memory import MemoryStore
from src.coach.skills import SkillsCache


def make_agent(tmp_path, llm, skills_content=None):
    memory = MemoryStore(tmp_path / "memory")
    (tmp_path / "memory").mkdir()
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    if skills_content:
        for name, content in skills_content.items():
            (skills_dir / f"{name}.md").write_text(content)
    skills = SkillsCache(skills_dir)
    return CoachAgent(memory, skills, llm, get_date=lambda: "2026-03-22")


def test_reply_passes_agent_state_in_system_prompt(tmp_path):
    llm = MagicMock(return_value="response")
    memory = MemoryStore(tmp_path / "memory")
    (tmp_path / "memory").mkdir()
    memory.save_agent_state("# State\ncurrent progress")
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    agent = CoachAgent(memory, SkillsCache(skills_dir), llm, get_date=lambda: "2026-03-22")

    agent.reply("tell me about mcp")

    first_call_system = llm.call_args_list[0][0][0]
    assert "current progress" in first_call_system


def test_reply_passes_selected_skills_in_system_prompt(tmp_path):
    llm = MagicMock(return_value="response")
    agent = make_agent(tmp_path, llm, skills_content={
        "mcp": "# MCP\nModel context protocol guidance"
    })

    agent.reply("tell me about mcp")

    first_call_system = llm.call_args_list[0][0][0]
    assert "Model context protocol guidance" in first_call_system


def test_reply_appends_both_turns_to_session_log(tmp_path):
    llm = MagicMock(return_value="the assistant reply")
    agent = make_agent(tmp_path, llm)

    agent.reply("hello")

    import json
    log = (tmp_path / "memory" / "sessions" / "2026-03-22.jsonl").read_text()
    lines = [json.loads(l) for l in log.strip().splitlines()]
    roles = [l["role"] for l in lines]
    assert "user" in roles
    assert "assistant" in roles
    user_line = next(l for l in lines if l["role"] == "user")
    assert user_line["content"] == "hello"
    assistant_line = next(l for l in lines if l["role"] == "assistant")
    assert assistant_line["content"] == "the assistant reply"


def test_reply_saves_agent_state_after_turn(tmp_path):
    call_count = 0

    def llm(system, messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "main response"
        return "# Updated State\nnew state content"

    agent = make_agent(tmp_path, llm)
    agent.reply("a question")

    state = (tmp_path / "memory" / "agent_state.md").read_text()
    assert "Updated State" in state


def test_reply_returns_response(tmp_path):
    llm = MagicMock(return_value="coaching advice")
    # Second call for state update
    llm.side_effect = ["coaching advice", "# State\nupdated"]
    agent = make_agent(tmp_path, llm)

    result = agent.reply("how do I improve?")
    assert result == "coaching advice"


def test_checkin_produces_response_without_user_message(tmp_path):
    llm = MagicMock(side_effect=["check-in message", "# State\nupdated"])
    agent = make_agent(tmp_path, llm)

    result = agent.checkin()

    assert result == "check-in message"
    assert llm.called


def test_checkin_appends_to_session_log(tmp_path):
    llm = MagicMock(side_effect=["check-in message", "# State\nupdated"])
    agent = make_agent(tmp_path, llm)

    agent.checkin()

    import json
    log = (tmp_path / "memory" / "sessions" / "2026-03-22.jsonl").read_text()
    lines = [json.loads(l) for l in log.strip().splitlines()]
    assert any(l["role"] == "assistant" and "check-in" in l["content"] for l in lines)


def test_skill_refinement_updates_skill_on_positive_signal(tmp_path):
    call_count = 0

    def llm(system, messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "explanation of mcp"
        if call_count == 2:
            return "# State\nupdated"
        # Third call: skill refinement
        return "# MCP\nimproved content after positive feedback"

    agent = make_agent(tmp_path, llm, skills_content={
        "mcp": "# MCP\noriginal content"
    })

    # First turn: agent explains mcp
    agent.reply("tell me about mcp")
    # Second turn: user signals it worked well
    agent.reply("that explanation worked well, thanks")

    skills_dir = tmp_path / "skills"
    updated = (skills_dir / "mcp.md").read_text()
    assert "improved content after positive feedback" in updated


def test_reply_works_when_skills_directory_is_empty(tmp_path):
    llm = MagicMock(side_effect=["response", "# State\nupdated"])
    agent = make_agent(tmp_path, llm)

    result = agent.reply("hello")
    assert result == "response"
