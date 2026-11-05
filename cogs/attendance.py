import discord
from discord.ext import commands
from discord import app_commands
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from typing import Optional, Literal
from core.config import BotConfig
from core.scheduler import ScheduleManager

DAY_MAP = {
    "mon": "월요일",
    "tue": "화요일",
    "wed": "수요일",
    "thu": "목요일",
    "fri": "금요일",
    "sat": "토요일",
    "sun": "일요일"
}

DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

class AttendanceActionView(discord.ui.View):
    def __init__(self, ucheck_url: str):
        super().__init__(timeout=None)
        # Link button to Ucheck
        if ucheck_url:
            self.add_item(discord.ui.Button(
                label="Ucheck 전자출결 열기",
                style=discord.ButtonStyle.link,
                url=ucheck_url,
                emoji="🌐"
            ))

    @discord.ui.button(label="출석체크 완료", style=discord.ButtonStyle.success, emoji="✅", custom_id="btn_attendance_done")
    async def confirm_attendance(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update embed to indicate completion
        message = interaction.message
        if message and message.embeds:
            embed = message.embeds[0]
            embed.color = 0x2ECC71  # Green
            embed.title = f"✅ [출석 완료] {embed.title.replace('🔔 ', '')}"
            embed.set_footer(text=f"{embed.footer.text} • {interaction.user.name}님 출석 확인됨")
            
            button.disabled = True
            button.label = "출석 완료됨"
            button.style = discord.ButtonStyle.secondary
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("출석체크가 확인되었습니다!", ephemeral=True)

class AttendanceCog(commands.Cog, name="출석 알림 및 시간표"):
    def __init__(self, bot: commands.Bot, config: BotConfig, schedule_mgr: ScheduleManager):
        self.bot = bot
        self.config = config
        self.schedule_mgr = schedule_mgr

    async def send_dm_embed(self, embed: discord.Embed, view: Optional[discord.ui.View], log_text: str):
        try:
            user = await self.bot.fetch_user(self.config.target_user_id)
            if user:
                await user.send(embed=embed, view=view)
                print(f"[발송 성공] {log_text}")
        except discord.Forbidden:
            print(f"[발송 실패] {log_text} - DM 차단 또는 비활성화 상태입니다.")
        except Exception as e:
            print(f"[발송 오류] {log_text} - {e}")

    async def send_class_reminder(self, item: dict, is_pre_remind: bool = False):
        period_str = f" ({item['period']})" if item.get("period") else ""
        
        if is_pre_remind:
            title = f"⏳ [사전 알림] {item['subject']}{period_str}"
            description = f"**{item['subject']}** 수업이 **{self.config.pre_reminder_minutes}분 뒤**에 시작됩니다!\n출석체크 준비를 해주세요."
            footer_suffix = f" • 시작 {self.config.pre_reminder_minutes}분 전"
        else:
            title = f"🔔 {item['subject']}{period_str}"
            description = f"**{item['subject']}** Ucheck 출석체크를 해주세요!"
            footer_suffix = ""

        color_val = int(item.get("color", "0x3498DB"), 16) if isinstance(item.get("color"), str) else 0x3498DB
        embed = discord.Embed(
            title=title,
            description=description,
            color=color_val
        )
        embed.add_field(name="시작 시각", value=item["time"], inline=True)
        day_kr = DAY_MAP.get(item["day"].lower(), item["day"].upper())
        embed.set_footer(text=f"정기 강의 알림 • {day_kr}{footer_suffix}")

        view = AttendanceActionView(self.config.ucheck_url)
        await self.send_dm_embed(embed, view, f"{item['subject']}{period_str} ({item['time']})")

    def sync_scheduler_jobs(self):
        """Register all class reminders into APScheduler"""
        schedules = self.schedule_mgr.load_schedules()
        registered_count = 0

        for item in schedules:
            try:
                hour, minute = map(int, item["time"].split(":"))
                
                # Main reminder at class start time
                self.schedule_mgr.scheduler.add_job(
                    self.send_class_reminder,
                    trigger=CronTrigger(
                        day_of_week=item["day"],
                        hour=hour,
                        minute=minute,
                        timezone=self.config.timezone
                    ),
                    id=item["id"],
                    args=[item, False],
                    replace_existing=True
                )
                registered_count += 1

                # Optional pre-reminder
                pre_min = self.config.pre_reminder_minutes
                if pre_min > 0:
                    start_dt = datetime(2000, 1, 1, hour, minute) - timedelta(minutes=pre_min)
                    pre_h, pre_m = start_dt.hour, start_dt.minute
                    self.schedule_mgr.scheduler.add_job(
                        self.send_class_reminder,
                        trigger=CronTrigger(
                            day_of_week=item["day"],
                            hour=pre_h,
                            minute=pre_m,
                            timezone=self.config.timezone
                        ),
                        id=f"pre_{item['id']}",
                        args=[item, True],
                        replace_existing=True
                    )
            except Exception as e:
                print(f"[스케줄 등록 오류] {item.get('id')}: {e}")

        print(f"[시스템] 총 {registered_count}개의 수업 일정 스케줄러 동기화 완료")

    # Slash Command Group
    schedule_group = app_commands.Group(name="시간표", description="강의 시간표 조회 및 관리 명령어")

    @schedule_group.command(name="오늘", description="오늘 예정된 강의 일정 목록을 확인합니다.")
    async def schedule_today(self, interaction: discord.Interaction):
        # Current day in Korean/day code
        weekday_idx = datetime.now().weekday() # 0 is Monday
        today_code = DAY_ORDER[weekday_idx]
        today_kr = DAY_MAP[today_code]

        schedules = self.schedule_mgr.load_schedules()
        today_items = [s for s in schedules if s.get("day", "").lower() == today_code]
        today_items.sort(key=lambda x: x.get("time", "00:00"))

        embed = discord.Embed(
            title=f"📅 오늘의 강의 시간표 ({today_kr})",
            color=0x3498DB,
            timestamp=datetime.now()
        )

        if not today_items:
            embed.description = "🎉 오늘은 예정된 수업이 없습니다! 편안한 하루 보내세요."
        else:
            for item in today_items:
                period_str = f" [{item['period']}]" if item.get("period") else ""
                embed.add_field(
                    name=f"⏰ {item['time']} - {item['subject']}{period_str}",
                    value=f"ID: `{item['id']}`",
                    inline=False
                )
            embed.set_footer(text=f"총 {len(today_items)}개 강의 예정")

        view = AttendanceActionView(self.config.ucheck_url)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @schedule_group.command(name="전체", description="전체 주간 강의 시간표를 조회합니다.")
    async def schedule_all(self, interaction: discord.Interaction):
        schedules = self.schedule_mgr.load_schedules()
        
        embed = discord.Embed(
            title="📚 주간 전체 강의 시간표",
            description="등록된 모든 수업 알림 목록입니다.",
            color=0x9B59B6
        )

        for day in DAY_ORDER:
            day_items = [s for s in schedules if s.get("day", "").lower() == day]
            if day_items:
                day_items.sort(key=lambda x: x.get("time", "00:00"))
                lines = []
                for item in day_items:
                    period_str = f" ({item['period']})" if item.get("period") else ""
                    lines.append(f"• **{item['time']}** : {item['subject']}{period_str} `[id: {item['id']}]`")
                embed.add_field(
                    name=f"📌 {DAY_MAP[day]} ({len(day_items)}개)",
                    value="\n".join(lines),
                    inline=False
                )

        embed.set_footer(text=f"총 {len(schedules)}개 강의 등록됨 • Ucheck 연동 중")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @schedule_group.command(name="추가", description="새로운 수업 알림 일정을 추가합니다.")
    @app_commands.describe(
        item_id="고유 식별자 ID (예: mon_01)",
        day="요일 선택",
        time_str="시작 시각 (HH:MM 형식, 예: 09:20)",
        subject="과목명 (예: 컴퓨터구조)",
        period="차시 (선택사항, 예: 1차시)",
        color="임베드 색상 16진수 (기본: 0x3498DB)"
    )
    async def schedule_add(
        self,
        interaction: discord.Interaction,
        item_id: str,
        day: Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        time_str: str,
        subject: str,
        period: Optional[str] = None,
        color: str = "0x3498DB"
    ):
        try:
            # Validate time format
            parts = time_str.split(":")
            if len(parts) != 2 or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                await interaction.response.send_message("❌ 시간 형식은 `HH:MM` 형태여야 합니다 (예: 09:20).", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ 올바른 시각 숫자를 입력해주세요.", ephemeral=True)
            return

        new_item = {
            "id": item_id.strip(),
            "day": day,
            "time": time_str.strip(),
            "subject": subject.strip(),
            "period": period.strip() if period else None,
            "color": color.strip()
        }

        success = self.schedule_mgr.add_schedule(new_item)
        if success:
            self.sync_scheduler_jobs()
            period_str = f" ({new_item['period']})" if new_item['period'] else ""
            await interaction.response.send_message(
                f"✅ **{new_item['subject']}{period_str}** 일정이 성공적으로 추가되고 스케줄러에 등록되었습니다!\n"
                f"• 요일: {DAY_MAP[day]} | 시간: {time_str} | ID: `{item_id}`",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(f"❌ 이미 존재하는 ID(`{item_id}`)이거나 저장에 실패했습니다.", ephemeral=True)

    @schedule_group.command(name="삭제", description="등록된 수업 알림을 ID로 삭제합니다.")
    @app_commands.describe(item_id="삭제할 일정의 고유 ID (예: tue_01)")
    async def schedule_delete(self, interaction: discord.Interaction, item_id: str):
        success = self.schedule_mgr.delete_schedule(item_id.strip())
        if success:
            await interaction.response.send_message(f"🗑️ ID `{item_id}` 일정이 시간표와 스케줄러에서 삭제되었습니다.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ ID `{item_id}` 항목을 찾을 수 없습니다.", ephemeral=True)

async def setup(bot: commands.Bot):
    # Cog will be added in main.py with dependencies passed
    pass
