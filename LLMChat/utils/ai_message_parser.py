import re
from typing import List, Optional, Dict, Any
from napcat.message_types import MessageSegment

def parse_ai_message_to_segments(text: str, current_msg_id: Optional[int] = None) -> List[MessageSegment]:
    """
    解析AI输出，将结构化标记转为MessageSegment。
    支持：
      - [reply] 或 [reply:消息ID]：回复消息
      - [@qq:QQ号] 或 [CQ:at,qq=QQ号]：@某人
      - [music:平台:ID]：音乐卡片
    其余内容作为text消息段。
    """
    segments: List[MessageSegment] = []
    # 正则
    pattern = re.compile(
        # 回复
        r"(?P<reply>\[reply(?::(?P<reply_id>\d+))?])"
        # @
        r"|(?P<at1>\[@qq:(?P<at_qq1>\d+)])"
        r"|(?P<at2>\[CQ:at,qq=(?P<at_qq2>\d+)])"
        # 音乐
        r"|(?P<music>\[music:(?P<music_type>[a-zA-Z0-9]+):(?P<music_id>[a-zA-Z0-9]+)])"
    )
    last_idx = 0
    for m in pattern.finditer(text):
        # 添加标记前的文本段
        if m.start() > last_idx:
            seg_text = text[last_idx:m.start()].strip()
            if seg_text:
                segments.append({"type": "text", "data": {"text": seg_text}})
        # 处理结构化标记
        if m.group("reply"):
            reply_id = m.group("reply_id")
            if reply_id:
                segments.append({"type": "reply", "data": {"id": int(reply_id)}})
            elif current_msg_id is not None:
                segments.append({"type": "reply", "data": {"id": int(current_msg_id)}})
        elif m.group("at1"):
            qq = m.group("at_qq1")
            segments.append({"type": "at", "data": {"qq": qq}})
        elif m.group("at2"):
            qq = m.group("at_qq2")
            segments.append({"type": "at", "data": {"qq": qq}})
        elif m.group("music"):
            music_type = m.group("music_type")
            music_id = m.group("music_id")
            segments.append({"type": "music", "data": {"type": music_type, "id": music_id}})
        last_idx = m.end()
    # 添加最后一个标记后的文本段
    if last_idx < len(text):
        seg_text = text[last_idx:].strip()
        if seg_text:
            segments.append({"type": "text", "data": {"text": seg_text}})
    if not segments:
        segments.append({"type": "text", "data": {"text": text}})
    return segments 