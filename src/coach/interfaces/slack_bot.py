from typing import Callable

from ..agent import CoachAgent
from ..memory import MemoryStore


class SlackBot:
    """Slack Bolt integration. Depends only on CoachAgent and MemoryStore."""

    def __init__(self, agent: CoachAgent, memory: MemoryStore):
        self._agent = agent
        self._memory = memory
        self._send_fn: Callable[[str], None] | None = None

    def set_send_fn(self, fn: Callable[[str], None]) -> None:
        """Inject the function used to post messages (e.g. app.client.chat_postMessage)."""
        self._send_fn = fn

    def handle_message(self, text: str, say: Callable[[str], None]) -> None:
        response = self._agent.reply(text)
        say(response)

    def flush_pending_checkins(self, send_fn: Callable[[str], None]) -> None:
        items = self._memory.load_pending_checkins()
        if not items:
            return
        for item in items:
            send_fn(item)
        self._memory.clear_pending_checkins()

    def send_message(self, text: str) -> None:
        if self._send_fn is None:
            raise RuntimeError("send_fn not set — call set_send_fn() first")
        self._send_fn(text)

    def start(self, slack_app, channel_id: str) -> None:
        """Wire Bolt event handlers and start the Socket Mode receiver."""
        send_fn = lambda text: slack_app.client.chat_postMessage(
            channel=channel_id, text=text
        )
        self.set_send_fn(send_fn)
        self.flush_pending_checkins(send_fn)

        @slack_app.message()
        def on_message(message, say):
            self.handle_message(message.get("text", ""), say)

        slack_app.start()
