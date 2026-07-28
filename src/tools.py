"""
Tool registry cho đề tài 6: Đặt lịch khám bệnh và tư vấn chuyên khoa.

Tất cả tool đều trả về chuỗi JSON để ReAct Agent có thể đọc Observation
nhất quán. Lỗi nghiệp vụ được trả về với ``status="error"`` thay vì làm
chương trình dừng đột ngột.
"""

from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import requests


REQUEST_TIMEOUT_SECONDS = 10
MAX_WEB_CONTENT_BYTES = 2_000_000


def _result(status: str, **payload: Any) -> str:
    """Đóng gói kết quả tool thành chuỗi JSON Unicode."""
    return json.dumps({"status": status, **payload}, ensure_ascii=False, indent=2)


def _normalize_text(value: str) -> str:
    """Chuẩn hóa chữ thường và bỏ dấu để so khớp tiếng Việt."""
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_marks.replace("đ", "d"))


SPECIALTY_RULES = {
    "Cấp cứu": [
        "dau nguc du doi",
        "kho tho nghiem trong",
        "bat tinh",
        "ngat xiu",
        "liet nua nguoi",
        "co giat",
        "chay mau khong cam",
    ],
    "Tim mạch": ["dau nguc", "hoi hop", "tim dap nhanh", "tang huyet ap", "kho tho"],
    "Thần kinh": ["dau dau", "chong mat", "te bi", "run tay", "mat ngu"],
    "Da liễu": ["noi man", "ngua", "mun", "viem da", "phat ban", "di ung da"],
    "Tai Mũi Họng": ["dau hong", "u tai", "nghet mui", "viem xoang", "khan tieng"],
    "Tiêu hóa": ["dau bung", "day bung", "tieu chay", "tao bon", "non", "trao nguoc"],
    "Cơ Xương Khớp": ["dau lung", "dau khop", "dau vai", "te chan tay", "chan thuong"],
    "Nhi khoa": ["tre em", "em be", "tre so sinh", "be bi"],
    "Sản phụ khoa": ["mang thai", "thai ky", "kinh nguyet", "phu khoa"],
    "Mắt": ["mo mat", "dau mat", "do mat", "giam thi luc", "nhin mo"],
}

EMERGENCY_KEYWORDS = SPECIALTY_RULES["Cấp cứu"] + [
    "khong tho duoc",
    "me man",
    "tinh tao kem",
    "tieu ra mau nhieu",
]

URGENT_KEYWORDS = [
    "sot cao",
    "dau du doi",
    "non lien tuc",
    "kho tho",
    "chay mau",
    "phan ve",
]


DOCTORS = {
    "BS001": {
        "name": "BS. Nguyễn Minh Anh",
        "specialty": "Tim mạch",
        "hospital": "Bệnh viện Bạch Mai",
        "location": "Hà Nội",
        "working_days": [0, 2, 4],
        "slots": ["08:00", "09:30", "14:00", "15:30"],
    },
    "BS002": {
        "name": "BS. Trần Thu Hà",
        "specialty": "Thần kinh",
        "hospital": "Bệnh viện Bạch Mai",
        "location": "Hà Nội",
        "working_days": [1, 3, 5],
        "slots": ["08:30", "10:00", "13:30", "15:00"],
    },
    "BS003": {
        "name": "BS. Lê Quang Huy",
        "specialty": "Da liễu",
        "hospital": "Bệnh viện Đại học Y Hà Nội",
        "location": "Hà Nội",
        "working_days": [0, 1, 3, 5],
        "slots": ["09:00", "10:30", "14:30", "16:00"],
    },
    "BS004": {
        "name": "BS. Phạm Lan Hương",
        "specialty": "Nhi khoa",
        "hospital": "Bệnh viện Nhi Trung ương",
        "location": "Hà Nội",
        "working_days": [0, 1, 2, 3, 4],
        "slots": ["08:00", "09:00", "13:30", "14:30"],
    },
    "BS005": {
        "name": "BS. Võ Đức Long",
        "specialty": "Tiêu hóa",
        "hospital": "Bệnh viện Chợ Rẫy",
        "location": "TP.HCM",
        "working_days": [0, 2, 4],
        "slots": ["07:30", "09:00", "13:00", "14:30"],
    },
    "BS006": {
        "name": "BS. Đặng Ngọc Mai",
        "specialty": "Tai Mũi Họng",
        "hospital": "Bệnh viện Chợ Rẫy",
        "location": "TP.HCM",
        "working_days": [1, 3, 5],
        "slots": ["08:00", "10:00", "14:00", "16:00"],
    },
    "BS007": {
        "name": "BS. Bùi Thanh Sơn",
        "specialty": "Cơ Xương Khớp",
        "hospital": "Bệnh viện Đại học Y Hà Nội",
        "location": "Hà Nội",
        "working_days": [1, 2, 4],
        "slots": ["08:30", "10:30", "13:30", "15:30"],
    },
    "BS008": {
        "name": "BS. Hoàng Khánh Linh",
        "specialty": "Mắt",
        "hospital": "Bệnh viện Chợ Rẫy",
        "location": "TP.HCM",
        "working_days": [0, 3, 5],
        "slots": ["08:00", "09:30", "13:00", "15:00"],
    },
}


