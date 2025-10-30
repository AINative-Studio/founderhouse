"""
Integration Health Check Background Task
Scheduled task to monitor integration health
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import db_manager
from app.services.health_check_service import HealthCheckService


logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler = None


async def run_workspace_health_check(workspace_id: UUID):
    """
    Run health check for all integrations in a workspace

    Args:
        workspace_id: Workspace UUID
    """
    try:
        logger.info(f"Starting health check for workspace {workspace_id}")

        # Get database client
        db = db_manager.get_client()

        # Create health check service
        health_service = HealthCheckService(db)

        # Run health checks
        health_checks = await health_service.check_all_integrations_health(workspace_id)

        # Log results
        healthy_count = sum(1 for hc in health_checks if hc.is_healthy)
        total_count = len(health_checks)

        logger.info(
            f"Completed health check for workspace {workspace_id}: "
            f"{healthy_count}/{total_count} integrations healthy"
        )

        # Alert on unhealthy integrations (in production, send notifications)
        unhealthy = [hc for hc in health_checks if not hc.is_healthy]
        if unhealthy:
            logger.warning(
                f"Workspace {workspace_id} has {len(unhealthy)} unhealthy integrations: "
                f"{[hc.platform.value for hc in unhealthy]}"
            )

    except Exception as e:
        logger.error(f"Error running health check for workspace {workspace_id}: {str(e)}")


async def run_all_workspaces_health_check():
    """
    Run health check for all workspaces
    This is the main scheduled task
    """
    try:
        logger.info("Starting scheduled health check for all workspaces")
        start_time = datetime.utcnow()

        # Get database client
        db = db_manager.get_client()

        # Get all unique workspace IDs from integrations
        response = db.table("core.integrations").select("workspace_id").execute()

        workspace_ids = set()
        for row in response.data:
            workspace_ids.add(UUID(row["workspace_id"]))

        logger.info(f"Found {len(workspace_ids)} workspaces to check")

        # Run health checks for each workspace
        tasks = []
        for workspace_id in workspace_ids:
            task = run_workspace_health_check(workspace_id)
            tasks.append(task)

        # Run all health checks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        # Log completion
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Completed scheduled health check for {len(workspace_ids)} workspaces "
            f"in {duration:.2f} seconds"
        )

    except Exception as e:
        logger.error(f"Error in scheduled health check: {str(e)}")


def schedule_health_checks(interval_hours: int = 6):
    """
    Schedule periodic health checks

    Args:
        interval_hours: Interval between health checks in hours (default: 6)
    """
    global scheduler

    if scheduler is None:
        scheduler = AsyncIOScheduler()

    # Add job to run every N hours
    scheduler.add_job(
        run_all_workspaces_health_check,
        trigger=IntervalTrigger(hours=interval_hours),
        id="integration_health_check",
        name="Integration Health Check",
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )

    # Start scheduler if not already running
    if not scheduler.running:
        scheduler.start()
        logger.info(f"Scheduled integration health checks every {interval_hours} hours")
    else:
        logger.info("Health check scheduler already running")


def stop_health_checks():
    """Stop the health check scheduler"""
    global scheduler

    if scheduler and scheduler.running:
        scheduler.shutdown()
        scheduler = None
        logger.info("Stopped health check scheduler")


async def run_immediate_health_check_for_workspace(workspace_id: UUID) -> dict:
    """
    Run an immediate health check for a workspace (on-demand)

    Args:
        workspace_id: Workspace UUID

    Returns:
        Health check results
    """
    try:
        logger.info(f"Running immediate health check for workspace {workspace_id}")

        # Get database client
        db = db_manager.get_client()

        # Create health check service
        health_service = HealthCheckService(db)

        # Get health dashboard
        dashboard = await health_service.get_health_dashboard(workspace_id)

        logger.info(f"Immediate health check completed for workspace {workspace_id}")
        return dashboard

    except Exception as e:
        logger.error(f"Error in immediate health check: {str(e)}")
        raise


# Convenience function for manual testing
async def test_health_check_task():
    """
    Test health check task manually
    This is useful for development and testing
    """
    logger.info("Running test health check...")

    # Get database client
    db = db_manager.get_client()

    # Get first workspace with integrations
    response = db.table("core.integrations").select("workspace_id").limit(1).execute()

    if response.data:
        workspace_id = UUID(response.data[0]["workspace_id"])
        result = await run_immediate_health_check_for_workspace(workspace_id)
        logger.info(f"Test health check result: {result}")
        return result
    else:
        logger.warning("No integrations found for testing")
        return None


# Initialize scheduler on module import (if in production)
# This can be called from main.py during application startup
def init_scheduler():
    """
    Initialize the health check scheduler
    Called from main.py during application startup
    """
    try:
        # Schedule health checks every 6 hours
        schedule_health_checks(interval_hours=6)
        logger.info("Integration health check scheduler initialized")
    except Exception as e:
        logger.error(f"Failed to initialize health check scheduler: {str(e)}")
