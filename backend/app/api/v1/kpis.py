"""
KPI API Endpoints
Endpoints for managing KPIs and metrics
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from app.services.kpi_ingestion_service import KPIIngestionService
from app.models.kpi_metric import (
    KPIMetricResponse,
    KPISnapshot,
    KPITimeSeriesResponse,
    KPITimeSeriesRequest,
    SyncStatus,
    AggregationPeriod
)


router = APIRouter(prefix="/kpis", tags=["KPIs"])


def get_kpi_service() -> KPIIngestionService:
    """Dependency for KPI service"""
    return KPIIngestionService()


@router.get("", response_model=List[KPIMetricResponse])
async def list_kpis(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: bool = Query(True, description="Filter by active status"),
    kpi_service: KPIIngestionService = Depends(get_kpi_service)
):
    """
    List available KPIs for a workspace

    Returns all KPI metrics configured for the workspace.
    """
    try:
        query = kpi_service.supabase.table("kpi_metrics").select("*").eq(
            "workspace_id", str(workspace_id)
        ).eq("is_active", is_active)

        if category:
            query = query.eq("category", category)

        result = query.execute()

        return [KPIMetricResponse(**metric) for metric in result.data]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching KPIs: {str(e)}")


@router.get("/{metric_id}/history", response_model=KPITimeSeriesResponse)
async def get_metric_history(
    metric_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    period: AggregationPeriod = Query(AggregationPeriod.DAILY, description="Aggregation period"),
    limit: int = Query(100, le=1000, description="Maximum data points"),
    kpi_service: KPIIngestionService = Depends(get_kpi_service)
):
    """
    Get time-series data for a specific metric

    Returns historical data points for the metric within the specified date range.
    """
    try:
        # Get metric info
        metric_result = kpi_service.supabase.table("kpi_metrics").select("*").eq(
            "id", str(metric_id)
        ).single().execute()

        if not metric_result.data:
            raise HTTPException(status_code=404, detail="Metric not found")

        metric = KPIMetricResponse(**metric_result.data)

        # Get historical data
        data_points = await kpi_service.get_metric_history(
            metric_id=metric_id,
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            period=period,
            limit=limit
        )

        # Calculate statistics
        if data_points:
            values = [dp.value for dp in data_points]
            import numpy as np
            statistics = {
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "std": float(np.std(values))
            }

            # Calculate trend
            if len(values) >= 2:
                percentage_change = ((values[-1] - values[0]) / abs(values[0])) * 100 if values[0] != 0 else 0
                trend = {
                    "direction": "up" if percentage_change > 0 else "down" if percentage_change < 0 else "stable",
                    "percentage_change": percentage_change
                }
            else:
                trend = None
        else:
            statistics = None
            trend = None

        return KPITimeSeriesResponse(
            metric_id=metric_id,
            metric_name=metric.name,
            category=metric.category,
            unit=metric.unit,
            period=period,
            data_points=data_points,
            statistics=statistics,
            trend=trend
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metric history: {str(e)}")


@router.get("/current", response_model=KPISnapshot)
async def get_current_snapshot(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    kpi_service: KPIIngestionService = Depends(get_kpi_service)
):
    """
    Get latest snapshot of all KPIs

    Returns the most recent values for all active KPIs in the workspace.
    """
    try:
        snapshot = await kpi_service.get_current_snapshot(workspace_id)
        return snapshot

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching KPI snapshot: {str(e)}")


@router.post("/sync")
async def trigger_manual_sync(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    metrics_to_sync: Optional[List[str]] = Query(None, description="Specific metrics to sync"),
    kpi_service: KPIIngestionService = Depends(get_kpi_service)
):
    """
    Manually trigger KPI sync from Granola

    Initiates an immediate sync of KPI data from the Granola API.
    """
    try:
        # Get Granola credentials for workspace
        integration = kpi_service.supabase.table("integrations").select("credentials").eq(
            "workspace_id", str(workspace_id)
        ).eq("platform", "granola").single().execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="Granola integration not found for workspace"
            )

        credentials = integration.data["credentials"]

        # Trigger sync
        sync_status = await kpi_service.sync_kpis_from_granola(
            workspace_id=workspace_id,
            credentials=credentials,
            metrics_to_sync=metrics_to_sync
        )

        return {
            "status": sync_status.status,
            "metrics_synced": sync_status.metrics_synced,
            "errors": sync_status.errors,
            "last_sync_at": sync_status.last_sync_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering KPI sync: {str(e)}")


@router.get("/sync-status", response_model=SyncStatus)
async def get_sync_status(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    kpi_service: KPIIngestionService = Depends(get_kpi_service)
):
    """
    Get last KPI sync status

    Returns information about the most recent KPI sync operation.
    """
    try:
        result = kpi_service.supabase.table("kpi_sync_status").select("*").eq(
            "workspace_id", str(workspace_id)
        ).order("last_sync_at", desc=True).limit(1).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="No sync status found")

        return SyncStatus(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sync status: {str(e)}")
