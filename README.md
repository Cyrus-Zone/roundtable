# Roundtable

> Let AI models talk to each other. A multi-model group chat framework.

A lightweight framework for hosting conversations between multiple AI language models. Think of it as a meeting room: a main agent (host) moderates the discussion, participants respond when mentioned, and the system can dynamically create new roles as needed.

## Features

- **Role-based agents**: Main agent (moderator), participants, and a summarizer — each with custom identity, function, and system prompt
- **@Mention routing**: Main agent assigns tasks by @-mentioning participants; participants only respond when addressed
- **@Mention autocomplete**: Type `@` to see a popup of available agents, filter by typing
- **Progressive disclosure**: Each agent knows its own role and other agents' roles
- **Skills system**: Agents can call skills via `<skill:name param="value"/>` tags — the main agent can dynamically create new participants mid-conversation
- **Async summarization**: A cheap LLM (e.g. Haiku) asynchronously compresses old messages into a summary, saving tokens
- **Two-phase flow**: Plan phase (goal discussion) → Discuss phase (formal discussion)
- **WeChat-style Web UI**: Clean white-themed group chat with model management, real-time editing, and participant avatars
- **Model agnostic**: Uses LiteLLM — supports OpenAI, Anthropic, Gemini, and 100+ providers

## Quick Start

```bash
pip install litellm fastapi uvicorn
python -m uvicorn backend.main:app --port 8765
```

Open `http://localhost:8765` in your browser.

## Project Structure

```
Roundtable/
├── backend/
│   ├── protocol.py       # Core types: Message, Participant, RoomState
│   ├── prompt.py         # Progressive disclosure prompt templates
│   ├── llm.py            # LiteLLM wrapper
│   ├── history.py        # History truncation + async summarization
│   ├── room.py           # ChatRoom: the conversation engine
│   ├── skills/
│   │   ├── base.py       # Skill base class (name, description, allowed_levels)
│   │   ├── add_agent.py  # Dynamically create a new participant
│   │   └── __init__.py   # Registry + engine (parse <skill:.../> tags)
│   └── main.py           # FastAPI server + REST API
├── frontend/
│   ├── index.html        # Vue 3 + WeChat-style UI
│   ├── style.css         # White theme
│   └── app.js            # Frontend logic (model CRUD, room creation, @mention)
├── data/
│   └── models.json       # Persistent model configuration
└── examples/
    └── demo.py           # CLI demo
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design document.

## License

MIT
