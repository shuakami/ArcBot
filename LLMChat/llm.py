import json
import requests

from config import CONFIG
from utils.files import load_conversation_history, save_conversation_history
from utils.text import estimate_tokens


def get_ai_response(conversation):
    """
    调用 AI 接口，基于 conversation 内容进行流式返回。
    
    参数:
      conversation: 包含对话上下文消息的列表，格式符合 AI 接口要求
    
    返回:
      通过 yield 分段返回 AI 回复内容；如果遇到错误则抛出异常。
    """
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
        # 去除前缀 "data:" 和两端空白
        if line.startswith("data:"):
            line = line[len("data:"):].strip()
        # 检查是否为结束标志
        if line == "[DONE]":
            break
        try:
            data = json.loads(line)
            if CONFIG["debug"]: print(repr(line))
        except Exception as e:
            print("解析流式响应出错:", e, "line内容:", repr(line))
            continue

        delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
        if delta:
            # 统一替换换行符格式
            delta = delta.replace("\r\n", "\n")
            buffer += delta
            # 当 buffer 中包含 "[send]" 或以换行符结束时进行分段输出
            while "[send]" in buffer or (buffer.endswith("\n") and "\n" in buffer):
                if "[send]" in buffer:
                    part, buffer = buffer.split("[send]", 1)
                else:
                    part, buffer = buffer.split("\n", 1)
                part = part.strip()
                if part:
                    yield part
    # 输出剩余内容（如果 buffer 中仍有内容）
    if buffer.strip():
        yield buffer.strip()


def build_context_within_limit(full_history):
    """
    根据配置的 max_context_tokens 构建不超过限制的上下文。
    
    参数:
      full_history: 包含完整对话历史的列表（消息字典），其中第一条消息可能是系统提示
    
    返回:
      context: 包含的消息列表，token 数量不超过限制
    """
    max_tokens = CONFIG["ai"].get("max_context_tokens", 15000)
    context = []
    current_tokens = 0

    # 分离系统提示和对话历史记录
    system_prompt = None
    dialog_history = []
    if full_history and full_history[0]["role"] == "system":
        system_prompt = full_history[0]
        dialog_history = full_history[1:]
    else:
        dialog_history = full_history

    # 如果存在系统提示，则始终保证其在上下文中
    if system_prompt:
        system_tokens = estimate_tokens(system_prompt.get("content", ""))
        if system_tokens <= max_tokens:
            context.append(system_prompt)
            current_tokens += system_tokens
        else:
            print(f"警告：系统提示过长 ({system_tokens} tokens)，超过最大限制 {max_tokens} tokens，本次请求将不包含系统提示。")
            system_prompt = None

    # 从最近的消息开始，倒序添加直到接近 token 限制
    for message in reversed(dialog_history):
        message_content = message.get("content", "")
        message_tokens = estimate_tokens(message_content)

        # 如果加入当前消息会超过限制，并且已经有内容则停止添加
        if current_tokens + message_tokens > max_tokens and context:
            break

        # 将消息插入到上下文中；如果存在系统提示，则保证它始终在第一条
        if not context and system_prompt:
            context.insert(1, message)
        else:
            context.insert(0 if not system_prompt else 1, message)

        current_tokens += message_tokens

        if current_tokens > max_tokens and len(context) == (1 if not system_prompt else 2):
            print(f"警告：最新的消息过长 ({message_tokens} tokens)，可能导致上下文被截断。")

    # 如果上下文为空，则至少加入最近一条消息
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
    根据对话历史和当前用户输入构建上下文，调用 AI 接口并返回回复内容。

    参数:
      chat_id: 私聊时为用户 QQ，群聊时为群号
      user_input: 用户输入的文本（群聊时，已去除 "#" 前缀）
      chat_type: "private" 或 "group"

    流程：
      1. 加载完整对话历史
      2. 将当前用户输入添加到历史记录中
      3. 构建满足 token 限制的上下文
      4. 调用 AI 接口获取回复，使用 yield 流式返回回复分段
      5. 将 AI 的完整回复加入到对话历史中，并保存
    """
    # 1. 加载完整历史记录
    full_history = load_conversation_history(chat_id, chat_type)

    # 2. 将用户输入添加到对话历史中（记录保存用）
    full_history.append({"role": "user", "content": user_input})

    # 3. 构建满足 token 限制的上下文
    context_to_send = build_context_within_limit(full_history)

    response_segments = []
    full_response = ""
    try:
        # 4. 调用 AI 接口，流式返回回复分段
        for segment in get_ai_response(context_to_send):
            response_segments.append(segment)
            yield segment
        full_response = "\n".join(response_segments)
    except Exception as e:
        yield f"AI响应出错: {e}"

    # 5. 将 AI 的完整回复加入历史记录中，并保存到文件
    full_history.append({"role": "assistant", "content": full_response})
    save_conversation_history(chat_id, full_history, chat_type)
