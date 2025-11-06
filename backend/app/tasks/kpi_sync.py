"""
KPI Sync Background Job
Scheduled job to sync KPI data from Granola every 6 hours
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.kpi_ingestion_service import KPIIngestionService
from app.database import get_supabase_client


logger = logging.getLogger(__name__)


class KPISyncJob:
    """Background job for syncing KPI data"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.kpi_service = KPIIngestionService()
        self.supabase = get_supabase_client()
        self.scheduler = AsyncIOScheduler()

    async def sync_all_workspaces(self):
        """Sync KPIs for all active workspaces"""
        self.logger.info("Starting KPI sync for all workspaces")

        try:
            # Get all active workspace integrations with Granola
            result = self.supabase.table("integrations").select(
                "workspace_id, credentials"
            ).eq("platform", "granola").eq("status", "active").execute()

            workspaces = result.data or []

            for workspace in workspaces:
                try:
                    workspace_id = workspace["workspace_id"]
                    credentials = workspace["credentials"]

                    self.logger.info(f"Syncing KPIs for workspace {workspace_id}")

                    # Sync KPIs
                    sync_status = await self.kpi_service.sync_kpis_from_granola(
                        workspace_id=workspace_id,
                        credentials=credentials
                    )

                    # Log sync result
                    if sync_status.status == "success":
                        self.logger.info(
                            f"Successfully synced {sync_status.metrics_synced} metrics "
                            f"for workspace {workspace_id}"
                        )
                    else:
                        self.logger.warning(
                            f"Sync completed with errors for workspace {workspace_id}: "
                            f"{sync_status.errors}"
                        )

                    # Log event
                    await self._log_sync_event(workspace_id, sync_status)

                except Exception as e:
                    self.logger.error(f"Error syncing workspace {workspace.get('workspace_id')}: {str(e)}")

            self.logger.info(f"Completed KPI sync for {len(workspaces)} workspaces")

        except Exception as e:
            self.logger.error(f"Error in KPI sync job: {str(e)}")

    async def _log_sync_event(self, workspace_id, sync_status):
        """Log sync event to ops.events table"""
        try:
            event = {
                "workspace_id": str(workspace_id),
                "event_type": "kpi_sync",
                "event_data": {
                    "status": sync_status.status,
                    "metrics_synced": sync_status.metrics_synced,
                    "errors": sync_status.errors
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            self.supabase.table("events").insert(event).execute()

        except Exception as e:
            self.logger.error(f"Error logging sync event: {str(e)}")

    def start(self):
        """Start the scheduler"""
        # Run every 6 hours
        self.scheduler.add_job(
            self.sync_all_workspaces,
            trigger=IntervalTrigger(hours=6),
            id="kpi_sync",
            name="Sync KPIs from Granola",
            replace_existing=True
        )

        # Run immediately on startup
        self.scheduler.add_job(
            self.sync_all_workspaces,
            id="kpi_sync_startup",
            name="Initial KPI sync on startup"
        )

        self.scheduler.start()
        self.logger.info("KPI sync job scheduled (every 6 hours)")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        self.logger.info("KPI sync job stopped")


# Global instance
kpi_sync_job = KPISyncJob()
