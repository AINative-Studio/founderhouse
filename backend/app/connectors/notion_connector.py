"""
Notion MCP Connector
Handles Notion pages and databases
"""
from typing import Dict, Any, List, Optional

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class NotionConnector(BaseConnector):
    """Connector for Notion API"""

    @property
    def platform_name(self) -> str:
        return "notion"

    @property
    def base_url(self) -> str:
        return "https://api.notion.com/v1"

    def _get_default_headers(self) -> Dict[str, str]:
        """Override to add Notion-Version header"""
        headers = super()._get_default_headers()
        headers["Notion-Version"] = "2022-06-28"  # API version
        return headers

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Notion API"""
        try:
            self.validate_credentials()
            user_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "user": user_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Notion connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get bot user information"""
        return await self.make_request("GET", "/users/me")

    async def search(
        self,
        query: Optional[str] = None,
        filter_type: Optional[str] = None,
        page_size: int = 100
    ) -> ConnectorResponse:
        """
        Search Notion workspace

        Args:
            query: Search query text
            filter_type: Filter by "page" or "database"
            page_size: Number of results per page

        Returns:
            ConnectorResponse with search results
        """
        json_data = {"page_size": page_size}
        if query:
            json_data["query"] = query
        if filter_type:
            json_data["filter"] = {"value": filter_type, "property": "object"}

        return await self.make_request("POST", "/search", json=json_data)

    async def get_page(self, page_id: str) -> ConnectorResponse:
        """
        Get page details

        Args:
            page_id: Page ID

        Returns:
            ConnectorResponse with page details
        """
        return await self.make_request("GET", f"/pages/{page_id}")

    async def get_page_content(self, page_id: str) -> ConnectorResponse:
        """
        Get page content blocks

        Args:
            page_id: Page ID

        Returns:
            ConnectorResponse with page blocks
        """
        return await self.make_request("GET", f"/blocks/{page_id}/children")

    async def create_page(
        self,
        parent_id: str,
        parent_type: str = "database_id",
        title: str = "",
        properties: Optional[Dict[str, Any]] = None
    ) -> ConnectorResponse:
        """
        Create a new page

        Args:
            parent_id: Parent database or page ID
            parent_type: Type of parent ("database_id" or "page_id")
            title: Page title
            properties: Page properties

        Returns:
            ConnectorResponse with created page details
        """
        json_data = {
            "parent": {parent_type: parent_id}
        }

        if properties:
            json_data["properties"] = properties
        elif title:
            json_data["properties"] = {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            }

        return await self.make_request("POST", "/pages", json=json_data)

    async def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any]
    ) -> ConnectorResponse:
        """
        Update page properties

        Args:
            page_id: Page ID
            properties: Properties to update

        Returns:
            ConnectorResponse with updated page
        """
        json_data = {"properties": properties}
        return await self.make_request("PATCH", f"/pages/{page_id}", json=json_data)

    async def query_database(
        self,
        database_id: str,
        filter_conditions: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100
    ) -> ConnectorResponse:
        """
        Query a database

        Args:
            database_id: Database ID
            filter_conditions: Filter conditions
            sorts: Sort configuration
            page_size: Number of results

        Returns:
            ConnectorResponse with query results
        """
        json_data = {"page_size": page_size}
        if filter_conditions:
            json_data["filter"] = filter_conditions
        if sorts:
            json_data["sorts"] = sorts

        return await self.make_request("POST", f"/databases/{database_id}/query", json=json_data)

    async def get_database(self, database_id: str) -> ConnectorResponse:
        """
        Get database details

        Args:
            database_id: Database ID

        Returns:
            ConnectorResponse with database details
        """
        return await self.make_request("GET", f"/databases/{database_id}")

    async def append_block_children(
        self,
        block_id: str,
        children: List[Dict[str, Any]]
    ) -> ConnectorResponse:
        """
        Append content blocks to a page or block

        Args:
            block_id: Parent block ID
            children: List of block objects to append

        Returns:
            ConnectorResponse with appended blocks
        """
        json_data = {"children": children}
        return await self.make_request("PATCH", f"/blocks/{block_id}/children", json=json_data)

    async def list_users(self, page_size: int = 100) -> ConnectorResponse:
        """
        List users in workspace

        Args:
            page_size: Number of users per page

        Returns:
            ConnectorResponse with users list
        """
        params = {"page_size": page_size}
        return await self.make_request("GET", "/users", params=params)
