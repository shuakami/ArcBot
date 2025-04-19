import asyncio
import aiohttp
import urllib.parse
from typing import Dict, Any
from napcat.message_types import MessageSegment

async def fetch_music_data(session: aiohttp.ClientSession, query: str, max_retries: int = 1) -> MessageSegment:
    """
    异步从音乐API获取数据，支持自动重试。
    
    Args:
        session (aiohttp.ClientSession): aiohttp会话
        query (str): 搜索查询，支持 "歌手-歌曲" 或 "歌曲" 格式
        max_retries (int, optional): 最大重试次数. 默认为 1.
        
    Returns:
        MessageSegment: 音乐消息段或错误文本消息段
    """
    retries = 0
    last_error = None
    
    # 解析查询字符串，分离歌手和歌曲名
    parts = query.split('-', 1)
    target_song = parts[1].strip() if len(parts) > 1 else query.strip()
    target_artist = parts[0].strip() if len(parts) > 1 else None
    
    while retries <= max_retries:
        try:
            print(f"[Debug] Music Fetch: Querying for '{query}' (attempt {retries + 1}/{max_retries + 1})") 
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://sicha.ltd/musicapi/cloudsearch?keywords={encoded_query}&limit=20"
            print(f"[Debug] Music Fetch: Requesting URL: {search_url}")
            
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                print(f"[Debug] Music Fetch: Received status {response.status} for query '{query}'")
                response.raise_for_status()
                data = await response.json()
                print(f"[Debug] Music Fetch: Received data for '{query}': {data}")

                if data.get("code") == 200 and isinstance(data.get("result"), dict) and isinstance(data["result"].get("songs"), list):
                    songs = data["result"]["songs"]
                    if songs:
                        # 计算每首歌的匹配得分
                        scored_songs = []
                        for song in songs:
                            score = 0
                            song_name = song.get("name", "").lower()
                            popularity = song.get("pop", 0)
                            
                            # 如果有指定歌手，考虑歌手匹配度
                            if target_artist:
                                artists = [ar.get("name", "").lower() for ar in song.get("ar", [])]
                                target_artist_lower = target_artist.lower()
                                if any(target_artist_lower == artist for artist in artists):
                                    score += 1000  # 完全匹配
                                elif any(target_artist_lower in artist for artist in artists):
                                    score += 500   # 部分匹配
                            
                            # 歌曲名匹配得分（主要权重）
                            target_song_lower = target_song.lower()
                            if target_song_lower == song_name:
                                score += 500 if not target_artist else 100  # 没有歌手时提高歌曲名匹配权重
                            elif target_song_lower in song_name:
                                score += 250 if not target_artist else 50   # 没有歌手时提高部分匹配权重
                            
                            # 热度得分（次要权重）
                            normalized_popularity = min(popularity, 100) / 100
                            score += normalized_popularity * (50 if not target_artist else 1)  # 没有歌手时提高热度权重
                            
                            scored_songs.append((score, song))
                            print(f"[Debug] Music Score: '{song_name}' by {song.get('ar', [])} - Score: {score} (Pop: {popularity})")
                        
                        # 按得分降序排序
                        scored_songs.sort(key=lambda x: x[0], reverse=True)
                        best_match = scored_songs[0][1]
                        
                        result_segment = {"type": "music", "data": {"type": "163", "id": str(best_match["id"])}}
                        print(f"[Debug] Music Fetch: Success for '{query}', returning music segment with score {scored_songs[0][0]}")
                        return result_segment
                    else:
                        print(f"[Debug] Music Fetch: No songs found for '{query}'.")
                        return {"type": "text", "data": {"text": f"抱歉，找不到歌曲：{query} 喵。再试一次呗~"}}
                else:
                    print(f"[Debug] Music Fetch: API format error for '{query}'.")
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