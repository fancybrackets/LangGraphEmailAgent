const STORAGE_KEY = "local-agent-conversations-v1";

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const threadInput = document.getElementById("thread-id");
const modelSelect = document.getElementById("model-select");
const refreshModelsBtn = document.getElementById("refresh-models");
const healthBadge = document.getElementById("health-status");
const sendBtn = document.getElementById("send-btn");
const activeModelBadge = document.getElementById("active-model-badge");
const chatList = document.getElementById("chat-list");
const newChatBtn = document.getElementById("new-chat-btn");

let conversations = [];
let activeConversationId = null;

function randomThreadId() {
  return `thread-${Math.random().toString(36).slice(2, 10)}`;
}

function shortTitle(text) {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) return "Yeni sohbet";
  return clean.length > 34 ? `${clean.slice(0, 34)}...` : clean;
}

function saveConversations() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ activeConversationId, conversations }),
  );
}

function loadConversations() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      conversations = parsed.conversations || [];
      activeConversationId = parsed.activeConversationId || null;
    } catch {
      conversations = [];
      activeConversationId = null;
    }
  }

  if (!conversations.length) {
    createConversation();
  } else if (!conversations.find((c) => c.id === activeConversationId)) {
    activeConversationId = conversations[0].id;
  }
}

function getActiveConversation() {
  return conversations.find((c) => c.id === activeConversationId) || null;
}

function createConversation() {
  const session = {
    id: randomThreadId(),
    title: "Yeni sohbet",
    createdAt: new Date().toISOString(),
    messages: [],
  };
  conversations.unshift(session);
  activeConversationId = session.id;
  saveConversations();
  renderConversationList();
  renderChat();
}

function renderConversationList() {
  chatList.innerHTML = "";
  for (const convo of conversations) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `chat-item ${convo.id === activeConversationId ? "active" : ""}`;
    btn.innerHTML = `
      <div class="chat-item-title">${convo.title}</div>
      <div class="chat-item-sub">${convo.id}</div>
    `;
    btn.addEventListener("click", () => {
      activeConversationId = convo.id;
      saveConversations();
      renderConversationList();
      renderChat();
    });
    chatList.appendChild(btn);
  }
}

function renderChat() {
  const convo = getActiveConversation();
  if (!convo) return;

  threadInput.value = convo.id;
  chatLog.innerHTML = "";
  for (const item of convo.messages) {
    const div = document.createElement("div");
    div.className = `msg ${item.role}`;
    div.textContent = item.text;
    chatLog.appendChild(div);
  }
  chatLog.scrollTop = chatLog.scrollHeight;
}

function appendMessage(role, text) {
  const convo = getActiveConversation();
  if (!convo) return;
  convo.messages.push({ role, text });
  if (role === "user" && convo.title === "Yeni sohbet") {
    convo.title = shortTitle(text);
  }
  saveConversations();
  renderConversationList();
  renderChat();
}

async function apiJSON(path, options = {}) {
  const resp = await fetch(path, options);
  let data = {};
  try {
    data = await resp.json();
  } catch {
    data = {};
  }
  if (!resp.ok) {
    throw new Error(data?.detail || "Bilinmeyen hata");
  }
  return data;
}

async function loadHealth() {
  try {
    const data = await apiJSON("/health");
    const ok = data.status === "ok" && data.ollama_reachable !== false;
    healthBadge.textContent = ok ? "Hazir" : "Kismen hazir";
    healthBadge.className = `badge ${ok ? "ok" : "neutral"}`;
  } catch {
    healthBadge.textContent = "Baglanti yok";
    healthBadge.className = "badge err";
  }
}

async function loadModels() {
  modelSelect.innerHTML = '<option value="">Aktif modeli kullan</option>';
  const data = await apiJSON("/models");
  for (const model of data.models || []) {
    const option = document.createElement("option");
    option.value = model.name;
    option.textContent = model.name;
    modelSelect.appendChild(option);
  }
}

async function loadActiveModelBadge() {
  try {
    const data = await apiJSON("/models/active");
    activeModelBadge.textContent = data.active_model || "(secilmedi)";
  } catch {
    activeModelBadge.textContent = "(alinamadi)";
    activeModelBadge.className = "badge err";
  }
}

async function sendMessage(message) {
  const convo = getActiveConversation();
  if (!convo) throw new Error("Aktif sohbet bulunamadi.");

  const payload = {
    thread_id: convo.id,
    message,
  };

  const selectedModel = modelSelect.value.trim();
  if (selectedModel) payload.model = selectedModel;

  return apiJSON("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;

  appendMessage("user", message);
  messageInput.value = "";
  sendBtn.disabled = true;
  sendBtn.textContent = "Gonderiliyor...";

  try {
    const data = await sendMessage(message);
    appendMessage("assistant", data.reply || "(Bos cevap)");
  } catch (error) {
    appendMessage("error", `Hata: ${error.message}`);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Gonder";
  }
});

newChatBtn.addEventListener("click", createConversation);
refreshModelsBtn.addEventListener("click", () => {
  Promise.all([loadModels(), loadActiveModelBadge()]).catch((error) => {
    appendMessage("error", `Model listesi hatasi: ${error.message}`);
  });
});

loadConversations();
renderConversationList();
renderChat();
loadHealth();
Promise.all([loadModels(), loadActiveModelBadge()]).catch((error) => {
  appendMessage("error", `Model listesi hatasi: ${error.message}`);
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    loadActiveModelBadge().catch(() => {});
  }
});
