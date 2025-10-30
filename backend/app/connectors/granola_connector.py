"""
Granola MCP Connector
Handles KPIs and metrics from Granola
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class GranolaConnector(BaseConnector):
    """Connector for Granola API"""

    @property
    def platform_name(self) -> str:
        return "granola"

    @property
    def base_url(self) -> str:
        # Note: This is a placeholder URL - actual Granola API endpoint may differ
        return "https://api.granola.so/v1"

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Granola API"""
        try:
            self.validate_credentials()
            user_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "user": user_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Granola connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get authenticated user information"""
        return await self.make_request("GET", "/user")

    async def list_metrics(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> ConnectorResponse:
        """
        List available metrics

        Args:
            limit: Number of metrics to retrieve
            offset: Pagination offset

        Returns:
            ConnectorResponse with metrics list
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        return await self.make_request("GET", "/metrics", params=params)

    async def get_metric(
        self,
        metric_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ConnectorResponse:
        """
        Get metric data

        Args:
            metric_id: Metric ID
            start_date: Start date for data
            end_date: End date for data

        Returns:
            ConnectorResponse with metric data
        """
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        return await self.make_request("GET", f"/metrics/{metric_id}", params=params)

    async def get_dashboard_metrics(
        self,
        dashboard_id: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Get metrics for a dashboard

        Args:
            dashboard_id: Optional dashboard ID (defaults to main dashboard)

        Returns:
            ConnectorResponse with dashboard metrics
        """
        endpoint = "/dashboards/default/metrics" if not dashboard_id else f"/dashboards/{dashboard_id}/metrics"
        return await self.make_request("GET", endpoint)

    async def get_kpis(
        self,
        category: Optional[str] = None
    ) -> ConnectorResponse:
        """
        Get KPI summary

        Args:
            category: Optional category filter (revenue, users, growth, etc.)

        Returns:
            ConnectorResponse with KPI data
        """
        params = {}
        if category:
            params["category"] = category

        return await self.make_request("GET", "/kpis", params=params)

    async def get_insights(
        self,
        limit: int = 10
    ) -> ConnectorResponse:
        """
        Get AI-generated insights

        Args:
            limit: Number of insights to retrieve

        Returns:
            ConnectorResponse with insights
        """
        params = {"limit": limit}
        return await self.make_request("GET", "/insights", params=params)

    async def get_trends(
        self,
        metric_id: str,
        period: str = "week"
    ) -> ConnectorResponse:
        """
        Get trend analysis for a metric

        Args:
            metric_id: Metric ID
            period: Time period (day, week, month, quarter, year)

        Returns:
            ConnectorResponse with trend data
        """
        params = {"period": period}
        return await self.make_request("GET", f"/metrics/{metric_id}/trends", params=params)

    async def create_custom_metric(
        self,
        name: str,
        definition: Dict[str, Any]
    ) -> ConnectorResponse:
        """
        Create a custom metric

        Args:
            name: Metric name
            definition: Metric definition and calculation logic

        Returns:
            ConnectorResponse with created metric
        """
        json_data = {
            "name": name,
            "definition": definition
        }
        return await self.make_request("POST", "/metrics", json=json_data)