HOSPITALS = {
    "bệnh viện bạch mai": {
        "name": "Bệnh viện Bạch Mai",
        "address": "78 Giải Phóng, Hà Nội",
        "specialties": ["Tim mạch", "Thần kinh", "Tiêu hóa", "Cơ Xương Khớp"],
        "official_url": "https://bachmai.gov.vn/",
        "appointment_note": "Lịch và quy trình khám có thể thay đổi; hãy kiểm tra website chính thức trước khi đi.",
    },
    "bệnh viện chợ rẫy": {
        "name": "Bệnh viện Chợ Rẫy",
        "address": "201B Nguyễn Chí Thanh, TP.HCM",
        "specialties": ["Tim mạch", "Tiêu hóa", "Tai Mũi Họng", "Mắt"],
        "official_url": "https://choray.vn/",
        "appointment_note": "Lịch và quy trình khám có thể thay đổi; hãy kiểm tra website chính thức trước khi đi.",
    },
    "bệnh viện nhi trung ương": {
        "name": "Bệnh viện Nhi Trung ương",
        "address": "18/879 La Thành, Hà Nội",
        "specialties": ["Nhi khoa", "Cấp cứu nhi", "Ngoại nhi"],
        "official_url": "https://benhviennhitrunguong.gov.vn/",
        "appointment_note": "Lịch và quy trình khám có thể thay đổi; hãy kiểm tra website chính thức trước khi đi.",
    },
    "bệnh viện đại học y hà nội": {
        "name": "Bệnh viện Đại học Y Hà Nội",
        "address": "Số 1 Tôn Thất Tùng, Hà Nội",
        "specialties": ["Nội khoa", "Da liễu", "Cơ Xương Khớp", "Ngoại khoa"],
        "official_url": "https://benhviendaihocyhanoi.com/",
        "appointment_note": "Lịch và quy trình khám có thể thay đổi; hãy kiểm tra website chính thức trước khi đi.",
    },
}


# Lịch đặt chỉ tồn tại trong bộ nhớ của phiên chạy demo.
BOOKINGS: dict[str, dict[str, str]] = {}


