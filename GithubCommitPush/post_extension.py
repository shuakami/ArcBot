import json
import requests

def load_config(config_path='config.json'):
    """读取配置文件并返回字典对象"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config()

post_url = config.get("napcat_url", "")
post_token = config.get("napcat_token", "")
post_group_ids = config.get("napcat_group_ids", [])

def send_msg_to_group(text, time_str):
    """
    将文本发送到配置的多个群。
    - text:     文本信息
    - time_str: 时间字符串（仅作附加说明）
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {post_token}"
    }

    # 构造要发送的文本
    message_part = [
        {
            "type": "text",
            "data": {
                "text": f"{text}\n\n时间：{time_str}\n"
            }
        }
    ]

    # 依次发送到每个群
    for group_id in post_group_ids:
        body = {
            "group_id": group_id,
            "message": message_part
        }
        try:
            resp = requests.post(post_url, headers=headers, data=json.dumps(body))
            print(f"已向群 {group_id} 发送消息，返回码：{resp.status_code}，返回：{resp.text}")
        except Exception as e:
            print(f"发送到群 {group_id} 时出现异常：{e}")
