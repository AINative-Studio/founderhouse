"""
Fireflies.ai MCP Connector
Handles meeting transcripts from Fireflies
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class FirefliesConnector(BaseConnector):
    """Connector for Fireflies.ai GraphQL API"""

    @property
    def platform_name(self) -> str:
        return "fireflies"

    @property
    def base_url(self) -> str:
        return "https://api.fireflies.ai/graphql"

    def _get_default_headers(self) -> Dict[str, str]:
        """Override to use API key in Authorization header"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AI-Chief-of-Staff/1.0"
        }

        api_key = self.credentials.get("api_key") or self.credentials.get("access_token")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        return headers

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to Fireflies API"""
        try:
            self.validate_credentials()
            user_info = await self.get_user_info()
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "user": user_info.data},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"Fireflies connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get authenticated user information"""
        query = """
        query {
            user {
                user_id
                name
                email
            }
        }
        """
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

    async def list_transcripts(
        self,
        limit: int = 50,
        skip: int = 0
    ) -> ConnectorResponse:
        """
        List meeting transcripts

        Args:
            limit: Number of transcripts to retrieve
            skip: Number of transcripts to skip

        Returns:
            ConnectorResponse with transcripts list
        """
        query = f"""
        query {{
            transcripts(limit: {limit}, skip: {skip}) {{
                id
                title
                date
                duration
                host_name
                host_email
                meeting_attendees {{
                    displayName
                    email
                }}
                summary {{
                    overview
                    action_items
                    keywords
                }}
            }}
        }}
        """
        return await self._execute_query(query)

    async def get_transcript(self, transcript_id: str) -> ConnectorResponse:
        """
        Get transcript details

        Args:
            transcript_id: Transcript ID

        Returns:
            ConnectorResponse with transcript details
        """
        query = f"""
        query {{
            transcript(id: "{transcript_id}") {{
                id
                title
                date
                duration
                transcript_url
                audio_url
                video_url
                host_name
                host_email
                meeting_attendees {{
                    displayName
                    email
                }}
                summary {{
                    overview
                    action_items
                    keywords
                    outline
                }}
                sentences {{
                    text
                    speaker_name
                    start_time
                    end_time
                }}
            }}
        }}
        """
        return await self._execute_query(query)

    async def search_transcripts(
        self,
        query: str,
        limit: int = 50
    ) -> ConnectorResponse:
        """
        Search transcripts

        Args:
            query: Search query
            limit: Number of results

        Returns:
            ConnectorResponse with search results
        """
        graphql_query = f"""
        query {{
            transcripts(search: "{query}", limit: {limit}) {{
                id
                title
                date
                duration
                host_name
                summary {{
                    overview
                    action_items
                }}
            }}
        }}
        """
        return await self._execute_query(graphql_query)

    async def get_transcript_summary(self, transcript_id: str) -> ConnectorResponse:
        """
        Get transcript summary only

        Args:
            transcript_id: Transcript ID

        Returns:
            ConnectorResponse with summary
        """
        query = f"""
        query {{
            transcript(id: "{transcript_id}") {{
                id
                title
                summary {{
                    overview
                    action_items
                    keywords
                    outline
                }}
            }}
        }}
        """
        return await self._execute_query(query)