def assess_urgency(symptoms: str) -> str:
    """
    Sàng lọc mức độ khẩn cấp sơ bộ từ mô tả triệu chứng.

    Args:
        symptoms: Mô tả triệu chứng bằng ngôn ngữ tự nhiên.

    Returns:
        Chuỗi JSON gồm mức độ ``emergency``, ``urgent`` hoặc ``routine`` và
        hành động khuyến nghị. Tool không thay thế chẩn đoán của bác sĩ.
    """
    if not isinstance(symptoms, str) or not symptoms.strip():
        return _result("error", message="Triệu chứng không được để trống.")

    normalized = _normalize_text(symptoms)
    emergency_matches = [word for word in EMERGENCY_KEYWORDS if word in normalized]
    urgent_matches = [word for word in URGENT_KEYWORDS if word in normalized]

    if emergency_matches:
        return _result(
            "success",
            urgency="emergency",
            matched_signs=emergency_matches,
            recommendation=(
                "Có dấu hiệu cảnh báo khẩn cấp. Hãy gọi 115 hoặc đến cơ sở cấp cứu gần nhất; "
                "không chờ đặt lịch khám thông thường."
            ),
            disclaimer="Đây là sàng lọc tự động, không phải chẩn đoán y khoa.",
        )
    if urgent_matches:
        return _result(
            "success",
            urgency="urgent",
            matched_signs=urgent_matches,
            recommendation="Nên liên hệ cơ sở y tế và được khám trong ngày.",
            disclaimer="Đây là sàng lọc tự động, không phải chẩn đoán y khoa.",
        )
    return _result(
        "success",
        urgency="routine",
        matched_signs=[],
        recommendation="Có thể tiếp tục bước gợi ý chuyên khoa và đặt lịch khám thông thường.",
        disclaimer="Nếu triệu chứng nặng lên, hãy liên hệ cơ sở y tế ngay.",
    )


def recommend_specialty(symptoms: str) -> str:
    """
    Gợi ý chuyên khoa phù hợp dựa trên từ khóa triệu chứng, không chẩn đoán bệnh.

    Args:
        symptoms: Mô tả triệu chứng của người cần khám.

    Returns:
        Chuỗi JSON chứa tối đa ba chuyên khoa được gợi ý và các dấu hiệu đã
        khớp. Nếu có dấu hiệu cấp cứu, tool ưu tiên hướng dẫn cấp cứu.
    """
    if not isinstance(symptoms, str) or not symptoms.strip():
        return _result("error", message="Triệu chứng không được để trống.")

    normalized = _normalize_text(symptoms)
    if any(keyword in normalized for keyword in EMERGENCY_KEYWORDS):
        return _result(
            "success",
            recommendations=[{"specialty": "Cấp cứu", "matched_signs": ["dấu hiệu cảnh báo"]}],
            warning="Hãy ưu tiên gọi 115 hoặc đến cơ sở cấp cứu gần nhất.",
            disclaimer="Không sử dụng kết quả này để tự chẩn đoán.",
        )

    matches = []
    for specialty, keywords in SPECIALTY_RULES.items():
        if specialty == "Cấp cứu":
            continue
        matched = [keyword for keyword in keywords if keyword in normalized]
        if matched:
            matches.append({"specialty": specialty, "matched_signs": matched, "score": len(matched)})

    matches.sort(key=lambda item: item["score"], reverse=True)
    recommendations = [
        {"specialty": item["specialty"], "matched_signs": item["matched_signs"]}
        for item in matches[:3]
    ]
    if not recommendations:
        recommendations = [{"specialty": "Nội tổng quát", "matched_signs": []}]

    return _result(
        "success",
        recommendations=recommendations,
        disclaimer="Kết quả chỉ định hướng nơi khám, không phải chẩn đoán y khoa.",
    )


