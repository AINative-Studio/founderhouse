"""
Briefing Service
Service for generating daily briefings and summaries
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from pathlib import Path

from app.models.briefing import (
    BriefingCreate,
    BriefingResponse,
    BriefingType,
    BriefingStatus,
    BriefingSection,
    MorningBriefContent,
    EveningWrapContent,
    InvestorSummaryContent
)
from app.models.founder import FounderResponse
from app.database import get_supabase_client


logger = logging.getLogger(__name__)


class BriefingService:
    """Service for generating and managing briefings"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.logger = logging.getLogger(__name__)
        self.templates_dir = Path(__file__).parent.parent / "templates" / "briefings"

    async def generate_briefing(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        briefing_type: BriefingType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[BriefingResponse]:
        """
        Generate a briefing

        Args:
            workspace_id: Workspace ID
            founder_id: Founder ID
            briefing_type: Type of briefing
            start_date: Start of reporting period
            end_date: End of reporting period

        Returns:
            Generated briefing
        """
        try:
            # Set default dates
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                if briefing_type == BriefingType.MORNING:
                    start_date = end_date - timedelta(days=1)
                elif briefing_type == BriefingType.EVENING:
                    start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                elif briefing_type == BriefingType.INVESTOR:
                    start_date = end_date - timedelta(days=7)
                else:
                    start_date = end_date - timedelta(days=1)

            # Get founder info
            founder = await self._get_founder(founder_id)

            # Generate content based on type
            if briefing_type == BriefingType.MORNING:
                content = await self._generate_morning_brief(workspace_id, founder_id, founder)
                sections = self._create_morning_sections(content)
                title = f"Morning Brief - {end_date.strftime('%B %d, %Y')}"

            elif briefing_type == BriefingType.EVENING:
                content = await self._generate_evening_wrap(workspace_id, founder_id, founder, start_date, end_date)
                sections = self._create_evening_sections(content)
                title = f"Evening Wrap - {end_date.strftime('%B %d, %Y')}"

            elif briefing_type == BriefingType.INVESTOR:
                content = await self._generate_investor_summary(workspace_id, founder_id, start_date, end_date)
                sections = self._create_investor_sections(content)
                title = f"Weekly Update - Week of {start_date.strftime('%B %d, %Y')}"

            else:
                raise ValueError(f"Unsupported briefing type: {briefing_type}")

            # Create briefing
            briefing = BriefingCreate(
                workspace_id=workspace_id,
                founder_id=founder_id,
                briefing_type=briefing_type,
                title=title,
                start_date=start_date,
                end_date=end_date,
                sections=sections,
                summary=content.get("summary", ""),
                key_highlights=content.get("highlights", []),
                action_items=content.get("action_items", [])
            )

            # Save briefing
            result = self.supabase.table("briefings").insert(
                briefing.model_dump(mode="json")
            ).execute()

            if result.data:
                self.logger.info(f"Generated {briefing_type.value} briefing for founder {founder_id}")
                return BriefingResponse(**result.data[0])

            return None

        except Exception as e:
            self.logger.error(f"Error generating briefing: {str(e)}")
            return None

    async def _generate_morning_brief(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        founder: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate morning brief content"""
        try:
            # Get today's schedule
            schedule = await self._get_today_schedule(workspace_id, founder_id)

            # Get overnight updates
            overnight = await self._get_overnight_updates(workspace_id)

            # Get KPI snapshot
            kpis = await self._get_kpi_snapshot(workspace_id)

            # Get urgent items
            urgent = await self._get_urgent_items(workspace_id, founder_id)

            # Get recommendations
            recommendations = await self._get_top_recommendations(workspace_id, founder_id, limit=3)

            # Get unread counts
            unread = await self._get_unread_summary(workspace_id)

            return {
                "founder_name": founder.get("display_name", ""),
                "schedule": schedule,
                "overnight_updates": overnight,
                "kpi_snapshot": kpis,
                "urgent_items": urgent,
                "recommendations": recommendations,
                "unread_summary": unread,
                "summary": f"You have {len(schedule)} meetings today and {len(urgent)} urgent items.",
                "highlights": self._extract_highlights(kpis, urgent),
                "action_items": self._extract_actions(urgent, recommendations)
            }

        except Exception as e:
            self.logger.error(f"Error generating morning brief: {str(e)}")
            return {}

    async def _generate_evening_wrap(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        founder: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate evening wrap content"""
        try:
            # Get today's meetings
            meetings = await self._get_meetings_today(workspace_id, start_date, end_date)

            # Get completed tasks
            completed = await self._get_completed_tasks(workspace_id, founder_id, start_date, end_date)

            # Get pending tasks
            pending = await self._get_pending_tasks(workspace_id, founder_id)

            # Get KPI changes
            kpi_changes = await self._get_kpi_changes(workspace_id, start_date, end_date)

            # Get new insights
            insights = await self._get_new_insights(workspace_id, start_date, end_date)

            # Get tomorrow preview
            tomorrow = await self._get_tomorrow_preview(workspace_id, founder_id)

            summary = f"Today you had {len(meetings)} meetings and completed {len(completed)} tasks."

            return {
                "founder_name": founder.get("display_name", ""),
                "meetings_today": meetings,
                "tasks_completed": completed,
                "tasks_pending": pending,
                "kpi_changes": kpi_changes,
                "new_insights": insights,
                "tomorrow_preview": tomorrow,
                "summary": summary,
                "highlights": self._extract_day_highlights(meetings, completed, kpi_changes),
                "action_items": [task.get("description", "") for task in pending[:5]]
            }

        except Exception as e:
            self.logger.error(f"Error generating evening wrap: {str(e)}")
            return {}

    async def _generate_investor_summary(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate investor summary content"""
        try:
            # Get key metrics
            key_metrics = await self._get_investor_metrics(workspace_id, start_date, end_date)

            # Get growth highlights
            growth = await self._get_growth_highlights(workspace_id, start_date, end_date)

            # Get challenges
            challenges = await self._get_challenges(workspace_id, start_date, end_date)

            # Financial overview
            financial = await self._get_financial_overview(workspace_id, start_date, end_date)

            # Product updates (placeholder - would integrate with product tracking)
            product_updates = []

            # Team updates (placeholder)
            team_updates = []

            # Asks
            asks = []

            # Next milestones (placeholder)
            milestones = []

            summary = f"This week we achieved {len(growth)} key milestones."

            return {
                "key_metrics": key_metrics,
                "growth_highlights": growth,
                "challenges": challenges,
                "financial_overview": financial,
                "product_updates": product_updates,
                "team_updates": team_updates,
                "asks": asks,
                "next_milestones": milestones,
                "summary": summary,
                "highlights": growth[:5],
                "action_items": []
            }

        except Exception as e:
            self.logger.error(f"Error generating investor summary: {str(e)}")
            return {}

    def _create_morning_sections(self, content: Dict[str, Any]) -> List[BriefingSection]:
        """Create sections for morning brief"""
        sections = [
            BriefingSection(
                title="Today's Schedule",
                content=self._format_schedule(content.get("schedule", [])),
                order=1,
                section_type="schedule",
                importance=5
            ),
            BriefingSection(
                title="Urgent Items",
                content=self._format_urgent_items(content.get("urgent_items", [])),
                order=2,
                section_type="urgent",
                importance=5
            ),
            BriefingSection(
                title="Key Metrics",
                content=self._format_kpis(content.get("kpi_snapshot", {})),
                order=3,
                section_type="kpis",
                importance=4
            ),
        ]
        return sections

    def _create_evening_sections(self, content: Dict[str, Any]) -> List[BriefingSection]:
        """Create sections for evening wrap"""
        sections = [
            BriefingSection(
                title="Day Summary",
                content=content.get("summary", ""),
                order=1,
                section_type="summary",
                importance=5
            ),
            BriefingSection(
                title="Meetings Today",
                content=self._format_meetings(content.get("meetings_today", [])),
                order=2,
                section_type="meetings",
                importance=4
            ),
            BriefingSection(
                title="Tasks",
                content=self._format_tasks(
                    content.get("tasks_completed", []),
                    content.get("tasks_pending", [])
                ),
                order=3,
                section_type="tasks",
                importance=4
            ),
        ]
        return sections

    def _create_investor_sections(self, content: Dict[str, Any]) -> List[BriefingSection]:
        """Create sections for investor summary"""
        sections = [
            BriefingSection(
                title="Executive Summary",
                content=content.get("summary", ""),
                order=1,
                section_type="summary",
                importance=5
            ),
            BriefingSection(
                title="Key Metrics",
                content=self._format_investor_metrics(content.get("key_metrics", {})),
                order=2,
                section_type="metrics",
                importance=5
            ),
        ]
        return sections

    # Helper methods for data retrieval
    async def _get_founder(self, founder_id: UUID) -> Dict[str, Any]:
        """Get founder information"""
        try:
            result = self.supabase.table("founders").select("*").eq("id", str(founder_id)).single().execute()
            return result.data or {}
        except:
            return {}

    async def _get_today_schedule(self, workspace_id: UUID, founder_id: UUID) -> List[Dict[str, Any]]:
        """Get today's meetings/events"""
        # Placeholder - would integrate with calendar
        return []

    async def _get_overnight_updates(self, workspace_id: UUID) -> List[Dict[str, Any]]:
        """Get overnight updates"""
        return []

    async def _get_kpi_snapshot(self, workspace_id: UUID) -> Dict[str, Any]:
        """Get current KPI snapshot"""
        try:
            result = self.supabase.table("kpi_metrics").select("*, kpi_data_points(*)").eq(
                "workspace_id", str(workspace_id)
            ).eq("is_active", True).execute()
            return {"metrics": result.data or []}
        except:
            return {}

    async def _get_urgent_items(self, workspace_id: UUID, founder_id: UUID) -> List[Dict[str, Any]]:
        """Get urgent items"""
        return []

    async def _get_top_recommendations(
        self, workspace_id: UUID, founder_id: UUID, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get top recommendations"""
        try:
            result = self.supabase.table("recommendations").select("*").eq(
                "workspace_id", str(workspace_id)
            ).eq("founder_id", str(founder_id)).eq(
                "status", "pending"
            ).order("priority").limit(limit).execute()
            return result.data or []
        except:
            return []

    async def _get_unread_summary(self, workspace_id: UUID) -> Dict[str, int]:
        """Get unread message counts"""
        return {}

    async def _get_meetings_today(
        self, workspace_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get today's meetings"""
        return []

    async def _get_completed_tasks(
        self, workspace_id: UUID, founder_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get completed tasks"""
        return []

    async def _get_pending_tasks(self, workspace_id: UUID, founder_id: UUID) -> List[Dict[str, Any]]:
        """Get pending tasks"""
        return []

    async def _get_kpi_changes(
        self, workspace_id: UUID, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get KPI changes"""
        return {}

    async def _get_new_insights(
        self, workspace_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get new insights"""
        return []

    async def _get_tomorrow_preview(self, workspace_id: UUID, founder_id: UUID) -> Dict[str, Any]:
        """Get tomorrow's preview"""
        return {}

    async def _get_investor_metrics(
        self, workspace_id: UUID, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get investor-relevant metrics"""
        return {}

    async def _get_growth_highlights(
        self, workspace_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[str]:
        """Get growth highlights"""
        return []

    async def _get_challenges(
        self, workspace_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[str]:
        """Get current challenges"""
        return []

    async def _get_financial_overview(
        self, workspace_id: UUID, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get financial overview"""
        return {}

    # Formatting helpers
    def _format_schedule(self, schedule: List[Dict[str, Any]]) -> str:
        return "No meetings scheduled" if not schedule else "\n".join([
            f"- {m.get('time', '')}: {m.get('title', '')}" for m in schedule
        ])

    def _format_urgent_items(self, items: List[Dict[str, Any]]) -> str:
        return "No urgent items" if not items else "\n".join([
            f"- {item.get('description', '')}" for item in items
        ])

    def _format_kpis(self, kpis: Dict[str, Any]) -> str:
        return "No KPI data available"

    def _format_meetings(self, meetings: List[Dict[str, Any]]) -> str:
        return "No meetings today" if not meetings else "\n".join([
            f"- {m.get('title', '')}" for m in meetings
        ])

    def _format_tasks(self, completed: List, pending: List) -> str:
        return f"Completed: {len(completed)}\nPending: {len(pending)}"

    def _format_investor_metrics(self, metrics: Dict[str, Any]) -> str:
        return "No metrics available"

    def _extract_highlights(self, kpis: Dict, urgent: List) -> List[str]:
        return [f"{len(urgent)} urgent items require attention"]

    def _extract_actions(self, urgent: List, recs: List) -> List[str]:
        return [item.get("description", "") for item in urgent[:3]]

    def _extract_day_highlights(self, meetings: List, completed: List, kpis: Dict) -> List[str]:
        return [f"Completed {len(completed)} tasks", f"Attended {len(meetings)} meetings"]
