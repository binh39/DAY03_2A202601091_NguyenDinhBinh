"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import math
import os
import re
import sys
import time
import unicodedata
from ast import literal_eval
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Chỉ import registry để app tự nhận mọi tool do Role 2 đăng ký.
from tools import AVAILABLE_TOOLS
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    MAX_ITERATIONS,
    MAX_REPEATED_ACTIONS,
    REACT_SYSTEM_PROMPT,
    SAFE_FALLBACK_MESSAGE,
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    
    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")
    
    # Gọi LLM Provider thực hiện sinh câu trả lời
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")
    return response


def parse_llm_response(response: str) -> dict:
    """
    Parse output ReAct thành Action hoặc Final Answer.

    Format hợp lệ:
        Action: search_specialties['đau răng']
        Final Answer: Nội dung trả lời
    """
    if not isinstance(response, str) or not response.strip():
        raise ValueError("LLM trả về phản hồi rỗng.")

    # Một số model tự bọc phản hồi trong Markdown code fence.
    cleaned = re.sub(r"^\s*```(?:text|python)?\s*", "", response.strip(), flags=re.I)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    final_match = re.search(r"(?im)^\s*Final\s+Answer\s*:\s*(.*)$", cleaned)
    action_match = re.search(
        r"(?im)^\s*Action\s*:\s*([A-Za-z_]\w*)\s*\[(.*)\]\s*$",
        cleaned,
    )

    if final_match and action_match:
        raise ValueError("Phản hồi chỉ được chứa một Action hoặc một Final Answer.")

    if final_match:
        answer = cleaned[final_match.start(1):].strip()
        if not answer:
            raise ValueError("Final Answer không có nội dung.")
        return {"type": "final", "content": answer}

    if not action_match:
        raise ValueError(
            "Sai format; cần `Action: ten_tool['tham số']` "
            "hoặc `Final Answer: ...`."
        )

    tool_name, raw_args = action_match.groups()
    try:
        # Bọc thành tuple và dùng literal_eval để không thực thi code tùy ý.
        args = literal_eval(f"({raw_args},)") if raw_args.strip() else ()
    except (SyntaxError, ValueError) as exc:
        raise ValueError(f"Tham số Action không hợp lệ: {raw_args}") from exc

    if not isinstance(args, tuple):
        args = (args,)
    return {"type": "action", "tool": tool_name, "args": list(args)}


def execute_tool(tool_name: str, args: list) -> str:
    """Chạy tool trong AVAILABLE_TOOLS và luôn trả về Observation dạng chuỗi."""
    tool = AVAILABLE_TOOLS.get(tool_name)
    if tool is None:
        valid_tools = ", ".join(sorted(AVAILABLE_TOOLS))
        return (
            f'LỖI: Tool "{tool_name}" không tồn tại. '
            f"Các tool hợp lệ: {valid_tools}."
        )

    if not isinstance(args, (list, tuple)):
        return "LỖI: Tham số của Action phải là một danh sách."

    try:
        return str(tool(*args))
    except TypeError as exc:
        return f'LỖI: Sai tham số cho tool "{tool_name}": {exc}'
    except Exception as exc:
        return f'LỖI: Tool "{tool_name}" thực thi thất bại: {exc}'


def _current_question(user_query: str) -> str:
    """Tách câu hỏi hiện tại khỏi phần context do web_server thêm vào."""
    marker = "Câu hỏi hiện tại:"
    return user_query.rsplit(marker, 1)[-1].strip() if marker in user_query else user_query.strip()


def _has_doctor_intent(user_query: str) -> bool:
    """Chỉ cho phép luồng tìm bác sĩ khi câu hỏi hiện tại yêu cầu rõ."""
    current = _current_question(user_query).lower()
    return bool(
        re.search(
            r"\b(bác\s*sĩ|bac\s*si|doctor|chuyên\s*gia|ai\s+khám|ai\s+kham)\b",
            current,
        )
    )


def _normalize_for_intent(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char)).replace("đ", "d")


def _should_route_specialty_directly(user_query: str) -> bool:
    """Route ổn định khi người dùng mô tả từ hai triệu chứng cụ thể trở lên."""
    current = _normalize_for_intent(_current_question(user_query))
    medication_intents = [
        "ke don",
        "thuoc gi",
        "khang sinh",
        "lieu dung",
        "uong thuoc",
    ]
    if any(intent in current for intent in medication_intents):
        return False
    concrete_symptoms = [
        "dau bung",
        "buon non",
        "tieu chay",
        "dau rang",
        "ho keo dai",
        "kho tho",
        "dau nguc",
        "sot",
        "bieng an",
        "nghet mui",
        "dau hong",
    ]
    return sum(symptom in current for symptom in concrete_symptoms) >= 2