def search_doctors(specialty: str, location: str | None = None) -> str:
    """
    Tìm bác sĩ trong danh mục demo theo chuyên khoa và địa điểm tùy chọn.

    Args:
        specialty: Tên chuyên khoa, ví dụ ``Tim mạch`` hoặc ``Da liễu``.
        location: Địa điểm tùy chọn, ví dụ ``Hà Nội`` hoặc ``TP.HCM``.

    Returns:
        Chuỗi JSON chứa danh sách bác sĩ và mã ``doctor_id`` dùng cho các
        bước kiểm tra lịch và đặt lịch.
    """
    if not isinstance(specialty, str) or not specialty.strip():
        return _result("error", message="Chuyên khoa không được để trống.")
    if location is not None and not isinstance(location, str):
        return _result("error", message="Địa điểm phải là chuỗi hoặc null.")

    specialty_normalized = _normalize_text(specialty)
    location_normalized = _normalize_text(location or "")
    doctors = []

    for doctor_id, doctor in DOCTORS.items():
        doctor_specialty = _normalize_text(doctor["specialty"])
        doctor_location = _normalize_text(doctor["location"])
        specialty_matches = (
            specialty_normalized in doctor_specialty or doctor_specialty in specialty_normalized
        )
        location_matches = not location_normalized or location_normalized in doctor_location
        if specialty_matches and location_matches:
            doctors.append(
                {
                    "doctor_id": doctor_id,
                    "name": doctor["name"],
                    "specialty": doctor["specialty"],
                    "hospital": doctor["hospital"],
                    "location": doctor["location"],
                }
            )

    if not doctors:
        return _result(
            "error",
            message=f"Không tìm thấy bác sĩ phù hợp với chuyên khoa '{specialty}'.",
            suggestion="Hãy thử chuyên khoa khác hoặc bỏ điều kiện địa điểm.",
        )
    return _result("success", count=len(doctors), doctors=doctors, data_type="demo")


def _available_slots(doctor_id: str, appointment_date: date) -> list[str]:
    doctor = DOCTORS[doctor_id]
    if appointment_date.weekday() not in doctor["working_days"]:
        return []

    booked_times = {
        booking["appointment_time"][-5:]
        for booking in BOOKINGS.values()
        if booking["doctor_id"] == doctor_id
        and booking["appointment_time"].startswith(appointment_date.isoformat())
    }
    return [slot for slot in doctor["slots"] if slot not in booked_times]


def check_available_slots(doctor_id: str, appointment_date: str) -> str:
    """
    Kiểm tra các khung giờ khám còn trống của một bác sĩ trong 90 ngày tới.

    Args:
        doctor_id: Mã bác sĩ do ``search_doctors`` trả về.
        appointment_date: Ngày cần khám theo định dạng ``YYYY-MM-DD``.

    Returns:
        Chuỗi JSON chứa các giờ còn trống. Ngày sai định dạng, ngày quá khứ
        hoặc mã bác sĩ không tồn tại được trả về dưới dạng lỗi an toàn.
    """
    if not isinstance(doctor_id, str) or doctor_id.upper() not in DOCTORS:
        return _result("error", message=f"Không tìm thấy bác sĩ có mã '{doctor_id}'.")
    if not isinstance(appointment_date, str):
        return _result("error", message="Ngày khám phải có định dạng YYYY-MM-DD.")

    normalized_id = doctor_id.upper()
    try:
        requested_date = date.fromisoformat(appointment_date)
    except ValueError:
        return _result("error", message="Ngày khám không hợp lệ; hãy dùng định dạng YYYY-MM-DD.")

    today = date.today()
    if requested_date < today:
        return _result("error", message="Không thể kiểm tra hoặc đặt lịch cho ngày trong quá khứ.")
    if requested_date > today + timedelta(days=90):
        return _result("error", message="Chỉ hỗ trợ kiểm tra lịch trong 90 ngày tới.")

    slots = _available_slots(normalized_id, requested_date)
    doctor = DOCTORS[normalized_id]
    return _result(
        "success",
        doctor_id=normalized_id,
        doctor_name=doctor["name"],
        appointment_date=requested_date.isoformat(),
        available_slots=slots,
        message=None if slots else "Bác sĩ không làm việc hoặc đã hết lịch trong ngày này.",
        data_type="demo",
    )


