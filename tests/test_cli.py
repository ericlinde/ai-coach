import pytest
from unittest.mock import MagicMock, patch
from src.coach.interfaces.cli import run


def make_agent(replies=None):
    agent = MagicMock()
    if replies:
        agent.reply.side_effect = replies
    else:
        agent.reply.return_value = "response"
    return agent


def make_memory(checkins=None):
    memory = MagicMock()
    memory.load_pending_checkins.return_value = checkins or []
    return memory


def test_pending_checkins_printed_before_first_prompt(capsys, monkeypatch):
    agent = make_agent()
    memory = make_memory(checkins=["Check in #1", "Check in #2"])
    inputs = iter(["exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    run(agent, memory)

    out = capsys.readouterr().out
    assert "Check in #1" in out
    assert "Check in #2" in out


def test_each_input_line_calls_agent_reply(monkeypatch):
    agent = make_agent(replies=["r1", "r2", "r3"])
    memory = make_memory()
    inputs = iter(["question 1", "question 2", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    run(agent, memory)

    assert agent.reply.call_count == 2
    agent.reply.assert_any_call("question 1")
    agent.reply.assert_any_call("question 2")


def test_response_is_printed(capsys, monkeypatch):
    agent = make_agent(replies=["here is my answer"])
    memory = make_memory()
    inputs = iter(["a question", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    run(agent, memory)

    out = capsys.readouterr().out
    assert "here is my answer" in out


def test_eof_exits_without_error(monkeypatch):
    agent = make_agent()
    memory = make_memory()
    monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError))

    # Should not raise
    run(agent, memory)


def test_exit_command_exits_loop(monkeypatch):
    agent = make_agent()
    memory = make_memory()
    inputs = iter(["exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    run(agent, memory)

    agent.reply.assert_not_called()


def test_no_checkins_prints_nothing_extra(capsys, monkeypatch):
    agent = make_agent()
    memory = make_memory(checkins=[])
    inputs = iter(["exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    run(agent, memory)

    out = capsys.readouterr().out
    assert "Check in" not in out
