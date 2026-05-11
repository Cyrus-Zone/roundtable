# Roundtable Architecture Design

## Overview

Roundtable is a multi-model group chat framework where AI models can converse with each other in a structured meeting format. It is not a free-for-all chat — it follows a **meeting metaphor**:

- **Main Agent (主持人)**: Moderates the discussion, controls pacing, assigns tasks, judges completion
- **Participants (参与者)**: Domain experts who only speak when @-mentioned
- **Summarizer (工具人)**: A cheap LLM that silently compresses old messages into summaries
- **User (用户)**: Highest authority — can interrupt, change goals, stop the discussion

## Core Design Decisions

### 1. Role-Based Architecture (Not Free Chat)

Unlike typical multi-model tools that just show parallel outputs side-by-side, Roundtable enforces **structured turn-taking**:

| Role | When it speaks | What it sees |
|------|----------------|--------------|
| User | Anytime | Everything |
| Main Agent | After every message | Full history |
| Participant | Only when @-mentioned | Summary + recent messages |
| Summarizer | Asynchronously, never speaks | Old messages for compression |

### 2. @Mention Routing

The main agent controls the conversation by @-mentioning participants:

```
Main Agent: "@架构师 你觉得应该用什么技术栈？"
→ Backend detects "@架构师" → triggers the "架构师" LLM to respond
→ Other participants are NOT called (saves tokens)
```

Two layers work together:
- **Program-level routing**: Only @-mentioned participants get an LLM call
- **Prompt-level awareness**: The @-mentioned participant knows it was addressed and can respond contextually

The frontend provides an **autocomplete popup** when the user types `@`, making it easy to mention agents by name.

### 3. Progressive Disclosure

Each agent receives a system prompt that progressively discloses information:

```
You are {name}, {identity}.
You are the {level} of this discussion.
Your responsibility: {function}

Other participants:
- {other1_name}: {other1_identity} ({other1_function})
- {other2_name}: {other2_identity} ({other2_function})

Available Skills:
- add_agent: Create a new participant in the discussion.
  Usage: <skill:add_agent name="AgentName" identity="Role" function="What they do"/>

Rules:
- If someone @-mentions you, you should respond
- If no one @-mentions you, focus on the summary only, do not initiate
- If @all is used, everyone should respond
```

This means the **same model can play different roles** — a GPT-4o instance with "security auditor" system prompt behaves completely differently from a GPT-4o instance with "performance optimizer" system prompt.

### 4. History Management

As conversations grow longer, token costs explode. Roundtable uses a **two-tier history strategy**:

```
┌──────────────────────────────────────┐
│ [Summary] Discussion goal is X,       │ ← Async-maintained by Summarizer LLM
│               Architect suggests Y    │
│               Currently debating Z    │
├──────────────────────────────────────┤
│ [Full] Main: "@Architect..."         │ ← Last N messages (default: 10)
│ [Full] Architect: "I recommend..."    │
│ [Full] Main: "@SecurityAuditor..."    │
└──────────────────────────────────────┘
```

- **Recent messages**: Kept intact (default: last 10)
- **Old messages**: Compressed into a summary by the Summarizer LLM
- **Trigger**: When total token count exceeds threshold (default: 8000)
- **Async**: Runs via FastAPI BackgroundTasks, doesn't block the response

### 5. Two-Phase Flow

#### Plan Phase
When a room is created, it starts in Plan mode:
- User describes their needs
- Main Agent asks clarifying questions
- Main Agent summarizes the agreed goal
- User confirms → transition to Discuss phase

#### Discuss Phase
- Main Agent drives the discussion toward the goal
- Uses @-mentions to assign tasks to participants
- Judges when the goal is met and announces completion
- User can interrupt at any time to modify the goal

### 6. Skills System

Skills are extensible capabilities that agents can invoke via `<skill:name param="value"/>` tags in their replies. The backend parses these tags, executes the corresponding skill, and replaces the tag with a human-readable result.

#### Architecture

```
┌─────────────────────────────────────────────┐
│ Agent replies with:                          │
│ "I think we need a security expert.         │
│  <skill:add_agent name="SecAuditor"          │
│    identity="Security expert"                │
│    function="Review security"/>              │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ Skills Engine:                               │
│ 1. Regex-parse <skill:.../> tags             │
│ 2. Look up skill in registry                 │
│ 3. Execute skill.execute(params, room)       │
│ 4. Replace tag with display text             │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ Clean reply sent to chat:                    │
│ "I think we need a security expert.          │
│  「SecAuditor」已加入讨论（Security expert）"  │
│                                              │
│ System message: 「SecAuditor」已加入讨论      │
└─────────────────────────────────────────────┘
```

