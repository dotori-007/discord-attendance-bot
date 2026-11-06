import os
import json
from dataclasses import dataclass, field
from typing import Optional
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs): pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SCHEDULES_PATH = os.path.join(BASE_DIR, "schedules.json")

# Load .env file automatically
load_dotenv(ENV_PATH)

@dataclass
class RebootConfig:
    check_time: str = "09:00"
    threshold_days: int = 6

@dataclass
class BotConfig:
    bot_token: str
    target_user_id: int
    timezone: str = "Asia/Seoul"
    reboot_check: RebootConfig = field(default_factory=RebootConfig)
    ucheck_url: str = "https://ucheck.plus"
    pre_reminder_minutes: int = 0  # 0: 수업 시작 정각만, >0: 시작 N분 전 사전 알림

def load_config() -> BotConfig:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 환경 변수 우선 적용 (보안 지원)
    bot_token = os.environ.get("DISCORD_BOT_TOKEN") or data.get("bot_token", "")
    target_user_id = int(os.environ.get("DISCORD_TARGET_USER_ID") or data.get("target_user_id", 0))
    timezone = data.get("timezone", "Asia/Seoul")

    reboot_raw = data.get("reboot_check", {})
    reboot_config = RebootConfig(
        check_time=reboot_raw.get("check_time", "09:00"),
        threshold_days=int(reboot_raw.get("threshold_days", 6))
    )

    ucheck_url = data.get("ucheck_url", "https://ucheck.plus")
    pre_reminder_minutes = int(data.get("pre_reminder_minutes", 0))

    return BotConfig(
        bot_token=bot_token,
        target_user_id=target_user_id,
        timezone=timezone,
        reboot_check=reboot_config,
        ucheck_url=ucheck_url,
        pre_reminder_minutes=pre_reminder_minutes
    )

def save_config(config: BotConfig) -> None:
    data = {
        "bot_token": config.bot_token,
        "target_user_id": config.target_user_id,
        "timezone": config.timezone,
        "reboot_check": {
            "check_time": config.reboot_check.check_time,
            "threshold_days": config.reboot_check.threshold_days
        },
        "ucheck_url": config.ucheck_url,
        "pre_reminder_minutes": config.pre_reminder_minutes
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
