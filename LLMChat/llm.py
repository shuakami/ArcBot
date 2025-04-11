import os
import json
import requests
from utils import get_history_file, load_conversation_history, save_conversation_history
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


def process_conversation(chat_id, user_input, chat_type="private"):
    """
    chat_id：私聊中为用户QQ，群聊中为群号；
    user_input：用户输入的消息文本（群聊时外部已去除 # 前缀）；
    chat_type: "private" 或 "group"
    """
    history = load_conversation_history(chat_id, chat_type)
    history.append({"role": "user", "content": user_input})
    response_segments = []
    try:
        for segment in get_ai_response(history):
            response_segments.append(segment)
            yield segment
    except Exception as e:
        yield f"AI响应出错: {e}"
    full_response = "\n".join(response_segments)
    history.append({"role": "assistant", "content": full_response})
    save_conversation_history(chat_id, history, chat_type)
