const bookingForm = document.querySelector("#split-booking-form");
const successPanel = document.querySelector("#split-success");
const successMessage = document.querySelector("#split-success-message");
const appointmentDate = document.querySelector("#split-appointment-date");
const bookingSteps = document.querySelectorAll(".booking-steps li");
const menuToggle = document.querySelector("#menu-toggle");
const primaryNav = document.querySelector("#primary-nav");

menuToggle.addEventListener("click", () => {
  const isOpen = primaryNav.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", String(isOpen));
  menuToggle.setAttribute("aria-label", isOpen ? "Đóng menu" : "Mở menu");
});

const localDate = new Date();
localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
appointmentDate.min = localDate.toISOString().split("T")[0];

bookingForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!bookingForm.reportValidity()) return;

  const appointment = Object.fromEntries(new FormData(bookingForm).entries());
  appointment.id = `ATM-${Date.now().toString().slice(-6)}`;
  appointment.createdAt = new Date().toISOString();
  appointment.status = "pending";

  const appointments = JSON.parse(localStorage.getItem("anTamAppointments") || "[]");
  appointments.push(appointment);
  localStorage.setItem("anTamAppointments", JSON.stringify(appointments));

  const dateLabel = new Intl.DateTimeFormat("vi-VN", { dateStyle: "long" })
    .format(new Date(`${appointment.date}T00:00:00`));
  successMessage.textContent =
    `Mã lịch hẹn ${appointment.id}. Bạn đã chọn ${appointment.specialty} vào ${appointment.time}, ${dateLabel}. Chúng tôi sẽ liên hệ qua số ${appointment.phone} để xác nhận.`;

  bookingForm.hidden = true;
  successPanel.hidden = false;
  bookingSteps.forEach((step) => step.classList.add("active"));
  successPanel.scrollIntoView({ behavior: "smooth", block: "center" });
});

document.querySelector("#new-booking").addEventListener("click", () => {
  bookingForm.reset();
  appointmentDate.min = localDate.toISOString().split("T")[0];
  successPanel.hidden = true;
  bookingForm.hidden = false;
  bookingSteps.forEach((step, index) => step.classList.toggle("active", index === 0));
  bookingForm.elements.fullName.focus();
});

const chatForm = document.querySelector("#split-chat-form");
const chatInput = document.querySelector("#split-chat-input");
const chatMessages = document.querySelector("#split-chat-messages");
const traceTimeline = document.querySelector("#trace-timeline");
const traceEmpty = document.querySelector("#trace-empty");
const traceStatus = document.querySelector("#trace-status");
const metricSteps = document.querySelector("#metric-steps");
const metricTools = document.querySelector("#metric-tools");
const metricTokens = document.querySelector("#metric-tokens");
const metricCost = document.querySelector("#metric-cost");
const metricModel = document.querySelector("#metric-model");
const metricDuration = document.querySelector("#metric-duration");
const traceQuery = document.querySelector("#trace-query");
const traceQueryText = document.querySelector("#trace-query-text");

const bookingWelcome =
  "Xin chào! Tôi là trợ lý Vinmec. Bạn có thể mô tả nhu cầu hoặc triệu chứng chính, tôi sẽ giúp định hướng chuyên khoa.";
let chatBusy = false;

function appendMessage(content, sender = "bot", extraClass = "") {
  const wrapper = document.createElement("div");
  wrapper.className = `split-message ${sender} ${extraClass}`.trim();
  if (sender === "bot") {
    const avatar = document.createElement("span");
    avatar.className = "mini-avatar";
    avatar.textContent = "✦";
    wrapper.appendChild(avatar);
  }
  const bubble = document.createElement("div");
  window.ChatAPI.renderRichText(bubble, content);
  wrapper.appendChild(bubble);
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrapper;
}

function applyAssistantSuggestion(text) {
  const normalized = text.toLocaleLowerCase("vi");
  const specialtySelect = bookingForm.elements.specialty;
  if (normalized.includes("tim mạch")) {
    specialtySelect.value = "Tim mạch";
  } else if (normalized.includes("nhi - sơ sinh") || normalized.includes("nhi khoa")) {
    specialtySelect.value = "Nhi khoa";
  } else if (normalized.includes("cơ xương khớp")) {
    specialtySelect.value = "Cơ xương khớp";
  }
}

function setTraceStatus(type, label) {
  traceStatus.className = `trace-status ${type || ""}`.trim();
  traceStatus.lastChild.textContent = ` ${label}`;
}

