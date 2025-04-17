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

def get_ai_response_with_image(conversation, image=None, image_type="url"):
    """
    调用支持图片输入的 AI 接口，基于 conversation 内容和图片返回完整回复（非流式）。
    参数：
      conversation: 对话上下文消息列表，格式同 get_ai_response
      image: 可选，图片内容，可以是 URL、base64 字符串或本地文件路径
      image_type: 指定图片类型，"url"（默认）、"base64"、"file"（自动读取为base64）
    返回：
      完整AI回复内容（字符串）
    用法示例：
      reply = get_ai_response_with_image(conv, image="http://xxx.jpg", image_type="url")
    """
    headers = {
        "Authorization": f"Bearer {CONFIG['image_ai']['token']}",
        "Content-Type": "application/json"
    }
    messages = list(conversation)
    if image:
        # 构造图片消息结构（OpenAI兼容格式）
        if image_type == "file":
            import base64
            with open(image, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            image_obj = {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
        elif image_type == "base64":
            image_obj = {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}
        else:  # url
            image_obj = {"type": "image_url", "image_url": {"url": image}}
        # 图片和文本一起作为最后一条 user 消息
        if messages and messages[-1].get("role") == "user":
            if "content" in messages[-1] and isinstance(messages[-1]["content"], list):
                messages[-1]["content"].append(image_obj)
            elif "content" in messages[-1]:
                messages[-1]["content"] = [messages[-1]["content"], image_obj]
            else:
                messages[-1]["content"] = [image_obj]
        else:
            messages.append({"role": "user", "content": [image_obj]})
    payload = {
        "model": CONFIG["image_ai"]["model"],
        "messages": messages,
        "stream": False
    }
    # print("[DEBUG] image_ai payload:", json.dumps(payload, ensure_ascii=False)[:1000])
    response = requests.post(CONFIG["image_ai"]["api_url"], headers=headers, json=payload)
    # print("[DEBUG] image_ai response status:", response.status_code)
    # print("[DEBUG] image_ai response text:", response.text[:2000])
    if response.status_code != 200:
        raise Exception(f"AI接口调用失败, 状态码：{response.status_code}, {response.text}")
    data = response.json()
    # 兼容OpenAI格式，取完整回复
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return content 