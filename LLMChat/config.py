import json
import os

CONFIG_PATH = os.path.join("config", "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)
