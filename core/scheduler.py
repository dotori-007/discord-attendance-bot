import os
import json
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.config import SCHEDULES_PATH, BotConfig

class ScheduleManager:
    def __init__(self, scheduler: AsyncIOScheduler):
        self.scheduler = scheduler
        self.schedules: List[Dict[str, Any]] = []

    def load_schedules(self) -> List[Dict[str, Any]]:
        if not os.path.exists(SCHEDULES_PATH):
            self.schedules = []
            return self.schedules

        try:
            with open(SCHEDULES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.schedules = data
            else:
                self.schedules = []
        except Exception as e:
            print(f"[스케줄 오류] schedules.json 로드 실패: {e}")
            self.schedules = []
        return self.schedules

    def save_schedules(self, schedules: Optional[List[Dict[str, Any]]] = None) -> bool:
        if schedules is not None:
            self.schedules = schedules
        try:
            with open(SCHEDULES_PATH, "w", encoding="utf-8") as f:
                json.dump(self.schedules, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[스케줄 오류] schedules.json 저장 실패: {e}")
            return False

    def add_schedule(self, item: Dict[str, Any]) -> bool:
        # Check duplicate ID
        for s in self.schedules:
            if s.get("id") == item.get("id"):
                return False
        self.schedules.append(item)
        return self.save_schedules()

    def delete_schedule(self, schedule_id: str) -> bool:
        original_len = len(self.schedules)
        self.schedules = [s for s in self.schedules if s.get("id") != schedule_id]
        if len(self.schedules) < original_len:
            self.save_schedules()
            # Remove job from scheduler if registered
            if self.scheduler.get_job(schedule_id):
                self.scheduler.remove_job(schedule_id)
            pre_id = f"pre_{schedule_id}"
            if self.scheduler.get_job(pre_id):
                self.scheduler.remove_job(pre_id)
            return True
        return False
