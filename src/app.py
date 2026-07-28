"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import os
import re
import sys
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

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import AVAILABLE_TOOLS, get_weather, search_flights
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS
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


def parse_llm_response(response: str):
    """
    Parse một phản hồi ReAct thành Final Answer hoặc Action.

    Action chấp nhận dạng: tool_name['arg 1', 'arg 2'].
    Hàm chỉ phân tích cú pháp; việc kiểm tra tool/arguments thuộc execute_tool().
    """
    if not isinstance(response, str) or not response.strip():
        raise ValueError("LLM trả về phản hồi rỗng.")

    final_match = re.search(
        r"(?im)^\s*Final\s+Answer\s*:\s*(.*)$", response
    )
    if final_match:
        final_answer = response[final_match.start(1):].strip()
        if not final_answer:
            raise ValueError("Final Answer không có nội dung.")
        return {"type": "final", "content": final_answer}

    action_match = re.search(
        r"(?im)^\s*Action\s*:\s*([A-Za-z_]\w*)\s*\[(.*)\]\s*$",
        response,
    )
    if not action_match:
        raise ValueError(
            "Sai format: cần `Action: tool['arg']` hoặc `Final Answer: ...`."
        )

    tool_name, raw_args = action_match.groups()
    try:
        # Bọc thành tuple để dùng parser literal an toàn, không dùng eval().
        parsed_args = literal_eval(f"({raw_args},)") if raw_args.strip() else ()
    except (SyntaxError, ValueError) as exc:
        raise ValueError(f"Tham số Action không hợp lệ: {raw_args}") from exc

    if not isinstance(parsed_args, tuple):
        parsed_args = (parsed_args,)
    return {"type": "action", "tool": tool_name, "args": list(parsed_args)}


def execute_tool(tool_name: str, args):
    """Thực thi một tool đã đăng ký và luôn trả Observation dạng chuỗi."""
    tool = AVAILABLE_TOOLS.get(tool_name)
    if tool is None:
        valid_tools = ", ".join(sorted(AVAILABLE_TOOLS))
        return f"LỖI: Tool '{tool_name}' không tồn tại. Tool hợp lệ: {valid_tools}."

    if not isinstance(args, (list, tuple)):
        return "LỖI: Danh sách tham số của tool không hợp lệ."

    try:
        return str(tool(*args))
    except TypeError as exc:
        return f"LỖI: Tham số không hợp lệ cho tool '{tool_name}': {exc}"
    except Exception as exc:
        return f"LỖI: Tool '{tool_name}' thực thi thất bại: {exc}"


def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) có Guardrails.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    history = f"User Question: {user_query}"

    for step in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")
        response = provider.generate(history, system_prompt=REACT_SYSTEM_PROMPT)
        print(f"🤖 LLM Output:\n{response}")

        try:
            parsed = parse_llm_response(response)
        except ValueError as exc:
            observation = f"LỖI FORMAT: {exc}"
            print(f"👁️ Observation: {observation}")
            history += f"\n\n{response}\nObservation: {observation}"
            continue

        if parsed["type"] == "final":
            print(f"🏁 Final Answer: {parsed['content']}")
            return parsed["content"]

        observation = execute_tool(parsed["tool"], parsed["args"])
        print(f"🛠️ Action: {parsed['tool']}{parsed['args']}")
        print(f"👁️ Observation: {observation}")
        history += f"\n\n{response}\nObservation: {observation}"

    fallback = (
        f"Không thể hoàn thành yêu cầu sau {MAX_ITERATIONS} bước. "
        "Vui lòng thử lại hoặc cung cấp thêm thông tin."
    )
    print(
        f"🛡️ GUARDRAIL TRIGGERED: Đã đạt giới hạn tối đa "
        f"{MAX_ITERATIONS} bước. Ngắt lặp an toàn!"
    )
    return fallback


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
    
    # Chạy thử câu test số 3
    sample_query = tests[2]["question"]
    
    print("--- DEMO 1: CHẠY TRÊN CHATBOT BASELINE ---")
    run_baseline_chatbot(sample_query, provider)
    
    print("\n--- DEMO 2: CHẠY TRÊN REACT AGENT ---")
    run_react_agent(sample_query, provider)
