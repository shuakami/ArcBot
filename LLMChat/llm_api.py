import json
import requests
import base64
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
    自动判断API类型：
    - 如果image_ai.api_url包含'dashscope.aliyuncs.com'，用dashscope SDK
    - 否则用OpenAI兼容HTTP请求
    """
    api_url = CONFIG['image_ai']['api_url']
    token = CONFIG['image_ai']['token']
    model = CONFIG['image_ai']['model']
    # 自动处理本地图片为base64
    if image_type == "file" and image:
        with open(image, "rb") as f:
            image = base64.b64encode(f.read()).decode()
        image_type = "base64"
    # 判断是否为阿里云DashScope
    if "dashscope.aliyuncs.com" in api_url:
        try:
            import dashscope
        except ImportError:
            raise Exception("未检测到dashscope库，请先安装：pip install dashscope")
        dashscope.api_key = token
        messages = []
        for msg in conversation:
            if msg["role"] == "user" and image:
                content = []
                if "content" in msg:
                    if isinstance(msg["content"], str):
                        content.append({"text": msg["content"]})
                    elif isinstance(msg["content"], list):
                        content.extend(msg["content"])
                if image_type == "base64":
                    content.append({"image": f"data:image/png;base64,{image}"})
                else:
                    content.append({"image": image})
                messages.append({"role": msg["role"], "content": content})
            else:
                messages.append(msg)
        try:
            response = dashscope.MultiModalConversation.call(
                model=model,
                messages=messages
            )
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"调用失败: {response.code}, {response.message}")
        except Exception as e:
            raise Exception(f"调用DashScope API失败: {str(e)}")
    else:
        # OpenAI兼容HTTP请求
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        messages = list(conversation)
        if image:
            image_obj = None
            if image_type == "base64":
                image_obj = {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}
            else:
                image_obj = {"type": "image_url", "image_url": {"url": image}}
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
            "model": model,
            "messages": messages,
            "stream": False
        }
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"AI接口调用失败, 状态码：{response.status_code}, {response.text}")
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content
        except Exception as e:
            raise Exception(f"调用OpenAI兼容API失败: {str(e)}") 