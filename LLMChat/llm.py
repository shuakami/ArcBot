import os
import json
import requests
from utils import get_history_file, load_conversation_history, save_conversation_history, estimate_tokens
from config import CONFIG

def get_ai_response(conversation):
    headers = {
        "Authorization": f"Bearer {CONFIG['ai']['token']}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": CONFIG["ai"]["model"],
        "messages": conversation,
        "stream": True
    }
    response = requests.post(CONFIG["ai"]["api_url"], headers=headers, json=payload, stream=True)
    if response.status_code != 200:
        raise Exception(f"AI接口调用失败, 状态码：{response.status_code}, {response.text}")

    buffer = ""
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.strip():
            continue
        # 处理前缀 "data:" 以及空白字符
        if line.startswith("data:"):
            line = line[len("data:"):].strip()
        # 检查是否为结束标志
        if line == "[DONE]":
            break
        try:
            data = json.loads(line)
            print(repr(line))
        except Exception as e:
            print("解析流式响应出错:", e, "line内容:", repr(line))
            continue

        delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
        if delta:
            # 统一替换换行符格式
            delta = delta.replace("\r\n", "\n")
            buffer += delta
            # 只要 buffer 中包含 "[send]" 或者以换行符结束，就进行分割
            while "[send]" in buffer or ("\n" in buffer and buffer.endswith("\n")):
                if "[send]" in buffer:
                    part, buffer = buffer.split("[send]", 1)
                else:
                    # 当缓冲区以换行符结束时，按换行符分割
                    part, buffer = buffer.split("\n", 1)
                part = part.strip()
                if part:
                    yield part
    # 输出剩余内容（不管有没有换行符）
    if buffer.strip():
        yield buffer.strip()


def build_context_within_limit(full_history):
    """根据配置的 max_context_tokens 构建不超过限制的上下文"""
    max_tokens = CONFIG["ai"].get("max_context_tokens", 15000)
    context = []
    current_tokens = 0

    # 分离系统提示和对话历史
    system_prompt = None
    dialog_history = []
    if full_history and full_history[0]["role"] == "system":
        system_prompt = full_history[0]
        dialog_history = full_history[1:]
    else:
        dialog_history = full_history

    # 确保系统提示总是包含在内（如果存在）
    if system_prompt:
        system_tokens = estimate_tokens(system_prompt.get("content", ""))
        if system_tokens <= max_tokens:
            context.append(system_prompt)
            current_tokens += system_tokens
        else:
            # 如果系统提示本身就超限，那就不包含它了
            print(f"警告：系统提示过长 ({system_tokens} tokens)，已超过最大限制 {max_tokens} tokens，本次请求将不包含系统提示。")
            system_prompt = None # 确保下面不会再次添加

    # 从最新的消息开始向前添加，直到达到 Token 上限
    for message in reversed(dialog_history):
        message_content = message.get("content", "")
        message_tokens = estimate_tokens(message_content)

        # 如果加上这条消息会超限，并且上下文已有内容（至少有系统提示或之前的消息），则停止添加
        if current_tokens + message_tokens > max_tokens and context:
             # 如果第一条用户消息就超长，则必须包含它（但可能需要截断）
            break

        # 插入到上下文的开头（因为是从后往前遍历）
        # 如果 context 为空，说明这是第一条要加入的消息（可能是用户消息或历史消息）
        if not context and system_prompt:
             # 如果有系统提示，则插入到系统提示之后
             context.insert(1, message)
        else:
             # 如果没有系统提示，或者已有其他消息，则插入到最前面
             context.insert(0 if not system_prompt else 1, message)

        current_tokens += message_tokens

        # 加上最新消息后刚好超限
        if current_tokens > max_tokens and len(context) == (1 if not system_prompt else 2):
             print(f"警告：最新的消息过长 ({message_tokens} tokens)，可能导致上下文被截断。")
             pass

    # 如果 context 为空，至少要包含最新的用户消息
    if not context and dialog_history:
        last_message = dialog_history[-1]
        last_content = last_message.get("content", "")
        last_tokens = estimate_tokens(last_content)
        if last_tokens <= max_tokens:
            context.append(last_message)
            current_tokens += last_tokens

    print(f"构建上下文：包含 {len(context)} 条消息，估算 {current_tokens} tokens (上限 {max_tokens})。原始历史 {len(full_history)} 条。")
    return context


def process_conversation(chat_id, user_input, chat_type="private"):
    """
    chat_id：私聊中为用户QQ，群聊中为群号；
    user_input：用户输入的消息文本（群聊时外部已去除 # 前缀）；
    chat_type: "private" 或 "group"
    """
    # 1. 加载完整历史记录
    full_history = load_conversation_history(chat_id, chat_type)

    # 2. 将当前用户输入添加到完整历史记录中（用于保存）
    full_history.append({"role": "user", "content": user_input})

    # 3. 基于完整历史记录构建本次请求的上下文（滑动窗口）
    context_to_send = build_context_within_limit(full_history)

    response_segments = []
    full_response = ""
    try:
        # 4. 使用构建好的上下文调用 AI
        for segment in get_ai_response(context_to_send):
            response_segments.append(segment)
            yield segment
        full_response = "\n".join(response_segments)
    except Exception as e:
        yield f"AI响应出错: {e}"
    # 5. 将 AI 的完整回复添加到完整历史记录中
    full_history.append({"role": "assistant", "content": full_response})

    # 6. 保存完整历史记录到文件
    save_conversation_history(chat_id, full_history, chat_type)
