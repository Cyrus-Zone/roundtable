"""FastAPI entry point."""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.protocol import Participant, Level
from backend.room import ChatRoom

app = FastAPI(title="Roundtable")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent.parent / "data"
MODELS_FILE = DATA_DIR / "models.json"
ROOMS: dict[str, ChatRoom] = {}


def load_models() -> list[dict]:
    if MODELS_FILE.exists():
        with open(MODELS_FILE) as f:
            return json.load(f).get("models", [])
    return []


def save_models(models: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODELS_FILE, "w", encoding="utf-8") as f:
        json.dump({"models": models}, f, ensure_ascii=False, indent=2)


def _build_participants(model_dicts: list[dict]) -> list[Participant]:
    return [
        Participant(
            name=m["name"],
            model=m["model"],
            api_key=m["api_key"],
            base_url=m.get("base_url"),
            identity=m.get("identity", ""),
            function=m.get("function", ""),
            level=Level(m.get("level", "participant")),
            system_prompt=m.get("system_prompt", ""),
        )
        for m in model_dicts
    ]


# ── Models CRUD ──────────────────────────────────────────────────

@app.get("/api/models")
def get_models():
    return load_models()


@app.post("/api/models")
def save_model_endpoint(model: dict):
    models = load_models()
    models.append(model)
    save_models(models)
    return {"ok": True}


@app.delete("/api/models/{name}")
def delete_model(name: str):
    models = [m for m in load_models() if m["name"] != name]
    save_models(models)
    return {"ok": True}


# ── Room ─────────────────────────────────────────────────────────

@app.post("/api/rooms")
def create_room(room_req: dict):
    """
    Create a new room.
    Body: {"models": [name1, name2, ...]} — list of model names to include
    """
    all_models = load_models()
    name_map = {m["name"]: m for m in all_models}

    selected = []
    for name in room_req.get("models", []):
        if name in name_map:
            selected.append(name_map[name])

    if not selected:
        raise HTTPException(400, "No valid models selected")

    room = ChatRoom(_build_participants(selected))
    ROOMS[room.id] = room
    return {"room_id": room.id}


@app.get("/api/rooms/{room_id}")
def get_room(room_id: str):
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    return room.to_dict()


@app.post("/api/rooms/{room_id}/message")
def send_message(room_id: str, body: dict, background_tasks: BackgroundTasks):
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(404, "Room not found")

    content = body.get("content", "")
    if not content:
        raise HTTPException(400, "Empty message")

    replies = room.process_user_message(content)

    # Queue summarization to run after response is sent
    background_tasks.add_task(room.try_summarize)

    return {
        "history": room.to_dict()["history"],
        "replies": [
            {"sender": r.sender, "content": r.content, "timestamp": r.timestamp}
            for r in replies
        ],
    }


@app.post("/api/rooms/{room_id}/goal")
def set_goal(room_id: str, body: dict):
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    room.set_goal(
        goal=body.get("goal", ""),
        termination=body.get("termination", ""),
    )
    return {"ok": True}


# ── Static files ─────────────────────────────────────────────────

frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")
