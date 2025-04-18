import time
import threading
import random
import re

from config import CONFIG
from llm import process_conversation
from logger import log_message
from utils.blacklist import is_blacklisted
from utils.text import extract_text_from_message
from utils.whitelist import is_whitelisted
from napcat.message_sender import IMessageSender
from napcat.message_types import MessageSegment
from utils.message_content import parse_group_message_content
from utils.ai_message_parser import parse_ai_message_to_segments


def check_access(sender_id, is_group=False):
    """
    根据配置的名单模式过滤消息：
      - 黑名单模式：如果目标在黑名单中，则返回 False
      - 白名单模式：如果目标不在白名单中，则返回 False
      - 其它情况返回 True
    参数 is_group 为 True 时，表示检查群聊名单，False 时为用户消息名单
    """
    mode_key = "group_list_mode" if is_group else "qq_list_mode"
    if CONFIG["debug"]: print(f"检查 {mode_key} 模式")
    mode = CONFIG["qqbot"].get(mode_key, "black").lower()
    if CONFIG["debug"]: print(f"当前模式: {mode}")
    if mode == "black":
        return not is_blacklisted(sender_id, is_group)
    elif mode == "white":
        return is_whitelisted(sender_id, is_group)
    return True

def handle_private_message(msg_dict, sender: IMessageSender):
    """
    处理私聊消息：
      - 记录消息日志
      - 异步生成回复，达到流式发送的效果
    """
    try:
        sender_info = msg_dict["sender"]
        user_id = str(sender_info["user_id"])
        if CONFIG["debug"]: print(f"收到私聊消息: {user_id} - {sender_info.get('nickname', '')}")

        # 检查是否允许处理该消息
        if not check_access(user_id):
            return

        username = sender_info.get("nickname", "")
        message_id = str(msg_dict.get("message_id", ""))
        content = extract_text_from_message(msg_dict)
        timestamp = msg_dict.get("time", int(time.time()))
        # 格式化时间戳前缀
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        content_with_time = f"[时间:{time_str}] {content}"

        # 记录消息日志
        log_message(user_id, username, message_id, content_with_time, timestamp)
        print(f"\nQ: {username}[{user_id}] \n消息Id: {message_id} | 时间戳: {timestamp}\n内容: {content_with_time}")

        # 异步处理回复消息，实现流式发送效果
        def process_and_send():
            for segment in process_conversation(user_id, content_with_time, chat_type="private"):
                sender.set_input_status(user_id)
                time.sleep(random.uniform(1.0, 3.0))
                msg_segments = parse_ai_message_to_segments(segment, message_id)
                sender.send_private_msg(int(user_id), msg_segments)

        threading.Thread(target=process_and_send, daemon=True).start()

    except Exception as e:
        print("处理私聊消息异常:", e)


def handle_group_message(msg_dict, sender: IMessageSender):
    """
    处理群聊消息：
      - 记录消息日志
      - 异步生成回复消息，实现流式发送效果
    """
    try:
        group_id = str(msg_dict.get("group_id", ""))
        raw_message = msg_dict.get("raw_message", "")
        group_prefix = CONFIG["qqbot"].get("group_prefix", "#")
        # 仅处理以 '#' 开头的消息
        if not raw_message.startswith(group_prefix):
            return

        # 解析图片/表情包/文本
        content = parse_group_message_content(msg_dict)
        sender_info = msg_dict["sender"]
        user_id = str(sender_info["user_id"])
        if CONFIG["debug"]: print(f"收到群聊消息: {group_id} - {user_id} - {sender_info.get('nickname', '')}")

        # 检查是否允许处理该消息
        if not check_access(group_id, True):
            return
        if not check_access(user_id):
            return

        username = sender_info.get("nickname", "")
        message_id = str(msg_dict.get("message_id", ""))
        timestamp = msg_dict.get("time", int(time.time()))

        # 记录群聊消息日志
        log_message(user_id, username, message_id, raw_message, timestamp, group_id)
        print(f"\n群: {group_id} | Q: {username} [{user_id}] \n消息Id: {message_id} | 时间戳: {timestamp}\n内容: {raw_message}")

        # 将用户信息附加到消息中
        user_content = f"[用户{user_id}-{username}] {content}"
        # 格式化时间戳前缀
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        user_content_with_time = f"[时间:{time_str}] {user_content}"

        # 异步处理回复消息，实现流式发送效果
        def process_and_send():
            for segment in process_conversation(group_id, user_content_with_time, chat_type="group"):
                msg_segments = parse_ai_message_to_segments(segment, message_id)
                sender.send_group_msg(int(group_id), msg_segments)
                time.sleep(random.uniform(1.0, 3.0))

        threading.Thread(target=process_and_send, daemon=True).start()

    except Exception as e:
        print("处理群聊消息异常:", e)
