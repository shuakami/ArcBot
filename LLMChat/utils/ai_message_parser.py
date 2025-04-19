import re
import asyncio
import aiohttp
import urllib.parse
from typing import List, Optional, Dict, Any
from napcat.message_types import MessageSegment
from utils.notebook import notebook
from utils.files import load_conversation_history

async def fetch_music_data(session: aiohttp.ClientSession, query: str, max_retries: int = 1) -> MessageSegment:
    """异步从音乐API获取数据，支持自动重试。"""
    retries = 0
    last_error = None
    
    while retries <= max_retries:
        try:
            print(f"[Debug] Music Fetch: Querying for '{query}' (attempt {retries + 1}/{max_retries + 1})") 
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://sicha.ltd/musicapi/cloudsearch?keywords={encoded_query}&limit=1"
            print(f"[Debug] Music Fetch: Requesting URL: {search_url}")
            
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                print(f"[Debug] Music Fetch: Received status {response.status} for query '{query}'")
                response.raise_for_status()
                data = await response.json()
                print(f"[Debug] Music Fetch: Received data for '{query}': {data}")

                song_id = None
                if data.get("code") == 200 and isinstance(data.get("result"), dict) and isinstance(data["result"].get("songs"), list):
                    songs = data["result"]["songs"]
                    if songs:
                        first_song = songs[0]
                        if isinstance(first_song, dict):
                            song_id = first_song.get("id")

                if song_id:
                    result_segment = {"type": "music", "data": {"type": "163", "id": str(song_id)}}
                    print(f"[Debug] Music Fetch: Success for '{query}', returning music segment.")
                    return result_segment
                else:
                    print(f"[Debug] Music Fetch: Song ID not found or API format error for '{query}'.")
                    return {"type": "text", "data": {"text": f"抱歉，找不到歌曲：{query} 喵。再试一次呗~"}}
                    
        except (aiohttp.ClientResponseError, asyncio.TimeoutError, aiohttp.ClientError) as e:
            last_error = e
            retries += 1
            if retries <= max_retries:
                print(f"[Warning] Music Fetch: Error on attempt {retries}/{max_retries + 1} for '{query}': {e}")
                await asyncio.sleep(1)  # 重试前等待1秒
                continue
            else:
                print(f"[Error] Music Fetch: All retry attempts failed for '{query}': {e}")
                if isinstance(e, aiohttp.ClientResponseError):
                    return {"type": "text", "data": {"text": f"音乐服务暂时不可用喵 ({query})"}}
                elif isinstance(e, asyncio.TimeoutError):
                    return {"type": "text", "data": {"text": f"音乐搜索超时了 T_T ({query})"}}
                else:
                    return {"type": "text", "data": {"text": f"音乐搜索失败了喵 T_T ({query})"}}
        except Exception as e:
            print(f"[Error] Music Fetch: Unknown error processing query '{query}': {e}")
            return {"type": "text", "data": {"text": f"处理音乐请求时出错啦 ({query})"}}

async def parse_ai_message_to_segments(text: str, current_msg_id: Optional[int] = None, chat_id: Optional[str] = None, chat_type: str = "private") -> List[MessageSegment]:
    """
    解析AI输出，将结构化标记转为MessageSegment。
    支持：
      - [reply] 或 [reply:消息ID]：回复消息
      - [@qq:QQ号] 或 [CQ:at,qq=QQ号]：@某人
      - [music:歌曲名] 或 [music:歌曲名-歌手]：自动搜索并发送音乐卡片 (并行处理)
      - [note:内容] 或 [note:内容:context]：静默记录笔记（不会发送任何消息）
        如果带有:context参数，会自动保存最近5条对话作为上下文
    其余内容作为text消息段。
    """
    print(f"[Debug] AI Parser: Received raw text: {text}")
    segments_placeholders: List[Optional[MessageSegment]] = []
    pattern = re.compile(
        r"(?P<reply>\[reply(?::(?P<reply_id>\d+))?])"
        r"|(?P<at1>\[@qq:(?P<at_qq1>\d+)])"
        r"|(?P<at2>\[CQ:at,qq=(?P<at_qq2>\d+)])"
        r"|(?P<music>\[music:(?P<music_query>[^\]]+)])"
        r"|(?P<note>\[note:(?P<note_content>[^:\]]+)(?::(?P<note_context>context))?\])"
    )

    def get_recent_context(chat_id: str, chat_type: str) -> Optional[str]:
        """获取最近5条对话作为上下文"""
        if not chat_id:
            return None
            
        try:
            history = load_conversation_history(chat_id, chat_type)
            if not history:
                return None
                
            # 过滤掉系统消息，只保留用户和助手的对话
            dialog = [msg for msg in history if msg["role"] != "system"]
            # 获取最后5条消息
            recent = dialog[-5:] if len(dialog) > 5 else dialog
            
            context = []
            for msg in recent:
                role = "用户" if msg["role"] == "user" else "AI"
                content = msg["content"]
                context.append(f"{role}: {content}")
                
            return "\n".join(context)
        except Exception as e:
            print(f"获取对话上下文失败: {e}")
            return None

    last_idx = 0
    matches = list(pattern.finditer(text))
    music_tasks = []
    music_indices = {}

    async with aiohttp.ClientSession() as session:
        for i, m in enumerate(matches):
            if m.start() > last_idx:
                seg_text = text[last_idx:m.start()].strip()
                if seg_text:
                    segments_placeholders.append({"type": "text", "data": {"text": seg_text}})

            if m.group("reply"):
                reply_id = m.group("reply_id")
                segment: MessageSegment = {"type": "reply", "data": {}}
                if reply_id:
                    segment["data"]["id"] = int(reply_id)
                elif current_msg_id is not None:
                    segment["data"]["id"] = int(current_msg_id)
                else:
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
                    placeholder_index = len(segments_placeholders)
                    segments_placeholders.append(None)
                    task_index = len(music_tasks)
                    music_tasks.append(fetch_music_data(session, query))
                    music_indices[task_index] = placeholder_index
                else:
                    segments_placeholders.append({"type": "text", "data": {"text": "[music:] 标签内容为空"}})
            elif m.group("note"):
                note_content = m.group("note_content").strip()
                if note_content:
                    context = None
                    if m.group("note_context") == "context" and chat_id:
                        context = get_recent_context(chat_id, chat_type)
                    notebook.add_note(note_content, context)

            last_idx = m.end()

        if last_idx < len(text):
            seg_text = text[last_idx:].strip()
            if seg_text:
                segments_placeholders.append({"type": "text", "data": {"text": seg_text}})

        if music_tasks:
            music_results = await asyncio.gather(*music_tasks, return_exceptions=True)
            for i, result in enumerate(music_results):
                placeholder_index = music_indices[i]
                if isinstance(result, Exception):
                    print(f"音乐任务执行时捕获异常: {result}")
                    segments_placeholders[placeholder_index] = {"type": "text", "data": {"text": "处理音乐请求时发生内部错误，请上报管理员喵"}}
                else:
                    segments_placeholders[placeholder_index] = result

    final_segments: List[MessageSegment] = [seg for seg in segments_placeholders if seg is not None]

    if not final_segments:
        final_segments.append({"type": "text", "data": {"text": ""}})

    return final_segments