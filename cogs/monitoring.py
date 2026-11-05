import time
import os
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord import app_commands
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import psutil

from core.config import BotConfig
from core.scheduler import ScheduleManager

BOT_START_TIME = time.time()

class MonitoringCog(commands.Cog, name="시스템 모니터링 및 진단"):
    def __init__(self, bot: commands.Bot, config: BotConfig, schedule_mgr: ScheduleManager):
        self.bot = bot
        self.config = config
        self.schedule_mgr = schedule_mgr

    async def send_dm_embed(self, embed: discord.Embed, log_text: str):
        try:
            user = await self.bot.fetch_user(self.config.target_user_id)
            if user:
                await user.send(embed=embed)
                print(f"[발송 성공] {log_text}")
        except discord.Forbidden:
            print(f"[발송 실패] {log_text} - DM 차단 또는 비활성화 상태입니다.")
        except Exception as e:
            print(f"[발송 오류] {log_text} - {e}")

    async def check_server_uptime(self):
        """봇 프로세스 가동 시간 및 시스템 상태 점검"""
        uptime_seconds = time.time() - BOT_START_TIME
        uptime_days = uptime_seconds / 86400
        threshold_days = self.config.reboot_check.threshold_days

        if uptime_days >= threshold_days:
            boot_dt = datetime.fromtimestamp(BOT_START_TIME)
            formatted_boot = boot_dt.strftime("%Y-%m-%d %H:%M:%S")
            days_int = int(uptime_days)
            hours_int = int((uptime_days - days_int) * 24)

            # Memory info
            process = psutil.Process(os.getpid())
            mem_mb = process.memory_info().rss / (1024 * 1024)

            embed = discord.Embed(
                title="⚠️ 봇 프로세스 재시작 권장 알림",
                description=(
                    f"봇이 호스팅 패널에서 재시작 없이 **{days_int}일 {hours_int}시간** 동안 연속 가동 중입니다.\n"
                    f"원활한 메모리 관리와 시스템 안정을 위해 패널에서 재시작(Restart)을 권장합니다."
                ),
                color=0xE74C3C
            )
            embed.add_field(name="마지막 실행 시각", value=formatted_boot, inline=True)
            embed.add_field(name="현재 메모리 점유", value=f"{mem_mb:.1f} MB", inline=True)
            embed.set_footer(text="봇 가동 상태 주기 점검 • APScheduler")

            await self.send_dm_embed(embed, f"봇 업타임 경고 ({days_int}일 경과)")

    def register_uptime_check(self):
        check_time = self.config.reboot_check.check_time
        check_h, check_m = map(int, check_time.split(":"))
        self.schedule_mgr.scheduler.add_job(
            self.check_server_uptime,
            trigger=CronTrigger(hour=check_h, minute=check_m, timezone=self.config.timezone),
            id="check_server_uptime",
            replace_existing=True
        )
        print(f"[시스템] Uptime 점검 작업 등록 완료 ({check_time})")

    async def send_test_dm(self, user_id: int):
        try:
            user = await self.bot.fetch_user(user_id)
            if user:
                embed = discord.Embed(
                    title="🧪 1분 테스트 완료!",
                    description="`/test` 명령어 입력 후 정확히 1분이 경과하여 메시지가 정상 발송되었습니다.\n스케줄러와 DM 시스템이 완벽하게 동작 중입니다.",
                    color=0x95A5A6,
                    timestamp=datetime.now()
                )
                embed.add_field(name="시스템 핑", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
                embed.set_footer(text="스케줄러 진단 완료")
                await user.send(embed=embed)
                print(f"[발송 성공] {user.name}님에게 테스트 DM 발송 완료")
        except Exception as e:
            print(f"[발송 오류] 테스트 DM 실패 - {e}")

    @app_commands.command(name="test", description="스케줄러 테스트용: 1분 뒤에 DM을 발송합니다.")
    async def test_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ 1분 뒤에 DM으로 테스트 알림을 발송하겠습니다!", ephemeral=True)
        
        run_time = datetime.now() + timedelta(minutes=1)
        self.schedule_mgr.scheduler.add_job(
            self.send_test_dm,
            trigger=DateTrigger(run_date=run_time),
            args=[interaction.user.id],
            id=f"test_{interaction.user.id}_{run_time.timestamp()}"
        )
        print(f"[테스트 예약] {interaction.user.name}님이 /test 실행. (1분 뒤 발송 예정)")

    @app_commands.command(name="상태", description="봇의 실시간 시스템 리소스 및 상태를 확인합니다.")
    async def status_command(self, interaction: discord.Interaction):
        uptime_seconds = time.time() - BOT_START_TIME
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        mins = int((uptime_seconds % 3600) // 60)
        secs = int(uptime_seconds % 60)
        uptime_str = f"{days}일 {hours}시간 {mins}분 {secs}초"

        # psutil metrics
        process = psutil.Process(os.getpid())
        bot_mem_mb = process.memory_info().rss / (1024 * 1024)
        bot_cpu = process.cpu_percent(interval=0.1)

        sys_mem = psutil.virtual_memory()
        total_ram_gb = sys_mem.total / (1024 ** 3)
        used_ram_gb = sys_mem.used / (1024 ** 3)

        ping_ms = round(self.bot.latency * 1000)
        active_jobs = len(self.schedule_mgr.scheduler.get_jobs())

        embed = discord.Embed(
            title="📊 봇 시스템 상태 및 리소스 현황",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        embed.add_field(name="⏱️ 봇 가동 시간", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="📶 게이트웨이 핑", value=f"`{ping_ms} ms`", inline=True)
        embed.add_field(name="📅 등록된 스케줄", value=f"`{active_jobs} 개`", inline=True)

        embed.add_field(name="🧠 봇 RAM 사용량", value=f"`{bot_mem_mb:.2f} MB`", inline=True)
        embed.add_field(name="⚡ 봇 CPU 사용률", value=f"`{bot_cpu:.1f} %`", inline=True)
        embed.add_field(name="🖥️ 호스트 전체 RAM", value=f"`{used_ram_gb:.2f} / {total_ram_gb:.2f} GB ({sys_mem.percent}%)`", inline=True)

        embed.set_footer(text=f"봇: {self.bot.user.name} • discord.py {discord.__version__}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    pass
