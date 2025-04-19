import json
import os
from typing import List, Dict, Optional
import time

class AINotebook:
    def __init__(self):
        self.notebook_file = os.path.join("data", "notebook.json")
        self._ensure_notebook_file()
        self.notes = self._load_notes()
    
    def _ensure_notebook_file(self):
        """确保笔记本文件和目录存在"""
        os.makedirs(os.path.dirname(self.notebook_file), exist_ok=True)
        if not os.path.exists(self.notebook_file):
            with open(self.notebook_file, "w", encoding="utf-8") as f:
                json.dump({"notes": []}, f, ensure_ascii=False, indent=2)
    
    def _load_notes(self) -> List[Dict]:
        """加载笔记"""
        try:
            with open(self.notebook_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("notes", [])
        except Exception as e:
            print(f"加载笔记本出错: {e}")
            return []
    
    def _save_notes(self):
        """保存笔记"""
        try:
            with open(self.notebook_file, "w", encoding="utf-8") as f:
                json.dump({"notes": self.notes}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存笔记本出错: {e}")
    
    def add_note(self, content: str, context: Optional[str] = None) -> bool:
        """
        添加新笔记
        :param content: 笔记内容
        :param context: 可选的上下文信息
        :return: 是否添加成功
        """
        try:
            note = {
                "id": len(self.notes) + 1,
                "content": content,
                "context": context,
                "created_at": int(time.time())
            }
            self.notes.append(note)
            self._save_notes()
            return True
        except Exception as e:
            print(f"添加笔记失败: {e}")
            return False
    
    def get_all_notes(self) -> List[Dict]:
        """获取所有笔记"""
        return self.notes
    
    def get_notes_as_context(self) -> str:
        """将笔记转换为系统提示的上下文格式"""
        if not self.notes:
            return ""
        
        context = "以下是 Saki & Nya 之前记录下的重要信息：\n"
        for note in self.notes:
            content = note["content"]
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", 
                                     time.localtime(note["created_at"]))
            context += f"- {content}"
            
            # 如果笔记包含上下文，则添加上下文信息
            if note.get("context"):
                context += f"\n  记录这条笔记时的上下文：{note['context']}"
            
            context += f" (记录于 {created_at})\n"
            
        return context.strip()
    
    def clear_notes(self):
        """清空所有笔记"""
        self.notes = []
        self._save_notes()

# 创建全局笔记本实例
notebook = AINotebook() 