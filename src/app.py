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


def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) có Guardrails.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    history = f"User Question: {user_query}"
    action_counts = {}

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
            answer = parsed["content"]
            print(f"🏁 Final Answer: {answer}")
            return answer

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
            return SAFE_FALLBACK_MESSAGE

        print(f"🛠️ Action: {parsed['tool']}{parsed['args']}")
        observation = execute_tool(parsed["tool"], parsed["args"])
        print(f"👁️ Observation:\n{observation}")

        # Chỉ ứng dụng được phép chèn Observation thật vào lịch sử.
        history += f"\n\n{response}\nObservation: {observation}"

    print(
        f"🛡️ GUARDRAIL TRIGGERED: Đã đạt giới hạn tối đa "
        f"{MAX_ITERATIONS} bước. Ngắt lặp an toàn!"
    )
    return SAFE_FALLBACK_MESSAGE


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
