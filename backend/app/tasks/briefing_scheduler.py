"""
Briefing Scheduler
Scheduled job to generate and deliver daily briefings
"""
import logging
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.briefing_service import BriefingService
from app.models.briefing import BriefingType, DeliveryChannel
from app.database import get_supabase_client


logger = logging.getLogger(__name__)


class BriefingSchedulerJob:
    """Background job for scheduling briefing generation and delivery"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.briefing_service = BriefingService()
        self.supabase = get_supabase_client()
        self.scheduler = AsyncIOScheduler()

    async def generate_morning_briefs(self):
        """Generate morning briefs for all founders"""
        self.logger.info("Generating morning briefs")

        try:
            # Get all active briefing schedules for morning briefs
            result = self.supabase.table("briefing_schedules").select("*").eq(
                "briefing_type", BriefingType.MORNING.value
            ).eq("enabled", True).execute()

            schedules = result.data or []

            for schedule in schedules:
                try:
                    workspace_id = schedule["workspace_id"]
                    founder_id = schedule["founder_id"]

                    # Generate briefing
                    briefing = await self.briefing_service.generate_briefing(
                        workspace_id=workspace_id,
                        founder_id=founder_id,
                        briefing_type=BriefingType.MORNING
                    )

                    if briefing:
                        # Deliver briefing
                        await self._deliver_briefing(
                            briefing,
                            schedule.get("delivery_channels", [DeliveryChannel.IN_APP.value])
                        )

                        self.logger.info(f"Generated morning brief for founder {founder_id}")

                except Exception as e:
                    self.logger.error(
                        f"Error generating morning brief for founder {schedule.get('founder_id')}: {str(e)}"
                    )

            self.logger.info(f"Completed morning briefs generation for {len(schedules)} founders")

        except Exception as e:
            self.logger.error(f"Error in morning brief job: {str(e)}")

    async def generate_evening_wraps(self):
        """Generate evening wraps for all founders"""
        self.logger.info("Generating evening wraps")

        try:
            result = self.supabase.table("briefing_schedules").select("*").eq(
                "briefing_type", BriefingType.EVENING.value
            ).eq("enabled", True).execute()

            schedules = result.data or []

            for schedule in schedules:
                try:
                    workspace_id = schedule["workspace_id"]
                    founder_id = schedule["founder_id"]

                    briefing = await self.briefing_service.generate_briefing(
                        workspace_id=workspace_id,
                        founder_id=founder_id,
                        briefing_type=BriefingType.EVENING
                    )

                    if briefing:
                        await self._deliver_briefing(
                            briefing,
                            schedule.get("delivery_channels", [DeliveryChannel.IN_APP.value])
                        )

                        self.logger.info(f"Generated evening wrap for founder {founder_id}")

                except Exception as e:
                    self.logger.error(
                        f"Error generating evening wrap for founder {schedule.get('founder_id')}: {str(e)}"
                    )

            self.logger.info(f"Completed evening wraps generation for {len(schedules)} founders")

        except Exception as e:
            self.logger.error(f"Error in evening wrap job: {str(e)}")

    async def generate_weekly_investor_summaries(self):
        """Generate weekly investor summaries"""
        self.logger.info("Generating weekly investor summaries")

        try:
            # Run on Sundays for weekly summaries
            if datetime.now().weekday() != 6:  # 6 = Sunday
                return

            result = self.supabase.table("briefing_schedules").select("*").eq(
                "briefing_type", BriefingType.INVESTOR.value
            ).eq("enabled", True).execute()

            schedules = result.data or []

            for schedule in schedules:
                try:
                    workspace_id = schedule["workspace_id"]
                    founder_id = schedule["founder_id"]

                    briefing = await self.briefing_service.generate_briefing(
                        workspace_id=workspace_id,
                        founder_id=founder_id,
                        briefing_type=BriefingType.INVESTOR
                    )

                    if briefing:
                        await self._deliver_briefing(
                            briefing,
                            schedule.get("delivery_channels", [DeliveryChannel.EMAIL.value])
                        )

                        self.logger.info(f"Generated investor summary for founder {founder_id}")

                except Exception as e:
                    self.logger.error(
                        f"Error generating investor summary for founder {schedule.get('founder_id')}: {str(e)}"
                    )

            self.logger.info(f"Completed investor summaries for {len(schedules)} founders")

        except Exception as e:
            self.logger.error(f"Error in investor summary job: {str(e)}")

    async def _deliver_briefing(self, briefing, delivery_channels: list):
        """Deliver briefing via specified channels"""
        for channel in delivery_channels:
            try:
                if channel == DeliveryChannel.EMAIL.value:
                    await self._send_email(briefing)
                elif channel == DeliveryChannel.SLACK.value:
                    await self._send_slack(briefing)
                elif channel == DeliveryChannel.DISCORD.value:
                    await self._send_discord(briefing)
                # IN_APP is stored in database, no delivery needed

                # Update delivery status
                self.supabase.table("briefings").update({
                    "status": "delivered",
                    "delivered_at": datetime.utcnow().isoformat(),
                    "delivery_channels": delivery_channels
                }).eq("id", str(briefing.id)).execute()

            except Exception as e:
                self.logger.error(f"Error delivering briefing via {channel}: {str(e)}")

    async def _send_email(self, briefing):
        """Send briefing via email"""
        # Placeholder - would integrate with email service
        self.logger.info(f"Sending briefing {briefing.id} via email")

    async def _send_slack(self, briefing):
        """Send briefing via Slack"""
        # Placeholder - would integrate with Slack connector
        self.logger.info(f"Sending briefing {briefing.id} via Slack")

    async def _send_discord(self, briefing):
        """Send briefing via Discord"""
        # Placeholder - would integrate with Discord connector
        self.logger.info(f"Sending briefing {briefing.id} via Discord")

    def start(self):
        """Start the scheduler"""
        # Morning briefs at 8 AM
        self.scheduler.add_job(
            self.generate_morning_briefs,
            trigger=CronTrigger(hour=8, minute=0),
            id="morning_briefs",
            name="Generate morning briefs",
            replace_existing=True
        )

        # Evening wraps at 6 PM
        self.scheduler.add_job(
            self.generate_evening_wraps,
            trigger=CronTrigger(hour=18, minute=0),
            id="evening_wraps",
            name="Generate evening wraps",
            replace_existing=True
        )

        # Weekly investor summaries on Sundays at 9 AM
        self.scheduler.add_job(
            self.generate_weekly_investor_summaries,
            trigger=CronTrigger(day_of_week="sun", hour=9, minute=0),
            id="investor_summaries",
            name="Generate weekly investor summaries",
            replace_existing=True
        )

        self.scheduler.start()
        self.logger.info("Briefing scheduler started")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        self.logger.info("Briefing scheduler stopped")


# Global instance
briefing_scheduler = BriefingSchedulerJob()
