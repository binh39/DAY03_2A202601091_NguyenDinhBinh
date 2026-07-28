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

function appendMessage(content, sender = "bot") {
  const message = document.createElement("div");
  message.className = `message ${sender}`;
  message.textContent = content;
  chatMessages.appendChild(message);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function getBotResponse(text) {
  const normalized = text.toLocaleLowerCase("vi");
  if (normalized.includes("đặt lịch") || normalized.includes("lịch khám")) {
    setTimeout(openBooking, 500);
    return "Tôi đã mở biểu mẫu đặt lịch cho bạn. Hãy chọn chuyên khoa và thời gian phù hợp nhé.";
  }
  if (normalized.includes("giờ") || normalized.includes("làm việc")) {
    return "Bệnh viện làm việc từ 07:00–19:00, Thứ 2 đến Thứ 7. Khoa Cấp cứu hoạt động 24/7.";
  }
  if (normalized.includes("chuyên khoa") || normalized.includes("đau")) {
    return "Bạn có thể mô tả vị trí hoặc triệu chứng chính. Hiện website có Tim mạch, Nhi khoa, Cơ xương khớp, Sản phụ khoa và Khám tổng quát.";
  }
  if (normalized.includes("địa chỉ") || normalized.includes("ở đâu")) {
    return "Địa chỉ mẫu hiện tại là 123 Đường Sức Khỏe, TP. Hồ Chí Minh. Thông tin chính thức có thể cập nhật sau.";
  }
  return "Cảm ơn bạn đã chia sẻ. Chatbot hiện đang ở chế độ demo. Tôi có thể hỗ trợ đặt lịch, giờ làm việc, địa chỉ hoặc gợi ý chuyên khoa.";
}

function handleChat(text) {
  const cleanText = text.trim();
  if (!cleanText) return;
  appendMessage(cleanText, "user");
  chatInput.value = "";
  setTimeout(() => appendMessage(getBotResponse(cleanText)), 350);
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  handleChat(chatInput.value);
});

document.querySelectorAll("#chat-suggestions button").forEach((button) => {
  button.addEventListener("click", () => handleChat(button.textContent));
});

// Điểm nối API chatbot sau này:
// Thay getBotResponse() bằng fetch('/api/chat', { method: 'POST', ... })
// và giữ nguyên appendMessage() để hiển thị phản hồi từ backend.
