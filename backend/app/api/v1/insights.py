"""
Insights API Endpoints
Endpoints for anomaly detection and trend analysis
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query

from app.services.anomaly_detection_service import AnomalyDetectionService
from app.models.anomaly import (
    AnomalyResponse,
    AnomalyListRequest,
    AnomalyListResponse,
    TrendResponse,
    TrendListRequest,
    TrendListResponse,
    MetricAnalysis,
    DetectionMethod,
    AnomalySeverity,
    TrendDirection
)


router = APIRouter(prefix="/insights", tags=["Insights"])


def get_anomaly_service() -> AnomalyDetectionService:
    """Dependency for anomaly detection service"""
    return AnomalyDetectionService()


@router.get("/anomalies", response_model=AnomalyListResponse)
async def list_anomalies(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    metric_ids: Optional[List[UUID]] = Query(None, description="Filter by metric IDs"),
    severity: Optional[List[AnomalySeverity]] = Query(None, description="Filter by severity"),
    is_acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    days_back: int = Query(30, description="Days of history to retrieve"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service)
):
    """
    List recent anomalies

    Returns detected anomalies with optional filtering.
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days_back)

        query = anomaly_service.supabase.table("anomalies").select("*").eq(
            "workspace_id", str(workspace_id)
        ).gte("detected_at", start_date.isoformat())

        if metric_ids:
            query = query.in_("metric_id", [str(mid) for mid in metric_ids])

        if severity:
            query = query.in_("severity", [s.value for s in severity])

        if is_acknowledged is not None:
            query = query.eq("is_acknowledged", is_acknowledged)

        # Get total count
        count_result = query.execute()
        total_count = len(count_result.data)

        # Get paginated results
        result = query.order("detected_at", desc=True).range(offset, offset + limit - 1).execute()

        anomalies = [AnomalyResponse(**a) for a in result.data]

        return AnomalyListResponse(
            anomalies=anomalies,
            total_count=total_count,
            has_more=total_count > (offset + limit),
            filters_applied={
                "workspace_id": str(workspace_id),
                "days_back": days_back,
                "severity": [s.value for s in severity] if severity else None
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching anomalies: {str(e)}")


@router.get("/trends", response_model=TrendListResponse)
async def list_trends(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    metric_ids: Optional[List[UUID]] = Query(None, description="Filter by metric IDs"),
    direction: Optional[List[TrendDirection]] = Query(None, description="Filter by direction"),
    is_significant: bool = Query(True, description="Filter by significance"),
    days_back: int = Query(30),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service)
):
    """
    List KPI trends

    Returns detected trends with optional filtering.
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days_back)

        query = anomaly_service.supabase.table("trends").select("*").eq(
            "workspace_id", str(workspace_id)
        ).gte("created_at", start_date.isoformat())

        if metric_ids:
            query = query.in_("metric_id", [str(mid) for mid in metric_ids])

        if direction:
            query = query.in_("direction", [d.value for d in direction])

        if is_significant:
            query = query.eq("is_significant", True)

        count_result = query.execute()
        total_count = len(count_result.data)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        trends = [TrendResponse(**t) for t in result.data]

        return TrendListResponse(
            trends=trends,
            total_count=total_count,
            has_more=total_count > (offset + limit),
            filters_applied={
                "workspace_id": str(workspace_id),
                "is_significant": is_significant
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trends: {str(e)}")


@router.get("/{metric_id}/analysis", response_model=MetricAnalysis)
async def analyze_metric(
    metric_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    days_back: int = Query(30, description="Days of historical data to analyze"),
    detection_methods: Optional[List[DetectionMethod]] = Query(
        None,
        description="Detection methods to use"
    ),
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service)
):
    """
    Deep dive analysis of a specific metric

    Performs comprehensive analysis including anomaly detection, trend analysis,
    and statistical measures.
    """
    try:
        analysis = await anomaly_service.analyze_metric(
            metric_id=metric_id,
            workspace_id=workspace_id,
            days_back=days_back,
            detection_methods=detection_methods
        )

        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing metric: {str(e)}")


@router.post("/analyze")
async def trigger_analysis(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    metric_ids: Optional[List[UUID]] = Query(None, description="Specific metrics to analyze"),
    days_back: int = Query(30),
    detection_methods: Optional[List[DetectionMethod]] = Query(None),
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service)
):
    """
    Trigger on-demand analysis for metrics

    Runs anomaly detection and trend analysis on specified metrics or all metrics.
    """
    try:
        # Get metrics to analyze
        if metric_ids:
            metrics_query = anomaly_service.supabase.table("kpi_metrics").select("id").in_(
                "id", [str(mid) for mid in metric_ids]
            )
        else:
            metrics_query = anomaly_service.supabase.table("kpi_metrics").select("id").eq(
                "workspace_id", str(workspace_id)
            ).eq("is_active", True)

        metrics = metrics_query.execute()

        results = {
            "analyzed_metrics": 0,
            "anomalies_detected": 0,
            "trends_detected": 0,
            "errors": []
        }

        for metric in metrics.data:
            try:
                metric_id = UUID(metric["id"])

                analysis = await anomaly_service.analyze_metric(
                    metric_id=metric_id,
                    workspace_id=workspace_id,
                    days_back=days_back,
                    detection_methods=detection_methods
                )

                results["analyzed_metrics"] += 1
                results["anomalies_detected"] += len(analysis.anomalies)
                results["trends_detected"] += len(analysis.trends)

            except Exception as e:
                results["errors"].append(f"Error analyzing metric {metric['id']}: {str(e)}")

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering analysis: {str(e)}")
