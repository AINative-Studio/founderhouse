"""
KPI Ingestion Service
Handles ingestion of KPI data from Granola and other sources
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

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
        self.logger = logging.getLogger(__name__)

    async def initialize_standard_kpis(
        self,
        workspace_id: UUID,
        source_platform: str = "granola",
        db: Optional[Session] = None
    ) -> List[KPIMetricResponse]:
        """
        Initialize standard KPI definitions for a workspace

        Args:
            workspace_id: Workspace ID
            source_platform: Source platform name
            db: Database session

        Returns:
            List of created KPI metrics
        """
        created_metrics = []

        if not db:
            return created_metrics

        for kpi_key, kpi_def in self.STANDARD_KPIS.items():
            try:
                # Check if metric already exists
                existing_query = text("""
                    SELECT * FROM kpis.kpi_metrics
                    WHERE workspace_id = :workspace_id AND name = :name
                """)
                existing_result = db.execute(existing_query, {
                    "workspace_id": str(workspace_id),
                    "name": kpi_def["name"]
                })
                existing_row = existing_result.fetchone()

                if existing_row:
                    self.logger.info(f"Metric {kpi_def['name']} already exists for workspace {workspace_id}")
                    created_metrics.append(KPIMetricResponse(**dict(existing_row._mapping)))
                    continue

                # Create new metric
                metric_data = KPIMetricCreate(
                    workspace_id=workspace_id,
                    source_platform=source_platform,
                    **kpi_def
                )

                insert_query = text("""
                    INSERT INTO kpis.kpi_metrics
                    (workspace_id, source_platform, name, display_name, category, unit, description)
                    VALUES (:workspace_id, :source_platform, :name, :display_name, :category, :unit, :description)
                    RETURNING *
                """)
                result = db.execute(insert_query, {
                    "workspace_id": str(metric_data.workspace_id),
                    "source_platform": metric_data.source_platform,
                    "name": metric_data.name,
                    "display_name": metric_data.display_name,
                    "category": metric_data.category.value,
                    "unit": metric_data.unit.value,
                    "description": metric_data.description
                })
                db.commit()

                row = result.fetchone()
                if row:
                    created_metrics.append(KPIMetricResponse(**dict(row._mapping)))
                    self.logger.info(f"Created metric {kpi_def['name']} for workspace {workspace_id}")

            except Exception as e:
                self.logger.error(f"Error creating metric {kpi_def['name']}: {str(e)}")

        return created_metrics

    async def sync_kpis_from_granola(
        self,
        workspace_id: UUID,
        credentials: Dict[str, Any],
        metrics_to_sync: Optional[List[str]] = None,
        db: Optional[Session] = None
    ) -> SyncStatus:
        """
        Sync KPI data from Granola

        Args:
            workspace_id: Workspace ID
            credentials: Granola API credentials
            metrics_to_sync: Optional list of specific metrics to sync (default: all)
            db: Database session

        Returns:
            SyncStatus with sync results
        """
        sync_start = datetime.utcnow()
        metrics_synced = 0
        errors = []

        if not db:
            return SyncStatus(
                workspace_id=workspace_id,
                last_sync_at=sync_start,
                status="error",
                metrics_synced=0,
                errors=["Database session not provided"]
            )

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
                await self.initialize_standard_kpis(workspace_id, db=db)

                # Get metric definitions from database
                metrics_query = text("""
                    SELECT * FROM kpis.kpi_metrics
                    WHERE workspace_id = :workspace_id
                """)
                metrics_result = db.execute(metrics_query, {"workspace_id": str(workspace_id)})
                metric_rows = metrics_result.fetchall()
                metric_map = {m["name"]: dict(m._mapping) for m in metric_rows}

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
                        insert_query = text("""
                            INSERT INTO kpis.kpi_data_points
                            (metric_id, workspace_id, value, timestamp, period, metadata)
                            VALUES (:metric_id, :workspace_id, :value, :timestamp, :period, :metadata::jsonb)
                            RETURNING *
                        """)
                        result = db.execute(insert_query, {
                            "metric_id": str(data_point.metric_id),
                            "workspace_id": str(data_point.workspace_id),
                            "value": data_point.value,
                            "timestamp": data_point.timestamp,
                            "period": data_point.period.value,
                            "metadata": json.dumps(data_point.metadata)
                        })
                        db.commit()

                        row = result.fetchone()
                        if row:
                            metrics_synced += 1
                            self.logger.info(f"Synced {kpi_name}: {value}")

                    except Exception as e:
                        error_msg = f"Error syncing {kpi_name}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)

                # Calculate derived metrics
                await self._calculate_derived_metrics(workspace_id, metric_map, db=db)

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
                upsert_query = text("""
                    INSERT INTO kpis.kpi_sync_status
                    (workspace_id, last_sync_at, next_sync_at, status, metrics_synced, errors, metadata)
                    VALUES (:workspace_id, :last_sync_at, :next_sync_at, :status, :metrics_synced, :errors::jsonb, :metadata::jsonb)
                    ON CONFLICT (workspace_id)
                    DO UPDATE SET
                        last_sync_at = EXCLUDED.last_sync_at,
                        next_sync_at = EXCLUDED.next_sync_at,
                        status = EXCLUDED.status,
                        metrics_synced = EXCLUDED.metrics_synced,
                        errors = EXCLUDED.errors,
                        metadata = EXCLUDED.metadata
                """)
                db.execute(upsert_query, {
                    "workspace_id": str(workspace_id),
                    "last_sync_at": sync_status.last_sync_at,
                    "next_sync_at": sync_status.next_sync_at,
                    "status": sync_status.status,
                    "metrics_synced": sync_status.metrics_synced,
                    "errors": json.dumps(sync_status.errors),
                    "metadata": json.dumps(sync_status.metadata)
                })
                db.commit()

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
        metric_map: Dict[str, Any],
        db: Optional[Session] = None
    ) -> None:
        """
        Calculate derived metrics from base metrics

        Args:
            workspace_id: Workspace ID
            metric_map: Map of metric names to metric definitions
            db: Database session
        """
        if not db:
            return

        try:
            # Calculate LTV:CAC ratio if both metrics exist
            if "ltv" in metric_map and "cac" in metric_map:
                ltv_metric = metric_map["ltv"]
                cac_metric = metric_map["cac"]

                # Get latest LTV value
                ltv_query = text("""
                    SELECT value FROM kpis.kpi_data_points
                    WHERE metric_id = :metric_id
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                ltv_result = db.execute(ltv_query, {"metric_id": ltv_metric["id"]})
                ltv_row = ltv_result.fetchone()

                # Get latest CAC value
                cac_result = db.execute(ltv_query, {"metric_id": cac_metric["id"]})
                cac_row = cac_result.fetchone()

                if ltv_row and cac_row:
                    ltv_value = ltv_row["value"]
                    cac_value = cac_row["value"]

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

                            insert_query = text("""
                                INSERT INTO kpis.kpi_data_points
                                (metric_id, workspace_id, value, timestamp, period, metadata)
                                VALUES (:metric_id, :workspace_id, :value, :timestamp, :period, :metadata::jsonb)
                            """)
                            db.execute(insert_query, {
                                "metric_id": str(data_point.metric_id),
                                "workspace_id": str(data_point.workspace_id),
                                "value": data_point.value,
                                "timestamp": data_point.timestamp,
                                "period": data_point.period.value,
                                "metadata": json.dumps(data_point.metadata)
                            })
                            db.commit()

        except Exception as e:
            self.logger.error(f"Error calculating derived metrics: {str(e)}")

    async def get_current_snapshot(
        self,
        workspace_id: UUID,
        db: Optional[Session] = None
    ) -> KPISnapshot:
        """
        Get current snapshot of all KPIs

        Args:
            workspace_id: Workspace ID
            db: Database session

        Returns:
            KPISnapshot with current values
        """
        try:
            if not db:
                return KPISnapshot(
                    workspace_id=workspace_id,
                    timestamp=datetime.utcnow(),
                    metrics=[],
                    metadata={"error": "Database session not provided"}
                )

            # Get all metrics for workspace
            metrics_query = text("""
                SELECT * FROM kpis.kpi_metrics
                WHERE workspace_id = :workspace_id AND is_active = true
            """)
            metrics_result = db.execute(metrics_query, {"workspace_id": str(workspace_id)})
            metric_rows = metrics_result.fetchall()

            metrics = []

            for metric in metric_rows:
                # Get latest data point
                data_point_query = text("""
                    SELECT * FROM kpis.kpi_data_points
                    WHERE metric_id = :metric_id
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                data_point_result = db.execute(data_point_query, {"metric_id": metric["id"]})
                data_point_row = data_point_result.fetchone()

                if data_point_row:
                    metrics.append({
                        "metric_id": metric["id"],
                        "name": metric["name"],
                        "display_name": metric["display_name"],
                        "category": metric["category"],
                        "unit": metric["unit"],
                        "value": data_point_row["value"],
                        "timestamp": data_point_row["timestamp"]
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
        limit: int = 100,
        db: Optional[Session] = None
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
            db: Database session

        Returns:
            List of KPI data points
        """
        try:
            if not db:
                return []

            # Build query with filters
            conditions = [
                "metric_id = :metric_id",
                "workspace_id = :workspace_id",
                "period = :period"
            ]
            params = {
                "metric_id": str(metric_id),
                "workspace_id": str(workspace_id),
                "period": period.value,
                "limit": limit
            }

            if start_date:
                conditions.append("timestamp >= :start_date")
                params["start_date"] = start_date

            if end_date:
                conditions.append("timestamp <= :end_date")
                params["end_date"] = end_date

            query = text(f"""
                SELECT * FROM kpis.kpi_data_points
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
                LIMIT :limit
            """)

            result = db.execute(query, params)
            rows = result.fetchall()

            return [KPIDataPointResponse(**dict(row._mapping)) for row in rows]

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
