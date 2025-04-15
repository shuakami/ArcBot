import json
import requests

from config import CONFIG
from utils.files import load_conversation_history, save_conversation_history
from utils.text import estimate_tokens
from llm_api import get_ai_response
from context_utils import build_context_within_limit


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
