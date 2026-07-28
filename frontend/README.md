# An Tâm Medical — Frontend

Website bệnh viện mẫu tích hợp ReAct chatbot từ Python backend.

## Chạy local

```powershell
python src/web_server.py
```

Mở `http://localhost:5173`.

## Những phần đã hoạt động

- Responsive cho desktop, tablet và mobile.
- Menu mobile và điều hướng theo section.
- Form đặt lịch có validation, mã lịch hẹn và lưu vào `localStorage`.
- Trang `booking.html` chia đôi màn hình: lịch khám bên trái, chatbot bên phải.
- Trang `appointments.html` hiển thị và quản lý các lịch khám đã xác nhận.
- Cả hai chatbot gọi chung ReAct Agent và tool trong `src/tools.py`.
- Lịch sử hai chatbot được đồng bộ qua API và lưu tại `data/chat_history.json`.
- Link trong phản hồi chatbot có thể bấm và được mở an toàn ở tab mới.
- Giao diện dùng Be Vietnam Pro và Noto Serif, hỗ trợ đầy đủ tiếng Việt.
- Thông báo cho các nội dung chưa được kết nối.

## Thay nội dung sau này

- Thông tin bệnh viện và bác sĩ: sửa trong `index.html`.
- Màu sắc và giao diện: sửa các biến đầu file `styles.css`.
- Cấu hình LLM bằng `LLM_PROVIDER`, `LLM_MODEL` và API key tương ứng trong `.env`.
- Nối đặt lịch backend: thay phần lưu `localStorage` trong sự kiện submit của `bookingForm`.
