import asyncio
import os
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import load_config, BotConfig
from core.scheduler import ScheduleManager
from cogs.attendance import AttendanceCog
from cogs.monitoring import MonitoringCog

# ==========================================
# 1. 봇 및 스케줄러 환경 초기화
# ==========================================
config: BotConfig = load_config()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()
schedule_mgr = ScheduleManager(scheduler)

attendance_cog = AttendanceCog(bot, config, schedule_mgr)
monitoring_cog = MonitoringCog(bot, config, schedule_mgr)

# ==========================================
# 2. 봇 이벤트 핸들러
# ==========================================
@bot.event
async def on_ready():
    print("=" * 45)
    print(f"🤖 봇 로그인 완료: {bot.user.name} ({bot.user.id})")
    print(f"타깃 유저 ID: {config.target_user_id}")
    print("=" * 45)

    # 슬래시 커맨드 동기화
    try:
        synced = await bot.tree.sync()
        print(f"[시스템] 슬래시 커맨드 {len(synced)}개 글로벌 동기화 완료")
    except Exception as e:
        print(f"[오류] 슬래시 커맨드 동기화 실패: {e}")

    # 스케줄러 초기화 및 작업 등록
    scheduler.remove_all_jobs()
    attendance_cog.sync_scheduler_jobs()
    monitoring_cog.register_uptime_check()

    if not scheduler.running:
        scheduler.start()
        print("[시스템] APScheduler 비동기 엔진 가동 완료")

# ==========================================
# 3. 메인 실행 루틴
# ==========================================
async def main():
    async with bot:
        # Cogs 등록
        await bot.add_cog(attendance_cog)
        await bot.add_cog(monitoring_cog)
        
        # 슬래시 커맨드 트리 연결
        bot.tree.add_command(monitoring_cog.test_command)
        bot.tree.add_command(monitoring_cog.status_command)
        bot.tree.add_command(attendance_cog.schedule_group)

        # 봇 실행
        await bot.start(config.bot_token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[시스템] 봇 프로세스가 사용자에 의해 종료되었습니다.")
