import json
from chat_logic import handle_group_message, handle_private_message
from command_handler import process_reset_command, process_admin_command, process_group_management_command

def handle_incoming_message(message):
    try:
        msg = json.loads(message)
        if msg.get("post_type") != "message":
            return
        # 优先处理命令类消息
        if process_reset_command(msg):
            return
        if process_admin_command(msg):
            return
        
        # 正常聊天逻辑分为私聊和群聊
        if msg.get("message_type") == "private":
            handle_private_message(msg)
        elif msg.get("message_type") == "group":
            handle_group_message(msg)
    except Exception as e:
        print("处理ws消息异常:", e)
