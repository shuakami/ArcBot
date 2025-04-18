"""
群聊消息内容解析与富媒体处理工具
- 支持图片、表情包检测与描述
- 可扩展更多类型
"""
from typing import Dict, Any, List
from llm_api import get_ai_response_with_image
import os
import requests
import tempfile

def describe_image(image_source: str, image_type: str = "url") -> str:
    """
    识图接口：根据图片来源(URL或路径)返回描述。
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
        desc = get_ai_response_with_image(conversation, image=image_source, image_type=image_type)
        return f"[图片内容描述: {desc.strip()}]"
    except Exception as e:
        # 返回包含具体错误信息的字符串
        return f"[图片内容描述获取失败: {str(e)}]"

def get_mface_description(mface_data: dict) -> str:
    """
    表情包描述接口（旧逻辑，仅处理URL）。
    """
    summary = mface_data.get("summary")
    desc_parts = []
    if summary:
        desc_parts.append(f"[表情包: {summary}]")
    url = mface_data.get("url") # 旧逻辑只处理url
    if url:
        desc_parts.append(describe_image(url, image_type="url")) # 明确是url
    return " ".join(desc_parts) if desc_parts else "[表情包]"

def parse_group_message_content(msg_dict: Dict[str, Any]) -> str:
    """
    解析群聊消息内容，拼接图片/表情包描述和用户文本。
    优先使用file字段，若无效则尝试下载url到临时文件再识别。
    """
    message_segments: List[Dict[str, Any]] = msg_dict.get("message", [])
    text_parts = []
    image_descs = []
    mface_descs = []
    temp_files_to_delete = [] # 记录需要删除的临时文件

    for seg in message_segments:
        seg_type = seg.get("type")
        data = seg.get("data", {})
        temp_file_path = None # 当前循环的临时文件路径

        try:
            if seg_type == "text":
                text_parts.append(data.get("text", ""))
            elif seg_type == "image" or seg_type == "mface":
                image_source_path = None
                is_temp_file = False

                # 1. 优先尝试 file 字段
                file_path = data.get("file")
                if file_path and os.path.exists(file_path): # 简单检查路径是否存在
                    image_source_path = file_path
                else:
                    # 2. file 无效，尝试 url 下载
                    url = data.get("url")
                    if url:
                        try:
                            response = requests.get(url, stream=True, timeout=10) # 增加超时
                            response.raise_for_status() # 检查HTTP错误
                            # 创建临时文件
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    temp_f.write(chunk)
                                temp_file_path = temp_f.name
                                temp_files_to_delete.append(temp_file_path) # 加入待删除列表
                                image_source_path = temp_file_path
                                is_temp_file = True
                        except requests.exceptions.RequestException as req_e:
                            print(f"下载图片URL失败: {url}, Error: {req_e}")
                        except IOError as io_e:
                            print(f"写入临时文件失败: {io_e}")
                        except Exception as down_e: # 其他下载或文件操作异常
                            print(f"处理图片URL时发生未知错误: {url}, Error: {down_e}")

                # 3. 如果获取到有效图片源（本地或临时文件），进行描述
                if image_source_path:
                    desc = describe_image(image_source_path, image_type="file")
                    if seg_type == "image":
                        image_descs.append(desc)
                    elif seg_type == "mface":
                         summary = data.get("summary")
                         mface_part = f"[表情包: {summary}] {desc}" if summary else desc
                         mface_descs.append(mface_part)

            elif seg_type == "face":
                # QQ原生表情可选处理
                face_id = data.get("id")
                if face_id:
                    mface_descs.append(f"[QQ表情:{face_id}]")

        except Exception as e:
             print(f"处理消息段时出错: {seg}, Error: {e}")
             # 如果当前循环创建了临时文件，确保它被标记为删除
             if temp_file_path and temp_file_path not in temp_files_to_delete:
                 temp_files_to_delete.append(temp_file_path)

    # 函数结束前，清理所有本次创建的临时文件
    for f_path in temp_files_to_delete:
        try:
            os.remove(f_path)
        except OSError as e:
            print(f"删除临时文件失败: {f_path}, Error: {e}")

    return " ".join(image_descs + mface_descs + text_parts).strip() 