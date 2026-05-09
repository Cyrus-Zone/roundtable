"""Core protocol: Message, Participant, RoomState"""
from dataclasses import dataclass, field
from enum import Enum
from time import time


class Level(str, Enum):
    MAIN = "main"
    PARTICIPANT = "participant"


class Phase(str, Enum):
    PLAN = "plan"
    DISCUSS = "discuss"


@dataclass
class Message:
    sender: str            # "user", "architect", "gpt-4o", ...
    content: str
    target: str = "all"    # "all" or specific participant name
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time)

    def mentions(self, name: str) -> bool:
        """Check if this message @mentions the given name."""
        return f"@{name}" in self.content


@dataclass
class Participant:
    name: str
    model: str             # LiteLLM model name, e.g. "gpt-4o"
    api_key: str
    base_url: str | None = None
    identity: str = ""
    function: str = ""
    level: Level = Level.PARTICIPANT
    system_prompt: str = ""  # user override; empty = use generated prompt


@dataclass
class RoomState:
    id: str
    phase: Phase = Phase.PLAN
    goal: str = ""
    termination_condition: str = ""
    history: list[Message] = field(default_factory=list)
    summary: str = ""
