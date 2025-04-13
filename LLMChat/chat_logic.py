import time
import threading
from blacklist import is_blacklisted
from config import CONFIG
from llm import process_conversation
from logger import log_message
from post import send_ws_message, set_input_status
from utils import extract_text_from_message
from whitelist import is_whitelisted
from group_manager import is_group_enabled

def handle_private_message(msg_dict):
    try:
        sender = msg_dict["sender"]
        user_id = str(sender["user_id"])

        # 根据当前名单模式检查是否允许处理该消息
        if not check_access(user_id):
            return
        
        username = sender.get("nickname", "")
        message_id = str(msg_dict.get("message_id", ""))
        content = extract_text_from_message(msg_dict)
        timestamp = msg_dict.get("time", int(time.time()))
        
        # 记录私聊消息
        log_message(user_id, username, message_id, content, timestamp)
        print(f'QQ:{user_id} - {username} | 消息Id: {message_id}\n消息: {content}\n时间戳:{timestamp}')
        
        # 使用子线程异步处理回复，达到流式发送效果
        def process_and_send():
            for segment in process_conversation(user_id, content, chat_type="private"):
                set_input_status(user_id)
                import time
                import random
                time.sleep(random.uniform(1.0, 3.0))
                payload = {
                    "action": "send_private_msg",
                    "params": {
                        "user_id": int(user_id),
                        "message": [{
                            "type": "text",
                            "data": {
                                "text": segment
                            }
                        }]
                    }
                }
                send_ws_message(payload)

        threading.Thread(target=process_and_send, daemon=True).start()
    except Exception as e:
        print("处理私聊消息异常:", e)

def handle_group_message(msg_dict):
    try:
        group_id = str(msg_dict.get("group_id", ""))
        # 检查群聊是否启用
        if not is_group_enabled(group_id):
            return

        raw_message = msg_dict.get("raw_message", "")
        # 群聊中只有以 "#" 开头的消息才触发回复
        if not raw_message.startswith("#"):
            return

        # 去掉 "#" 前缀
        content = raw_message.lstrip("#").strip()
        sender = msg_dict["sender"]
        user_id = str(sender["user_id"])

        # 检查当前名单设置对该消息是否允许
        if not check_access(user_id):
            return
        
        username = sender.get("nickname", "")
        message_id = str(msg_dict.get("message_id", ""))
        timestamp = msg_dict.get("time", int(time.time()))
        
        # 记录群聊消息
        log_message(user_id, username, message_id, raw_message, timestamp, group_id)
        print(f'群号: {group_id}QQ:{user_id} - {username} | 消息Id: {message_id}\n消息: {raw_message}\n时间戳:{timestamp}')
        
        # 在对话中附带用户 QQ 与昵称信息
        user_content = f"[用户{user_id}-{username}] {content}"
        def process_and_send():
            for segment in process_conversation(group_id, user_content, chat_type="group"):
                payload = {
                    "action": "send_group_msg",
                    "params": {
                        "group_id": int(group_id),
                        "message": [{
                            "type": "text",
                            "data": {
                                "text": segment
                            }
                        }]
                    }
                }
                send_ws_message(payload)
                import time
                import random
                time.sleep(random.uniform(1.0, 3.0))
                
        threading.Thread(target=process_and_send, daemon=True).start()
    except Exception as e:
        print("处理群聊消息异常:", e)


def check_access(sender_qq):
    """
    根据配置的名单模式过滤消息：
      - 黑名单模式：如果发送者在黑名单中，则返回 False
      - 白名单模式：如果发送者不在白名单中，则返回 False
      - 其它情况返回 True
    """
    mode = CONFIG["qqbot"].get("list_mode", "black").lower()
    if mode == "black":
        return not is_blacklisted(sender_qq)
    elif mode == "white":
        return is_whitelisted(sender_qq)
    return True