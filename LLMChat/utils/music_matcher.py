"""
音乐搜索匹配算法模块。
提供了一套基于编辑距离和其他特征的音乐搜索匹配算法。
支持单个搜索和批量并行搜索。
"""

import re
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

@dataclass
class SearchQuery:
    """搜索查询数据类"""
    song_name: str
    artist_name: str
    query_id: Optional[str] = None  # 可选的查询ID，用于追踪结果

@dataclass
class SearchResult:
    """搜索结果数据类"""
    query: SearchQuery
    result: Optional[Dict[str, Any]]
    score: float
    error: Optional[str] = None

def normalize(text: str) -> str:
    """
    对文本进行标准化处理：
    1. 去除括号及其内容
    2. 去除标点符号
    3. 转换为小写
    4. 去除多余空格
    
    Args:
        text: 输入文本
        
    Returns:
        标准化后的文本
    """
    # 去除括号及其内容
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'（[^）]*）', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'【[^】]*】', '', text)
    
    # 去除标点符号
    text = re.sub(r'[^\w\s]', '', text)
    
    # 转换为小写并去除多余空格
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    
    return text

def calculate_levenshtein_distance(s1: str, s2: str) -> int:
    """
    计算两个字符串之间的编辑距离。
    
    Args:
        s1: 第一个字符串
        s2: 第二个字符串
        
    Returns:
        编辑距离值
    """
    if len(s1) < len(s2):
        return calculate_levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def calculate_song_score(
    input_song: str,
    input_artist: str,
    candidate_song: str,
    candidate_artist: str,
    popularity: int,
    weights: Tuple[float, float, float] = (0.6, 0.3, 0.1)
) -> float:
    """
    计算候选歌曲的匹配得分。
    
    Args:
        input_song: 输入的歌曲名
        input_artist: 输入的歌手名
        candidate_song: 候选歌曲名
        candidate_artist: 候选歌手名
        popularity: 歌曲热度(0-100)
        weights: 权重元组(歌手权重, 歌名权重, 热度权重)
        
    Returns:
        匹配得分(0-1之间的浮点数)
    """
    # 标准化处理
    input_song_norm = normalize(input_song)
    input_artist_norm = normalize(input_artist)
    candidate_song_norm = normalize(candidate_song)
    candidate_artist_norm = normalize(candidate_artist)
    
    # 计算歌手匹配度(AM)
    artist_match = 1.0 if input_artist_norm == candidate_artist_norm else 0.0
    
    # 计算歌名相似度(NS)
    max_len = max(len(input_song_norm), len(candidate_song_norm))
    if max_len == 0:
        name_similarity = 0.0
    else:
        edit_distance = calculate_levenshtein_distance(input_song_norm, candidate_song_norm)
        name_similarity = 1.0 - (edit_distance / max_len)
    
    # 计算热度得分(Pop)
    popularity_score = popularity / 100.0
    
    # 计算总分
    w1, w2, w3 = weights
    total_score = w1 * artist_match + w2 * name_similarity + w3 * popularity_score
    
    return total_score

async def search_music_async(
    keywords: str,
    limit: int = 30,
    session: Optional[aiohttp.ClientSession] = None,
    timeout: float = 10.0
) -> List[Dict]:
    """
    异步调用音乐搜索API。
    
    Args:
        keywords: 搜索关键词
        limit: 返回结果数量限制
        session: aiohttp会话（可选）
        timeout: 请求超时时间（秒）
        
    Returns:
        搜索结果列表
    """
    url = f"https://sicha.ltd/musicapi/search?keywords={keywords}&limit={limit}"
    
    should_close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        should_close_session = True
    
    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("result", {}).get("songs", [])
            else:
                print(f"搜索音乐时出错: HTTP {response.status}")
                return []
    except Exception as e:
        print(f"搜索音乐时发生错误: {e}")
        return []
    finally:
        if should_close_session:
            await session.close()

