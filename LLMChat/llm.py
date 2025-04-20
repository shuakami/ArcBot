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
    print(f"[DEBUG] 开始处理对话 - chat_id: {chat_id}, chat_type: {chat_type}")
    
    try:
        # 1. 加载完整历史记录
        full_history = load_conversation_history(chat_id, chat_type)
        print(f"[DEBUG] 已加载对话历史，共 {len(full_history)} 条记录")

        # 2. 将用户输入添加到对话历史中（记录保存用）
        full_history.append({"role": "user", "content": user_input})
        print(f"[DEBUG] 已添加用户输入到历史记录")

        # 3. 构建满足 token 限制的上下文
        context_to_send = build_context_within_limit(full_history)
        print(f"[DEBUG] 已构建上下文，共 {len(context_to_send)} 条消息")

        response_segments = []
        full_response = ""
        
        print(f"[DEBUG] 开始调用AI接口")
        # 4. 调用 AI 接口，流式返回回复分段
        for segment in get_ai_response(context_to_send):
            print(f"[DEBUG] 收到AI回复片段: {segment[:100]}...")  # 只打印前100个字符
            response_segments.append(segment)
            yield segment
            
        full_response = "\n".join(response_segments)
        print(f"[DEBUG] AI回复完成，总长度: {len(full_response)}")
        
    except Exception as e:
        error_msg = f"AI响应出错: {e}"
        print(f"[ERROR] {error_msg}")
        yield error_msg
        full_response = error_msg

    try:
        # 5. 将 AI 的完整回复加入历史记录中，并保存到文件
        full_history.append({"role": "assistant", "content": full_response})
        save_conversation_history(chat_id, full_history, chat_type)
        print(f"[DEBUG] 已保存对话历史")
    except Exception as e:
        print(f"[ERROR] 保存对话历史时出错: {e}")
