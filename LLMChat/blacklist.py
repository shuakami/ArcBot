import os
import json

BLACKLIST_FILE = os.path.join("config", "blacklist.json")

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("加载黑名单出错:", e)
        return []

def save_blacklist(blacklist):
    try:
        with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(blacklist, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("保存黑名单出错:", e)

def add_blacklist(qq):
    blacklist = load_blacklist()
    if qq not in blacklist:
        blacklist.append(qq)
        save_blacklist(blacklist)
        return True
    return False

def remove_blacklist(qq):
    blacklist = load_blacklist()
    if qq in blacklist:
        blacklist.remove(qq)
        save_blacklist(blacklist)
        return True
    return False

def is_blacklisted(qq):
    blacklist = load_blacklist()
    return qq in blacklist
