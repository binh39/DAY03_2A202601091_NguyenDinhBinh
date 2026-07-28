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

const bookingWelcome =
  "Xin chào! Tôi là trợ lý An Tâm. Bạn có thể mô tả nhu cầu hoặc triệu chứng chính, tôi sẽ giúp định hướng chuyên khoa.";
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

function renderHistory(messages) {
  chatMessages.replaceChildren();
  if (!messages.length) {
    appendMessage(bookingWelcome);
    return;
  }
  messages.forEach((item) => {
    const sender = item.role === "user" ? "user" : "bot";
    appendMessage(item.content, sender);
    if (sender === "bot") applyAssistantSuggestion(item.content);
  });
}

async function loadChatHistory() {
  try {
    const data = await window.ChatAPI.getHistory();
    renderHistory(data.messages || []);
  } catch (error) {
    renderHistory([]);
    appendMessage(`Không tải được lịch sử: ${error.message}`);
  }
}

async function handleChat(text) {
  const cleanText = text.trim();
  if (!cleanText || chatBusy) return;
  chatBusy = true;
  appendMessage(cleanText, "user");
  chatInput.value = "";
  chatInput.disabled = true;
  const loading = appendMessage("Đang phân tích và tra cứu…", "bot", "loading-message");
  try {
    const data = await window.ChatAPI.sendMessage(cleanText);
    renderHistory(data.messages || []);
  } catch (error) {
    loading.remove();
    appendMessage(`Xin lỗi, chatbot chưa thể phản hồi: ${error.message}`);
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
