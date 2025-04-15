"""
消息段类型声明：用于描述QQ机器人API支持的所有消息类型。
每个消息段为一个dict，包含 type（消息类型）和 data（类型相关数据）字段。

MessageSegment 是所有消息段类型的联合类型。

常见用法：
- 文本消息：{"type": "text", "data": {"text": "内容"}}
- @某人：{"type": "at", "data": {"qq": "QQ号"}}
- 图片：{"type": "image", "data": {"file": "图片URL或路径"}}
- 表情：{"type": "face", "data": {"id": 表情ID}}
- JSON卡片：{"type": "json", "data": {"data": "json字符串"}}
- 语音：{"type": "record", "data": {"file": "语音文件路径"}}
- 视频：{"type": "video", "data": {"file": "视频文件路径"}}
- 回复：{"type": "reply", "data": {"id": 消息ID}}
- 音乐：{"type": "music", "data": {"type": "qq"/"163"等, "id": "音乐ID"}}
- 文件：{"type": "file", "data": {"file": "文件路径或URL"}}
- 节点：{"type": "node", "data": {"user_id": "QQ号", "nickname": "昵称", "content": [MessageSegment, ...]}}

详见每个类型的注释。
"""
from typing import TypedDict, Literal, Union, List, Optional

class TextSegment(TypedDict):
    type: Literal["text"]
    data: dict  # {"text": str}  # 文本内容

class AtSegment(TypedDict):
    type: Literal["at"]
    data: dict  # {"qq": str}  # 被@的QQ号

class ImageSegment(TypedDict):
    type: Literal["image"]
    data: dict  # {"file": str}  # 图片文件路径、URL或base64

class FaceSegment(TypedDict):
    type: Literal["face"]
    data: dict  # {"id": int}  # QQ表情ID

class JsonSegment(TypedDict):
    type: Literal["json"]
    data: dict  # {"data": str}  # JSON卡片内容，字符串格式

class RecordSegment(TypedDict):
    type: Literal["record"]
    data: dict  # {"file": str}  # 语音文件路径、URL或base64

class VideoSegment(TypedDict):
    type: Literal["video"]
    data: dict  # {"file": str}  # 视频文件路径、URL或base64

class ReplySegment(TypedDict):
    type: Literal["reply"]
    data: dict  # {"id": int}  # 被回复的消息ID

class MusicSegment(TypedDict):
    type: Literal["music"]
    data: dict  # {"type": str, "id": str}  # type: "qq"/"163"/"xm"等，id:音乐ID

class DiceSegment(TypedDict):
    type: Literal["dice"]
    data: dict  # {}  # 掷骰子，无需额外参数

class RpsSegment(TypedDict):
    type: Literal["rps"]
    data: dict  # {}  # 猜拳，无需额外参数

class FileSegment(TypedDict):
    type: Literal["file"]
    data: dict  # {"file": str}  # 文件路径或URL

class NodeSegment(TypedDict):
    type: Literal["node"]
    data: dict  # {"user_id": str, "nickname": str, "content": List[MessageSegment]}  # 消息节点（转发消息）

MessageSegment = Union[
    TextSegment, AtSegment, ImageSegment, FaceSegment, JsonSegment, RecordSegment, VideoSegment,
    ReplySegment, MusicSegment, DiceSegment, RpsSegment, FileSegment, NodeSegment
] 