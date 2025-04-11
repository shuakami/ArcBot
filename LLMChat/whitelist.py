import os
import json

WHITELIST_FILE = os.path.join("config", "whitelist.json")

def load_whitelist():
    if not os.path.exists(WHITELIST_FILE):
        return []
    try:
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("加载白名单出错:", e)
        return []

def save_whitelist(whitelist):
    try:
        with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
            json.dump(whitelist, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("保存白名单出错:", e)

def add_whitelist(qq):
    whitelist = load_whitelist()
    if qq not in whitelist:
        whitelist.append(qq)
        save_whitelist(whitelist)
        return True
    return False

def remove_whitelist(qq):
    whitelist = load_whitelist()
    if qq in whitelist:
        whitelist.remove(qq)
        save_whitelist(whitelist)
        return True
    return False

def is_whitelisted(qq):
    whitelist = load_whitelist()
    return qq in whitelist
