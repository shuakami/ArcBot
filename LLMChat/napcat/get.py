import json
from config import CONFIG
from napcat.chat_logic import handle_group_message, handle_private_message
from napcat.command_handler import process_command, user_add_role_state, send_reply
from napcat.message_sender import WebSocketSender
from utils.emoji_storage import emoji_storage
import utils.role_manager as role_manager
from utils.text import extract_text_from_message
import asyncio

def handle_incoming_message(message):
    try:
        msg = json.loads(message)
        if msg.get("post_type") != "message":
            return
        
        # --- 角色添加状态处理 --- 
        sender = WebSocketSender()
        sender_info = msg.get("sender", {})
        user_id = str(sender_info.get("user_id"))
        message_type = msg.get("message_type")
        # 确定消息来源ID (私聊是user_id, 群聊是group_id)
        chat_id = str(msg.get("group_id") if message_type == "group" else user_id)
        state_key = (user_id, chat_id)

        if state_key in user_add_role_state:
            current_state_data = user_add_role_state[state_key]
            current_state = current_state_data.get('state')
            message_text = extract_text_from_message(msg).strip()

            if current_state == 'awaiting_prompt':
                if not message_text:
                    reply_text = "Prompt 不能为空，请重新输入 Prompt："
                    send_reply(msg, reply_text, sender)
                else:
                    print(f"[DEBUG] Received prompt for role add from {user_id} in {chat_id}: {message_text[:50]}...")
                    current_state_data['prompt'] = message_text
                    current_state_data['state'] = 'awaiting_name'
                    reply_text = "请输入该模板的名字："
                    send_reply(msg, reply_text, sender)
                return # 消息已被状态机处理
            
            elif current_state == 'awaiting_name':
                if not message_text:
                    reply_text = "角色名称不能为空，请重新输入该模板的名字："
                    send_reply(msg, reply_text, sender)
                else:
                    role_name = message_text
                    prompt = current_state_data.get('prompt', '')
                    print(f"[DEBUG] Received name for role add from {user_id} in {chat_id}: {role_name}")
                    if role_manager.add_role(role_name, prompt):
                        reply_text = f"角色模板 '{role_name}' 添加成功！"
                    else:
                        # add_role 内部会打印错误，这里给用户一个通用提示
                        reply_text = f"添加角色模板 '{role_name}' 失败了（可能是名称已存在？）。"
                    send_reply(msg, reply_text, sender)
                    # 清理状态
                    del user_add_role_state[state_key]
                return # 消息已被状态机处理
            
            elif current_state == 'awaiting_edit_prompt':
                if not message_text:
                    reply_text = "新 Prompt 不能为空，请重新输入新 Prompt："
                    send_reply(msg, reply_text, sender)
                else:
                    role_name_to_edit = current_state_data.get('role_name_to_edit', '')
                    new_prompt = message_text
                    print(f"[DEBUG] Received new prompt for role edit from {user_id} in {chat_id} for role '{role_name_to_edit}': {new_prompt[:50]}...")
                    if role_manager.edit_role(role_name_to_edit, new_prompt):
                        reply_text = f"角色模板 '{role_name_to_edit}' 更新成功！"
                    else:
                        reply_text = f"更新角色模板 '{role_name_to_edit}' 失败了（可能是角色在其间被删除了？）。"
                    send_reply(msg, reply_text, sender)
                    # 清理状态
                    del user_add_role_state[state_key]
                return # 消息已被状态机处理
        # --- 状态处理结束 ---
        
        if CONFIG["debug"]: print("收到消息:", msg)
        
        # 检查并存储表情包
        emoji_storage.store_emoji(msg)
        
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
