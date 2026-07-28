const STORAGE_KEY = "anTamAppointments";
const list = document.querySelector("#appointments-list");
const emptyState = document.querySelector("#appointments-empty");
const countLabel = document.querySelector("#appointment-count");
const filter = document.querySelector("#appointment-filter");
const toast = document.querySelector("#toast");
const menuToggle = document.querySelector("#menu-toggle");
const primaryNav = document.querySelector("#primary-nav");
let toastTimer;

menuToggle.addEventListener("click", () => {
  const isOpen = primaryNav.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", String(isOpen));
  menuToggle.setAttribute("aria-label", isOpen ? "Đóng menu" : "Mở menu");
});

function readAppointments() {
  try {
    const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function writeAppointments(appointments) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(appointments));
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

function addText(parent, tag, content, className = "") {
  const element = document.createElement(tag);
  element.className = className;
  element.textContent = content;
  parent.appendChild(element);
  return element;
}

function formatAppointmentDate(value) {
  const date = new Date(`${value}T00:00:00`);
  return {
    day: new Intl.DateTimeFormat("vi-VN", { day: "2-digit" }).format(date),
    month: new Intl.DateTimeFormat("vi-VN", { month: "short", year: "numeric" }).format(date),
  };
}

function createCard(appointment) {
  const card = document.createElement("article");
  const status = appointment.status || "pending";
  card.className = `appointment-card ${status === "cancelled" ? "cancelled" : ""}`;
  const dateParts = formatAppointmentDate(appointment.date);

  const date = document.createElement("div");
  date.className = "appointment-date";
  addText(date, "strong", dateParts.day);
  addText(date, "span", dateParts.month);

  const main = document.createElement("div");
  main.className = "appointment-main";
  const heading = document.createElement("div");
  heading.className = "appointment-heading";
  addText(heading, "h2", appointment.specialty || "Khám tổng quát");
  addText(
    heading,
    "span",
    status === "cancelled" ? "Đã hủy" : "Chờ xác nhận",
    "status-badge",
  );
  main.appendChild(heading);

  const meta = document.createElement("div");
  meta.className = "appointment-meta";
  addText(meta, "span", `⏱ ${appointment.time || "Chưa chọn giờ"}`);
  addText(meta, "span", `Bác sĩ: ${appointment.doctor || "Không chỉ định"}`);
  addText(meta, "span", `Người khám: ${appointment.fullName || "—"}`);
  addText(meta, "span", `Điện thoại: ${appointment.phone || "—"}`);
  main.appendChild(meta);
  if (appointment.note) addText(main, "p", `Ghi chú: ${appointment.note}`, "appointment-note");

  const actions = document.createElement("div");
  actions.className = "appointment-actions";
  addText(actions, "span", `Mã: ${appointment.id}`, "appointment-code");
  if (status !== "cancelled") {
    const cancel = addText(actions, "button", "Hủy lịch", "cancel-button");
    cancel.type = "button";
    cancel.addEventListener("click", () => cancelAppointment(appointment.id));
  }

  card.append(date, main, actions);
  return card;
}

function cancelAppointment(id) {
  const appointments = readAppointments();
  const target = appointments.find((item) => item.id === id);
  if (!target) return;
  target.status = "cancelled";
  target.cancelledAt = new Date().toISOString();
  writeAppointments(appointments);
  renderAppointments();
  showToast(`Đã hủy lịch ${id}.`);
}

function renderAppointments() {
  const all = readAppointments().sort((a, b) =>
    `${a.date || ""}${a.time || ""}`.localeCompare(`${b.date || ""}${b.time || ""}`),
  );
  const selected = filter.value;
  const visible = selected === "all"
    ? all
    : all.filter((item) => (item.status || "pending") === selected);

  countLabel.textContent = `${all.length} lịch hẹn`;
  list.replaceChildren(...visible.map(createCard));
  emptyState.hidden = visible.length > 0;
}

filter.addEventListener("change", renderAppointments);
window.addEventListener("storage", renderAppointments);
renderAppointments();
