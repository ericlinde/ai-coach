from typing import Callable

from ..agent import CoachAgent


class SlackBot:
    """Slack Bolt integration. Depends only on CoachAgent."""

    def __init__(self, agent: CoachAgent):
        self._agent = agent
        self._send_fn: Callable[[str], None] | None = None

    def set_send_fn(self, fn: Callable[[str], None]) -> None:
        """Inject the function used to post messages (e.g. app.client.chat_postMessage)."""
        self._send_fn = fn

    def handle_message(self, text: str, say: Callable[[str], None]) -> None:
        response = self._agent.reply(text)
        say(response)

    def flush_pending_checkins(self, messages: list[str], send_fn: Callable[[str], None]) -> None:
        """Send a list of pending check-ins. The caller is responsible for clearing the queue."""
        for message in messages:
            send_fn(message)

    def send_message(self, text: str) -> None:
        if self._send_fn is None:
            raise RuntimeError("send_fn not set — call set_send_fn() first")
        self._send_fn(text)

    def start(self, slack_app, channel_id: str, pending_checkins: list[str]) -> None:
        """Wire Bolt event handlers and start the Socket Mode receiver."""
        send_fn = lambda text: slack_app.client.chat_postMessage(
            channel=channel_id, text=text
        )
        self.set_send_fn(send_fn)
        self.flush_pending_checkins(pending_checkins, send_fn)

        @slack_app.message()
        def on_message(message, say):
            self.handle_message(message.get("text", ""), say)

        slack_app.start()
