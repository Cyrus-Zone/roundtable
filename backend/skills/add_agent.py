"""Add a new participant agent to the room."""
from backend.protocol import Participant, Level
from backend.skills.base import Skill, SkillResult

MAX_PARTICIPANTS = 10


class AddAgentSkill(Skill):
    name = "add_agent"
    description = "Create a new participant in the discussion. Use when the current participants are insufficient to cover all aspects of the topic."
    allowed_levels = ["main"]

    @property
    def usage(self) -> str:
        return '<skill:add_agent name="AgentName" identity="Role description" function="What they do"/>'

    def execute(self, params: dict, room) -> SkillResult:
        name = params.get("name", "").strip()
        identity = params.get("identity", "").strip()
        function_desc = params.get("function", "").strip()

        if not name:
            return SkillResult(success=False, display_text="创建失败：缺少 name 参数")

        # Check duplicates
        if name in room.participants:
            return SkillResult(success=False, display_text=f"「{name}」已存在")

        # Check limit
        participant_count = sum(1 for p in room.participants.values() if p.level == Level.PARTICIPANT)
        if participant_count >= MAX_PARTICIPANTS:
            return SkillResult(success=False, display_text=f"参与者数量已达上限（{MAX_PARTICIPANTS}）")

        # Inherit main agent's config
        main = room.main_agent
        new_agent = Participant(
            name=name,
            model=main.model if main else "gpt-4o-mini",
            api_key=main.api_key if main else "",
            base_url=main.base_url if main else None,
            identity=identity or f"{name}",
            function=function_desc or "参与讨论",
            level=Level.PARTICIPANT,
        )

        room.participants[name] = new_agent
        return SkillResult(
            success=True,
            display_text=f"「{name}」已加入讨论（{identity or '未设置职责'}）",
            metadata={"agent_name": name},
        )
