const { createApp, ref, computed, nextTick, onMounted } = Vue;

const API = "";

createApp({
    setup() {
        // State
        const activePanel = ref("models");
        const models = ref([]);
        const rooms = ref([]);
        const currentRoomId = ref(null);
        const messages = ref([]);
        const currentPhase = ref("plan");
        const roomModels = ref([]);
        const inputText = ref("");
        const loading = ref(false);
        const messagesEl = ref(null);

        // Model modal
        const showModelModal = ref(false);
        const editingIndex = ref(-1);
        const showKey = ref(false);
        const form = ref({ name: "", model: "", api_key: "", base_url: "", identity: "", function: "", level: "participant" });

        // Room modal
        const showRoomModal = ref(false);
        const selectedForRoom = ref([]);

        // ── Model CRUD ─────────────────────────────────────
        async function fetchModels() {
            try {
                const res = await fetch(`${API}/api/models`);
                models.value = await res.json();
            } catch (e) { console.error(e); }
        }

        function openAddModel() {
            editingIndex.value = -1;
            form.value = { name: "", model: "", api_key: "", base_url: "", identity: "", function: "", level: "participant" };
            showKey.value = false;
            showModelModal.value = true;
        }

        function openEditModel(i) {
            editingIndex.value = i;
            form.value = { ...models.value[i] };
            showKey.value = false;
            showModelModal.value = true;
        }

        function closeModelModal() {
            showModelModal.value = false;
        }

        async function saveModel() {
            const data = { ...form.value, base_url: form.value.base_url || null };
            if (editingIndex.value >= 0) {
                // Update: delete old + add new
                const oldName = models.value[editingIndex.value].name;
                await fetch(`${API}/api/models/${encodeURIComponent(oldName)}`, { method: "DELETE" });
            }
            await fetch(`${API}/api/models`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            showModelModal.value = false;
            await fetchModels();
        }

        async function deleteModel() {
            if (editingIndex.value < 0) return;
            const name = models.value[editingIndex.value].name;
            await fetch(`${API}/api/models/${encodeURIComponent(name)}`, { method: "DELETE" });
            showModelModal.value = false;
            await fetchModels();
        }

        // ── Room ───────────────────────────────────────────
        function openCreateRoom() {
            selectedForRoom.value = models.value.map(m => m.name);
            showRoomModal.value = true;
        }

        async function createRoom() {
            const res = await fetch(`${API}/api/rooms`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ models: selectedForRoom.value }),
            });
            const data = await res.json();
            showRoomModal.value = false;
            await fetchRooms();
            selectRoom(data.room_id);
        }

        async function fetchRooms() {
            // Rooms are in-memory, so we just track them from creation
            // For MVP, we store room info in localStorage
            try {
                const stored = JSON.parse(localStorage.getItem("rt_rooms") || "[]");
                rooms.value = stored;
            } catch (e) { rooms.value = []; }
        }

        function saveRoomInfo(id, roomData) {
            let list = JSON.parse(localStorage.getItem("rt_rooms") || "[]");
            if (!list.find(r => r.id === id)) {
                list.push({
                    id,
                    phase: roomData.phase,
                    participantCount: Object.keys(roomData.participants || {}).length || roomModels.value.length,
                });
                localStorage.setItem("rt_rooms", JSON.stringify(list));
            }
            fetchRooms();
        }

        async function selectRoom(id) {
            currentRoomId.value = id;
            try {
                const res = await fetch(`${API}/api/rooms/${id}`);
                const data = await res.json();
                messages.value = data.history || [];
                currentPhase.value = data.phase || "plan";
                roomModels.value = data.participants || [];
                await nextTick();
                scrollToBottom();
            } catch (e) {
                messages.value = [];
            }
        }

        // ── Send message ───────────────────────────────────
        async function sendMessage() {
            const content = inputText.value.trim();
            if (!content || !currentRoomId.value || loading.value) return;

            loading.value = true;
            // Optimistic: add user message immediately
            messages.value.push({ sender: "user", content, timestamp: Date.now() });
            inputText.value = "";
            await nextTick();
            scrollToBottom();

            try {
                const res = await fetch(`${API}/api/rooms/${currentRoomId.value}/message`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ content }),
                });
                const data = await res.json();
                // Replace full history from server
                messages.value = data.history || [];
                currentPhase.value = data.phase || currentPhase.value;
                await nextTick();
                scrollToBottom();
            } catch (err) {
                messages.value.push({ sender: "系统", content: "发送失败: " + err.message, timestamp: Date.now() });
            }
            loading.value = false;
        }

        function scrollToBottom() {
            if (messagesEl.value) {
                messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
            }
        }

        // ── Helpers ────────────────────────────────────────
        function avatarClass(sender) {
            if (sender === "user") return "user-avatar";
            if (sender === "系统") return "";
            // Check if sender is main agent
            const m = roomModels.value.find(r => r.name === sender);
            if (m && m.level === "main") return "main-avatar";
            return "participant-avatar";
        }

        function senderLabel(sender) {
            if (sender === "user") return "我";
            if (sender === "系统") return "系";
            return sender.substring(0, 2);
        }

        function highlightMention(text) {
            return text.replace(/@(\S+)/g, '<span class="mention">@$1</span>');
        }

        // ── Init ───────────────────────────────────────────
        onMounted(() => {
            fetchModels();
            fetchRooms();
        });

        return {
            activePanel, models, rooms, currentRoomId, messages, currentPhase, roomModels,
            inputText, loading, messagesEl,
            showModelModal, editingIndex, showKey, form,
            showRoomModal, selectedForRoom,
            fetchModels, openAddModel, openEditModel, closeModelModal, saveModel, deleteModel,
            openCreateRoom, createRoom, selectRoom,
            sendMessage, avatarClass, senderLabel, highlightMention,
        };
    },
}).mount("#app");
