"""Skill registry and engine."""
import re

from backend.skills.base import Skill, SkillResult
from backend.skills.add_agent import AddAgentSkill


class SkillRegistry:
    """Global registry of all available skills."""
    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill):
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def get_for_level(self, level: str) -> list[Skill]:
        """Return skills available to agents with the given level."""
        return [s for s in self._skills.values() if level in s.allowed_levels]

    def get_descriptors(self, level: str) -> str:
        """Build the skills section text for system prompts."""
        available = self.get_for_level(level)
        if not available:
            return ""
        lines = ["Available Skills (use <skill:name param=\"value\"/> in your reply):"]
        for s in available:
            lines.append(f"- {s.name}: {s.description}  Usage: {s.usage}")
        return "\n".join(lines) + "\n"


# -- Built-in skills --
registry = SkillRegistry()
registry.register(AddAgentSkill())


# -- Skill engine: parse and execute skills from agent text --
_SKILL_PATTERN = re.compile(r'<skill:(\w+)\s+([^/>]*)/?>')


def _parse_params(raw: str) -> dict:
    """Parse key="value" or key='value' or key=value from a string."""
    params = {}
    for m in re.finditer(r'(\w+)="([^"]*?)"', raw):
        params[m.group(1)] = m.group(2)
    for m in re.finditer(r"(\w+)='([^']*?)'", raw):
        params[m.group(1)] = m.group(2)
    # Fallback: unquoted key=value
    for m in re.finditer(r'(\w+)=(\S+)', raw):
        if m.group(1) not in params:
            params[m.group(1)] = m.group(2)
    return params


def execute_skills(text: str, room) -> tuple[str, list[SkillResult]]:
    """
    Find all <skill:...> tags in text, execute them, replace with results.
    Returns (cleaned_text, list_of_results).
    """
    results = []

    def _replace(m):
        skill_name = m.group(1)
        raw_params = m.group(2).strip()
        params = _parse_params(raw_params)

        skill = registry.get(skill_name)
        if skill is None:
            return f"[Unknown skill: {skill_name}]"

        try:
            result = skill.execute(params, room)
            results.append(result)
            return result.display_text
        except Exception as e:
            results.append(SkillResult(success=False, display_text=f"[Failed: {e}]"))
            return f"[{skill_name} failed]"

    cleaned = _SKILL_PATTERN.sub(_replace, text)
    return cleaned, results
