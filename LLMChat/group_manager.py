import json
import os

GROUP_CONFIG_PATH = os.path.join("config", "groups.json")

def _load_groups():
    try:
        with open(GROUP_CONFIG_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def _save_groups(groups):
    with open(GROUP_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(list(groups), f, indent=4)

enabled_groups = _load_groups()

def is_group_enabled(group_id):
    return str(group_id) in enabled_groups

def enable_group(group_id):
    group_id_str = str(group_id)
    if group_id_str not in enabled_groups:
        enabled_groups.add(group_id_str)
        _save_groups(enabled_groups)
        return True
    return False

def disable_group(group_id):
    group_id_str = str(group_id)
    if group_id_str in enabled_groups:
        enabled_groups.remove(group_id_str)
        _save_groups(enabled_groups)
        return True
    return False

def get_enabled_groups():
    return list(enabled_groups) 