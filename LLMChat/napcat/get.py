import json
from config import CONFIG
from napcat.chat_logic import handle_group_message, handle_private_message
from napcat.command_handler import process_command
from napcat.message_sender import WebSocketSender
from utils.emoji_storage import emoji_storage
import asyncio

def handle_incoming_message(message):
    try:
        msg = json.loads(message)
        if msg.get("post_type") != "message":
            return
        
        if CONFIG["debug"]: print("收到消息:", msg)
        
        # 检查并存储表情包
        emoji_storage.store_emoji(msg)
        
        sender = WebSocketSender()
        # 优先处理命令类消息
        if process_command(msg, sender):
            return
        
        # 正常聊天逻辑分为私聊和群聊
        if msg.get("message_type") == "private":
            if CONFIG["debug"]: print("处理私聊消息")
            handle_private_message(msg, sender)
        elif msg.get("message_type") == "group":
            if CONFIG["debug"]: print("处理群聊消息")
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(handle_group_message(msg, sender))
            except RuntimeError:
                asyncio.run(handle_group_message(msg, sender))
    except Exception as e:
        print("处理ws消息异常:", e)
