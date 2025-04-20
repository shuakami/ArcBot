import json
import os
from typing import Dict, List, Optional

# 激活角色状态存储
# key: (chat_id: str, chat_type: str), value: role_name: str (None for default)
active_roles: Dict[tuple[str, str], Optional[str]] = {}

ROLES_FILE = os.path.join("data", "roles.json")

def _ensure_roles_file():
    """确保角色文件和目录存在"""
    os.makedirs(os.path.dirname(ROLES_FILE), exist_ok=True)
    if not os.path.exists(ROLES_FILE):
        with open(ROLES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_roles() -> Dict[str, str]:
    """加载所有角色，返回一个 名字->Prompt 的字典"""
    _ensure_roles_file()
    try:
        with open(ROLES_FILE, "r", encoding="utf-8") as f:
            roles = json.load(f)
            # 确保返回的是字典
            return roles if isinstance(roles, dict) else {}
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] 加载角色文件失败: {e}")
        return {}

def save_roles(roles: Dict[str, str]):
    """保存角色字典到文件"""
    _ensure_roles_file()
    try:
        with open(ROLES_FILE, "w", encoding="utf-8") as f:
            json.dump(roles, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"[ERROR] 保存角色文件失败: {e}")

def add_role(name: str, prompt: str) -> bool:
    """添加一个新角色。如果名字已存在则失败。"""
    roles = load_roles()
    normalized_name = name.strip()
    if not normalized_name:
        print("[ERROR] 角色名称不能为空")
        return False
    if normalized_name in roles:
        print(f"[ERROR] 角色名称 '{normalized_name}' 已存在")
        return False
    roles[normalized_name] = prompt.strip()
    save_roles(roles)
    print(f"[INFO] 角色 '{normalized_name}' 添加成功")
    return True

def edit_role(name: str, new_prompt: str) -> bool:
    """编辑一个已存在的角色。如果名字不存在则失败。"""
    roles = load_roles()
    normalized_name = name.strip()
    if not normalized_name:
        print("[ERROR] 角色名称不能为空")
        return False
    if normalized_name not in roles:
        print(f"[ERROR] 角色名称 '{normalized_name}' 不存在")
        return False
    roles[normalized_name] = new_prompt.strip()
    save_roles(roles)
    print(f"[INFO] 角色 '{normalized_name}' 编辑成功")
    return True

def delete_role(name: str) -> bool:
    """删除一个角色。如果名字不存在则失败。"""
    roles = load_roles()
    normalized_name = name.strip()
    if not normalized_name:
        print("[ERROR] 角色名称不能为空")
        return False
    if normalized_name not in roles:
        print(f"[ERROR] 角色名称 '{normalized_name}' 不存在")
        return False
    del roles[normalized_name]
    save_roles(roles)
    print(f"[INFO] 角色 '{normalized_name}' 删除成功")
    return True

def get_role_names() -> List[str]:
    """获取所有角色的名称列表"""
    roles = load_roles()
    return list(roles.keys())

def set_active_role(chat_id: str, chat_type: str, role_name: Optional[str]):
    """设置当前聊天的激活角色"""
    state_key = (chat_id, chat_type)
    if role_name is None:
        if state_key in active_roles:
            del active_roles[state_key]
            print(f"[INFO] Chat ({chat_id}, {chat_type}) 已切换回默认角色。")
        else:
            print(f"[INFO] Chat ({chat_id}, {chat_type}) 当前已是默认角色。")
    else:
        roles = load_roles()
        normalized_name = role_name.strip()
        if normalized_name not in roles:
            print(f"[ERROR] 尝试设置的角色 '{normalized_name}' 不存在。")
            return False # 指示设置失败
        active_roles[state_key] = normalized_name
        print(f"[INFO] Chat ({chat_id}, {chat_type}) 已切换到角色: {normalized_name}")
        return True # 指示设置成功

def get_active_role(chat_id: str, chat_type: str) -> Optional[str]:
    """获取当前聊天的激活角色名称"""
    state_key = (chat_id, chat_type)
    return active_roles.get(state_key)

def get_active_role_prompt(chat_id: str, chat_type: str) -> Optional[str]:
    """获取当前激活角色的 Prompt"""
    role_name = get_active_role(chat_id, chat_type)
    if role_name:
        roles = load_roles()
        return roles.get(role_name) # 如果角色被删了，这里会返回 None
    return None

def get_role_selection_prompt() -> str:
    """生成包含角色列表和切换指令的系统提示片段"""
    role_names = get_role_names()
    if not role_names:
        return "" # 没有自定义角色时，不添加任何提示
    
    prompt = "\n\n角色切换指令\n"
    prompt += "你可以根据对话内容、氛围或自己的状态，在合适的时机切换到不同的角色来回应。"
    prompt += "可用角色列表：\n"
    prompt += " - 默认(Saki&Nya)\n"
    prompt += "\n".join(f" - {name}" for name in role_names)
    prompt += "\n\n切换角色时，请在你的回复中（单独一行或与其他内容一起）使用以下内部标记：\n"
    prompt += "`[setrole:角色名称]` 或 `[setrole:default]`\n"
    prompt += "例如：要切换到角色'默认（Saki&Nya）'，使用 `[setrole:default]`\n"
    prompt += "切换是内部操作，用户不会看到这个标记。请自然地完成角色转换。"
    prompt += "请不要过于频繁地切换角色。"
    prompt += "\n"
    return prompt

# 初始化时确保文件存在
_ensure_roles_file() 