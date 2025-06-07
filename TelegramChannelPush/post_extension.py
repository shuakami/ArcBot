import json
import requests

def load_config(config_path='config.json'):
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config()
post_url = config.get("napcat_url", "")
post_token = config.get("napcat_token", "")
post_group_ids = config.get("napcat_group_ids", [])

def send_msg_to_group(text, time_str, base64_list):
    """
    向指定 URL 发送包含多张图片 + 文本的请求。

    - text:      TG 消息文本
    - time_str:  消息时间（字符串）
    - base64_list: 收到的所有图片 base64 列表，如果无图片则为空列表
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {post_token}"
    }

    # 构造多张图片消息
    # 每张图片一个元素 {"type": "image", "data": {"file": "data:image/jpeg;base64,..."}}
    images_part = []
    for b64_str in base64_list:
        images_part.append({
            "type": "image",
            "data": {
                "file": f"data:image/jpeg;base64,{b64_str}"
            }
        })

    # 文本部分（示例里将TG文本与时间合并成一个字符串）
    text_part = {
        "type": "text",
        "data": {
            "text": f"{text}\n\n发布时间：{time_str}\n信息来源: @{config.get('channel_username', '')}"
        }
    }

    # 将所有图片元素 + 文本元素 组成一个列表
    message_list = images_part + [text_part]

    # 依次发送到每个群
    for group_id in post_group_ids:
        body = {
            "group_id": group_id,
            "message": message_list
        }
        try:
            resp = requests.post(post_url, headers=headers, data=json.dumps(body))
            print(f"已向群 {group_id} 发送消息，状态码：{resp.status_code}，返回：{resp.text}")
        except Exception as e:
            print(f"发送到群 {group_id} 时出现异常：{e}")