def _specialty_final_answer(observation: str) -> str | None:
    """Tạo câu trả lời an toàn từ Observation khi chỉ cần định hướng khoa."""
    try:
        data = json.loads(observation)
    except (TypeError, json.JSONDecodeError):
        return None

    status = data.get("status")
    if status == "success" and data.get("specialties"):
        specialty = data["specialties"][0]
        name = specialty.get("specialty_name", "chuyên khoa phù hợp")
        guidance = specialty.get("guidance", "")
        facilities = specialty.get("available_at") or []
        source = specialty.get("official_source", "")
        disclaimer = data.get(
            "disclaimer",
            "Kết quả chỉ mang tính định hướng, không phải chẩn đoán y khoa.",
        )
        parts = [
            f"Dựa trên triệu chứng bạn mô tả, bạn nên bắt đầu thăm khám tại khoa {name}.",
        ]
        if guidance:
            parts.append(guidance)
        if facilities:
            parts.append(f"Chuyên khoa này hiện có tại: {', '.join(facilities)}.")
        parts.append(disclaimer)
        parts.append(
            "Nếu triệu chứng nặng lên nhanh hoặc bạn cảm thấy tình trạng khẩn cấp, "
            "hãy liên hệ cơ sở y tế gần nhất."
        )
        if source:
            parts.append(f"Nguồn tham khảo chính thức: {source}")
        return " ".join(parts)

    if status in {"needs_clarification", "safety_stop", "error"}:
        return data.get("message") or "Vui lòng cung cấp thêm thông tin để được hỗ trợ."
    return None


