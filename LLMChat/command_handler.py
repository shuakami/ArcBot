import os
from blacklist import add_blacklist, remove_blacklist
from config import CONFIG
from post import send_ws_message
from utils import extract_text_from_message, get_history_file
from whitelist import add_whitelist, remove_whitelist

def process_reset_command(msg_dict):
    """
    处理 /arcreset 命令：
      - 私聊：任何人发送 /arcreset 重置自己的对话记录
      - 群聊：必须以 "/arcreset [群号]" 形式，并且只有管理员（admin_qq）才能重置对应群组记录
    执行后回复提示信息。
    """
    # 私聊消息中 text 来自 message 数组；群聊取 raw_message
    if msg_dict.get("message_type") == "group":
        text = msg_dict.get("raw_message", "")
    else:
        # 拼接私聊所有文本段
        text = "".join(seg.get("data", {}).get("text", "") for seg in msg_dict.get("message", []) if seg.get("type") == "text")
        
    if not text.startswith("/arcreset"):
        return False
    
    sender_qq = str(msg_dict["sender"]["user_id"])
    if msg_dict.get("message_type") == "group":
        tokens = text.split()
        if len(tokens) >= 2:
            target_group = tokens[1].strip()
            admin_qq = CONFIG["qqbot"].get("admin_qq", "")
            if sender_qq != admin_qq:
                reply = "只有管理员才能重置群聊记录。"
            else:
                history_file = get_history_file(target_group, chat_type="group")
                if os.path.exists(history_file):
                    os.remove(history_file)
                    reply = f"群号 {target_group} 的聊天记录已重置。"
                else:
                    reply = f"群号 {target_group} 无聊天记录可重置。"
        else:
            reply = "命令格式错误，请使用：/arcreset [群号]"
    else:
        # 私聊重置，直接删除对应对话文件
        history_file = get_history_file(sender_qq, chat_type="private")
        if os.path.exists(history_file):
            os.remove(history_file)
            reply = "你的聊天记录已重置。"
        else:
            reply = "你没有聊天记录。"
    
    # 构造回复消息
    if msg_dict.get("message_type") == "private":
        payload = {
            "action": "send_private_msg",
            "params": {
                "user_id": int(sender_qq),
                "message": [{
                    "type": "text",
                    "data": {"text": reply}
                }]
            }
        }
    else:
        payload = {
            "action": "send_group_msg",
            "params": {
                "group_id": int(msg_dict.get("group_id")),
                "message": [{
                    "type": "text",
                    "data": {"text": reply}
                }]
            }
        }
    send_ws_message(payload)
    return True

def process_admin_command(msg_dict):
    """
    处理名单管理相关指令：
    - /arcblack add [QQ号]
    - /arcblack remove [QQ号]
    - /arcwhite add [QQ号]
    - /arcwhite remove [QQ号]
    
    仅允许配置中的 admin_qq 执行相关命令。命令处理完毕后直接回复提示信息，并返回 True。
    如果不是名单管理命令，则返回 False。
    """
    text = extract_text_from_message(msg_dict)
    sender_qq = str(msg_dict["sender"]["user_id"])
    admin_qq = CONFIG["qqbot"].get("admin_qq", "")
    reply = None

    if text.startswith("/arcblack add"):
        if sender_qq != admin_qq:
            reply = "无权限执行该命令。"
        else:
            tokens = text.split()
            if len(tokens) >= 3:
                target_qq = tokens[2].strip()
                if add_blacklist(target_qq):
                    reply = f"QQ号 {target_qq} 已成功加入黑名单。"
                else:
                    reply = f"QQ号 {target_qq} 已在黑名单中。"
            else:
                reply = "命令格式错误，请使用：/arcblack add [QQ号]"

    elif text.startswith("/arcblack remove"):
        if sender_qq != admin_qq:
            reply = "无权限执行该命令。"
        else:
            tokens = text.split()
            if len(tokens) >= 3:
                target_qq = tokens[2].strip()
                if remove_blacklist(target_qq):
                    reply = f"QQ号 {target_qq} 已从黑名单中移除。"
                else:
                    reply = f"QQ号 {target_qq} 不在黑名单中。"
            else:
                reply = "命令格式错误，请使用：/arcblack remove [QQ号]"

    elif text.startswith("/arcwhite add"):
        if sender_qq != admin_qq:
            reply = "无权限执行该命令。"
        else:
            tokens = text.split()
            if len(tokens) >= 3:
                target_qq = tokens[2].strip()
                if add_whitelist(target_qq):
                    reply = f"QQ号 {target_qq} 已成功加入白名单。"
                else:
                    reply = f"QQ号 {target_qq} 已在白名单中。"
            else:
                reply = "命令格式错误，请使用：/arcwhite add [QQ号]"

    elif text.startswith("/arcwhite remove"):
        if sender_qq != admin_qq:
            reply = "无权限执行该命令。"
        else:
            tokens = text.split()
            if len(tokens) >= 3:
                target_qq = tokens[2].strip()
                if remove_whitelist(target_qq):
                    reply = f"QQ号 {target_qq} 已从白名单中移除。"
                else:
                    reply = f"QQ号 {target_qq} 不在白名单中。"
            else:
                reply = "命令格式错误，请使用：/arcwhite remove [QQ号]"

    if reply is not None:
        # 根据消息类型构造回复
        if msg_dict.get("message_type") == "private":
            payload = {
                "action": "send_private_msg",
                "params": {
                    "user_id": int(sender_qq),
                    "message": [{
                        "type": "text",
                        "data": {"text": reply}
                    }]
                }
            }
        elif msg_dict.get("message_type") == "group":
            payload = {
                "action": "send_group_msg",
                "params": {
                    "group_id": int(msg_dict.get("group_id")),
                    "message": [{
                        "type": "text",
                        "data": {"text": reply}
                    }]
                }
            }
        send_ws_message(payload)
        return True
    return False