# An Tâm Medical — Frontend

Website bệnh viện mẫu, chạy hoàn toàn phía client và không cần bước build.

## Chạy local

```powershell
cd frontend
python -m http.server 5173
```

Mở `http://localhost:5173`.

## Những phần đã hoạt động

- Responsive cho desktop, tablet và mobile.
- Menu mobile và điều hướng theo section.
- Form đặt lịch có validation, mã lịch hẹn và lưu vào `localStorage`.
- Trang `booking.html` chia đôi màn hình: lịch khám bên trái, chatbot bên phải.
- Chatbot demo hỗ trợ đặt lịch, giờ làm việc, địa chỉ và chuyên khoa.
- Thông báo cho các nội dung chưa được kết nối.

## Thay nội dung sau này

- Thông tin bệnh viện và bác sĩ: sửa trong `index.html`.
- Màu sắc và giao diện: sửa các biến đầu file `styles.css`.
- Nối chatbot thật: thay hàm `getBotResponse()` trong `script.js` bằng lời gọi API.
- Nối đặt lịch backend: thay phần lưu `localStorage` trong sự kiện submit của `bookingForm`.
