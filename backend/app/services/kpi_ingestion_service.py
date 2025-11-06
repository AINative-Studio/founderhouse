"""
KPI Ingestion Service
Handles ingestion of KPI data from Granola and other sources
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.connectors.granola_connector import GranolaConnector
from app.connectors.base_connector import ConnectorStatus, ConnectorError
from app.models.kpi_metric import (
    KPIMetricCreate,
    KPIMetricResponse,
    KPIDataPointCreate,
    KPIDataPointResponse,
    MetricCategory,
    MetricUnit,
    AggregationPeriod,
    KPISnapshot,
    SyncStatus
)
from app.database import get_supabase_client


logger = logging.getLogger(__name__)


class KPIIngestionService:
    """Service for ingesting KPI data from external sources"""

    # Standard KPI definitions for Granola
    STANDARD_KPIS = {
        "mrr": {
            "name": "mrr",
            "display_name": "Monthly Recurring Revenue",
            "category": MetricCategory.REVENUE,
            "unit": MetricUnit.CURRENCY,
            "description": "Monthly recurring revenue from subscriptions"
        },
        "arr": {
            "name": "arr",
            "display_name": "Annual Recurring Revenue",
            "category": MetricCategory.REVENUE,
            "unit": MetricUnit.CURRENCY,
            "description": "Annual recurring revenue"
        },
        "cac": {
            "name": "cac",
            "display_name": "Customer Acquisition Cost",
            "category": MetricCategory.USER_ACQUISITION,
            "unit": MetricUnit.CURRENCY,
            "description": "Average cost to acquire a customer"
        },
        "churn_rate": {
            "name": "churn_rate",
            "display_name": "Churn Rate",
            "category": MetricCategory.RETENTION,
            "unit": MetricUnit.PERCENTAGE,
            "description": "Percentage of customers who cancel"
        },
        "conversion_rate": {
            "name": "conversion_rate",
            "display_name": "Conversion Rate",
            "category": MetricCategory.USER_ACQUISITION,
            "unit": MetricUnit.PERCENTAGE,
            "description": "Percentage of leads that convert to customers"
        },
        "runway_months": {
            "name": "runway_months",
            "display_name": "Runway (Months)",
            "category": MetricCategory.FINANCIAL,
            "unit": MetricUnit.COUNT,
            "description": "Months of cash runway remaining"
        },
        "burn_rate": {
            "name": "burn_rate",
            "display_name": "Burn Rate",
            "category": MetricCategory.FINANCIAL,
            "unit": MetricUnit.CURRENCY,
            "description": "Monthly cash burn rate"
        },
        "active_users": {
            "name": "active_users",
            "display_name": "Active Users",
            "category": MetricCategory.GROWTH,
            "unit": MetricUnit.COUNT,
            "description": "Number of active users"
        },
        "ltv": {
            "name": "ltv",
            "display_name": "Lifetime Value",
            "category": MetricCategory.REVENUE,
            "unit": MetricUnit.CURRENCY,
            "description": "Average customer lifetime value"
        },
        "ltv_cac_ratio": {
            "name": "ltv_cac_ratio",
            "display_name": "LTV:CAC Ratio",
            "category": MetricCategory.FINANCIAL,
            "unit": MetricUnit.RATIO,
            "description": "Ratio of lifetime value to customer acquisition cost"
        }
    }

    def __init__(self):
        self.supabase = get_supabase_client()
        self.logger = logging.getLogger(__name__)

    async def initialize_standard_kpis(
        self,
        workspace_id: UUID,
        source_platform: str = "granola"
    ) -> List[KPIMetricResponse]:
        """
        Initialize standard KPI definitions for a workspace

        Args:
            workspace_id: Workspace ID
            source_platform: Source platform name

        Returns:
            List of created KPI metrics
        """
        created_metrics = []

        for kpi_key, kpi_def in self.STANDARD_KPIS.items():
            try:
                # Check if metric already exists
                existing = self.supabase.table("kpi_metrics").select("*").eq(
                    "workspace_id", str(workspace_id)
                ).eq("name", kpi_def["name"]).execute()

                if existing.data:
                    self.logger.info(f"Metric {kpi_def['name']} already exists for workspace {workspace_id}")
                    created_metrics.append(KPIMetricResponse(**existing.data[0]))
                    continue

                # Create new metric
                metric_data = KPIMetricCreate(
                    workspace_id=workspace_id,
                    source_platform=source_platform,
                    **kpi_def
                )

                result = self.supabase.table("kpi_metrics").insert(
                    metric_data.model_dump(mode="json")
                ).execute()

                if result.data:
                    created_metrics.append(KPIMetricResponse(**result.data[0]))
                    self.logger.info(f"Created metric {kpi_def['name']} for workspace {workspace_id}")

            except Exception as e:
                self.logger.error(f"Error creating metric {kpi_def['name']}: {str(e)}")

        return created_metrics

    async def sync_kpis_from_granola(
        self,
        workspace_id: UUID,
        credentials: Dict[str, Any],
        metrics_to_sync: Optional[List[str]] = None
    ) -> SyncStatus:
        """
        Sync KPI data from Granola

        Args:
            workspace_id: Workspace ID
            credentials: Granola API credentials
            metrics_to_sync: Optional list of specific metrics to sync (default: all)

        Returns:
            SyncStatus with sync results
        """
        sync_start = datetime.utcnow()
        metrics_synced = 0
        errors = []

        try:
            # Initialize Granola connector
            async with GranolaConnector(credentials) as connector:
                # Test connection
                test_result = await connector.test_connection()
                if test_result.status != ConnectorStatus.SUCCESS:
                    raise ConnectorError("Failed to connect to Granola API")

                # Get current KPIs from Granola
                kpi_response = await connector.get_kpis()

                if kpi_response.status != ConnectorStatus.SUCCESS:
                    raise ConnectorError(f"Failed to fetch KPIs: {kpi_response.error}")

                kpis_data = kpi_response.data

                # Ensure standard metrics exist
                await self.initialize_standard_kpis(workspace_id)

                # Get metric definitions from database
                metrics_result = self.supabase.table("kpi_metrics").select("*").eq(
                    "workspace_id", str(workspace_id)
                ).execute()

                metric_map = {m["name"]: m for m in metrics_result.data}

                # Process each KPI
                for kpi_name, kpi_value in kpis_data.items():
                    # Skip if not in metrics_to_sync filter
                    if metrics_to_sync and kpi_name not in metrics_to_sync:
                        continue

                    # Skip if metric not defined
                    if kpi_name not in metric_map:
                        self.logger.warning(f"Metric {kpi_name} not found in database")
                        continue

                    try:
                        metric = metric_map[kpi_name]

                        # Extract value and timestamp
                        if isinstance(kpi_value, dict):
                            value = float(kpi_value.get("value", 0))
                            timestamp = kpi_value.get("timestamp", datetime.utcnow().isoformat())
                        else:
                            value = float(kpi_value)
                            timestamp = datetime.utcnow().isoformat()

                        # Create data point
                        data_point = KPIDataPointCreate(
                            metric_id=UUID(metric["id"]),
                            workspace_id=workspace_id,
                            value=value,
                            timestamp=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
                            period=AggregationPeriod.DAILY,
                            metadata={
                                "source": "granola",
                                "sync_time": sync_start.isoformat()
                            }
                        )

                        # Insert data point
                        result = self.supabase.table("kpi_data_points").insert(
                            data_point.model_dump(mode="json")
                        ).execute()

                        if result.data:
                            metrics_synced += 1
                            self.logger.info(f"Synced {kpi_name}: {value}")

                    except Exception as e:
                        error_msg = f"Error syncing {kpi_name}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)

                # Calculate derived metrics
                await self._calculate_derived_metrics(workspace_id, metric_map)

                # Update sync status
                sync_status = SyncStatus(
                    workspace_id=workspace_id,
                    last_sync_at=sync_start,
                    next_sync_at=sync_start + timedelta(hours=6),
                    status="success" if not errors else "partial",
                    metrics_synced=metrics_synced,
                    errors=errors,
                    metadata={
                        "duration_seconds": (datetime.utcnow() - sync_start).total_seconds(),
                        "source": "granola"
                    }
                )

                # Store sync status
                self.supabase.table("kpi_sync_status").upsert({
                    "workspace_id": str(workspace_id),
                    **sync_status.model_dump(mode="json", exclude={"workspace_id"})
                }).execute()

                return sync_status

        except Exception as e:
            self.logger.error(f"KPI sync failed: {str(e)}")
            return SyncStatus(
                workspace_id=workspace_id,
                last_sync_at=sync_start,
                status="error",
                metrics_synced=metrics_synced,
                errors=[str(e)]
            )

    async def _calculate_derived_metrics(
        self,
        workspace_id: UUID,
        metric_map: Dict[str, Any]
    ) -> None:
        """
        Calculate derived metrics from base metrics

        Args:
            workspace_id: Workspace ID
            metric_map: Map of metric names to metric definitions
        """
        try:
            # Calculate LTV:CAC ratio if both metrics exist
            if "ltv" in metric_map and "cac" in metric_map:
                ltv_metric = metric_map["ltv"]
                cac_metric = metric_map["cac"]

                # Get latest values
                ltv_data = self.supabase.table("kpi_data_points").select("value").eq(
                    "metric_id", ltv_metric["id"]
                ).order("timestamp", desc=True).limit(1).execute()

                cac_data = self.supabase.table("kpi_data_points").select("value").eq(
                    "metric_id", cac_metric["id"]
                ).order("timestamp", desc=True).limit(1).execute()

                if ltv_data.data and cac_data.data:
                    ltv_value = ltv_data.data[0]["value"]
                    cac_value = cac_data.data[0]["value"]

                    if cac_value > 0:
                        ratio = ltv_value / cac_value

                        # Store ratio
                        if "ltv_cac_ratio" in metric_map:
                            ratio_metric = metric_map["ltv_cac_ratio"]
                            data_point = KPIDataPointCreate(
                                metric_id=UUID(ratio_metric["id"]),
                                workspace_id=workspace_id,
                                value=ratio,
                                timestamp=datetime.utcnow(),
                                period=AggregationPeriod.DAILY,
                                metadata={
                                    "derived": True,
                                    "formula": "ltv / cac"
                                }
                            )

                            self.supabase.table("kpi_data_points").insert(
                                data_point.model_dump(mode="json")
                            ).execute()

        except Exception as e:
            self.logger.error(f"Error calculating derived metrics: {str(e)}")

    async def get_current_snapshot(
        self,
        workspace_id: UUID
    ) -> KPISnapshot:
        """
        Get current snapshot of all KPIs

        Args:
            workspace_id: Workspace ID

        Returns:
            KPISnapshot with current values
        """
        try:
            # Get all metrics for workspace
            metrics_result = self.supabase.table("kpi_metrics").select("*").eq(
                "workspace_id", str(workspace_id)
            ).eq("is_active", True).execute()

            metrics = []

            for metric in metrics_result.data:
                # Get latest data point
                data_point = self.supabase.table("kpi_data_points").select("*").eq(
                    "metric_id", metric["id"]
                ).order("timestamp", desc=True).limit(1).execute()

                if data_point.data:
                    metrics.append({
                        "metric_id": metric["id"],
                        "name": metric["name"],
                        "display_name": metric["display_name"],
                        "category": metric["category"],
                        "unit": metric["unit"],
                        "value": data_point.data[0]["value"],
                        "timestamp": data_point.data[0]["timestamp"]
                    })

            return KPISnapshot(
                workspace_id=workspace_id,
                timestamp=datetime.utcnow(),
                metrics=metrics,
                metadata={"total_metrics": len(metrics)}
            )

        except Exception as e:
            self.logger.error(f"Error getting KPI snapshot: {str(e)}")
            return KPISnapshot(
                workspace_id=workspace_id,
                timestamp=datetime.utcnow(),
                metrics=[],
                metadata={"error": str(e)}
            )

    async def get_metric_history(
        self,
        metric_id: UUID,
        workspace_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: AggregationPeriod = AggregationPeriod.DAILY,
        limit: int = 100
    ) -> List[KPIDataPointResponse]:
        """
        Get historical data for a metric

        Args:
            metric_id: Metric ID
            workspace_id: Workspace ID
            start_date: Start date filter
            end_date: End date filter
            period: Aggregation period
            limit: Maximum number of data points

        Returns:
            List of KPI data points
        """
        try:
            query = self.supabase.table("kpi_data_points").select("*").eq(
                "metric_id", str(metric_id)
            ).eq("workspace_id", str(workspace_id)).eq("period", period)

            if start_date:
                query = query.gte("timestamp", start_date.isoformat())
            if end_date:
                query = query.lte("timestamp", end_date.isoformat())

            result = query.order("timestamp", desc=True).limit(limit).execute()

            return [KPIDataPointResponse(**dp) for dp in result.data]

        except Exception as e:
            self.logger.error(f"Error getting metric history: {str(e)}")
            return []

    async def validate_and_normalize_kpi(
        self,
        kpi_name: str,
        value: Any,
        unit: MetricUnit
    ) -> float:
        """
        Validate and normalize KPI values

        Args:
            kpi_name: KPI name
            value: Raw value
            unit: Metric unit

        Returns:
            Normalized float value

        Raises:
            ValueError: If value is invalid
        """
        try:
            # Convert to float
            normalized_value = float(value)

            # Validate based on unit type
            if unit == MetricUnit.PERCENTAGE:
                if normalized_value < 0 or normalized_value > 100:
                    raise ValueError(f"Percentage value must be between 0 and 100: {normalized_value}")

            elif unit == MetricUnit.CURRENCY:
                if normalized_value < 0:
                    self.logger.warning(f"Negative currency value for {kpi_name}: {normalized_value}")

            elif unit == MetricUnit.COUNT:
                if normalized_value < 0:
                    raise ValueError(f"Count value cannot be negative: {normalized_value}")

            return normalized_value

        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid KPI value for {kpi_name}: {str(e)}")
