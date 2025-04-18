import re
import asyncio
import aiohttp
import urllib.parse
from typing import List, Optional, Dict, Any
from napcat.message_types import MessageSegment

async def fetch_music_data(session: aiohttp.ClientSession, query: str) -> MessageSegment:
    """异步从音乐API获取数据。"""
    try:
        encoded_query = urllib.parse.quote(query)
        # 使用新的 API 地址
        search_url = f"https://sicha.ltd/musicapi/cloudsearch?keywords={encoded_query}&limit=1"
        async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=5)) as response: # 设置5秒超时
            response.raise_for_status()
            data = await response.json()

            song_id = None
            if data.get("code") == 200 and isinstance(data.get("result"), dict) and isinstance(data["result"].get("songs"), list):
                songs = data["result"]["songs"]
                if songs: # 检查列表是否非空
                    first_song = songs[0]
                    if isinstance(first_song, dict):
                        song_id = first_song.get("id")

            if song_id:
                return {"type": "music", "data": {"type": "163", "id": str(song_id)}}
            else:
                print(f"音乐搜索 API 未找到歌曲或格式错误 ({query}): {data}")
                return {"type": "text", "data": {"text": f"抱歉，找不到歌曲：{query}"}}
    except aiohttp.ClientResponseError as e:
        print(f"请求音乐搜索 API 时发生客户端错误 ({query}): {e.status} {e.message}")
        return {"type": "text", "data": {"text": f"音乐服务暂时不可用喵 ({query})"}}
    except asyncio.TimeoutError:
        print(f"请求音乐搜索 API 超时: {query}")
        return {"type": "text", "data": {"text": f"音乐搜索超时了 T_T ({query})"}}
    except aiohttp.ClientError as e:
        print(f"请求音乐搜索 API 失败 ({query}): {e}")
        return {"type": "text", "data": {"text": f"音乐搜索失败了喵 T_T ({query})"}}
    except Exception as e:
        print(f"处理音乐标签时发生未知错误 ({query}): {e}")
        return {"type": "text", "data": {"text": f"处理音乐请求时出错啦 ({query})"}}

async def parse_ai_message_to_segments(text: str, current_msg_id: Optional[int] = None) -> List[MessageSegment]:
    """
    解析AI输出，将结构化标记转为MessageSegment。
    支持：
      - [reply] 或 [reply:消息ID]：回复消息
      - [@qq:QQ号] 或 [CQ:at,qq=QQ号]：@某人
      - [music:歌曲名] 或 [music:歌曲名-歌手]：自动搜索并发送音乐卡片 (并行处理)
    其余内容作为text消息段。
    """
    segments_placeholders: List[Optional[MessageSegment]] = [] # 使用Optional来放置占位符
    pattern = re.compile(
        r"(?P<reply>\[reply(?::(?P<reply_id>\d+))?])"
        r"|(?P<at1>\[@qq:(?P<at_qq1>\d+)])"
        r"|(?P<at2>\[CQ:at,qq=(?P<at_qq2>\d+)])"
        r"|(?P<music>\[music:(?P<music_query>[^\]]+)])"
    )

    last_idx = 0
    matches = list(pattern.finditer(text))
    music_tasks = []
    music_indices = {} # 存储任务索引到占位符列表索引的映射

    # 异步会话应在函数内部创建和管理
    async with aiohttp.ClientSession() as session:
        # 第一遍：处理文本段，非音乐标签，并准备音乐任务
        for i, m in enumerate(matches):
            # 添加标记前的文本段
            if m.start() > last_idx:
                seg_text = text[last_idx:m.start()].strip()
                if seg_text:
                    segments_placeholders.append({"type": "text", "data": {"text": seg_text}})

            # 处理结构化标记
            if m.group("reply"):
                reply_id = m.group("reply_id")
                segment: MessageSegment = {"type": "reply", "data": {}}
                if reply_id:
                    segment["data"]["id"] = int(reply_id)
                elif current_msg_id is not None:
                    segment["data"]["id"] = int(current_msg_id)
                else:
                    # 如果没有指定ID也没有当前消息ID，则跳过此标记
                    continue
                segments_placeholders.append(segment)
            elif m.group("at1"):
                qq = m.group("at_qq1")
                segments_placeholders.append({"type": "at", "data": {"qq": qq}})
            elif m.group("at2"):
                qq = m.group("at_qq2")
                segments_placeholders.append({"type": "at", "data": {"qq": qq}})
            elif m.group("music"):
                query = m.group("music_query").strip()
                if query:
                    # 记录占位符位置，添加任务
                    placeholder_index = len(segments_placeholders)
                    segments_placeholders.append(None) # 添加占位符
                    task_index = len(music_tasks)
                    music_tasks.append(fetch_music_data(session, query))
                    music_indices[task_index] = placeholder_index
                else:
                    segments_placeholders.append({"type": "text", "data": {"text": "[music:] 标签内容为空"}})

            last_idx = m.end()

        # 添加最后一个标记后的文本段
        if last_idx < len(text):
            seg_text = text[last_idx:].strip()
            if seg_text:
                segments_placeholders.append({"type": "text", "data": {"text": seg_text}})

        # 并发执行所有音乐任务
        if music_tasks:
            music_results = await asyncio.gather(*music_tasks, return_exceptions=True)
            # 将结果填入占位符
            for i, result in enumerate(music_results):
                placeholder_index = music_indices[i]
                if isinstance(result, Exception):
                    # 如果 gather 捕获到异常，记录错误并放入文本段
                    print(f"音乐任务执行时捕获异常: {result}")
                    segments_placeholders[placeholder_index] = {"type": "text", "data": {"text": "处理音乐请求时发生内部错误，请上报管理员喵"}}
                else:
                    segments_placeholders[placeholder_index] = result

    # 移除 None 占位符构建最终列表
    final_segments: List[MessageSegment] = [seg for seg in segments_placeholders if seg is not None]

    # 如果解析后没有任何段，添加一个空文本段避免错误
    if not final_segments:
        final_segments.append({"type": "text", "data": {"text": ""}})

    return final_segments