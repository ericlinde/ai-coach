import datetime
import logging
from typing import Callable

log = logging.getLogger(__name__)

from .memory import MemoryStore
from .skills import SkillsCache, SkillNotFoundError

_POSITIVE_SIGNALS = ("worked well", "great explanation", "that helped", "makes sense",
                     "very helpful", "perfect explanation", "that was clear")
_NEGATIVE_SIGNALS = ("didn't understand", "that was confusing", "doesn't make sense",
                     "not helpful", "that was unclear", "explanation was poor")

_STATE_UPDATE_SYSTEM = (
    "You maintain a compact working-memory file (agent_state.md) for an AI coach. "
    "Given the conversation below, return an updated version of agent_state.md that "
    "reflects new progress, open threads, and observed learning style. "
    "Return only the raw Markdown — no preamble, no code fences."
)

_CHECKIN_USER_PROMPT = (
    "Generate a short, proactive check-in message for the user based on their current "
    "progress and open learning threads. Be concise and encouraging."
)

_SKILL_REFINE_SYSTEM = (
    "You are improving a coaching skill file. Given the current skill content and "
    "user feedback that the explanation {sentiment}, return an improved version of "
    "the skill file. Return only the raw Markdown — no preamble, no code fences."
)


def _default_get_date() -> str:
    return datetime.date.today().isoformat()


def _extract_keywords(text: str) -> list[str]:
    stop_words = {"a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
                  "of", "and", "or", "me", "my", "i", "you", "how", "do", "tell",
                  "about", "can", "what", "why", "when", "this", "that", "with"}
    words = text.lower().split()
    return [w.strip("?,!.") for w in words if w.strip("?,!.") not in stop_words and len(w) > 2]


def _detect_feedback(text: str) -> str | None:
    lower = text.lower()
    if any(signal in lower for signal in _POSITIVE_SIGNALS):
        return "worked well"
    if any(signal in lower for signal in _NEGATIVE_SIGNALS):
        return "did not work"
    return None


class CoachAgent:
    def __init__(
        self,
        memory: MemoryStore,
        skills: SkillsCache,
        llm: Callable[[str, list[dict]], str],
        get_date: Callable[[], str] = _default_get_date,
    ):
        self._memory = memory
        self._skills = skills
        self._llm = llm
        self._get_date = get_date
        self._last_selected_topics: list[str] = []

    def reply(self, user_message: str) -> str:
        feedback_signal = _detect_feedback(user_message)
        keywords = _extract_keywords(user_message)
        selected = self._skills.select(keywords)  # dict[topic, content]

        system = self._build_system(list(selected.values()))
        messages = [{"role": "user", "content": user_message}]
        response = self._llm(system, messages)

        date = self._get_date()
        self._memory.append_session_turn(date, "user", user_message)
        self._memory.append_session_turn(date, "assistant", response)

        self._update_agent_state(user_message, response)

        if feedback_signal and self._last_selected_topics:
            self._refine_skills(self._last_selected_topics, feedback_signal)

        self._last_selected_topics = list(selected.keys())
        return response

    def checkin(self) -> str:
        agent_state = self._memory.load_agent_state()
        system = agent_state if agent_state else "You are a personal AI coach."
        messages = [{"role": "user", "content": _CHECKIN_USER_PROMPT}]
        response = self._llm(system, messages)

        date = self._get_date()
        self._memory.append_session_turn(date, "assistant", response)

        self._update_agent_state(_CHECKIN_USER_PROMPT, response)
        return response

    def _build_system(self, selected_skills: list[str]) -> str:
        parts = ["You are a personal AI coach focused on AI-native development."]
        agent_state = self._memory.load_agent_state()
        if agent_state:
            parts.append("\n\n## Agent State\n" + agent_state)
        if selected_skills:
            parts.append("\n\n## Relevant Skills\n" + "\n\n---\n\n".join(selected_skills))
        return "".join(parts)

    def _update_agent_state(self, user_message: str, response: str) -> None:
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response},
        ]
        new_state = self._llm(_STATE_UPDATE_SYSTEM, messages)
        self._memory.save_agent_state(new_state)

    def _refine_skills(self, topics: list[str], sentiment: str) -> None:
        for topic in topics:
            try:
                current = self._skills.load(topic)
            except SkillNotFoundError:
                log.warning("_refine_skills: skill %r not found, skipping", topic)
                continue
            except Exception:
                log.exception("_refine_skills: unexpected error loading skill %r", topic)
                continue
            system = _SKILL_REFINE_SYSTEM.format(sentiment=sentiment)
            messages = [{"role": "user", "content": current}]
            improved = self._llm(system, messages)
            self._skills.update(topic, improved)
