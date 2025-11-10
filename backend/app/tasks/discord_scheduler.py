"""
Discord Scheduler
Background task for sending daily briefings to Discord at scheduled times
"""
import logging
from datetime import datetime, time
import asyncio
from typing import List

from app.services.discord_service import DiscordService
from app.services.briefing_service import BriefingService
from app.models.discord_message import DiscordBriefingRequest
from app.models.briefing import BriefingType
from app.database import get_db_context
from sqlalchemy import text


logger = logging.getLogger(__name__)


class DiscordScheduler:
    """Scheduler for Discord briefing automation"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.discord_service = DiscordService()
        self.briefing_service = BriefingService()
        self.running = False
        self.morning_briefing_time = time(8, 0)  # 8 AM
        self.evening_briefing_time = time(18, 0)  # 6 PM

    async def start(self):
        """Start the scheduler"""
        self.running = True
        self.logger.info("Discord scheduler started")

        while self.running:
            try:
                await self._check_and_send_briefings()
                # Check every 5 minutes
                await asyncio.sleep(300)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        self.logger.info("Discord scheduler stopped")

    async def _check_and_send_briefings(self):
        """Check if it's time to send briefings and send them"""
        now = datetime.utcnow()
        current_time = now.time()

        # Check if it's morning briefing time (within 5 minute window)
        if self._is_time_to_send(current_time, self.morning_briefing_time):
            await self._send_all_morning_briefings()

        # Check if it's evening briefing time
        elif self._is_time_to_send(current_time, self.evening_briefing_time):
            await self._send_all_evening_briefings()

    def _is_time_to_send(self, current_time: time, target_time: time, window_minutes: int = 5) -> bool:
        """
        Check if current time is within the target time window

        Args:
            current_time: Current time
            target_time: Target time to send
            window_minutes: Window in minutes

        Returns:
            True if within window
        """
        current_minutes = current_time.hour * 60 + current_time.minute
        target_minutes = target_time.hour * 60 + target_time.minute

        return abs(current_minutes - target_minutes) <= window_minutes

    async def _send_all_morning_briefings(self):
        """Send morning briefings to all configured workspaces"""
        try:
            self.logger.info("Sending morning briefings to Discord")

            # Get all active briefing schedules
            schedules = await self._get_active_schedules(BriefingType.MORNING)

            for schedule in schedules:
                try:
                    # Check if already sent today
                    if await self._already_sent_today(
                        schedule["workspace_id"],
                        schedule["founder_id"],
                        BriefingType.MORNING
                    ):
                        continue

                    # Generate briefing
                    briefing = await self.briefing_service.generate_briefing(
                        workspace_id=schedule["workspace_id"],
                        founder_id=schedule["founder_id"],
                        briefing_type=BriefingType.MORNING
                    )

                    if not briefing:
                        self.logger.warning(
                            f"Failed to generate morning briefing for workspace {schedule['workspace_id']}"
                        )
                        continue

                    # Send to Discord
                    request = DiscordBriefingRequest(
                        workspace_id=schedule["workspace_id"],
                        founder_id=schedule["founder_id"],
                        briefing_id=briefing.id,
                        channel_name=schedule.get("discord_channel", "daily-briefings"),
                        include_metrics=True,
                        include_action_items=True,
                        mention_team=schedule.get("mention_team", False)
                    )

                    await self.discord_service.send_briefing(request)

                    self.logger.info(
                        f"Sent morning briefing to Discord for workspace {schedule['workspace_id']}"
                    )

                except Exception as e:
                    self.logger.error(
                        f"Error sending morning briefing for workspace {schedule.get('workspace_id')}: {str(e)}"
                    )

        except Exception as e:
            self.logger.error(f"Error in send_all_morning_briefings: {str(e)}")

    async def _send_all_evening_briefings(self):
        """Send evening briefings to all configured workspaces"""
        try:
            self.logger.info("Sending evening briefings to Discord")

            # Get all active briefing schedules
            schedules = await self._get_active_schedules(BriefingType.EVENING)

            for schedule in schedules:
                try:
                    # Check if already sent today
                    if await self._already_sent_today(
                        schedule["workspace_id"],
                        schedule["founder_id"],
                        BriefingType.EVENING
                    ):
                        continue

                    # Generate briefing
                    briefing = await self.briefing_service.generate_briefing(
                        workspace_id=schedule["workspace_id"],
                        founder_id=schedule["founder_id"],
                        briefing_type=BriefingType.EVENING
                    )

                    if not briefing:
                        self.logger.warning(
                            f"Failed to generate evening briefing for workspace {schedule['workspace_id']}"
                        )
                        continue

                    # Send to Discord
                    request = DiscordBriefingRequest(
                        workspace_id=schedule["workspace_id"],
                        founder_id=schedule["founder_id"],
                        briefing_id=briefing.id,
                        channel_name=schedule.get("discord_channel", "daily-briefings"),
                        include_metrics=True,
                        include_action_items=True,
                        mention_team=False
                    )

                    await self.discord_service.send_briefing(request)

                    self.logger.info(
                        f"Sent evening briefing to Discord for workspace {schedule['workspace_id']}"
                    )

                except Exception as e:
                    self.logger.error(
                        f"Error sending evening briefing for workspace {schedule.get('workspace_id')}: {str(e)}"
                    )

        except Exception as e:
            self.logger.error(f"Error in send_all_evening_briefings: {str(e)}")

    async def _get_active_schedules(self, briefing_type: BriefingType) -> List[dict]:
        """
        Get active briefing schedules for a given type

        Returns:
            List of schedule dictionaries
        """
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        SELECT
                            workspace_id,
                            founder_id,
                            discord_channel,
                            mention_team
                        FROM briefing_schedules
                        WHERE briefing_type = :briefing_type
                        AND is_active = true
                        AND delivery_channels @> ARRAY['discord']
                    """),
                    {"briefing_type": briefing_type.value}
                )

                schedules = []
                for row in result.fetchall():
                    schedules.append({
                        "workspace_id": row[0],
                        "founder_id": row[1],
                        "discord_channel": row[2],
                        "mention_team": row[3] if len(row) > 3 else False
                    })

                return schedules

        except Exception as e:
            self.logger.error(f"Error getting active schedules: {str(e)}")
            return []

    async def _already_sent_today(
        self,
        workspace_id: str,
        founder_id: str,
        briefing_type: BriefingType
    ) -> bool:
        """Check if briefing already sent to Discord today"""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        SELECT COUNT(*) FROM discord_messages dm
                        JOIN briefings b ON dm.message_content LIKE '%' || b.title || '%'
                        WHERE dm.workspace_id = :workspace_id
                        AND dm.founder_id = :founder_id
                        AND dm.message_type = 'briefing'
                        AND b.briefing_type = :briefing_type
                        AND dm.created_at >= :today_start
                        AND dm.status = 'sent'
                    """),
                    {
                        "workspace_id": workspace_id,
                        "founder_id": founder_id,
                        "briefing_type": briefing_type.value,
                        "today_start": today_start
                    }
                )

                count = result.fetchone()[0]
                return count > 0

        except Exception as e:
            self.logger.error(f"Error checking if already sent: {str(e)}")
            return False


# Global scheduler instance
discord_scheduler = DiscordScheduler()