def book_appointment(
    patient_name: str,
    phone_number: str,
    doctor_id: str,
    appointment_time: str,
    confirmed: bool = False,
) -> str:
    """
    Tạo lịch khám demo sau khi người dùng xác nhận rõ ràng.

    Args:
        patient_name: Họ tên người bệnh.
        phone_number: Số điện thoại Việt Nam dạng ``0xxxxxxxxx`` hoặc ``+84xxxxxxxxx``.
        doctor_id: Mã bác sĩ do ``search_doctors`` trả về.
        appointment_time: Thời gian theo định dạng ``YYYY-MM-DD HH:MM``.
        confirmed: Phải là ``True`` sau khi người dùng xác nhận bác sĩ và giờ.

    Returns:
        Chuỗi JSON chứa mã lịch hẹn khi thành công. Dữ liệu chỉ lưu trong bộ
        nhớ của phiên demo và không phải lịch thật của bệnh viện.
    """
    if confirmed is not True:
        return _result(
            "error",
            message="Chưa có xác nhận của người dùng. Chỉ đặt lịch khi confirmed=true.",
        )
    if not isinstance(patient_name, str) or len(patient_name.strip()) < 2:
        return _result("error", message="Họ tên người bệnh không hợp lệ.")
    if not isinstance(phone_number, str) or not re.fullmatch(r"(?:\+84|0)\d{9}", phone_number.strip()):
        return _result("error", message="Số điện thoại không hợp lệ.")
    if not isinstance(doctor_id, str) or doctor_id.upper() not in DOCTORS:
        return _result("error", message=f"Không tìm thấy bác sĩ có mã '{doctor_id}'.")
    if not isinstance(appointment_time, str):
        return _result("error", message="Thời gian khám phải có định dạng YYYY-MM-DD HH:MM.")

    try:
        requested_datetime = datetime.strptime(appointment_time, "%Y-%m-%d %H:%M")
    except ValueError:
        return _result("error", message="Thời gian khám không hợp lệ; hãy dùng YYYY-MM-DD HH:MM.")

    normalized_id = doctor_id.upper()
    requested_date = requested_datetime.date()
    requested_slot = requested_datetime.strftime("%H:%M")
    today = date.today()
    if requested_date < today or requested_date > today + timedelta(days=90):
        return _result("error", message="Ngày đặt lịch phải nằm trong 90 ngày tới.")
    if requested_slot not in _available_slots(normalized_id, requested_date):
        return _result("error", message="Khung giờ đã chọn không còn trống hoặc bác sĩ không làm việc.")

    appointment_id = f"APT-{requested_date.strftime('%Y%m%d')}-{len(BOOKINGS) + 1:04d}"
    doctor = DOCTORS[normalized_id]
    BOOKING = {
        "appointment_id": appointment_id,
        "patient_name": patient_name.strip(),
        "phone_number": phone_number.strip(),
        "doctor_id": normalized_id,
        "doctor_name": doctor["name"],
        "hospital": doctor["hospital"],
        "appointment_time": requested_datetime.strftime("%Y-%m-%d %H:%M"),
    }
    BOOKINGS[appointment_id] = BOOKING
    return _result(
        "success",
        appointment=BOOKING,
        message="Đặt lịch demo thành công. Đây không phải xác nhận từ hệ thống thật của bệnh viện.",
    )


