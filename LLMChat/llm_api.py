import json
import requests
from config import CONFIG

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