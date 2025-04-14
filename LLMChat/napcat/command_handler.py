import os

from config import CONFIG, save_config
from napcat.post import send_ws_message
from utils.blacklist import add_blacklist, remove_blacklist
from utils.files import get_history_file
from utils.text import extract_text_from_message
from utils.whitelist import add_whitelist, remove_whitelist


def send_reply(msg_dict, reply):
    """
    根据消息类型构造回复 payload 并发送回复消息。
    """
    if msg_dict.get("message_type") == "private":
        payload = {
            "action": "send_private_msg",
            "params": {
                "user_id": int(msg_dict["sender"]["user_id"]),
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


def process_command(msg_dict):
    text = extract_text_from_message(msg_dict)
    if text.startswith("/arcreset"):
        return process_reset_command(msg_dict)
    elif text.startswith("/archelp"):
        return process_help_command(msg_dict)
    elif text.startswith("/arcblack") or text.startswith("/arcwhite"):
        return process_listmod_command(msg_dict)
    elif text.startswith("/arcqqlist"):
        return process_msg_list_command(msg_dict)
    elif text.startswith("/arcgrouplist"):
        return process_group_list_command(msg_dict)
    return False


def process_help_command(msg_dict):
    """
    处理菜单指令 /archelp，显示管理员相关命令使用方法：
    """
    help_text = (
        "ArcBot - 命令菜单\n"
        "=====聊天记录重置=====\n"
        "| /arcreset - 重置记录（私聊）\n"
        "| /arcreset [群号] - 重置指定群号记录\n"
        "=====黑白名单管理=====\n"
        "| /arcblack add [QQ/Q群] [msg/group] - 将QQ或群加入黑名单\n"
        "| /arcblack remove [QQ/Q群] [msg/group] - 将QQ或群从黑名单中移除\n"
        "| /arcwhite add [QQ/Q群] [msg/group] - 将QQ或群加入白名单\n"
        "| /arcwhite remove [QQ/Q群] [msg/group] - 将QQ或群从白名单中移除\n"
        "=====名单模式切换=====\n"
        "| /arcqqlist [white/black] - 切换QQ名单模式\n"
        "| /arcgrouplist [white/black] - 切换群聊名单模式\n"
    )

    send_reply(msg_dict, help_text)
    return True


def process_reset_command(msg_dict):
    """
    处理 /arcreset 命令：
      - 私聊：任何人发送 /arcreset 重置自己的对话记录
      - 群聊：必须以 "/arcreset [群号]" 形式，并且只有管理员（admin_qq）才能重置对应群组记录
    执行后回复提示信息，并返回 True；若不是 /arcreset 命令返回 False。
    """
    # 私聊消息中文本来自 message 数组；群聊直接取 raw_message
    if msg_dict.get("message_type") == "group":
        text = msg_dict.get("raw_message", "")
    else:
        text = "".join(
            seg.get("data", {}).get("text", "")
            for seg in msg_dict.get("message", [])
            if seg.get("type") == "text"
        )

    sender_qq = str(msg_dict["sender"]["user_id"])
    if msg_dict.get("message_type") == "group":
        tokens = text.split()
        if len(tokens) >= 2:
            target_group = tokens[1].strip()
            if sender_qq not in CONFIG["qqbot"].get("admin_qq", []):
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
        # 私聊重置自己的聊天记录
        history_file = get_history_file(sender_qq, chat_type="private")
        if os.path.exists(history_file):
            os.remove(history_file)
            reply = "你的聊天记录已重置。"
        else:
            reply = "你没有聊天记录。"

    send_reply(msg_dict, reply)
    return True


def process_listmod_command(msg_dict):
    """
    处理黑白名单管理相关指令：
      命令格式统一支持两类对象：QQ 或 群
      
      命令格式：
        - /arcblack add [QQ/Q群] [msg/group]
        - /arcblack remove [QQ/Q群] [msg/group]
        - /arcwhite add [QQ/Q群] [msg/group]
        - /arcwhite remove [QQ/Q群] [msg/group]
      
      “msg” 表示用户消息黑白名单，
      “group” 表示群聊黑白名单。
      
      仅允许配置中的 admin_qq 执行相关命令。命令处理完毕后直接回复提示信息，并返回 True；
      如果不是名单管理命令，则返回 False。
    """
    text = extract_text_from_message(msg_dict)
    sender_qq = str(msg_dict["sender"]["user_id"])
    reply = None
    admin_list = CONFIG["qqbot"].get("admin_qq", [])

    # 判断管理员权限
    if sender_qq not in admin_list:
        reply = "无权限执行该命令。"
        send_reply(msg_dict, reply)
        return True

    tokens = text.split()
    if len(tokens) < 4:
        reply = "命令格式错误，请使用：/arcblack add/remove [QQ/Q群] [msg/group] 或 /arcwhite add/remove [QQ/Q群] [msg/group]"
        send_reply(msg_dict, reply)
        return True
    # tokens[0] 为命令，如 /arcblack 或 /arcwhite
    # tokens[1] 为 add 或 remove
    # tokens[2] 为目标号码
    # tokens[3] 为类型标识，要求为 msg 或 group
    target_id = tokens[2].strip()
    list_type = tokens[3].lower()

    # 根据命令分支和名单类型选择处理逻辑：
    if text.startswith("/arcblack"):
        if tokens[1].lower() == "add":
            if list_type == "msg":
                if add_blacklist(target_id, is_group=False):
                    reply = f"QQ号 {target_id} 已成功加入用户黑名单。"
                else:
                    reply = f"QQ号 {target_id} 已在用户黑名单中。"
            elif list_type == "group":
                if add_blacklist(target_id, is_group=True):
                    reply = f"群号 {target_id} 已成功加入群聊黑名单。"
                else:
                    reply = f"群号 {target_id} 已在群聊黑名单中。"
            else:
                reply = "名单类型错误，请使用 msg 或 group。"
        elif tokens[1].lower() == "remove":
            if list_type == "msg":
                if remove_blacklist(target_id, is_group=False):
                    reply = f"QQ号 {target_id} 已从用户黑名单中移除。"
                else:
                    reply = f"QQ号 {target_id} 不在用户黑名单中。"
            elif list_type == "group":
                if remove_blacklist(target_id, is_group=True):
                    reply = f"群号 {target_id} 已从群聊黑名单中移除。"
                else:
                    reply = f"群号 {target_id} 不在群聊黑名单中。"
            else:
                reply = "名单类型错误，请使用 msg 或 group。"
        else:
            reply = "无效的命令操作，请使用 add 或 remove。"

    elif text.startswith("/arcwhite"):
        if tokens[1].lower() == "add":
            if list_type == "msg":
                if add_whitelist(target_id, is_group=False):
                    reply = f"QQ号 {target_id} 已成功加入用户白名单。"
                else:
                    reply = f"QQ号 {target_id} 已在用户白名单中。"
            elif list_type == "group":
                if add_whitelist(target_id, is_group=True):
                    reply = f"群号 {target_id} 已成功加入群聊白名单。"
                else:
                    reply = f"群号 {target_id} 已在群聊白名单中。"
            else:
                reply = "名单类型错误，请使用 msg 或 group。"
        elif tokens[1].lower() == "remove":
            if list_type == "msg":
                if remove_whitelist(target_id, is_group=False):
                    reply = f"QQ号 {target_id} 已从用户白名单中移除。"
                else:
                    reply = f"QQ号 {target_id} 不在用户白名单中。"
            elif list_type == "group":
                if remove_whitelist(target_id, is_group=True):
                    reply = f"群号 {target_id} 已从群聊白名单中移除。"
                else:
                    reply = f"群号 {target_id} 不在群聊白名单中。"
            else:
                reply = "名单类型错误，请使用 msg 或 group。"
        else:
            reply = "无效的命令操作，请使用 add 或 remove。"
    else:
        reply = "无效的命令。"

    send_reply(msg_dict, reply)
    return True


def process_msg_list_command(msg_dict):
    """
    处理修改用户消息名单模式指令：
      - /arcqqlist [white/black]
      
    仅允许管理员执行，命令处理后直接回复提示信息，并返回 True；
    如果不是该命令，则返回 False。
    """
    text = extract_text_from_message(msg_dict)
    tokens = text.split()
    if len(tokens) < 2 or tokens[1].lower() not in ("white", "black"):
        reply = "命令格式错误，请使用：/arcqqlist [white/black]"
    else:
        new_mode = tokens[1].lower()
        # 修改用户消息名单模式配置，并保存到配置文件
        CONFIG["qqbot"]["qq_list_mode"] = new_mode
        save_config()
        reply = f"私聊名单模式已切换为 {new_mode}。"
    
    send_reply(msg_dict, reply)
    return True

def process_group_list_command(msg_dict):
    """
    处理修改群聊名单模式指令：
      - /arcgrouplist [white/black]
      
    仅允许管理员执行，命令处理后直接回复提示信息，并返回 True；
    如果不是该命令，则返回 False。
    """
    text = extract_text_from_message(msg_dict)
    tokens = text.split()
    if len(tokens) < 2 or tokens[1].lower() not in ("white", "black"):
        reply = "命令格式错误，请使用：/arcgrouplist [white/black]"
    else:
        new_mode = tokens[1].lower()
        # 修改群聊名单模式配置，并保存到配置文件
        CONFIG["qqbot"]["group_list_mode"] = new_mode
        save_config()
        reply = f"群聊名单模式已切换为 {new_mode}。"
    
    send_reply(msg_dict, reply)
    return True