"""
Tool registry cho bộ test Vinmec trong ``config/test_cases.json``.

Ba tool public khớp chính xác với ``expected_tools``:

* ``search_specialties``: định hướng chuyên khoa từ triệu chứng.
* ``get_hospital_info``: tra cứu địa chỉ và giờ hoạt động cơ sở Vinmec.
* ``search_doctors``: tìm bác sĩ theo chuyên khoa và cơ sở.

Các tình huống cấp cứu, xin kê đơn, triệu chứng mơ hồ và ngoài phạm vi có
``expected_tools=[]``. Agent phải xử lý chúng bằng guardrail trong prompt,
không gọi tool. Mọi tool bên dưới vẫn trả JSON an toàn nếu bị gọi sai.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any


DATA_LAST_VERIFIED = "2026-07-28"


def _result(status: str, **payload: Any) -> str:
    """Đóng gói Observation thành chuỗi JSON Unicode nhất quán."""
    return json.dumps({"status": status, **payload}, ensure_ascii=False, indent=2)


def _normalize_text(value: str) -> str:
    """Chuẩn hóa chữ thường, bỏ dấu và khoảng trắng để so khớp tiếng Việt."""
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_marks.replace("đ", "d"))


SPECIALTIES = {
    "DENTAL": {
        "name": "Răng - Hàm - Mặt",
        "aliases": ["rang ham mat", "nha khoa", "rang"],
        "keywords": [
            "dau rang",
            "rang ham",
            "e buot rang",
            "sau rang",
            "chay mau loi",
            "viem loi",
            "nha khoa",
        ],
        "available_at": ["Vinmec Times City", "Vinmec Central Park"],
        "guidance": "Phù hợp để khám đau răng, sâu răng, ê buốt và bệnh lý vùng răng-hàm-mặt.",
        "source": "https://www.vinmec.com/vie/chuyen-khoa/rang-ham-mat",
    },
    "PEDIATRICS": {
        "name": "Nhi - Sơ sinh",
        "aliases": ["nhi", "nhi khoa", "nhi so sinh", "khoa nhi"],
        "keywords": [
            "be ",
            "be nha",
            "tre em",
            "tre nho",
            "so sinh",
            "tuoi bi",
            "bieng an",
        ],
        "available_at": ["Vinmec Times City", "Vinmec Central Park"],
        "guidance": "Tiếp nhận thăm khám các vấn đề sức khỏe của trẻ em và trẻ sơ sinh.",
        "source": (
            "https://www.vinmec.com/vie/co-so-y-te/"
            "khoa-nhi-so-sinh-benh-vien-da-khoa-quoc-te-vinmec-central-park-47751-vi-nhi"
        ),
    },
    "RESPIRATORY": {
        "name": "Hô hấp",
        "aliases": ["ho hap", "khoa ho hap", "noi ho hap"],
        "keywords": ["ho keo dai", "kho tho", "kho khe", "dau nguc", "dam", "viem phoi"],
        "available_at": ["Vinmec Times City", "Vinmec Central Park"],
        "guidance": "Khám các triệu chứng và bệnh lý liên quan đường hô hấp.",
        "source": "https://www.vinmec.com/vie/chuyen-khoa/ho-hap",
    },
    "CARDIOLOGY": {
        "name": "Tim mạch",
        "aliases": ["tim mach", "khoa tim mach"],
        "keywords": ["hoi hop", "tim dap nhanh", "tang huyet ap", "dau tuc nguc"],
        "available_at": ["Vinmec Times City", "Vinmec Central Park"],
        "guidance": "Khám và đánh giá các vấn đề liên quan tim và mạch máu.",
        "source": "https://www.vinmec.com/vie/chuyen-khoa/tim-mach",
    },
    "ENT": {
        "name": "Tai - Mũi - Họng",
        "aliases": ["tai mui hong", "khoa tai mui hong"],
        "keywords": ["dau hong", "nghet mui", "u tai", "khan tieng", "viem xoang"],
        "available_at": ["Vinmec Times City", "Vinmec Central Park"],
        "guidance": "Khám các vấn đề tai, mũi, họng và vùng đầu cổ liên quan.",
        "source": "https://www.vinmec.com/vie/chuyen-khoa/tai-mui-hong",
    },
    "GENERAL": {
        "name": "Nội tổng quát",
        "aliases": ["noi tong quat", "noi khoa", "khoa noi"],
        "keywords": ["sot", "met", "dau dau", "dau bung"],
        "available_at": ["Vinmec Times City", "Vinmec Central Park"],
        "guidance": "Đánh giá ban đầu khi triệu chứng đã đủ rõ nhưng chưa thuộc chuyên khoa cụ thể.",
        "source": "https://www.vinmec.com/vie/chuyen-khoa/noi-tong-quat",
    },
}


HOSPITALS = {
    "TIMES_CITY": {
        "name": "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
        "aliases": ["vinmec times city", "benh vien vinmec times city", "times city"],
        "address": "458 Minh Khai, Phường Vĩnh Tuy, Thành phố Hà Nội",
        "phone": "024 3974 3556",
        "working_hours": {
            "monday_to_friday": "08:00-12:00 và 13:00-17:00",
            "saturday": "08:00-12:00; một số chuyên khoa có lịch 13:00-17:00 theo tuần",
            "sunday": "Nghỉ khám ngoại trú thường quy",
            "emergency": "Dịch vụ vận chuyển và cấp cứu hoạt động 24/7",
        },
        "sunday_answer": (
            "Bệnh viện Vinmec Times City nghỉ khám ngoại trú thường quy vào Chủ Nhật. "
            "Dịch vụ cấp cứu vẫn hoạt động 24/7. Hãy gọi tổng đài trước khi đến vì lịch "
            "chuyên khoa và lịch ngày lễ có thể thay đổi."
        ),
        "source": "https://www.vinmec.com/vie/lien-he-voi-chung-toi/",
    },
    "CENTRAL_PARK": {
        "name": "Bệnh viện Đa khoa Quốc tế Vinmec Central Park",
        "aliases": ["vinmec central park", "benh vien vinmec central park", "central park"],
        "address": "720A Điện Biên Phủ, Phường Thạnh Mỹ Tây, TP. Hồ Chí Minh",
        "phone": "028 3622 1166",
        "working_hours": {
            "monday_to_friday": "07:30-12:00 và 13:00-17:00",
            "saturday": "07:30-12:00; một số chuyên khoa làm việc buổi chiều",
            "sunday": "Không có lịch khám thường quy được công bố trên trang liên hệ",
            "emergency": "Dịch vụ vận chuyển và cấp cứu hoạt động 24/7",
        },
        "sunday_answer": (
            "Trang liên hệ Vinmec không công bố lịch khám thường quy Chủ Nhật tại Central Park. "
            "Hãy gọi 028 3622 1166 để xác nhận; dịch vụ cấp cứu hoạt động 24/7."
        ),
        "source": "https://www.vinmec.com/vie/lien-he-voi-chung-toi/",
    },
}


DOCTORS = [
    {
        "doctor_id": "VMCP-PED-001",
        "name": "BSNT Vũ Thị Hiệu",
        "specialties": ["Nhi", "Sơ sinh"],
        "hospital_id": "CENTRAL_PARK",
        "experience": "14 năm",
        "services": ["Khám và điều trị bệnh trẻ em", "Hô hấp nhi", "Dinh dưỡng nhi"],
        "profile_url": "https://www.vinmec.com/vie/chuyen-gia-y-te/vu-thi-hieu",
    },
    {
        "doctor_id": "VMCP-PED-002",
        "name": "BS. Hồ Thị Ngọc Bích",
        "specialties": ["Nhi", "Sơ sinh", "Thận - Nội tiết nhi"],
        "hospital_id": "CENTRAL_PARK",
        "experience": "15 năm",
        "services": ["Nội tổng quát nhi", "Thận nhi", "Nội tiết nhi"],
        "profile_url": (
            "https://www.vinmec.com/vie/chuyen-gia-y-te/ho-thi-ngoc-bich-51889-vi"
        ),
    },
    {
        "doctor_id": "VMCP-PED-003",
        "name": "BS. Nguyễn Thị Huỳnh Như",
        "specialties": ["Nhi", "Sơ sinh"],
        "hospital_id": "CENTRAL_PARK",
        "experience": "5 năm",
        "services": ["Khám bệnh lý sơ sinh", "Theo dõi sức khỏe trẻ", "Tư vấn dinh dưỡng"],
        "profile_url": "https://www.vinmec.com/vie/chuyen-gia-y-te/nguyen-thi-huynh-nhu",
    },
]


RED_FLAG_KEYWORDS = [
    "ho ra mau",
    "dau nguc du doi",
    "dau tuc nguc du doi",
    "kho tho",
    "va mo hoi",
    "bat tinh",
    "liet nua nguoi",
    "co giat",
]


def _find_hospital(value: str) -> tuple[str, dict[str, Any]] | None:
    normalized = _normalize_text(value)
    for hospital_id, hospital in HOSPITALS.items():
        if any(_normalize_text(alias) in normalized for alias in hospital["aliases"]):
            return hospital_id, hospital
    return None


def search_specialties(symptoms: str, hospital_name: str | None = None) -> str:
    """
    Định hướng chuyên khoa Vinmec dựa trên triệu chứng đã được mô tả đủ rõ.

    Dùng cho TC_VINMEC_01 và bước đầu của TC_VINMEC_03. Không gọi tool này
    khi người dùng xin kê thuốc, có dấu hiệu cấp cứu hoặc chỉ nói mơ hồ như
    "mệt mỏi"; Agent phải xử lý các trường hợp đó bằng guardrail trước.

    Args:
        symptoms: Mô tả triệu chứng, ví dụ ``đau răng khi ăn lạnh``.
        hospital_name: Cơ sở Vinmec mong muốn, có thể bỏ trống.

    Returns:
        JSON chứa các chuyên khoa phù hợp, sắp xếp theo mức độ khớp.
    """
    if not isinstance(symptoms, str) or not symptoms.strip():
        return _result("error", message="Mô tả triệu chứng không được để trống.")
    if hospital_name is not None and not isinstance(hospital_name, str):
        return _result("error", message="Tên cơ sở phải là chuỗi hoặc null.")

    normalized = _normalize_text(symptoms)
    red_flags = [keyword for keyword in RED_FLAG_KEYWORDS if keyword in normalized]
    if red_flags:
        return _result(
            "safety_stop",
            red_flags=red_flags,
            message=(
                "Phát hiện dấu hiệu cảnh báo. Không tiếp tục phân loại/đặt lịch thường quy; "
                "hãy gọi 115 hoặc đến khoa Cấp cứu gần nhất."
            ),
        )

    hospital = _find_hospital(hospital_name) if hospital_name else None
    if hospital_name and hospital is None:
        return _result("error", message=f"Không nhận diện được cơ sở '{hospital_name}'.")

    scores: list[tuple[int, str, dict[str, Any], list[str]]] = []
    pediatric_context = bool(re.search(r"\b(be|tre|con)\b", normalized)) or bool(
        re.search(r"\b\d{1,2}\s*tuoi\b", normalized)
    )

    for specialty_id, specialty in SPECIALTIES.items():
        matched = [keyword for keyword in specialty["keywords"] if keyword in normalized]
        alias_matches = [alias for alias in specialty["aliases"] if alias in normalized]
        score = len(matched) + (2 * len(alias_matches))
        if specialty_id == "PEDIATRICS" and pediatric_context:
            score += 10
            matched.append("ngữ cảnh bệnh nhi")
        if score:
            scores.append((score, specialty_id, specialty, matched + alias_matches))

    vague_only = (
        scores
        and all(item[1] == "GENERAL" for item in scores)
        and any(phrase in normalized for phrase in ["met", "met moi", "khong khoe"])
    )
    if not scores or vague_only:
        return _result(
            "needs_clarification",
            message=(
                "Triệu chứng chưa đủ cụ thể. Hãy hỏi thêm vị trí khó chịu, triệu chứng đi kèm, "
                "thời gian kéo dài, độ tuổi và mức độ nặng trước khi chọn chuyên khoa."
            ),
        )

    scores.sort(key=lambda item: item[0], reverse=True)
    matches = []
    for _, specialty_id, specialty, matched_signs in scores[:3]:
        if hospital and hospital[1]["name"].replace("Bệnh viện Đa khoa Quốc tế ", "") not in specialty[
            "available_at"
        ]:
            continue
        matches.append(
            {
                "specialty_id": specialty_id,
                "specialty_name": specialty["name"],
                "matched_signs": list(dict.fromkeys(matched_signs)),
                "guidance": specialty["guidance"],
                "available_at": specialty["available_at"],
                "official_source": specialty["source"],
            }
        )

    if not matches:
        return _result("error", message="Không tìm thấy chuyên khoa phù hợp tại cơ sở đã chọn.")
    return _result(
        "success",
        count=len(matches),
        specialties=matches,
        disclaimer="Kết quả chỉ định hướng chuyên khoa, không phải chẩn đoán y khoa.",
        data_last_verified=DATA_LAST_VERIFIED,
    )


def get_hospital_info(hospital_name: str, info_type: str | None = None) -> str:
    """
    Tra cứu thông tin vận hành của một cơ sở Vinmec.

    Dùng cho TC_VINMEC_02. Có thể truyền cả câu hỏi vào ``hospital_name``;
    tool vẫn nhận diện được ``Vinmec Times City`` và ý hỏi về Chủ Nhật.

    Args:
        hospital_name: Tên cơ sở hoặc câu hỏi có chứa tên cơ sở.
        info_type: Nội dung cần hỏi, ví dụ ``giờ làm việc Chủ Nhật``.

    Returns:
        JSON chứa địa chỉ, điện thoại, giờ làm việc và nguồn chính thức.
    """
    if not isinstance(hospital_name, str) or not hospital_name.strip():
        return _result("error", message="Tên cơ sở không được để trống.")
    if info_type is not None and not isinstance(info_type, str):
        return _result("error", message="Loại thông tin phải là chuỗi hoặc null.")

    found = _find_hospital(hospital_name)
    if found is None:
        return _result(
            "error",
            message=f"Chưa có dữ liệu cho cơ sở '{hospital_name}'.",
            supported_hospitals=[hospital["name"] for hospital in HOSPITALS.values()],
        )

    hospital_id, hospital = found
    query = _normalize_text(f"{hospital_name} {info_type or ''}")
    if "chu nhat" in query or "sunday" in query:
        answer = hospital["sunday_answer"]
    elif any(keyword in query for keyword in ["gio", "lam viec", "lich"]):
        hours = hospital["working_hours"]
        answer = (
            f"Thứ 2-Thứ 6: {hours['monday_to_friday']}; "
            f"Thứ 7: {hours['saturday']}; Chủ Nhật: {hours['sunday']}. "
            f"{hours['emergency']}."
        )
    elif any(keyword in query for keyword in ["dia chi", "o dau", "lien he", "dien thoai"]):
        answer = f"Địa chỉ: {hospital['address']}. Điện thoại: {hospital['phone']}."
    else:
        answer = (
            f"{hospital['name']}; địa chỉ: {hospital['address']}; điện thoại: {hospital['phone']}."
        )

    return _result(
        "success",
        hospital_id=hospital_id,
        hospital_name=hospital["name"],
        answer=answer,
        address=hospital["address"],
        phone=hospital["phone"],
        working_hours=hospital["working_hours"],
        official_source=hospital["source"],
        data_last_verified=DATA_LAST_VERIFIED,
        verification_note="Hãy gọi tổng đài để xác nhận lịch chuyên khoa và lịch ngày lễ.",
    )


def search_doctors(specialty: str, hospital_name: str | None = None) -> str:
    """
    Tìm bác sĩ Vinmec theo chuyên khoa và cơ sở, không xếp hạng chủ quan.

    Dùng cho bước thứ hai của TC_VINMEC_03 sau khi ``search_specialties`` đã
    trả về Nhi - Sơ sinh tại Vinmec Central Park.

    Args:
        specialty: Tên chuyên khoa, ví dụ ``Nhi`` hoặc ``Nhi - Sơ sinh``.
        hospital_name: Cơ sở Vinmec mong muốn, ví dụ ``Vinmec Central Park``.

    Returns:
        JSON chứa danh sách hồ sơ bác sĩ và URL Vinmec để xác minh/đặt khám.
    """
    if not isinstance(specialty, str) or not specialty.strip():
        return _result("error", message="Chuyên khoa không được để trống.")
    if hospital_name is not None and not isinstance(hospital_name, str):
        return _result("error", message="Tên cơ sở phải là chuỗi hoặc null.")

    hospital = _find_hospital(hospital_name) if hospital_name else None
    if hospital_name and hospital is None:
        return _result("error", message=f"Không nhận diện được cơ sở '{hospital_name}'.")

    normalized_specialty = _normalize_text(specialty)
    doctors = []
    for doctor in DOCTORS:
        if hospital and doctor["hospital_id"] != hospital[0]:
            continue
        specialty_matches = any(
            _normalize_text(item) in normalized_specialty
            or normalized_specialty in _normalize_text(item)
            for item in doctor["specialties"]
        )
        if specialty_matches:
            hospital_data = HOSPITALS[doctor["hospital_id"]]
            doctors.append(
                {
                    "doctor_id": doctor["doctor_id"],
                    "name": doctor["name"],
                    "specialties": doctor["specialties"],
                    "hospital": hospital_data["name"],
                    "experience": doctor["experience"],
                    "services": doctor["services"],
                    "official_profile": doctor["profile_url"],
                }
            )

    if not doctors:
        return _result(
            "error",
            message=f"Không tìm thấy bác sĩ chuyên khoa '{specialty}' tại cơ sở đã chọn.",
            suggestion="Kiểm tra lại tên chuyên khoa/cơ sở hoặc tra cứu trực tiếp trên Vinmec.",
        )
    return _result(
        "success",
        count=len(doctors),
        doctors=doctors,
        ranking_note=(
            "Danh sách không xếp hạng 'bác sĩ tốt nhất'. Hãy chọn theo chuyên môn phù hợp, "
            "lịch khám và nhu cầu của bệnh nhân."
        ),
        data_last_verified=DATA_LAST_VERIFIED,
    )


# Registry chỉ gồm đúng các tool được khai báo trong expected_tools của test_cases.json.
AVAILABLE_TOOLS = {
    "search_specialties": search_specialties,
    "get_hospital_info": get_hospital_info,
    "search_doctors": search_doctors,
}
