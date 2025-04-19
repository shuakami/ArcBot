import json
import os
import time
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime

class ReminderManager:
    def __init__(self):
        self.reminder_file = os.path.join("data", "reminders.json")
        self._ensure_reminder_file()
        self.reminders = self._load_reminders()
        self.process_conversation: Optional[Callable] = None
    
    def init_process_conversation(self, process_conversation_func: Callable):
        """初始化处理对话的函数"""
        self.process_conversation = process_conversation_func
        self._start_check_thread()
    
    def _start_check_thread(self):
        """启动提醒检查线程"""
        if not self.process_conversation:
            print("[Warning] 提醒检查线程未启动：process_conversation 未初始化")
            return
        threading.Thread(target=self._check_reminders, daemon=True).start()
        print("[Info] 提醒检查线程已启动")
    
    def _check_reminders(self):
        """检查并处理到期的提醒任务"""
        last_check_time = int(time.time())
        
        while True:
            try:
                current_time = int(time.time())
                
                # 如果距离上次检查超过1分钟，获取这段时间内所有到期的提醒
                if current_time - last_check_time >= 60:
                    # 获取从上次检查到现在这段时间内所有到期的提醒
                    due_reminders = [r for r in self.reminders 
                                   if last_check_time < r["trigger_time"] <= current_time]
                    
                    if due_reminders:
                        # 更新提醒列表，移除已触发的提醒
                        self.reminders = [r for r in self.reminders if r not in due_reminders]
                        self._save_reminders()
                        
                        # 处理到期的提醒
                        for reminder in due_reminders:
                            try:
                                # 构建系统提示消息
                                system_message = {
                                    "role": "system",
                                    "content": f"现在是 {time.strftime('%Y-%m-%d %H:%M:%S')}，系统自动触发了你之前设置的提醒。\n"
                                              f"你自己设计的提醒原因：{reminder['reason']}\n"
                                              + (f"相关上下文：\n{reminder['context']}" if reminder.get('context') else "")
                                }
                                
                                # 调用对话处理函数发送提醒
                                if self.process_conversation:
                                    for segment in self.process_conversation(
                                        reminder['chat_id'],
                                        system_message['content'],
                                        chat_type=reminder['chat_type']
                                    ):
                                        pass  # 等待所有消息段处理完成
                            except Exception as e:
                                print(f"处理单个提醒任务时出错: {e}")
                                continue
                    
                    # 更新上次检查时间
                    last_check_time = current_time
                
                # 计算到下一分钟的等待时间
                next_minute = (current_time // 60 + 1) * 60
                wait_time = max(0.1, next_minute - time.time())  # 至少等待0.1秒，避免CPU空转
                time.sleep(wait_time)
                
            except Exception as e:
                print(f"提醒检查循环出错: {e}")
                # 发生错误时，等待1秒后继续
                time.sleep(1)
                # 重置上次检查时间，避免遗漏
                last_check_time = int(time.time()) - 65  # 稍微回退一点，确保不会遗漏
    
    def _ensure_reminder_file(self):
        """确保提醒文件和目录存在"""
        os.makedirs(os.path.dirname(self.reminder_file), exist_ok=True)
        if not os.path.exists(self.reminder_file):
            with open(self.reminder_file, "w", encoding="utf-8") as f:
                json.dump({"reminders": []}, f, ensure_ascii=False, indent=2)
    
    def _load_reminders(self) -> List[Dict]:
        """加载提醒任务"""
        try:
            with open(self.reminder_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("reminders", [])
        except Exception as e:
            print(f"加载提醒任务出错: {e}")
            return []
    
    def _save_reminders(self):
        """保存提醒任务"""
        try:
            with open(self.reminder_file, "w", encoding="utf-8") as f:
                json.dump({"reminders": self.reminders}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存提醒任务出错: {e}")
    
    def add_reminder(self, trigger_time: int, reason: str, chat_id: str, chat_type: str, context: Optional[str] = None) -> bool:
        """
        添加新提醒任务
        :param trigger_time: 触发时间戳
        :param reason: 提醒原因
        :param chat_id: 群ID或私聊ID
        :param chat_type: 聊天类型 ("group" 或 "private")
        :param context: 可选的上下文信息
        :return: 是否添加成功
        """
        try:
            reminder = {
                "id": len(self.reminders) + 1,
                "trigger_time": trigger_time,
                "reason": reason,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "context": context,
                "created_at": int(time.time())
            }
            self.reminders.append(reminder)
            self._save_reminders()
            return True
        except Exception as e:
            print(f"添加提醒任务失败: {e}")
            return False
    
    def get_due_reminders(self) -> List[Dict]:
        """获取所有到期的提醒任务"""
        current_time = int(time.time())
        due_reminders = []
        remaining_reminders = []
        
        for reminder in self.reminders:
            if reminder["trigger_time"] <= current_time:
                due_reminders.append(reminder)
            else:
                remaining_reminders.append(reminder)
        
        # 更新提醒列表，移除已触发的提醒
        if due_reminders:
            self.reminders = remaining_reminders
            self._save_reminders()
        
        return due_reminders
    
    def get_all_reminders(self) -> List[Dict]:
        """获取所有提醒任务"""
        return self.reminders
    
    def clear_reminders(self):
        """清空所有提醒任务"""
        self.reminders = []
        self._save_reminders()

# 创建全局单例实例
reminder_manager = ReminderManager() 