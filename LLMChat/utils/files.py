import os
import json
from utils.notebook import notebook

PRIVATE_DIR = os.path.join("data", "conversation", "private")
GROUP_DIR = os.path.join("data", "conversation", "group")
os.makedirs(PRIVATE_DIR, exist_ok=True)
os.makedirs(GROUP_DIR, exist_ok=True)

def get_latest_system_content() -> str:
    """获取最新的系统提示和笔记内容"""
    try:
        with open(os.path.join("config", "system_prompt.txt"), "r", encoding="utf-8") as sp:
            system_prompt = sp.read().strip()
        
        # 获取笔记内容
        notes_context = notebook.get_notes_as_context()
        if notes_context:
            system_prompt = f"{system_prompt}\n\n{notes_context}"
            
        return system_prompt
    except Exception as e:
        print("读取系统提示或笔记失败:", e)
        return ""

def get_history_file(id_str, chat_type="private"):
    if chat_type == "private":
        return os.path.join(PRIVATE_DIR, f"private_{id_str}.json")
    else:
        return os.path.join(GROUP_DIR, f"group_{id_str}.json")

def load_conversation_history(id_str, chat_type="private"):
    """
    加载对话历史，并确保系统提示是最新的
    每次加载时都会更新系统提示和笔记内容
    """
    history_file = get_history_file(id_str, chat_type)
    
    try:
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
                
            # 更新现有对话历史中的系统提示
            if history and history[0]["role"] == "system":
                history[0]["content"] = get_latest_system_content()
            else:
                # 如果没有系统提示，添加一个
                system_msg = {"role": "system", "content": get_latest_system_content()}
                history.insert(0, system_msg)
                
            return history
        else:
            # 新对话，创建包含系统提示的历史记录
            system_msg = {"role": "system", "content": get_latest_system_content()}
            return [system_msg]
            
    except Exception as e:
        print(f"加载对话历史出错: {e}")
        # 发生错误时，至少返回一个包含系统提示的新历史记录
        system_msg = {"role": "system", "content": get_latest_system_content()}
        return [system_msg]

def save_conversation_history(id_str, history, chat_type="private"):
    """保存对话历史记录"""
    history_file = get_history_file(id_str, chat_type)
    try:
        # 确保保存前系统提示是最新的
        if history and history[0]["role"] == "system":
            history[0]["content"] = get_latest_system_content()
            
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存对话历史记录失败: {e}")
