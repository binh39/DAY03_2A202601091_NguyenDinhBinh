const bookingForm = document.querySelector("#split-booking-form");
const successPanel = document.querySelector("#split-success");
const successMessage = document.querySelector("#split-success-message");
const appointmentDate = document.querySelector("#split-appointment-date");
const bookingSteps = document.querySelectorAll(".booking-steps li");

const localDate = new Date();
localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
appointmentDate.min = localDate.toISOString().split("T")[0];

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

function appendMessage(content, sender = "bot") {
  const wrapper = document.createElement("div");
  wrapper.className = `split-message ${sender}`;
  if (sender === "bot") {
    const avatar = document.createElement("span");
    avatar.className = "mini-avatar";
    avatar.textContent = "✦";
    wrapper.appendChild(avatar);
  }
  const bubble = document.createElement("div");
  bubble.textContent = content;
  wrapper.appendChild(bubble);
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function suggestSpecialty(text) {
  const normalized = text.toLocaleLowerCase("vi");
  const specialtySelect = bookingForm.elements.specialty;

  if (normalized.includes("tim") || normalized.includes("ngực") || normalized.includes("huyết áp")) {
    specialtySelect.value = "Tim mạch";
    return "Với nhu cầu bạn mô tả, bạn có thể chọn chuyên khoa Tim mạch. Tôi đã chọn sẵn chuyên khoa này trong lịch khám bên trái.";
  }
  if (normalized.includes("trẻ") || normalized.includes("bé") || normalized.includes("nhi")) {
    specialtySelect.value = "Nhi khoa";
    return "Bạn có thể chọn Nhi khoa. Tôi đã cập nhật lựa chọn trong biểu mẫu bên trái.";
  }
  if (normalized.includes("xương") || normalized.includes("khớp") || normalized.includes("lưng")) {
    specialtySelect.value = "Cơ xương khớp";
    return "Cơ xương khớp có thể phù hợp với mô tả của bạn. Tôi đã chọn sẵn trong biểu mẫu.";
  }
  if (normalized.includes("giờ") || normalized.includes("làm việc")) {
    return "Bệnh viện làm việc từ 07:00–19:00, Thứ 2 đến Thứ 7. Khoa Cấp cứu hoạt động 24/7.";
  }
  if (normalized.includes("chuyên khoa") || normalized.includes("không biết")) {
    return "Bạn hãy mô tả triệu chứng chính, vị trí khó chịu và thời gian xuất hiện. Tôi sẽ gợi ý chuyên khoa phù hợp hơn.";
  }
  return "Cảm ơn bạn đã chia sẻ. Chatbot đang ở chế độ demo; bạn có thể hỏi về chuyên khoa, giờ làm việc hoặc mô tả triệu chứng chính.";
}

function handleChat(text) {
  const cleanText = text.trim();
  if (!cleanText) return;
  appendMessage(cleanText, "user");
  chatInput.value = "";
  setTimeout(() => appendMessage(suggestSpecialty(cleanText)), 350);
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  handleChat(chatInput.value);
});

document.querySelectorAll("#split-chat-suggestions button").forEach((button) => {
  button.addEventListener("click", () => handleChat(button.dataset.message));
});

// Điểm nối chatbot thật:
// Thay suggestSpecialty() bằng fetch('/api/chat', { method: 'POST', ... }).
