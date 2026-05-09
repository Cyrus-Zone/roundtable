/* ── State ────────────────────────────────────── */
let models = [];
let roomId = null;
let loading = false;

const API = "";  // same origin

/* ── DOM refs ─────────────────────────────────── */
const modelForm = document.getElementById("model-form");
const modelList = document.getElementById("model-list");
const roomModels = document.getElementById("room-models");
const createBtn = document.getElementById("create-room");
const roomTitle = document.getElementById("room-title");
const phaseBadge = document.getElementById("phase-badge");
const messagesDiv = document.getElementById("messages");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

/* ── Init ─────────────────────────────────────── */
fetchModels();

/* ── Model CRUD ───────────────────────────────── */
async function fetchModels() {
    const res = await fetch(`${API}/api/models`);
    models = await res.json();
    renderModelList();
    renderRoomModelCheckboxes();
}

modelForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const model = {
        name: document.getElementById("m-name").value,
        model: document.getElementById("m-model").value,
        api_key: document.getElementById("m-key").value,
        base_url: document.getElementById("m-url").value || null,
        identity: document.getElementById("m-identity").value,
        function: document.getElementById("m-function").value,
        level: document.getElementById("m-level").value,
        system_prompt: "",
    };
    await fetch(`${API}/api/models`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(model),
    });
    modelForm.reset();
    fetchModels();
});

function renderModelList() {
    modelList.innerHTML = models.map((m) => `
        <li>
            <span><b>${m.name}</b> <span style="color:#888">(${m.model})</span> <span style="color:#666;font-size:11px">[${m.level === "main" ? "主" : "参"}]</span></span>
            <button class="del-btn" onclick="deleteModel('${m.name}')">&times;</button>
        </li>
    `).join("");
}

async function deleteModel(name) {
    await fetch(`${API}/api/models/${name}`, { method: "DELETE" });
    fetchModels();
}

/* ── Room creation ────────────────────────────── */
function renderRoomModelCheckboxes() {
    roomModels.innerHTML = models.map((m) => `
        <label>
            <input type="checkbox" value="${m.name}" onchange="updateCreateBtn()">
            ${m.name} (${m.model})
        </label>
    `).join("");
}

function updateCreateBtn() {
    const checked = roomModels.querySelectorAll("input:checked");
    createBtn.disabled = checked.length === 0;
}

createBtn.addEventListener("click", async () => {
    const checked = [...roomModels.querySelectorAll("input:checked")].map((c) => c.value);
    const res = await fetch(`${API}/api/rooms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ models: checked }),
    });
    const data = await res.json();
    roomId = data.room_id;
    roomTitle.textContent = `房间 ${roomId}`;
    userInput.disabled = false;
    sendBtn.disabled = false;
    phaseBadge.className = "plan";
    phaseBadge.textContent = "Plan";
    messagesDiv.innerHTML = '<div class="message system-summary">房间已创建，进入 Plan 模式。请先描述你的需求，主Agent 会和你讨论并确认目标。</div>';
});

/* ── Send message ─────────────────────────────── */
async function sendMessage() {
    const content = userInput.value.trim();
    if (!content || !roomId || loading) return;

    loading = true;
    userInput.disabled = true;
    sendBtn.disabled = true;
    appendMessage("user", content);
    userInput.value = "";

    try {
        const res = await fetch(`${API}/api/rooms/${roomId}/message`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content }),
        });
        const data = await res.json();

        // Render replies
        for (const r of data.replies) {
            appendMessage(r.sender, r.content);
        }

        // Update phase badge
        const roomData = await fetch(`${API}/api/rooms/${roomId}`).then((r) => r.json());
        phaseBadge.className = roomData.phase;
        phaseBadge.textContent = roomData.phase === "plan" ? "Plan" : "Discuss";

        // If entered discuss phase, show notification
        if (roomData.phase === "discuss" && phaseBadge.textContent === "Discuss") {
            appendMessage("system-summary", `讨论目标已确认：${roomData.goal}`);
        }
    } catch (err) {
        appendMessage("system-summary", "发送失败：" + err.message);
    }

    loading = false;
    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
}

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

/* ── Render helpers ───────────────────────────── */
function appendMessage(sender, content) {
    const div = document.createElement("div");
    const cls = sender === "user" ? "user" : sender.startsWith("[系统") ? "system-summary" : "";
    div.className = `message ${cls}`;

    if (!cls) {
        div.innerHTML = `<div class="sender">${sender}</div>${escapeHtml(content)}`;
    } else if (sender === "user") {
        div.innerHTML = `<div class="sender">你</div>${escapeHtml(content)}`;
    } else {
        div.textContent = content;
    }

    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function escapeHtml(text) {
    const d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
}
