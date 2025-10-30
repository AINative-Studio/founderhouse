"""
Monday.com MCP Connector
Handles Monday boards, items, and updates
"""
from typing import Dict, Any, List, Optional

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class MondayConnector(BaseConnector):
    """Connector for Monday.com GraphQL API"""

    @property
    def platform_name(self) -> str:
        return "monday"

    @property
    def base_url(self) -> str:
        return "https://api.monday.com/v2"

    def _get_default_headers(self) -> Dict[str, str]:
        """Override to use API token format for Monday"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AI-Chief-of-Staff/1.0"
        }

        api_token = self.credentials.get("api_token") or self.credentials.get("access_token")
        if api_token:
            headers["Authorization"] = api_token  # Monday uses direct token, not Bearer

        return headers

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Monday API"""
        try:
            self.validate_credentials()
            user_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "user": user_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Monday connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get authenticated user information"""
        query = "query { me { id name email } }"
        return await self._execute_query(query)

    async def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> ConnectorResponse:
        """
        Execute a GraphQL query

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            ConnectorResponse with query results
        """
        json_data = {"query": query}
        if variables:
            json_data["variables"] = variables

        response = await self.make_request("POST", "", json=json_data)

        # Check for GraphQL errors
        if response.data and "errors" in response.data:
            error_msg = response.data["errors"][0].get("message", "Unknown GraphQL error")
            raise ConnectorError(f"GraphQL error: {error_msg}")

        return response

    async def list_boards(self, limit: int = 50) -> ConnectorResponse:
        """
        List Monday boards

        Args:
            limit: Number of boards to retrieve

        Returns:
            ConnectorResponse with boards list
        """
        query = f"""
        query {{
            boards(limit: {limit}) {{
                id
                name
                description
                state
                board_kind
                columns {{
                    id
                    title
                    type
                }}
            }}
        }}
        """
        return await self._execute_query(query)

    async def get_board(self, board_id: str) -> ConnectorResponse:
        """
        Get board details

        Args:
            board_id: Board ID

        Returns:
            ConnectorResponse with board details
        """
        query = f"""
        query {{
            boards(ids: [{board_id}]) {{
                id
                name
                description
                state
                columns {{
                    id
                    title
                    type
                }}
                groups {{
                    id
                    title
                }}
            }}
        }}
        """
        return await self._execute_query(query)

    async def list_items(
        self,
        board_id: str,
        limit: int = 50
    ) -> ConnectorResponse:
        """
        List items in a board

        Args:
            board_id: Board ID
            limit: Number of items to retrieve

        Returns:
            ConnectorResponse with items list
        """
        query = f"""
        query {{
            boards(ids: [{board_id}]) {{
                items(limit: {limit}) {{
                    id
                    name
                    state
                    created_at
                    updated_at
                    column_values {{
                        id
                        title
                        text
                        value
                    }}
                }}
            }}
        }}
        """
        return await self._execute_query(query)

    async def create_item(
        self,
        board_id: str,
        item_name: str,
        group_id: Optional[str] = None,
        column_values: Optional[Dict[str, Any]] = None
    ) -> ConnectorResponse:
        """
        Create a new item in a board

        Args:
            board_id: Board ID
            item_name: Item name
            group_id: Optional group ID
            column_values: Optional column values as dict

        Returns:
            ConnectorResponse with created item details
        """
        import json

        column_values_str = ""
        if column_values:
            column_values_str = f', column_values: {json.dumps(json.dumps(column_values))}'

        group_str = f', group_id: "{group_id}"' if group_id else ""

        query = f"""
        mutation {{
            create_item(
                board_id: {board_id},
                item_name: "{item_name}"{group_str}{column_values_str}
            ) {{
                id
                name
                state
            }}
        }}
        """
        return await self._execute_query(query)

    async def update_item(
        self,
        item_id: str,
        column_values: Dict[str, Any]
    ) -> ConnectorResponse:
        """
        Update an item's column values

        Args:
            item_id: Item ID
            column_values: Column values to update

        Returns:
            ConnectorResponse with updated item details
        """
        import json

        column_values_str = json.dumps(json.dumps(column_values))

        query = f"""
        mutation {{
            change_multiple_column_values(
                item_id: {item_id},
                board_id: 0,
                column_values: {column_values_str}
            ) {{
                id
                name
            }}
        }}
        """
        return await self._execute_query(query)

    async def create_update(
        self,
        item_id: str,
        body: str
    ) -> ConnectorResponse:
        """
        Create an update (comment) on an item

        Args:
            item_id: Item ID
            body: Update text

        Returns:
            ConnectorResponse with created update details
        """
        query = f"""
        mutation {{
            create_update(
                item_id: {item_id},
                body: "{body}"
            ) {{
                id
                body
                created_at
            }}
        }}
        """
        return await self._execute_query(query)

    async def list_workspaces(self) -> ConnectorResponse:
        """
        List workspaces

        Returns:
            ConnectorResponse with workspaces list
        """
        query = """
        query {
            workspaces {
                id
                name
                description
            }
        }
        """
        return await self._execute_query(query)
