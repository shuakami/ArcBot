import re
import requests
import urllib.parse
from typing import List, Optional, Dict, Any
from napcat.message_types import MessageSegment

def parse_ai_message_to_segments(text: str, current_msg_id: Optional[int] = None) -> List[MessageSegment]:
    """
    解析AI输出，将结构化标记转为MessageSegment。
    支持：
      - [reply] 或 [reply:消息ID]：回复消息
      - [@qq:QQ号] 或 [CQ:at,qq=QQ号]：@某人
      - [music:歌曲名或歌手名]：自动搜索并发送音乐卡片
    其余内容作为text消息段。
    """
    segments: List[MessageSegment] = []
    pattern = re.compile(
        # 回复
        r"(?P<reply>\[reply(?::(?P<reply_id>\d+))?])"
        # @
        r"|(?P<at1>\[@qq:(?P<at_qq1>\d+)])"
        r"|(?P<at2>\[CQ:at,qq=(?P<at_qq2>\d+)])"
        # 音乐
        r"|(?P<music>\[music:(?P<music_query>[^\]]+)])"
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
            query = m.group("music_query").strip()
            if query:
                try:
                    encoded_query = urllib.parse.quote(query)
                    search_url = f"https://music-api.sdjz.wiki/search?keywords={encoded_query}&limit=1"
                    response = requests.get(search_url, timeout=5) # 5秒超时
                    response.raise_for_status()
                    data = response.json()

                    # 安全地提取歌曲ID
                    song_id = None
                    if data.get("code") == 200 and data.get("result", {}).get("songs"): # 检查code和列表
                         songs = data["result"]["songs"]
                         if songs and isinstance(songs, list) and len(songs) > 0: # 再次检查列表非空
                             first_song = songs[0]
                             if isinstance(first_song, dict):
                                 song_id = first_song.get("id")

                    if song_id:
                        segments.append({"type": "music", "data": {"type": "163", "id": str(song_id)}})
                    else:
                        print(f"音乐搜索 API 未找到歌曲或格式错误: {query}")
                        segments.append({"type": "text", "data": {"text": f"抱歉，找不到歌曲：{query}"}}) 
                except requests.exceptions.RequestException as e:
                    print(f"请求音乐搜索 API 失败: {e}")
                    segments.append({"type": "text", "data": {"text": f"音乐搜索失败了喵 T_T ({query})"}}) 
                except Exception as e:
                    print(f"处理音乐标签时发生未知错误: {e}")
                    segments.append({"type": "text", "data": {"text": f"处理音乐请求时出错啦 ({query})"}}) 
            else:
                 segments.append({"type": "text", "data": {"text": "[music:] 标签内容为空"}})

        last_idx = m.end()

    # 添加最后一个标记后的文本段
    if last_idx < len(text):
        seg_text = text[last_idx:].strip()
        if seg_text:
            segments.append({"type": "text", "data": {"text": seg_text}})

    # 如果解析后没有任何段（例如原始文本就是空的），添加一个空文本段避免错误
    if not segments:
        segments.append({"type": "text", "data": {"text": ""}})

    return segments