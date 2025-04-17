"""
群聊消息内容解析与富媒体处理工具
- 支持图片、表情包检测与描述
- 可扩展更多类型
"""
from typing import Dict, Any, List
from llm_api import get_ai_response_with_image
import os

def describe_image(image_url: str) -> str:
    """
    识图接口：根据图片URL返回图片内容描述。
    使用 LLM 多模态接口，加载 config/image_system_prompt.txt 作为 prompt。
    """
    prompt_path = os.path.join(os.path.dirname(__file__), '../config/image_system_prompt.txt')
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read().strip()
    except Exception as e:
        system_prompt = "请用中文描述这张图片的内容。"
    # 构造 LLM 对话
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请用中文描述这张图片的内容。"}
    ]
    try:
        desc = get_ai_response_with_image(conversation, image=image_url, image_type="url")
        return f"[图片内容描述: {desc.strip()}]"
    except Exception as e:
        return f"[图片内容描述获取失败]"

def get_mface_description(mface_data: dict) -> str:
    """
    表情包描述接口：先用 summary 字段（如有），再用 LLM 识别表情包图片内容，两者拼接。
    """
    summary = mface_data.get("summary")
    desc_parts = []
    if summary:
        desc_parts.append(f"[表情包: {summary}]")
    # 获取图片url/file字段
    url = mface_data.get("url") or mface_data.get("file")
    if url:
        desc_parts.append(describe_image(url))
    return " ".join(desc_parts) if desc_parts else "[表情包]"

def parse_group_message_content(msg_dict: Dict[str, Any]) -> str:
    """
    解析群聊消息内容，拼接图片/表情包描述和用户文本。
    返回：图片描述+表情包描述+用户文本
    """
    message_segments: List[Dict[str, Any]] = msg_dict.get("message", [])
    text_parts = []
    image_descs = []
    mface_descs = []
    for seg in message_segments:
        seg_type = seg.get("type")
        data = seg.get("data", {})
        if seg_type == "text":
            text_parts.append(data.get("text", ""))
        elif seg_type == "image":
            # 取图片URL/路径
            url = data.get("url") or data.get("file")
            if url:
                image_descs.append(describe_image(url))
        elif seg_type == "mface":
            mface_descs.append(get_mface_description(data))
        elif seg_type == "face":
            # QQ原生表情可选处理
            face_id = data.get("id")
            if face_id:
                mface_descs.append(f"[QQ表情:{face_id}]")
    # 拼接顺序：图片描述 + 表情包描述 + 用户文本
    return " ".join(image_descs + mface_descs + text_parts).strip() 