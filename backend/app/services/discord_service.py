"""
Discord Integration Service
Service for posting updates and briefings to Discord
Integrates with Discord MCP connector for bot operations
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.models.discord_message import (
    DiscordStatusUpdateRequest,
    DiscordBriefingRequest,
    DiscordMessageResponse,
    DiscordMessageCreate,
    DiscordMessageUpdate,
    DiscordMessageType,
    DiscordMessageStatus,
    DiscordEmbed
)
from app.models.briefing import BriefingResponse
from app.services.briefing_service import BriefingService
from app.database import get_db_context
from app.config import get_settings
from sqlalchemy import text


logger = logging.getLogger(__name__)


class DiscordService:
    """Service for Discord integration"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        self.briefing_service = BriefingService()

    async def post_status_update(
        self,
        request: DiscordStatusUpdateRequest
    ) -> Optional[DiscordMessageResponse]:
        """
        Post a status update to Discord

        Args:
            request: Status update request

        Returns:
            Message record
        """
        try:
            # Get or determine channel ID
            channel_id = request.channel_id or await self._get_default_channel(
                request.workspace_id,
                "status-updates"
            )

            # Create embed if provided
            embed_data = None
            if request.embed:
                embed_data = request.embed

            # Create message record
            message_create = DiscordMessageCreate(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                message_type=DiscordMessageType.STATUS_UPDATE,
                channel_id=channel_id,
                channel_name=request.channel_name,
                message_content=request.message,
                status=DiscordMessageStatus.PENDING,
                embed_data=embed_data
            )

            # Save to database
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO discord_messages
                        (workspace_id, founder_id, message_type, channel_id, channel_name, message_content, status, embed_data)
                        VALUES (:workspace_id, :founder_id, :message_type, :channel_id, :channel_name, :message_content, :status, :embed_data)
                        RETURNING *
                    """),
                    {
                        "workspace_id": str(message_create.workspace_id),
                        "founder_id": str(message_create.founder_id),
                        "message_type": message_create.message_type.value,
                        "channel_id": message_create.channel_id,
                        "channel_name": message_create.channel_name,
                        "message_content": message_create.message_content,
                        "status": message_create.status.value,
                        "embed_data": message_create.embed_data
                    }
                )
                await db.commit()
                row = result.fetchone()

            message_id = row.id

            # Send to Discord
            discord_message_id = await self._send_to_discord(
                channel_id=channel_id,
                content=request.message,
                embed=embed_data,
                mentions=request.mentions
            )

            # Update message status
            await self._update_message(
                message_id,
                DiscordMessageUpdate(
                    status=DiscordMessageStatus.SENT,
                    discord_message_id=discord_message_id,
                    sent_at=datetime.utcnow()
                )
            )

            # Get updated message
            message = await self.get_message(message_id)

            self.logger.info(f"Posted status update to Discord channel {channel_id}")
            return message

        except Exception as e:
            self.logger.error(f"Error posting status update: {str(e)}")
            if 'message_id' in locals():
                await self._update_message(
                    message_id,
                    DiscordMessageUpdate(
                        status=DiscordMessageStatus.FAILED,
                        error_message=str(e)
                    )
                )
            return None

    async def send_briefing(
        self,
        request: DiscordBriefingRequest
    ) -> Optional[DiscordMessageResponse]:
        """
        Send a daily briefing to Discord

        Args:
            request: Briefing request

        Returns:
            Message record
        """
        try:
            # Get briefing
            if request.briefing_id:
                # Get specific briefing
                async with get_db_context() as db:
                    result = await db.execute(
                        text("SELECT * FROM briefings WHERE id = :id"),
                        {"id": str(request.briefing_id)}
                    )
                    row = result.fetchone()
                    if not row:
                        raise ValueError(f"Briefing {request.briefing_id} not found")
                    briefing = BriefingResponse(**dict(row))
            else:
                # Get latest morning briefing
                briefing = await self.briefing_service.generate_briefing(
                    workspace_id=request.workspace_id,
                    founder_id=request.founder_id,
                    briefing_type="morning"
                )

            if not briefing:
                raise ValueError("No briefing available")

            # Format briefing for Discord
            embed = await self._format_briefing_embed(
                briefing,
                include_metrics=request.include_metrics,
                include_action_items=request.include_action_items
            )

            # Get channel ID
            channel_id = request.channel_id or await self._get_default_channel(
                request.workspace_id,
                request.channel_name
            )

            # Create message record
            message_create = DiscordMessageCreate(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                message_type=DiscordMessageType.BRIEFING,
                channel_id=channel_id,
                channel_name=request.channel_name,
                message_content=briefing.title,
                status=DiscordMessageStatus.PENDING,
                embed_data=embed.model_dump()
            )

            # Save to database
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO discord_messages
                        (workspace_id, founder_id, message_type, channel_id, channel_name, message_content, status, embed_data)
                        VALUES (:workspace_id, :founder_id, :message_type, :channel_id, :channel_name, :message_content, :status, :embed_data)
                        RETURNING *
                    """),
                    {
                        "workspace_id": str(message_create.workspace_id),
                        "founder_id": str(message_create.founder_id),
                        "message_type": message_create.message_type.value,
                        "channel_id": message_create.channel_id,
                        "channel_name": message_create.channel_name,
                        "message_content": message_create.message_content,
                        "status": message_create.status.value,
                        "embed_data": message_create.embed_data
                    }
                )
                await db.commit()
                row = result.fetchone()

            message_id = row.id

            # Send to Discord
            mentions = []
            if request.mention_team:
                mentions = ["@here"]

            discord_message_id = await self._send_to_discord(
                channel_id=channel_id,
                content=f"**{briefing.title}**",
                embed=embed.model_dump(),
                mentions=mentions
            )

            # Update message status
            await self._update_message(
                message_id,
                DiscordMessageUpdate(
                    status=DiscordMessageStatus.SENT,
                    discord_message_id=discord_message_id,
                    sent_at=datetime.utcnow()
                )
            )

            message = await self.get_message(message_id)

            self.logger.info(f"Sent briefing to Discord channel {channel_id}")
            return message

        except Exception as e:
            self.logger.error(f"Error sending briefing: {str(e)}")
            if 'message_id' in locals():
                await self._update_message(
                    message_id,
                    DiscordMessageUpdate(
                        status=DiscordMessageStatus.FAILED,
                        error_message=str(e)
                    )
                )
            return None

    async def get_message(self, message_id: UUID) -> Optional[DiscordMessageResponse]:
        """Get message by ID"""
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("SELECT * FROM discord_messages WHERE id = :id"),
                    {"id": str(message_id)}
                )
                row = result.fetchone()

                if not row:
                    return None

                return DiscordMessageResponse(
                    id=row.id,
                    workspace_id=UUID(row.workspace_id),
                    founder_id=UUID(row.founder_id),
                    message_type=DiscordMessageType(row.message_type),
                    channel_id=row.channel_id,
                    channel_name=row.channel_name,
                    message_content=row.message_content,
                    discord_message_id=row.discord_message_id,
                    status=DiscordMessageStatus(row.status),
                    embed_data=row.embed_data,
                    error_message=row.error_message,
                    sent_at=row.sent_at,
                    created_at=row.created_at
                )

        except Exception as e:
            self.logger.error(f"Error getting message: {str(e)}")
            return None

    async def _send_to_discord(
        self,
        channel_id: str,
        content: str,
        embed: Optional[Dict[str, Any]] = None,
        mentions: List[str] = None
    ) -> str:
        """
        Send message to Discord via MCP connector

        In production, this would use Discord MCP connector
        For now, simulate sending

        Args:
            channel_id: Discord channel ID
            content: Message content
            embed: Discord embed object
            mentions: List of user/role mentions

        Returns:
            Discord message ID
        """
        # In production, use Discord MCP:
        # discord_mcp = DiscordMCP(token=self.settings.discord_bot_token)
        # message_id = await discord_mcp.send_message(channel_id, content, embed, mentions)

        # For now, simulate
        import hashlib
        message_id = hashlib.md5(f"{channel_id}{content}".encode()).hexdigest()

        self.logger.info(f"Simulated Discord message sent to {channel_id}")
        return message_id

    async def _get_default_channel(
        self,
        workspace_id: UUID,
        channel_name: str = "general"
    ) -> str:
        """
        Get default Discord channel for workspace

        In production, this would fetch from workspace settings
        """
        # For now, return a mock channel ID
        return f"channel_{workspace_id}_{channel_name}"

    async def _format_briefing_embed(
        self,
        briefing: BriefingResponse,
        include_metrics: bool = True,
        include_action_items: bool = True
    ) -> DiscordEmbed:
        """
        Format briefing as Discord embed

        Args:
            briefing: Briefing to format
            include_metrics: Include metrics in embed
            include_action_items: Include action items

        Returns:
            Discord embed object
        """
        fields = []

        # Add summary
        fields.append({
            "name": "Summary",
            "value": briefing.summary[:1024] if briefing.summary else "No summary available",
            "inline": False
        })

        # Add highlights
        if briefing.key_highlights:
            highlights_text = "\n".join([f"• {h}" for h in briefing.key_highlights[:5]])
            fields.append({
                "name": "Key Highlights",
                "value": highlights_text[:1024],
                "inline": False
            })

        # Add action items
        if include_action_items and briefing.action_items:
            actions_text = "\n".join([f"• {a}" for a in briefing.action_items[:5]])
            fields.append({
                "name": "Action Items",
                "value": actions_text[:1024],
                "inline": False
            })

        # Create embed
        embed = DiscordEmbed(
            title=briefing.title,
            description=f"Briefing for {briefing.start_date.strftime('%B %d, %Y')}",
            color=0x5865F2,  # Discord blurple
            fields=fields,
            footer={
                "text": "AI Chief of Staff"
            },
            timestamp=datetime.utcnow()
        )

        return embed

    async def _update_message(
        self,
        message_id: UUID,
        update: DiscordMessageUpdate
    ):
        """Update message record"""
        try:
            updates = []
            params = {"id": str(message_id)}

            if update.status:
                updates.append("status = :status")
                params["status"] = update.status.value

            if update.discord_message_id:
                updates.append("discord_message_id = :discord_message_id")
                params["discord_message_id"] = update.discord_message_id

            if update.error_message:
                updates.append("error_message = :error_message")
                params["error_message"] = update.error_message

            if update.sent_at:
                updates.append("sent_at = :sent_at")
                params["sent_at"] = update.sent_at

            if updates:
                query = f"UPDATE discord_messages SET {', '.join(updates)} WHERE id = :id"
                async with get_db_context() as db:
                    await db.execute(text(query), params)
                    await db.commit()

        except Exception as e:
            self.logger.error(f"Error updating message: {str(e)}")