def _clean_markup(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def search_web(query: str, max_results: int = 5) -> str:
    """
    Tìm kiếm thông tin công khai trên web qua nguồn kết quả Bing RSS.

    Args:
        query: Cụm từ cần tìm kiếm.
        max_results: Số kết quả cần lấy, từ 1 đến 10.

    Returns:
        Chuỗi JSON chứa tiêu đề, URL và mô tả ngắn. Kết quả tìm kiếm chưa
        được xác minh; Agent nên ưu tiên nguồn bệnh viện/Bộ Y tế chính thức.
    """
    if not isinstance(query, str) or not query.strip():
        return _result("error", message="Từ khóa tìm kiếm không được để trống.")
    if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= 10:
        return _result("error", message="max_results phải là số nguyên từ 1 đến 10.")

    endpoint = f"https://www.bing.com/search?format=rss&q={quote_plus(query.strip())}"
    try:
        response = requests.get(
            endpoint,
            headers={"User-Agent": "MedicalAppointmentLab/1.0"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall(".//item")[:max_results]:
            items.append(
                {
                    "title": _clean_markup(item.findtext("title", "")),
                    "url": (item.findtext("link", "") or "").strip(),
                    "snippet": _clean_markup(item.findtext("description", "")),
                }
            )
    except (requests.RequestException, ET.ParseError) as exc:
        return _result("error", message=f"Không thể tìm kiếm web: {type(exc).__name__}.")

    if not items:
        return _result("error", message="Không tìm thấy kết quả phù hợp.")
    return _result(
        "success",
        query=query.strip(),
        count=len(items),
        results=items,
        warning="Hãy xác minh nội dung và ưu tiên nguồn y tế chính thức trước khi trả lời.",
    )


def _validate_public_url(url: str) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False, "Chỉ hỗ trợ URL HTTP hoặc HTTPS."
        if not parsed.hostname or parsed.username or parsed.password:
            return False, "URL không hợp lệ hoặc chứa thông tin đăng nhập."
        if parsed.port not in {None, 80, 443}:
            return False, "Chỉ cho phép cổng web 80 hoặc 443."

        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                return False, "URL trỏ tới mạng nội bộ hoặc địa chỉ không an toàn."
    except (ValueError, socket.gaierror, OSError):
        return False, "Không thể phân giải địa chỉ URL."
    return True, ""


class _VisibleTextParser(HTMLParser):
    """Trích văn bản hiển thị, bỏ script/style/noscript."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.parts.append(data.strip())


def _download_public_page(url: str) -> tuple[bytes | None, str, str, str | None]:
    current_url = url
    session = requests.Session()
    try:
        for _ in range(4):
            valid, reason = _validate_public_url(current_url)
            if not valid:
                return None, "", current_url, reason

            response = session.get(
                current_url,
                headers={"User-Agent": "MedicalAppointmentLab/1.0"},
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
                stream=True,
            )
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    return None, "", current_url, "Phản hồi chuyển hướng không có URL đích."
                current_url = urljoin(current_url, location)
                continue

            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
                response.close()
                return None, content_type, current_url, "Chỉ hỗ trợ nội dung HTML hoặc văn bản."

            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=16_384):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_WEB_CONTENT_BYTES:
                    response.close()
                    return None, content_type, current_url, "Trang web vượt giới hạn tải 2 MB."
                chunks.append(chunk)
            encoding = response.encoding or "utf-8"
            raw_content = b"".join(chunks)
            response.close()
            return raw_content, f"{content_type}; charset={encoding}", current_url, None
        return None, "", current_url, "Trang web chuyển hướng quá nhiều lần."
    except requests.RequestException as exc:
        return None, "", current_url, f"Không thể tải trang web: {type(exc).__name__}."
    finally:
        session.close()


def fetch_web_content(url: str, max_chars: int = 6000) -> str:
    """
    Tải và trích văn bản hiển thị từ một trang web công khai.

    Args:
        url: URL do ``search_web`` hoặc người dùng cung cấp.
        max_chars: Số ký tự tối đa trả về, từ 500 đến 20000.

    Returns:
        Chuỗi JSON chứa URL cuối, loại nội dung và văn bản đã làm sạch. Tool
        chặn localhost, IP riêng, cổng lạ, nội dung không phải text và trang
        lớn hơn 2 MB.
    """
    if not isinstance(url, str) or not url.strip():
        return _result("error", message="URL không được để trống.")
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or not 500 <= max_chars <= 20_000:
        return _result("error", message="max_chars phải là số nguyên từ 500 đến 20000.")

    raw_content, content_type, final_url, error = _download_public_page(url.strip())
    if error or raw_content is None:
        return _result("error", message=error or "Không thể tải nội dung.", url=final_url)

    charset_match = re.search(r"charset=([^;\s]+)", content_type)
    encoding = charset_match.group(1) if charset_match else "utf-8"
    try:
        decoded = raw_content.decode(encoding, errors="replace")
    except LookupError:
        decoded = raw_content.decode("utf-8", errors="replace")

    if content_type.startswith("text/html") or content_type.startswith("application/xhtml+xml"):
        parser = _VisibleTextParser()
        parser.feed(decoded)
        visible_text = " ".join(parser.parts)
    else:
        visible_text = decoded
    cleaned_text = re.sub(r"\s+", " ", html.unescape(visible_text)).strip()
    truncated = len(cleaned_text) > max_chars

    return _result(
        "success",
        url=final_url,
        content_type=content_type,
        content=cleaned_text[:max_chars],
        truncated=truncated,
        warning="Nội dung web là dữ liệu bên ngoài; cần kiểm chứng trước khi dùng cho tư vấn y tế.",
    )


def answer_hospital_question(question: str, hospital_name: str | None = None) -> str:
    """
    Hỏi đáp thông tin cơ bản từ danh mục bệnh viện có gắn nguồn chính thức.

    Args:
        question: Câu hỏi về địa chỉ, chuyên khoa, lịch/quy trình khám.
        hospital_name: Tên bệnh viện tùy chọn. Nếu bỏ trống, tool thử nhận diện
            tên bệnh viện xuất hiện trong câu hỏi.

    Returns:
        Chuỗi JSON chứa câu trả lời từ dữ liệu tham chiếu và URL chính thức.
        Thông tin biến động như giờ khám phải được kiểm tra lại bằng tool web.
    """
    if not isinstance(question, str) or not question.strip():
        return _result("error", message="Câu hỏi không được để trống.")
    if hospital_name is not None and not isinstance(hospital_name, str):
        return _result("error", message="Tên bệnh viện phải là chuỗi hoặc null.")

    combined = _normalize_text(f"{hospital_name or ''} {question}")
    selected = None
    for key, hospital in HOSPITALS.items():
        normalized_key = _normalize_text(key)
        short_name = normalized_key.replace("benh vien ", "")
        if normalized_key in combined or short_name in combined:
            selected = hospital
            break

    if selected is None:
        return _result(
            "error",
            message="Chưa nhận diện được bệnh viện trong danh mục demo.",
            supported_hospitals=[hospital["name"] for hospital in HOSPITALS.values()],
            suggestion="Hãy cung cấp tên bệnh viện hoặc dùng search_web để tìm nguồn chính thức.",
        )

    normalized_question = _normalize_text(question)
    if any(keyword in normalized_question for keyword in ["dia chi", "o dau", "duong di"]):
        answer = f"Địa chỉ tham chiếu: {selected['address']}."
    elif any(keyword in normalized_question for keyword in ["chuyen khoa", "kham gi", "dieu tri"]):
        answer = "Một số chuyên khoa trong danh mục: " + ", ".join(selected["specialties"]) + "."
    elif any(
        keyword in normalized_question
        for keyword in ["gio lam", "thu bay", "chu nhat", "lich kham", "dat lich", "bao hiem", "chi phi"]
    ):
        answer = (
            "Đây là thông tin có thể thay đổi. Hãy dùng search_web và fetch_web_content trên "
            "website chính thức trước khi trả lời hoặc đến khám."
        )
    else:
        answer = (
            f"{selected['name']} có địa chỉ tham chiếu tại {selected['address']}. "
            f"Các chuyên khoa tiêu biểu trong danh mục: {', '.join(selected['specialties'])}."
        )

    return _result(
        "success",
        hospital=selected["name"],
        answer=answer,
        official_source=selected["official_url"],
        verification_note=selected["appointment_note"],
        data_type="reference",
    )


# Danh sách 8 tool được đăng ký để ReAct Agent sử dụng.
AVAILABLE_TOOLS = {
    "assess_urgency": assess_urgency,
    "recommend_specialty": recommend_specialty,
    "search_doctors": search_doctors,
    "check_available_slots": check_available_slots,
    "book_appointment": book_appointment,
    "search_web": search_web,
    "fetch_web_content": fetch_web_content,
    "answer_hospital_question": answer_hospital_question,
}
