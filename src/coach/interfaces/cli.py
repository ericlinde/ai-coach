from ..agent import CoachAgent
from ..memory import MemoryStore


def run(agent: CoachAgent, memory: MemoryStore) -> None:
    """Run the interactive CLI loop."""
    checkins = memory.load_pending_checkins()
    for item in checkins:
        print(item)
    if checkins:
        memory.clear_pending_checkins()

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except EOFError:
            break

        if user_input.lower() == "exit":
            break

        if not user_input:
            continue

        response = agent.reply(user_input)
        print(f"\nCoach: {response}")