function prettyObservation(value) {
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function renderTrace(trace = [], metrics = {}, query = "") {
  traceTimeline.replaceChildren();
  traceEmpty.hidden = trace.length > 0;
  traceTimeline.hidden = trace.length === 0;
  traceQuery.hidden = !query;
  traceQueryText.textContent = query;

  metricSteps.textContent = metrics.iterations ?? trace.length;
  metricTools.textContent = metrics.tool_calls ?? trace.filter((item) => item.type === "tool").length;
  metricTokens.textContent = metrics.pending
    ? "Đang tính"
    : Object.hasOwn(metrics, "total_tokens_estimate")
    ? new Intl.NumberFormat("vi-VN").format(metrics.total_tokens_estimate)
    : "—";
  const cost = Number(metrics.estimated_cost_usd || 0);
  metricCost.textContent = metrics.pending
    ? "Đang tính"
    : Object.hasOwn(metrics, "estimated_cost_usd")
    ? `$${cost.toFixed(6)}`
    : "—";
  metricModel.textContent = metrics.pending ? "Đang gọi Agent…" : metrics.model || "Chưa có phiên chạy";
  metricDuration.textContent = metrics.pending ? "…" : metrics.duration_ms ? `${metrics.duration_ms} ms` : "—";

  trace.forEach((item, index) => {
    const step = document.createElement("li");
    step.className = `trace-step ${item.type || ""}`.trim();

    const number = document.createElement("span");
    number.className = "trace-step-number";
    number.textContent = String(item.step || index + 1);

    const head = document.createElement("div");
    head.className = "trace-step-head";
    const title = document.createElement("strong");
    title.textContent = item.label || "Agent step";
    const duration = document.createElement("span");
    duration.textContent = `${item.duration_ms || 0} ms`;
    head.append(title, duration);

    step.append(number, head);

    if (item.thought) {
      const thought = document.createElement("p");
      thought.className = "trace-thought";
      thought.textContent = item.thought;
      step.appendChild(thought);
    }

    if (item.action) {
      const action = document.createElement("div");
      action.className = "trace-action";
      action.textContent = `${item.action.tool}(${(item.action.args || []).map((arg) => JSON.stringify(arg)).join(", ")})`;
      step.appendChild(action);
    }

    if (item.observation) {
      const details = document.createElement("details");
      details.className = "trace-observation";
      const summary = document.createElement("summary");
      summary.textContent = "Xem Observation";
      const observation = document.createElement("pre");
      observation.textContent = prettyObservation(item.observation);
      details.append(summary, observation);
      step.appendChild(details);
    }

    traceTimeline.appendChild(step);
  });

  if (trace.length) {
    const hasError = trace.some((item) => ["format_error", "guardrail"].includes(item.type));
    setTraceStatus(hasError ? "error" : "complete", hasError ? "Đã chặn an toàn" : "Hoàn tất");
  } else {
    setTraceStatus("", "Sẵn sàng");
  }
}

function restoreLatestTrace(messages) {
  const assistantIndex = messages.findLastIndex((item) => item.role === "assistant");
  if (assistantIndex < 0) {
    renderTrace();
    return;
  }
  const latest = messages[assistantIndex];
  const userMessage = [...messages.slice(0, assistantIndex)]
    .reverse()
    .find((item) => item.role === "user");
  const query = userMessage?.content || "";
  if (!Array.isArray(latest.trace) || !latest.trace.length) {
    renderFailedTrace(query, "Phiên hội thoại cũ chưa có dữ liệu Agent Trace.");
    return;
  }
  renderTrace(latest.trace, latest.metrics || {}, query);
}

function renderPendingTrace(query) {
  renderTrace(
    [{
      step: 1,
      type: "pending",
      label: "Đang xử lý câu hỏi",
      thought: "Agent đang phân tích yêu cầu và lựa chọn bước tiếp theo.",
      duration_ms: 0,
    }],
    { iterations: 1, tool_calls: 0, pending: true },
    query,
  );
  setTraceStatus("running", "Đang xử lý");
}

function renderFailedTrace(query, message) {
  renderTrace(
    [{
      step: 1,
      type: "format_error",
      label: "Không thể hoàn thành",
      thought: message,
      duration_ms: 0,
    }],
    { iterations: 1, tool_calls: 0 },
    query,
  );
  setTraceStatus("error", "Có lỗi");
}

function renderHistory(messages) {
  chatMessages.replaceChildren();
  if (!messages.length) {
    appendMessage(bookingWelcome);
    renderTrace();
    return;
  }
  messages.forEach((item) => {
    const sender = item.role === "user" ? "user" : "bot";
    appendMessage(item.content, sender);
    if (sender === "bot") applyAssistantSuggestion(item.content);
  });
  restoreLatestTrace(messages);
}

async function loadChatHistory() {
  try {
    const data = await window.ChatAPI.getHistory();
    if (!chatBusy) renderHistory(data.messages || []);
  } catch (error) {
    if (!chatBusy) {
      renderHistory([]);
      appendMessage(`Không tải được lịch sử: ${error.message}`);
    }
  }
}

async function handleChat(text) {
  const cleanText = text.trim();
  if (!cleanText || chatBusy) return;
  chatBusy = true;
  appendMessage(cleanText, "user");
  chatInput.value = "";
  chatInput.disabled = true;
  renderPendingTrace(cleanText);
  const loading = appendMessage("Đang phân tích và tra cứu…", "bot", "loading-message");
  try {
    const data = await window.ChatAPI.sendMessage(cleanText);
    renderHistory(data.messages || []);
  } catch (error) {
    loading.remove();
    appendMessage(`Xin lỗi, chatbot chưa thể phản hồi: ${error.message}`);
    renderFailedTrace(cleanText, error.message);
  } finally {
    chatBusy = false;
    chatInput.disabled = false;
    chatInput.focus();
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  void handleChat(chatInput.value);
});

document.querySelectorAll("#split-chat-suggestions button").forEach((button) => {
  button.addEventListener("click", () => void handleChat(button.dataset.message));
});

void loadChatHistory();
window.addEventListener("focus", loadChatHistory);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) void loadChatHistory();
});
