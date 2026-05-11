"""Progressive disclosure prompt templates."""

PARTICIPANTS_INFO = """
其他参与者：
{participants_info}

规则：
- 如果有人 @了你（例如 @你的名字），说明这些话是对你说的，你可以选择回复
- 如果没有被 @，请只关注摘要，不要主动发言
- 如果 @了所有人（@all），所有人都应该回复
- 如果你想了解某个参与者的观点，请 @他
"""


def build_main_prompt(p: "Participant", others: list["Participant"], goal: str, termination: str, skills_info: str = "") -> str:
    """Build system prompt for the main agent."""
    others_info = "\n".join(
        f"- {o.name}: {o.identity}（{o.function}）"
        for o in others
    ) if others else "（无其他参与者）"

    participants = PARTICIPANTS_INFO.format(participants_info=others_info) if others else ""

    return (
        f"你是 {p.name}，{p.identity}。\n"
        f"你是本次讨论的主持人（main agent）。\n\n"
        f"你的职责：{p.function}\n\n"
        f"讨论目标：{goal}\n"
        f"结束条件：{termination}\n\n"
        f"你的权限：\n"
        f"- 控制讨论节奏，决定何时进入下一个话题\n"
        f"- 通过 @参与者名字 的方式分配任务，引导特定参与者发言\n"
        f"- 判断讨论是否达成目标，如果达成则宣布讨论结束\n"
        f"- 当讨论方向偏移时，主动纠正方向\n\n"
        f"{participants}"
        f"{skills_info}"
        f"格式要求：\n"
        f"- 在 plan 阶段，向用户确认需求和目标\n"
        f"- 在 discuss 阶段，通过 @ 分配任务给参与者\n"
        f"- 回复简洁，避免冗长的独白"
    )


def build_participant_prompt(
    p: "Participant",
    others: list["Participant"],
    goal: str,
    current_message: str,
    summary: str,
) -> str:
    """Build system prompt for a participant (only used when @'d)."""
    other_names = [o.name for o in others if o.name != p.name]
    others_info = "\n".join(
        f"- {o.name}: {o.identity}（{o.function}）"
        for o in others if o.name != p.name
    ) if other_names else "（无其他参与者）"

    participants = PARTICIPANTS_INFO.format(participants_info=others_info) if others else ""

    return (
        f"你是 {p.name}，{p.identity}。\n"
        f"你的职责：{p.function}\n\n"
        f"讨论目标：{goal}\n\n"
        f"{participants}"
        f"当前讨论摘要：\n{summary}\n\n"
        f"最新收到的消息（有人 @了你）：\n{current_message}\n\n"
        f"请根据上述信息和你的角色职责，给出专业的回复。"
    )


def build_summarizer_prompt(summary: str, new_messages: list["Message"]) -> str:
    """Build system prompt for the summarizer LLM."""
    msgs_text = "\n".join(
        f"{m.sender}: {m.content}" for m in new_messages
    )
    return (
        "你是一个会议记录员。你的任务是将讨论内容压缩成一段简洁的摘要。\n\n"
        f"已有的摘要（可能为空）：\n{summary}\n\n"
        f"新增的讨论内容：\n{msgs_text}\n\n"
        "请结合已有摘要和新内容，生成一段更新后的摘要（不超过 200 字）。\n"
        "摘要应包含：讨论目标、各参与者的主要观点、当前进展、待解决的问题。\n"
        "直接返回摘要文本，不要输出其他内容。"
    )
