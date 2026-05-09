# Roundtable

> Let AI models talk to each other. A multi-model group chat framework.

A lightweight framework for hosting conversations between multiple AI language models. Think of it as a meeting room: a main agent (host) moderates the discussion, participants respond when mentioned, and a summarizer keeps the conversation organized.

## Features

- **Role-based agents**: Main agent (moderator), participants, and a summarizer — each with custom identity, function, and system prompt
- **@Mention routing**: Main agent assigns tasks by @-mentioning participants; participants only respond when addressed
- **Progressive disclosure**: Each agent knows its own role and other agents' roles
- **Async summarization**: A cheap LLM (e.g. Haiku) asynchronously compresses old messages into a summary, saving tokens
- **Two-phase flow**: Plan phase (goal discussion) → Discuss phase (formal discussion)
- **Web UI**: Simple dark-themed group chat interface with model management panel
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
│   └── main.py           # FastAPI server + REST API
├── frontend/
│   ├── index.html        # Group chat UI
│   ├── style.css         # Dark theme
│   └── app.js            # Frontend logic
├── data/
│   └── models.json       # Persistent model configuration
└── examples/
    └── demo.py           # CLI demo
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design document.

## License

MIT
