import pytest
from unittest.mock import MagicMock, patch
from src.coach.interfaces.slack_bot import SlackBot


def make_bot(agent, memory=None):
    if memory is None:
        memory = MagicMock()
        memory.load_pending_checkins.return_value = []
    bot = SlackBot(agent, memory)
    return bot


def test_incoming_message_triggers_agent_reply(tmp_path):
    agent = MagicMock()
    agent.reply.return_value = "coaching response"
    bot = make_bot(agent)

    say = MagicMock()
    bot.handle_message("how do I improve?", say)

    agent.reply.assert_called_once_with("how do I improve?")


def test_response_is_passed_to_say(tmp_path):
    agent = MagicMock()
    agent.reply.return_value = "coaching response"
    bot = make_bot(agent)

    say = MagicMock()
    bot.handle_message("a question", say)

    say.assert_called_once_with("coaching response")


def test_pending_checkins_are_sent_on_startup():
    agent = MagicMock()
    memory = MagicMock()
    memory.load_pending_checkins.return_value = ["Check in #1", "Check in #2"]
    bot = SlackBot(agent, memory)

    send_fn = MagicMock()
    bot.flush_pending_checkins(send_fn)

    assert send_fn.call_count == 2
    send_fn.assert_any_call("Check in #1")
    send_fn.assert_any_call("Check in #2")


def test_flush_pending_checkins_clears_queue():
    agent = MagicMock()
    memory = MagicMock()
    memory.load_pending_checkins.return_value = ["Check in #1"]
    bot = SlackBot(agent, memory)

    bot.flush_pending_checkins(MagicMock())

    memory.clear_pending_checkins.assert_called_once()


def test_flush_pending_checkins_noop_when_empty():
    agent = MagicMock()
    memory = MagicMock()
    memory.load_pending_checkins.return_value = []
    bot = SlackBot(agent, memory)

    send_fn = MagicMock()
    bot.flush_pending_checkins(send_fn)

    send_fn.assert_not_called()
    memory.clear_pending_checkins.assert_not_called()


def test_send_message_sends_via_client():
    agent = MagicMock()
    bot = make_bot(agent)
    send_fn = MagicMock()
    bot.set_send_fn(send_fn)

    bot.send_message("hello from scheduler")

    send_fn.assert_called_once_with("hello from scheduler")
