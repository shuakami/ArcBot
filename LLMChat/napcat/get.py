import json
from config import CONFIG
from napcat.chat_logic import handle_group_message, handle_private_message
from napcat.command_handler import process_command

def handle_incoming_message(message):
    try:
        msg = json.loads(message)
        if msg.get("post_type") != "message":
            return
        
        if CONFIG["debug"]: print("收到消息:", msg)
        
        # 优先处理命令类消息
        if process_command(msg):
            return
        
        # 正常聊天逻辑分为私聊和群聊
        if msg.get("message_type") == "private":
            if CONFIG["debug"]: print("处理私聊消息")
            handle_private_message(msg)
        elif msg.get("message_type") == "group":
            if CONFIG["debug"]: print("处理群聊消息")
            handle_group_message(msg)
    except Exception as e:
        print("处理ws消息异常:", e)
