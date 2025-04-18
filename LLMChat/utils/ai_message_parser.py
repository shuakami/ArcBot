import re
import asyncio
from typing import List, Optional, Dict, Any
from napcat.message_types import MessageSegment
from utils.music_matcher import SearchQuery, find_best_match_async

async def parse_ai_message_to_segments(text: str, current_msg_id: Optional[int] = None) -> List[MessageSegment]:
    """
    解析AI输出，将结构化标记转为MessageSegment。
    支持：
      - [reply] 或 [reply:消息ID]：回复消息
      - [@qq:QQ号] 或 [CQ:at,qq=QQ号]：@某人
      - [music:歌曲名-歌手]：自动搜索并发送音乐卡片
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
                    # 解析歌曲名和歌手
                    song_parts = query.split('-', 1)
                    if len(song_parts) == 2:
                        song_name = song_parts[0].strip()
                        artist_name = song_parts[1].strip()
                        
                        # 创建搜索查询
                        search_query = SearchQuery(song_name=song_name, artist_name=artist_name)
                        
                        # 执行异步搜索
                        result = await find_best_match_async(search_query)
                        
                        if result.result and not result.error:
                            song_id = result.result.get("id")
                            if song_id:
                                segments.append({"type": "music", "data": {"type": "163", "id": str(song_id)}})
                            else:
                                segments.append({"type": "text", "data": {"text": f"抱歉，无法获取歌曲ID：{query}"}})
                        else:
                            segments.append({"type": "text", "data": {"text": f"抱歉，找不到歌曲：{query}"}})
                    else:
                        segments.append({"type": "text", "data": {"text": f"音乐标记格式错误，请使用'歌曲名-歌手'格式"}})
                except Exception as e:
                    print(f"处理音乐标签时发生错误: {e}")
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