#### Built-in Skills

| Skill | Description | Allowed Levels |
|-------|-------------|----------------|
| `add_agent` | Create a new participant dynamically, inheriting the main agent's model and API key | main only |

#### Adding Custom Skills

Create a class that extends `Skill`:

```python
from backend.skills.base import Skill, SkillResult

class MySkill(Skill):
    name = "my_skill"
    description = "What this skill does"
    allowed_levels = ["main"]

    def execute(self, params: dict, room) -> SkillResult:
        # ... do something
        return SkillResult(success=True, display_text="Done!")
```

Then register it:

```python
from backend.skills import registry
registry.register(MySkill())
```

### 7. Protocol Design

The entire system communicates through a single protocol type:

```python
@dataclass
class Message:
    sender: str          # "user", "主持人", "架构师", ...
    content: str
    target: str          # "all" or specific participant name
    metadata: dict       # extensible: confidence, tokens_used, ...
    timestamp: float
```

This is the **only** message format in the system. All LLM calls are wrapped in this type. Future extensions (MCP integration, structured outputs, streaming) add metadata without changing the core type.

## Data Flow

```
User types: "帮我设计一个用户系统"
    │
    ▼
┌─────────────────────────────────────────────┐
│ Main Agent receives full history            │
│ System prompt: goal + role + other agents   │
│             + available skills              │
│ Output: "好的，我们先明确需求范围..."          │
└─────────────────────────────────────────────┘
    │
    ▼ Message appended to history
    │
┌─────────────────────────────────────────────┐
│ Backend scans reply for @mentions           │
│ Finds: none (main agent is still in plan)    │
│ No participant calls triggered               │
│ Backend scans reply for <skill:.../> tags    │
│ Finds: none                                  │
└─────────────────────────────────────────────┘
    │
    ▼
User replies: "大概10万用户量，用Python"
    │
    ▼
┌─────────────────────────────────────────────┐
│ Main Agent receives updated history          │
│ Output: "@架构师 这个规模你建议用什么架构？"    │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ Backend detects "@架构师"                    │
│ Triggers "架构师" LLM with:                  │
│   - Summary of discussion so far             │
│   - Recent messages (full context)           │
│   - System prompt: "你是架构师，..."          │
│ Output: "我建议用 FastAPI + PostgreSQL..."    │
└─────────────────────────────────────────────┘
    │
    ▼ (async, non-blocking)
┌─────────────────────────────────────────────┐
│ HistoryManager checks token count            │
│ If > 8000: triggers Summarizer LLM           │
│ Summarizer: compresses old messages          │
│ Updates summary field                        │
└─────────────────────────────────────────────┘
```

## Frontend

The frontend is a **WeChat-style white-themed** group chat interface built with **Vue 3 (CDN)**:

- **Left sidebar**: Model management (add/edit/delete) + room list
- **Right panel**: Chat area with avatars, message bubbles, and phase badge
- **@Mention popup**: Auto-complete when typing `@`, filterable, keyboard navigable
- **Model modal**: Full form with identity, function, role (main/participant), API key toggle
- **Room creation modal**: Checkbox list of available models

## Extension Points

### MCP Integration (Future)
Each participant can be equipped with MCP tools (file read, web search, code execution). The protocol's `metadata` field can carry tool results.

### Streaming (Future)
Currently synchronous blocking calls. Streaming can be added per-message without changing the Message protocol — just deliver chunks instead of waiting for full completion.

### Custom Reply Strategies (Future)
Beyond @-mention routing, custom strategies can be implemented:
- `RoundRobin`: Each participant speaks in turn
- `Debate`: Two sides alternate arguments
- `Review`: Write → Review → Revise pipeline

## Why Not Build on AutoGen / LangGraph?

These are powerful frameworks but they serve a different audience:
- **AutoGen**: Developer-facing framework for building multi-agent workflows (requires Python code)
- **LangGraph**: State machine orchestration for agent pipelines (requires graph definitions)
- **Roundtable**: End-user product — open a web page, add models, start chatting

The value is in the **user experience**, not the orchestration complexity.
