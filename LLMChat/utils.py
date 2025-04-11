import os
import json
from config import CONFIG

PRIVATE_DIR = os.path.join("data", "conversation", "private")
GROUP_DIR = os.path.join("data", "conversation", "group")
os.makedirs(PRIVATE_DIR, exist_ok=True)
os.makedirs(GROUP_DIR, exist_ok=True)

def extract_text_from_message(msg_dict):
    text = ""
    for seg in msg_dict.get("message", []):
        if seg.get("type") == "text":
            text += seg.get("data", {}).get("text", "")
    return text

def get_history_file(id_str, chat_type="private"):
    if chat_type == "private":
        return os.path.join(PRIVATE_DIR, f"private_{id_str}.json")
    else:
        return os.path.join(GROUP_DIR, f"group_{id_str}.json")

def load_conversation_history(id_str, chat_type="private"):
    history_file = get_history_file(id_str, chat_type)
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        system_prompt = ""
        try:
            with open(os.path.join("config", "system_prompt.txt"), "r", encoding="utf-8") as sp:
                system_prompt = sp.read().strip()
        except Exception as e:
            print("读取 system_prompt.txt 失败:", e)
        system_msg = {"role": "system", "content": system_prompt}
        return [system_msg]

def save_conversation_history(id_str, history, chat_type="private"):
    history_file = get_history_file(id_str, chat_type)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
