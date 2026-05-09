"""CLI demo: quick test without the web UI."""
import os
import sys

sys.path.insert(0, str(__file__).resolve().parent.parent)

from backend.protocol import Participant, Level
from backend.room import ChatRoom


def main():
    print("=" * 60)
    print("Roundtable CLI Demo")
    print("=" * 60)

    api_key = os.environ.get("OPENAI_API_KEY", input("Enter OpenAI API key: "))
    if not api_key:
        print("API key required.")
        return

    # Create participants
    main_agent = Participant(
        name="主持人",
        model="gpt-4o-mini",
        api_key=api_key,
        identity="会议主持人",
        function="引导讨论，确认目标，分配任务",
        level=Level.MAIN,
    )
    participant = Participant(
        name="架构师",
        model="gpt-4o-mini",
        api_key=api_key,
        identity="系统架构师",
        function="提供技术架构建议",
        level=Level.PARTICIPANT,
    )

    room = ChatRoom([main_agent, participant])
    print(f"Room created: {room.id}")
    print("Phase: Plan — describe your topic to start discussing.")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("你: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        replies = room.process_user_message(user_input)
        for r in replies:
            print(f"\n{r.sender}: {r.content}\n")

    print("\nBye!")


if __name__ == "__main__":
    main()
