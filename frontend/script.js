const body = document.body;
const header = document.querySelector(".site-header");
const menuToggle = document.querySelector("#menu-toggle");
const primaryNav = document.querySelector("#primary-nav");
const modal = document.querySelector("#booking-modal");
const bookingForm = document.querySelector("#booking-form");
const bookingSuccess = document.querySelector("#booking-success");
const appointmentDate = document.querySelector("#appointment-date");
const toast = document.querySelector("#toast");
let lastFocusedElement = null;
let toastTimer;

const localDate = new Date();
localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
appointmentDate.min = localDate.toISOString().split("T")[0];

window.addEventListener("scroll", () => {
  header.classList.toggle("scrolled", window.scrollY > 110);
}, { passive: true });

menuToggle.addEventListener("click", () => {
  const isOpen = primaryNav.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", String(isOpen));
  menuToggle.setAttribute("aria-label", isOpen ? "Đóng menu" : "Mở menu");
});

primaryNav.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    primaryNav.classList.remove("open");
    menuToggle.setAttribute("aria-expanded", "false");
  });
});

function openBooking() {
  window.location.href = "booking.html";
}

function closeBooking() {
  modal.hidden = true;
  body.classList.remove("modal-open");
  lastFocusedElement?.focus();
}

document.querySelectorAll("[data-booking-open]").forEach((button) => button.addEventListener("click", openBooking));
document.querySelectorAll("[data-booking-close]").forEach((button) => button.addEventListener("click", closeBooking));

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !modal.hidden) closeBooking();
});

bookingForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!bookingForm.reportValidity()) return;

  const appointment = Object.fromEntries(new FormData(bookingForm).entries());
  appointment.id = `ATM-${Date.now().toString().slice(-6)}`;
  appointment.createdAt = new Date().toISOString();

  const appointments = JSON.parse(localStorage.getItem("anTamAppointments") || "[]");
  appointments.push(appointment);
  localStorage.setItem("anTamAppointments", JSON.stringify(appointments));

  const dateLabel = new Intl.DateTimeFormat("vi-VN", { dateStyle: "long" })
    .format(new Date(`${appointment.date}T00:00:00`));
  document.querySelector("#success-message").textContent =
    `Mã lịch hẹn ${appointment.id}. Bạn đã chọn ${appointment.specialty} vào ${appointment.time}, ${dateLabel}. Chúng tôi sẽ liên hệ qua số ${appointment.phone} để xác nhận.`;

  bookingForm.hidden = true;
  bookingSuccess.hidden = false;
  bookingForm.reset();
});

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2800);
}

document.querySelectorAll("[data-toast]").forEach((element) => {
  element.addEventListener("click", (event) => {
    event.preventDefault();
    showToast(element.dataset.toast);
  });
});

const chatToggle = document.querySelector("#chat-toggle");
const chatClose = document.querySelector("#chat-close");
const chatPanel = document.querySelector("#chat-panel");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const chatMessages = document.querySelector("#chat-messages");

function setChat(open) {
  chatPanel.hidden = !open;
  chatToggle.setAttribute("aria-expanded", String(open));
  document.querySelector(".chat-notice").hidden = open;
  if (open) setTimeout(() => chatInput.focus(), 50);
}

chatToggle.addEventListener("click", () => setChat(chatPanel.hidden));
chatClose.addEventListener("click", () => setChat(false));

const homeWelcome =
  "Xin chào! Tôi là trợ lý An Tâm. Tôi có thể giúp bạn định hướng chuyên khoa, tra cứu cơ sở hoặc tìm bác sĩ.";
let chatBusy = false;

function appendMessage(content, sender = "bot", extraClass = "") {
  const message = document.createElement("div");
  message.className = `message ${sender} ${extraClass}`.trim();
  window.ChatAPI.renderRichText(message, content);
  chatMessages.appendChild(message);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return message;
}

function renderHistory(messages) {
  chatMessages.replaceChildren();
  if (!messages.length) {
    appendMessage(homeWelcome);
    return;
  }
  messages.forEach((item) => {
    appendMessage(item.content, item.role === "user" ? "user" : "bot");
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
  const loading = appendMessage("Đang tra cứu thông tin…", "bot", "loading-message");
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

document.querySelectorAll("#chat-suggestions button").forEach((button) => {
  button.addEventListener("click", () => void handleChat(button.textContent));
});

void loadChatHistory();
window.addEventListener("focus", loadChatHistory);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) void loadChatHistory();
});
