"""ChatRoom: the conversation engine."""
import uuid

from backend.protocol import Message, Participant, Level, Phase, RoomState
from backend.prompt import build_main_prompt, build_participant_prompt
from backend.llm import call_llm
from backend.history import HistoryManager


class ChatRoom:
    def __init__(self, participants: list[Participant], goal: str = "", termination: str = ""):
        self.id = str(uuid.uuid4())[:8]
        self.participants = {p.name: p for p in participants}
        self.main_agent = next((p for p in participants if p.level == Level.MAIN), None)
        self.state = RoomState(
            id=self.id,
            goal=goal,
            termination_condition=termination,
        )
        self.history_mgr = HistoryManager(
            summarizer=next((p for p in participants if p.name == "summarizer"), None),
        )

    def _build_main_messages(self, user_msg: Message) -> list[dict]:
        """Build messages for main agent: system prompt + history + user message."""
        others = [p for p in self.participants.values() if p.level != Level.MAIN and p.name != "summarizer"]
        system = build_main_prompt(self.main_agent, others, self.state.goal, self.state.termination_condition)

        messages = [{"role": "system", "content": system}]
        for msg in self.state.history:
            messages.append({"role": "user", "content": f"{msg.sender}: {msg.content}"})
        messages.append({"role": "user", "content": f"{user_msg.sender}: {user_msg.content}"})
        return messages

    def _build_participant_messages(self, participant: Participant, user_msg: Message) -> list[dict]:
        """Build messages for a @'d participant."""
        others = [p for p in self.participants.values() if p.level != Level.MAIN and p.name != "summarizer"]
        context = self.history_mgr.get_context(self.state.history, participant.name)

        system = build_participant_prompt(
            participant, others, self.state.goal,
            f"{user_msg.sender}: {user_msg.content}",
            self.history_mgr.summary,
        )

        messages = [{"role": "system", "content": system}]
        for msg in context:
            messages.append({"role": "user", "content": f"{msg.sender}: {msg.content}"})
        return messages

    def _find_mentioned(self, content: str) -> list[Participant]:
        """Find all participants mentioned with @name in the content."""
        mentioned = []
        for name, p in self.participants.items():
            if p.level == Level.PARTICIPANT and f"@{name}" in content:
                mentioned.append(p)
        return mentioned

    def _send(self, msg: Message):
        """Append a message to history."""
        self.state.history.append(msg)

    def process_user_message(self, content: str, sender: str = "user") -> list[Message]:
        """
        Process a user message through the room.
        Returns list of all LLM replies.
        """
        user_msg = Message(sender=sender, content=content, target="all")
        self._send(user_msg)

        replies = []

        # Step 1: Main agent always responds
        if self.main_agent:
            messages = self._build_main_messages(user_msg)
            reply_content = call_llm(
                model=self.main_agent.model,
                messages=messages,
                api_key=self.main_agent.api_key,
                base_url=self.main_agent.base_url,
            )
            main_reply = Message(
                sender=self.main_agent.name,
                content=reply_content,
                target="all",
            )
            self._send(main_reply)
            replies.append(main_reply)

            # Step 2: Check if main agent @'d any participants
            mentioned = self._find_mentioned(reply_content)
            for participant in mentioned:
                p_messages = self._build_participant_messages(participant, main_reply)
                p_reply_content = call_llm(
                    model=participant.model,
                    messages=p_messages,
                    api_key=participant.api_key,
                    base_url=participant.base_url,
                )
                p_reply = Message(
                    sender=participant.name,
                    content=p_reply_content,
                    target=self.main_agent.name,
                )
                self._send(p_reply)
                replies.append(p_reply)

        return replies

    def try_summarize(self):
        """Trigger summarization (called from BackgroundTasks)."""
        self.history_mgr.summarize(self.state.history)

    def set_goal(self, goal: str, termination: str = ""):
        """Set discussion goal and enter discuss phase."""
        self.state.goal = goal
        self.state.termination_condition = termination
        self.state.phase = Phase.DISCUSS

    def to_dict(self) -> dict:
        """Serialize room state for API response."""
        return {
            "id": self.id,
            "phase": self.state.phase.value,
            "goal": self.state.goal,
            "termination_condition": self.state.termination_condition,
            "summary": self.history_mgr.summary,
            "participants": [
                {"name": p.name, "model": p.model, "level": p.level.value}
                for p in self.participants.values()
            ],
            "history": [
                {
                    "sender": m.sender,
                    "content": m.content,
                    "target": m.target,
                    "timestamp": m.timestamp,
                }
                for m in self.state.history
            ],
        }