async def find_best_match_async(
    query: SearchQuery,
    threshold: float = 0.6,
    weights: Tuple[float, float, float] = (0.6, 0.3, 0.1),
    session: Optional[aiohttp.ClientSession] = None
) -> SearchResult:
    """
    异步查找最佳匹配的歌曲。
    
    Args:
        query: 搜索查询对象
        threshold: 匹配分数阈值
        weights: 权重配置
        session: aiohttp会话（可选）
        
    Returns:
        搜索结果对象
    """
    try:
        # 先用歌曲名搜索
        search_results = await search_music_async(query.song_name, session=session)
        
        if not search_results:
            # 如果没有结果，尝试用歌手名+歌曲名搜索
            search_results = await search_music_async(
                f"{query.artist_name} {query.song_name}",
                session=session
            )
        
        if not search_results:
            return SearchResult(query=query, result=None, score=0.0, error="未找到搜索结果")
            
        # 计算每个候选歌曲的得分
        best_score = 0
        best_match = None
        
        for song in search_results:
            # 提取候选歌曲信息
            candidate_song = song["name"]
            candidate_artist = song["artists"][0]["name"] if song["artists"] else ""
            popularity = song.get("pop", 0)
            
            # 计算匹配得分
            score = calculate_song_score(
                query.song_name,
                query.artist_name,
                candidate_song,
                candidate_artist,
                popularity,
                weights
            )
            
            # 更新最佳匹配
            if score > best_score:
                best_score = score
                best_match = song
        
        # 如果最佳匹配的分数低于阈值，返回None
        if best_score < threshold:
            return SearchResult(query=query, result=None, score=best_score, error="匹配度低于阈值")
            
        return SearchResult(query=query, result=best_match, score=best_score)
        
    except Exception as e:
        return SearchResult(query=query, result=None, score=0.0, error=str(e))

async def batch_find_best_matches(
    queries: List[SearchQuery],
    threshold: float = 0.6,
    weights: Tuple[float, float, float] = (0.6, 0.3, 0.1),
    max_concurrent: int = 5,
    timeout: float = 30.0
) -> List[SearchResult]:
    """
    批量并行查找最佳匹配的歌曲。
    
    Args:
        queries: 搜索查询列表
        threshold: 匹配分数阈值
        weights: 权重配置
        max_concurrent: 最大并发请求数
        timeout: 整体超时时间（秒）
        
    Returns:
        搜索结果列表
    """
    async with aiohttp.ClientSession() as session:
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def wrapped_find_best_match(query: SearchQuery) -> SearchResult:
            async with semaphore:
                return await find_best_match_async(
                    query,
                    threshold=threshold,
                    weights=weights,
                    session=session
                )
        
        # 创建所有任务
        tasks = [wrapped_find_best_match(query) for query in queries]
        
        try:
            # 等待所有任务完成或超时
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            # 处理结果
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    final_results.append(SearchResult(
                        query=queries[i],
                        result=None,
                        score=0.0,
                        error=str(result)
                    ))
                else:
                    final_results.append(result)
            
            return final_results
            
        except asyncio.TimeoutError:
            return [
                SearchResult(query=query, result=None, score=0.0, error="请求超时")
                for query in queries
            ]

# 为了向后兼容，保留同步版本的函数
def find_best_match(
    song_name: str,
    artist_name: str,
    threshold: float = 0.6,
    weights: Tuple[float, float, float] = (0.6, 0.3, 0.1)
) -> Optional[Dict]:
    """
    同步版本的最佳匹配查找函数。
    
    Args:
        song_name: 要搜索的歌曲名
        artist_name: 要搜索的歌手名
        threshold: 匹配分数阈值
        weights: 权重配置
        
    Returns:
        最佳匹配的歌曲信息，如果没有找到合适的匹配则返回None
    """
    query = SearchQuery(song_name=song_name, artist_name=artist_name)
    
    # 在同步环境中运行异步函数
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            find_best_match_async(query, threshold, weights)
        )
        return result.result
    finally:
        loop.close()

# 使用示例
async def example_usage():
    # 创建多个搜索查询
    queries = [
        SearchQuery("海阔天空", "Beyond", "query1"),
        SearchQuery("光辉岁月", "Beyond", "query2"),
        SearchQuery("真的爱你", "Beyond", "query3"),
    ]
    
    # 执行批量搜索
    results = await batch_find_best_matches(
        queries,
        threshold=0.6,
        max_concurrent=3
    )
    
    # 处理结果
    for result in results:
        if result.error:
            print(f"查询 {result.query.query_id} 失败: {result.error}")
        else:
            print(f"查询 {result.query.query_id} 成功: {result.result['name']} (得分: {result.score:.2f})")

if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())