def run_react_agent_detailed(user_query: str, provider) -> dict:
    """
    Chạy ReAct Agent và trả answer kèm operational trace/metrics cho UI.

    Token và chi phí là ước tính phục vụ demo vì provider adapter hiện chỉ trả text.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    history = f"User Question: {user_query}"
    action_counts = {}
    trace = []
    started_at = time.perf_counter()
    input_characters = 0
    output_characters = 0
    tool_calls = 0
    llm_calls = 0

    def finish(answer: str) -> dict:
        input_tokens = max(1, math.ceil(input_characters / 4)) if llm_calls else 0
        output_tokens = max(1, math.ceil(output_characters / 4)) if llm_calls else 0
        input_rate = float(os.getenv("LLM_INPUT_COST_PER_1M", "0.15"))
        output_rate = float(os.getenv("LLM_OUTPUT_COST_PER_1M", "0.60"))
        estimated_cost = (
            (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
            if llm_calls
            else 0
        )
        return {
            "answer": answer,
            "trace": trace,
            "metrics": {
                "model": getattr(provider, "model_name", provider.__class__.__name__),
                "provider": provider.__class__.__name__,
                "iterations": len(trace),
                "tool_calls": tool_calls,
                "llm_calls": llm_calls,
                "input_tokens_estimate": input_tokens,
                "output_tokens_estimate": output_tokens,
                "total_tokens_estimate": input_tokens + output_tokens,
                "estimated_cost_usd": round(estimated_cost, 6),
                "duration_ms": round((time.perf_counter() - started_at) * 1000),
                "cost_note": "Ước tính demo; có thể cấu hình đơn giá bằng biến môi trường.",
            },
        }

    # Các mô tả có nhiều triệu chứng cụ thể được định tuyến ổn định thay vì
    # phụ thuộc model quyết định có gọi tool hay không.
    if not _has_doctor_intent(user_query) and _should_route_specialty_directly(user_query):
        current = _current_question(user_query)
        direct_started = time.perf_counter()
        observation = execute_tool("search_specialties", [current])
        tool_calls += 1
        trace.append(
            {
                "step": 1,
                "type": "tool",
                "label": "Định hướng chuyên khoa",
                "thought": "Phát hiện nhiều triệu chứng cụ thể; tra cứu chuyên khoa phù hợp.",
                "action": {"tool": "search_specialties", "args": [current]},
                "observation": observation[:6_000],
                "duration_ms": round((time.perf_counter() - direct_started) * 1000),
            }
        )
        policy_answer = _specialty_final_answer(observation)
        if policy_answer:
            output_characters += len(policy_answer)
            trace.append(
                {
                    "step": 2,
                    "type": "final",
                    "label": "Tổng hợp theo intent",
                    "thought": "Đã có Observation để trả lời an toàn; không tìm bác sĩ khi chưa được yêu cầu.",
                    "duration_ms": 0,
                }
            )
            print(f"🏁 Final Answer: {policy_answer}")
            return finish(policy_answer)

    for step in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")
        call_started = time.perf_counter()
        input_characters += len(history) + len(REACT_SYSTEM_PROMPT)
        llm_calls += 1
        response = provider.generate(history, system_prompt=REACT_SYSTEM_PROMPT)
        output_characters += len(response or "")
        print(f"🤖 LLM Output:\n{response}")
        thought_match = re.search(r"(?im)^\s*Thought\s*:\s*(.*)$", response or "")
        thought = thought_match.group(1).strip()[:300] if thought_match else ""

        try:
            parsed = parse_llm_response(response)
        except ValueError as exc:
            observation = f"LỖI FORMAT: {exc}"
            print(f"👁️ Observation: {observation}")
            trace.append(
                {
                    "step": step,
                    "type": "format_error",
                    "label": "Lỗi định dạng",
                    "thought": thought,
                    "observation": observation,
                    "duration_ms": round((time.perf_counter() - call_started) * 1000),
                }
            )
            history += f"\n\n{response}\nObservation: {observation}"
            continue

        if parsed["type"] == "final":
            answer = parsed["content"]
            trace.append(
                {
                    "step": step,
                    "type": "final",
                    "label": "Tổng hợp câu trả lời",
                    "thought": thought or "Đã đủ dữ liệu để phản hồi.",
                    "duration_ms": round((time.perf_counter() - call_started) * 1000),
                }
            )
            print(f"🏁 Final Answer: {answer}")
            return finish(answer)

        # JSON tạo khóa ổn định ngay cả khi args chứa chuỗi Unicode.
        action_key = json.dumps(
            [parsed["tool"], parsed["args"]],
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        action_counts[action_key] = action_counts.get(action_key, 0) + 1
        if action_counts[action_key] > MAX_REPEATED_ACTIONS:
            print(
                "🛡️ REPEATED ACTION: Agent đã lặp lại cùng tool và tham số. "
                "Ngắt lặp an toàn!"
            )
            trace.append(
                {
                    "step": step,
                    "type": "guardrail",
                    "label": "Chặn hành động lặp",
                    "thought": thought,
                    "action": {"tool": parsed["tool"], "args": parsed["args"]},
                    "duration_ms": round((time.perf_counter() - call_started) * 1000),
                }
            )
            return finish(SAFE_FALLBACK_MESSAGE)

        print(f"🛠️ Action: {parsed['tool']}{parsed['args']}")
        observation = execute_tool(parsed["tool"], parsed["args"])
        tool_calls += 1
        print(f"👁️ Observation:\n{observation}")
        trace.append(
            {
                "step": step,
                "type": "tool",
                "label": "Gọi công cụ",
                "thought": thought or "Cần dữ liệu đã xác minh từ công cụ.",
                "action": {"tool": parsed["tool"], "args": parsed["args"]},
                "observation": observation[:6_000],
                "duration_ms": round((time.perf_counter() - call_started) * 1000),
            }
        )

        # Chỉ ứng dụng được phép chèn Observation thật vào lịch sử.
        history += f"\n\n{response}\nObservation: {observation}"

        # Nếu người dùng chỉ cần định hướng khoa, không cho Agent tự mở rộng
        # sang tìm bác sĩ. Kết thúc trực tiếp từ Observation đã xác minh.
        if parsed["tool"] == "search_specialties" and not _has_doctor_intent(user_query):
            policy_answer = _specialty_final_answer(observation)
            if policy_answer:
                output_characters += len(policy_answer)
                trace.append(
                    {
                        "step": step + 1,
                        "type": "final",
                        "label": "Tổng hợp theo intent",
                        "thought": (
                            "Câu hỏi chỉ yêu cầu định hướng chuyên khoa; "
                            "không gọi thêm công cụ tìm bác sĩ."
                        ),
                        "duration_ms": 0,
                    }
                )
                print(f"🏁 Final Answer: {policy_answer}")
                return finish(policy_answer)

    print(
        f"🛡️ GUARDRAIL TRIGGERED: Đã đạt giới hạn tối đa "
        f"{MAX_ITERATIONS} bước. Ngắt lặp an toàn!"
    )
    trace.append(
        {
            "step": len(trace) + 1,
            "type": "guardrail",
            "label": "Đạt giới hạn vòng lặp",
            "thought": "Agent đã dùng hết ngân sách vòng lặp.",
            "duration_ms": 0,
        }
    )
    return finish(SAFE_FALLBACK_MESSAGE)


def run_react_agent(user_query: str, provider) -> str:
    """API tương thích cũ: chỉ trả Final Answer."""
    return run_react_agent_detailed(user_query, provider)["answer"]


if __name__ == "__main__":
    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")
    
    # Chạy thử test thông tin cơ sở; hỗ trợ cả schema mới "input" và cũ "question".
    sample_case = tests[2]
    sample_query = sample_case.get("input") or sample_case.get("question")
    if not sample_query:
        raise ValueError("Test case không có trường 'input' hoặc 'question'.")
    
    print("--- DEMO 1: CHẠY TRÊN CHATBOT BASELINE ---")
    run_baseline_chatbot(sample_query, provider)
    
    print("\n--- DEMO 2: CHẠY TRÊN REACT AGENT ---")
    run_react_agent(sample_query, provider)
