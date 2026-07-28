"""
Web server demo cho frontend bệnh viện và ReAct chatbot.

Chạy:
    python src/web_server.py

Server phục vụ thư mục frontend/ và các API:
    GET    /api/health
    GET    /api/chat/history?conversation_id=...
    POST   /api/chat
    DELETE /api/chat/history?conversation_id=...
"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"
HISTORY_FILE = DATA_DIR / "chat_history.json"
MAX_MESSAGES_PER_CONVERSATION = 100
MAX_USER_MESSAGE_LENGTH = 2_000
SERVER_INSTANCE_ID = str(uuid.uuid4())
SERVER_STARTED_AT = datetime.now(timezone.utc).isoformat()

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import run_react_agent_detailed  # noqa: E402
from providers import get_llm_provider  # noqa: E402


class JsonHistoryStore:
    """Kho JSON nhỏ, ghi atomically và có lock cho demo nhiều request."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()

    def _empty_data(self) -> dict:
        return {"conversations": {}}

    def _read_unlocked(self) -> dict:
        if not self.path.exists():
            return self._empty_data()
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict) or not isinstance(data.get("conversations"), dict):
                return self._empty_data()
            return data
        except (OSError, json.JSONDecodeError):
            return self._empty_data()

    def _write_unlocked(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.path)

    def get_messages(self, conversation_id: str) -> list[dict]:
        with self.lock:
            data = self._read_unlocked()
            messages = data["conversations"].get(conversation_id, [])
            return messages if isinstance(messages, list) else []

    def append_exchange(
        self,
        conversation_id: str,
        user_text: str,
        answer: str,
        trace: list[dict] | None = None,
        metrics: dict | None = None,
    ) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        new_messages = [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": user_text,
                "created_at": now,
            },
            {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": answer,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "trace": trace or [],
                "metrics": metrics or {},
            },
        ]
        with self.lock:
            data = self._read_unlocked()
            messages = data["conversations"].setdefault(conversation_id, [])
            messages.extend(new_messages)
            data["conversations"][conversation_id] = messages[-MAX_MESSAGES_PER_CONVERSATION:]
            self._write_unlocked(data)
            return data["conversations"][conversation_id]

    def clear(self, conversation_id: str) -> None:
        with self.lock:
            data = self._read_unlocked()
            data["conversations"].pop(conversation_id, None)
            self._write_unlocked(data)


history_store = JsonHistoryStore(HISTORY_FILE)
provider = get_llm_provider()
llm_lock = threading.Lock()


def build_agent_query(message: str, history: list[dict]) -> str:
    """Thêm tối đa 6 tin gần nhất để Agent hiểu ngữ cảnh hội thoại."""
    if not history:
        return message
    context_lines = []
    for item in history[-6:]:
        role = "Người dùng" if item.get("role") == "user" else "Trợ lý"
        content = str(item.get("content", "")).strip()
        if content:
            context_lines.append(f"{role}: {content}")
    context = "\n".join(context_lines)
    return (
        "Ngữ cảnh hội thoại trước đó (chỉ dùng để hiểu tham chiếu, không xem là "
        f"Observation từ tool):\n{context}\n\nCâu hỏi hiện tại: {message}"
    )


class HospitalRequestHandler(SimpleHTTPRequestHandler):
    server_version = "VinmecDemo/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Content-Length không hợp lệ.") from exc
        if length <= 0 or length > 20_000:
            raise ValueError("Nội dung request rỗng hoặc quá lớn.")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Body phải là JSON UTF-8 hợp lệ.") from exc

    @staticmethod
    def _conversation_id(query: dict, body: dict | None = None) -> str:
        value = (body or {}).get("conversation_id") or query.get("conversation_id", [""])[0]
        value = str(value).strip()
        if not value or len(value) > 100:
            raise ValueError("conversation_id không hợp lệ.")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "provider": provider.__class__.__name__,
                    "model": getattr(provider, "model_name", "mock"),
                    "server_instance_id": SERVER_INSTANCE_ID,
                    "server_started_at": SERVER_STARTED_AT,
                }
            )
            return
        if parsed.path == "/api/chat/history":
            try:
                conversation_id = self._conversation_id(parse_qs(parsed.query))
                messages = history_store.get_messages(conversation_id)
                self._send_json(
                    {
                        "conversation_id": conversation_id,
                        "messages": messages,
                        "server_instance_id": SERVER_INSTANCE_ID,
                        "server_started_at": SERVER_STARTED_AT,
                    }
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/chat":
            self._send_json({"error": "Không tìm thấy API."}, HTTPStatus.NOT_FOUND)
            return
        try:
            body = self._read_json_body()
            conversation_id = self._conversation_id(parse_qs(parsed.query), body)
            message = str(body.get("message", "")).strip()
            if not message:
                raise ValueError("Tin nhắn không được để trống.")
            if len(message) > MAX_USER_MESSAGE_LENGTH:
                raise ValueError("Tin nhắn quá dài.")

            history = history_store.get_messages(conversation_id)
            agent_query = build_agent_query(message, history)
            # Tránh hai request cùng lúc dùng chung provider/console trace.
            with llm_lock:
                result = run_react_agent_detailed(agent_query, provider)
            answer = result.get("answer")
            if not answer:
                answer = "Xin lỗi, tôi chưa thể xử lý yêu cầu này. Vui lòng thử lại."
            trace = result.get("trace", [])
            metrics = result.get("metrics", {})
            messages = history_store.append_exchange(
                conversation_id,
                message,
                answer,
                trace=trace,
                metrics=metrics,
            )
            self._send_json(
                {
                    "conversation_id": conversation_id,
                    "answer": answer,
                    "messages": messages,
                    "trace": trace,
                    "metrics": metrics,
                    "server_instance_id": SERVER_INSTANCE_ID,
                    "server_started_at": SERVER_STARTED_AT,
                }
            )
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            print(f"[CHAT API ERROR] {exc}", file=sys.stderr)
            self._send_json(
                {"error": "Chatbot đang tạm thời không khả dụng. Vui lòng thử lại."},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/chat/history":
            self._send_json({"error": "Không tìm thấy API."}, HTTPStatus.NOT_FOUND)
            return
        try:
            conversation_id = self._conversation_id(parse_qs(parsed.query))
            history_store.clear(conversation_id)
            self._send_json(
                {
                    "conversation_id": conversation_id,
                    "messages": [],
                    "server_instance_id": SERVER_INSTANCE_ID,
                    "server_started_at": SERVER_STARTED_AT,
                }
            )
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main() -> None:
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "5173"))
    server = ThreadingHTTPServer((host, port), HospitalRequestHandler)
    print("=" * 58)
    print("VINMEC — FRONTEND + REACT CHATBOT")
    print(f"Trang chủ : http://{host}:{port}")
    print(f"Đặt lịch : http://{host}:{port}/booking.html")
    print(f"Lịch sử  : {HISTORY_FILE}")
    print("Nhấn Ctrl+C để dừng.")
    print("=" * 58)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
