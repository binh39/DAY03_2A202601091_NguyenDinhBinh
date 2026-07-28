(function () {
  const STORAGE_KEY = "anTamConversationId";

  function createId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `demo-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function getConversationId() {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
      id = createId();
      localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  }

  async function request(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("Server trả về dữ liệu không hợp lệ.");
    }
    if (!response.ok) throw new Error(data.error || "Không thể kết nối chatbot.");
    return data;
  }

  async function getHistory() {
    const id = encodeURIComponent(getConversationId());
    return request(`/api/chat/history?conversation_id=${id}`);
  }

  async function sendMessage(message) {
    return request("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        conversation_id: getConversationId(),
        message,
      }),
    });
  }

  async function clearHistory() {
    const id = encodeURIComponent(getConversationId());
    return request(`/api/chat/history?conversation_id=${id}`, { method: "DELETE" });
  }

  function renderRichText(container, text) {
    const source = String(text || "");
    const linkPattern = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s<]+)/g;
    let cursor = 0;
    let match;
    while ((match = linkPattern.exec(source)) !== null) {
      if (match.index > cursor) {
        container.appendChild(document.createTextNode(source.slice(cursor, match.index)));
      }
      let url = match[2] || match[3];
      let trailing = "";
      if (!match[2]) {
        const trailingMatch = url.match(/[.,;:!?]+$/);
        if (trailingMatch) {
          trailing = trailingMatch[0];
          url = url.slice(0, -trailing.length);
        }
      }
      const link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.className = "chat-link";
      link.textContent = match[1] || url;
      container.appendChild(link);
      if (trailing) container.appendChild(document.createTextNode(trailing));
      cursor = match.index + match[0].length;
    }
    if (cursor < source.length) {
      container.appendChild(document.createTextNode(source.slice(cursor)));
    }
  }

  window.ChatAPI = {
    getConversationId,
    getHistory,
    sendMessage,
    clearHistory,
    renderRichText,
  };
})();
