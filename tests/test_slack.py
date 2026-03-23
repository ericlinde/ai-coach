import pytest
from unittest.mock import MagicMock
from src.coach.interfaces.slack_bot import SlackBot


def make_bot(agent=None):
    agent = agent or MagicMock()
    return SlackBot(agent)


def test_incoming_message_triggers_agent_reply():
    agent = MagicMock()
    agent.reply.return_value = "coaching response"
    bot = make_bot(agent)

    say = MagicMock()
    bot.handle_message("how do I improve?", say)

    agent.reply.assert_called_once_with("how do I improve?")


def test_response_is_passed_to_say():
    agent = MagicMock()
    agent.reply.return_value = "coaching response"
    bot = make_bot(agent)

    say = MagicMock()
    bot.handle_message("a question", say)

    say.assert_called_once_with("coaching response")


def test_pending_checkins_are_sent_on_flush():
    bot = make_bot()
    send_fn = MagicMock()

    bot.flush_pending_checkins(["Check in #1", "Check in #2"], send_fn)

    assert send_fn.call_count == 2
    send_fn.assert_any_call("Check in #1")
    send_fn.assert_any_call("Check in #2")


def test_flush_pending_checkins_noop_when_empty():
    bot = make_bot()
    send_fn = MagicMock()

    bot.flush_pending_checkins([], send_fn)

    send_fn.assert_not_called()


def test_send_message_sends_via_client():
    bot = make_bot()
    send_fn = MagicMock()
    bot.set_send_fn(send_fn)

    bot.send_message("hello from scheduler")

    send_fn.assert_called_once_with("hello from scheduler")


def test_slack_bot_has_no_memory_store_dependency():
    import inspect
    from src.coach.interfaces.slack_bot import SlackBot
    sig = inspect.signature(SlackBot.__init__)
    param_names = list(sig.parameters.keys())
    assert "memory" not in param_names
