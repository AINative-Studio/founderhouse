"""
Task Routing Service
Converts action items to tasks in Monday.com and other platforms
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.connectors.monday_connector import MondayConnector
from app.models.action_item import ActionItem, ActionItemPriority


logger = logging.getLogger(__name__)


class TaskRoutingService:
    """
    Routes action items to task management platforms

    Features:
    - Action item → Monday.com task conversion
    - Assignee inference from mentions/context
    - Priority classification
    - Due date inference
    - Task metadata enrichment
    """

    # Priority mapping to Monday.com labels
    MONDAY_PRIORITY_MAP = {
        ActionItemPriority.URGENT: "Critical",
        ActionItemPriority.HIGH: "High",
        ActionItemPriority.NORMAL: "Medium",
        ActionItemPriority.LOW: "Low"
    }

    def __init__(self, supabase_client=None):
        """
        Initialize task routing service

        Args:
            supabase_client: Supabase client for database operations
        """
        self.supabase = supabase_client
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def create_task_from_action_item(
        self,
        action_item: ActionItem,
        platform: str = "monday",
        credentials: Dict[str, Any] = None,
        board_id: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create task from action item

        Args:
            action_item: Action item to convert
            platform: Task platform (monday, notion)
            credentials: Platform credentials
            board_id: Target board/project ID
            additional_metadata: Additional task metadata

        Returns:
            Dictionary with task creation result
        """
        try:
            if platform == "monday":
                return await self._create_monday_task(
                    action_item,
                    credentials,
                    board_id,
                    additional_metadata
                )
            elif platform == "notion":
                # Placeholder for Notion integration
                raise NotImplementedError("Notion task creation not yet implemented")
            else:
                raise ValueError(f"Unsupported platform: {platform}")

        except Exception as e:
            self.logger.error(f"Failed to create task from action item {action_item.id}: {str(e)}")
            raise

    async def _create_monday_task(
        self,
        action_item: ActionItem,
        credentials: Dict[str, Any],
        board_id: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create task in Monday.com from action item"""
        try:
            # Connect to Monday
            async with MondayConnector(credentials) as monday:
                # If no board_id provided, get default board
                if not board_id:
                    boards_response = await monday.list_boards(limit=1)
                    boards = boards_response.data.get("data", {}).get("boards", [])
                    if not boards:
                        raise ValueError("No Monday.com boards found")
                    board_id = boards[0]["id"]

                # Build column values
                column_values = self._build_monday_column_values(
                    action_item,
                    additional_metadata
                )

                # Create item
                create_response = await monday.create_item(
                    board_id=board_id,
                    item_name=action_item.description[:255],  # Monday has char limit
                    column_values=column_values
                )

                item_data = create_response.data.get("data", {}).get("create_item", {})
                item_id = item_data.get("id")

                # Add context as update/comment
                if action_item.context:
                    await monday.create_update(
                        item_id=item_id,
                        body=f"Context from meeting:\n{action_item.context}"
                    )

                # Update action item with task info
                if self.supabase:
                    await self._update_action_item_task_info(
                        action_item.id,
                        task_platform="monday",
                        task_id=item_id,
                        task_url=f"https://monday.com/boards/{board_id}/pulses/{item_id}"
                    )

                self.logger.info(f"Created Monday task {item_id} from action item {action_item.id}")

                return {
                    "platform": "monday",
                    "task_id": item_id,
                    "board_id": board_id,
                    "task_url": f"https://monday.com/boards/{board_id}/pulses/{item_id}",
                    "action_item_id": str(action_item.id),
                    "status": "created"
                }

        except Exception as e:
            self.logger.error(f"Failed to create Monday task: {str(e)}")
            raise

    def _build_monday_column_values(
        self,
        action_item: ActionItem,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build Monday.com column values from action item"""
        column_values = {}

        # Status
        column_values["status"] = {"label": "To Do"}

        # Priority
        if action_item.priority:
            priority_label = self.MONDAY_PRIORITY_MAP.get(
                action_item.priority,
                "Medium"
            )
            column_values["priority"] = {"label": priority_label}

        # Due date
        if action_item.due_date:
            column_values["date"] = {
                "date": action_item.due_date.strftime("%Y-%m-%d")
            }

        # Person (assignee)
        if action_item.assignee_email:
            column_values["person"] = {
                "personsAndTeams": [
                    {"id": action_item.assignee_email, "kind": "person"}
                ]
            }

        # Tags
        if action_item.tags:
            column_values["tags"] = {"tag_ids": action_item.tags}

        # Add any additional metadata
        if additional_metadata:
            column_values.update(additional_metadata)

        return column_values

    async def batch_create_tasks(
        self,
        action_items: List[ActionItem],
        platform: str = "monday",
        credentials: Dict[str, Any] = None,
        board_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Create multiple tasks from action items

        Args:
            action_items: List of action items
            platform: Task platform
            credentials: Platform credentials
            board_id: Target board ID

        Returns:
            List of task creation results
        """
        results = []

        for action_item in action_items:
            try:
                result = await self.create_task_from_action_item(
                    action_item=action_item,
                    platform=platform,
                    credentials=credentials,
                    board_id=board_id
                )
                results.append({
                    "action_item_id": str(action_item.id),
                    "status": "success",
                    "result": result
                })

            except Exception as e:
                self.logger.error(f"Failed to create task for action item {action_item.id}: {str(e)}")
                results.append({
                    "action_item_id": str(action_item.id),
                    "status": "failed",
                    "error": str(e)
                })

        return results

    async def create_tasks_from_meeting(
        self,
        meeting_id: UUID,
        platform: str = "monday",
        credentials: Dict[str, Any] = None,
        board_id: Optional[str] = None,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Create tasks from all action items in a meeting

        Args:
            meeting_id: Meeting UUID
            platform: Task platform
            credentials: Platform credentials
            board_id: Target board ID
            min_confidence: Minimum confidence score for action items

        Returns:
            List of task creation results
        """
        try:
            # Fetch action items for meeting
            action_items = await self._get_meeting_action_items(meeting_id)

            # Filter by confidence
            filtered_items = [
                item for item in action_items
                if item.confidence_score >= min_confidence
            ]

            self.logger.info(
                f"Creating tasks for {len(filtered_items)} action items "
                f"(filtered from {len(action_items)} total)"
            )

            # Create tasks
            return await self.batch_create_tasks(
                action_items=filtered_items,
                platform=platform,
                credentials=credentials,
                board_id=board_id
            )

        except Exception as e:
            self.logger.error(f"Failed to create tasks from meeting {meeting_id}: {str(e)}")
            raise

    async def _update_action_item_task_info(
        self,
        action_item_id: UUID,
        task_platform: str,
        task_id: str,
        task_url: str
    ) -> None:
        """Update action item with task information"""
        if not self.supabase:
            return

        try:
            update_data = {
                "task_platform": task_platform,
                "task_id": task_id,
                "task_url": task_url,
                "updated_at": datetime.utcnow().isoformat()
            }

            self.supabase.table("action_items").update(update_data).eq(
                "id", str(action_item_id)
            ).execute()

        except Exception as e:
            self.logger.error(f"Failed to update action item task info: {str(e)}")

    async def _get_meeting_action_items(self, meeting_id: UUID) -> List[ActionItem]:
        """Fetch action items for a meeting"""
        if not self.supabase:
            return []

        try:
            result = self.supabase.table("action_items").select("*").eq(
                "meeting_id", str(meeting_id)
            ).execute()

            return [ActionItem(**item) for item in result.data]

        except Exception as e:
            self.logger.error(f"Failed to fetch action items: {str(e)}")
            return []

    async def link_task_to_meeting(
        self,
        task_id: str,
        meeting_id: UUID,
        platform: str = "monday",
        credentials: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Link existing task to meeting

        Args:
            task_id: Task ID in platform
            meeting_id: Meeting UUID
            platform: Task platform
            credentials: Platform credentials

        Returns:
            Link result
        """
        try:
            if platform == "monday":
                async with MondayConnector(credentials) as monday:
                    # Add meeting link as update
                    meeting_url = f"/meetings/{meeting_id}"  # Adjust based on frontend routing
                    await monday.create_update(
                        item_id=task_id,
                        body=f"Linked to meeting: {meeting_url}"
                    )

            return {
                "task_id": task_id,
                "meeting_id": str(meeting_id),
                "status": "linked"
            }

        except Exception as e:
            self.logger.error(f"Failed to link task to meeting: {str(e)}")
            raise
