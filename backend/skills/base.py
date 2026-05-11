"""Base class for skills."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SkillResult:
    success: bool
    display_text: str
    metadata: dict | None = None


class Skill(ABC):
    name: str = ""
    description: str = ""
    allowed_levels: list[str] = ["main"]

    @abstractmethod
    def execute(self, params: dict, room: ChatRoom) -> SkillResult:  # noqa: F821
        ...

    def to_descriptor(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "usage": f'<skill:{self.name} param1="value1" param2="value2"/>',
        }

    @property
    def usage(self) -> str:
        return f'<skill:{self.name} param1="value1" param2="value2"/>'
