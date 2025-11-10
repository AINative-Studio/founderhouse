"""
Feedback Service
Service for managing user feedback and improvement loops
Analyzes feedback sentiment and routes to appropriate teams
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from app.models.feedback import (
    FeedbackSubmitRequest,
    FeedbackResponse,
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackType,
    FeedbackCategory,
    FeedbackStatus,
    FeedbackSentiment,
    FeedbackAnalytics
)
from app.database import get_db_context
from sqlalchemy import text


logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for feedback management"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def submit_feedback(
        self,
        request: FeedbackSubmitRequest
    ) -> Optional[FeedbackResponse]:
        """
        Submit new feedback

        Args:
            request: Feedback submission request

        Returns:
            Created feedback record
        """
        try:
            # Analyze sentiment
            sentiment = self._analyze_sentiment(request.description)

            # Calculate priority score
            priority_score = self._calculate_priority(
                feedback_type=request.feedback_type,
                sentiment=sentiment,
                rating=request.rating
            )

            # Create feedback record
            feedback_create = FeedbackCreate(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                feedback_type=request.feedback_type,
                category=request.category,
                title=request.title,
                description=request.description,
                status=FeedbackStatus.NEW,
                sentiment=sentiment,
                context=request.context or {},
                rating=request.rating,
                attachments=request.attachments,
                contact_for_followup=request.contact_for_followup
            )

            # Save to database
            async with get_db_context() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO feedback
                        (workspace_id, founder_id, feedback_type, category, title, description,
                         status, sentiment, context, rating, attachments, contact_for_followup, priority_score)
                        VALUES (:workspace_id, :founder_id, :feedback_type, :category, :title, :description,
                                :status, :sentiment, :context, :rating, :attachments, :contact_for_followup, :priority_score)
                        RETURNING *
                    """),
                    {
                        "workspace_id": str(feedback_create.workspace_id),
                        "founder_id": str(feedback_create.founder_id),
                        "feedback_type": feedback_create.feedback_type.value,
                        "category": feedback_create.category.value,
                        "title": feedback_create.title,
                        "description": feedback_create.description,
                        "status": feedback_create.status.value,
                        "sentiment": sentiment.value if sentiment else None,
                        "context": feedback_create.context,
                        "rating": feedback_create.rating,
                        "attachments": feedback_create.attachments,
                        "contact_for_followup": feedback_create.contact_for_followup,
                        "priority_score": priority_score
                    }
                )
                await db.commit()
                row = result.fetchone()

            feedback = await self._build_feedback_response(row)

            # Trigger notifications for high priority feedback
            if priority_score > 0.8:
                await self._notify_high_priority_feedback(feedback)

            self.logger.info(f"Submitted feedback {feedback.id} with priority {priority_score:.2f}")
            return feedback

        except Exception as e:
            self.logger.error(f"Error submitting feedback: {str(e)}")
            return None

    async def get_feedback(self, feedback_id: UUID) -> Optional[FeedbackResponse]:
        """Get feedback by ID"""
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    text("SELECT * FROM feedback WHERE id = :id"),
                    {"id": str(feedback_id)}
                )
                row = result.fetchone()

                if not row:
                    return None

                return await self._build_feedback_response(row)

        except Exception as e:
            self.logger.error(f"Error getting feedback: {str(e)}")
            return None

    async def list_feedback(
        self,
        workspace_id: UUID,
        founder_id: Optional[UUID] = None,
        feedback_type: Optional[FeedbackType] = None,
        category: Optional[FeedbackCategory] = None,
        status: Optional[FeedbackStatus] = None,
        sentiment: Optional[FeedbackSentiment] = None,
        limit: int = 50
    ) -> List[FeedbackResponse]:
        """List feedback with filters"""
        try:
            query = "SELECT * FROM feedback WHERE workspace_id = :workspace_id"
            params = {"workspace_id": str(workspace_id)}

            if founder_id:
                query += " AND founder_id = :founder_id"
                params["founder_id"] = str(founder_id)

            if feedback_type:
                query += " AND feedback_type = :feedback_type"
                params["feedback_type"] = feedback_type.value

            if category:
                query += " AND category = :category"
                params["category"] = category.value

            if status:
                query += " AND status = :status"
                params["status"] = status.value

            if sentiment:
                query += " AND sentiment = :sentiment"
                params["sentiment"] = sentiment.value

            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit

            async with get_db_context() as db:
                result = await db.execute(text(query), params)
                rows = result.fetchall()

                feedback_list = []
                for row in rows:
                    feedback_list.append(await self._build_feedback_response(row))

                return feedback_list

        except Exception as e:
            self.logger.error(f"Error listing feedback: {str(e)}")
            return []

    async def update_feedback_status(
        self,
        feedback_id: UUID,
        status: FeedbackStatus,
        admin_notes: Optional[str] = None
    ) -> Optional[FeedbackResponse]:
        """Update feedback status"""
        try:
            update = FeedbackUpdate(
                status=status,
                admin_notes=admin_notes
            )

            if status in [FeedbackStatus.COMPLETED, FeedbackStatus.REJECTED]:
                update.resolved_at = datetime.utcnow()

            await self._update_feedback(feedback_id, update)

            return await self.get_feedback(feedback_id)

        except Exception as e:
            self.logger.error(f"Error updating feedback status: {str(e)}")
            return None

    async def upvote_feedback(self, feedback_id: UUID) -> bool:
        """Upvote feedback"""
        try:
            async with get_db_context() as db:
                await db.execute(
                    text("""
                        UPDATE feedback
                        SET upvotes = upvotes + 1
                        WHERE id = :id
                    """),
                    {"id": str(feedback_id)}
                )
                await db.commit()
                return True

        except Exception as e:
            self.logger.error(f"Error upvoting feedback: {str(e)}")
            return False

    async def get_analytics(
        self,
        workspace_id: UUID,
        days: int = 30
    ) -> FeedbackAnalytics:
        """Get feedback analytics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            async with get_db_context() as db:
                # Get total count
                result = await db.execute(
                    text("""
                        SELECT COUNT(*) FROM feedback
                        WHERE workspace_id = :workspace_id
                        AND created_at >= :start_date
                    """),
                    {
                        "workspace_id": str(workspace_id),
                        "start_date": start_date
                    }
                )
                total_feedback = result.fetchone()[0]

                # Get counts by type
                result = await db.execute(
                    text("""
                        SELECT feedback_type, COUNT(*) as count
                        FROM feedback
                        WHERE workspace_id = :workspace_id
                        AND created_at >= :start_date
                        GROUP BY feedback_type
                    """),
                    {
                        "workspace_id": str(workspace_id),
                        "start_date": start_date
                    }
                )
                by_type = {row[0]: row[1] for row in result.fetchall()}

                # Get counts by category
                result = await db.execute(
                    text("""
                        SELECT category, COUNT(*) as count
                        FROM feedback
                        WHERE workspace_id = :workspace_id
                        AND created_at >= :start_date
                        GROUP BY category
                    """),
                    {
                        "workspace_id": str(workspace_id),
                        "start_date": start_date
                    }
                )
                by_category = {row[0]: row[1] for row in result.fetchall()}

                # Get counts by status
                result = await db.execute(
                    text("""
                        SELECT status, COUNT(*) as count
                        FROM feedback
                        WHERE workspace_id = :workspace_id
                        AND created_at >= :start_date
                        GROUP BY status
                    """),
                    {
                        "workspace_id": str(workspace_id),
                        "start_date": start_date
                    }
                )
                by_status = {row[0]: row[1] for row in result.fetchall()}

                # Get counts by sentiment
                result = await db.execute(
                    text("""
                        SELECT sentiment, COUNT(*) as count
                        FROM feedback
                        WHERE workspace_id = :workspace_id
                        AND created_at >= :start_date
                        AND sentiment IS NOT NULL
                        GROUP BY sentiment
                    """),
                    {
                        "workspace_id": str(workspace_id),
                        "start_date": start_date
                    }
                )
                by_sentiment = {row[0]: row[1] for row in result.fetchall()}

                # Get average rating
                result = await db.execute(
                    text("""
                        SELECT AVG(rating) FROM feedback
                        WHERE workspace_id = :workspace_id
                        AND created_at >= :start_date
                        AND rating IS NOT NULL
                    """),
                    {
                        "workspace_id": str(workspace_id),
                        "start_date": start_date
                    }
                )
                avg_rating = result.fetchone()[0]

                return FeedbackAnalytics(
                    total_feedback=total_feedback,
                    by_type=by_type,
                    by_category=by_category,
                    by_status=by_status,
                    by_sentiment=by_sentiment,
                    average_rating=float(avg_rating) if avg_rating else None,
                    trending_topics=[],
                    top_requested_features=[]
                )

        except Exception as e:
            self.logger.error(f"Error getting analytics: {str(e)}")
            return FeedbackAnalytics(
                total_feedback=0,
                by_type={},
                by_category={},
                by_status={},
                by_sentiment={}
            )

    def _analyze_sentiment(self, text: str) -> FeedbackSentiment:
        """
        Analyze sentiment of feedback text

        In production, this would use NLP/sentiment analysis
        For now, use simple keyword matching
        """
        text_lower = text.lower()

        negative_keywords = ["bug", "error", "broken", "issue", "problem", "bad", "terrible", "awful"]
        positive_keywords = ["great", "awesome", "excellent", "love", "amazing", "fantastic"]

        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)

        if positive_count > negative_count:
            return FeedbackSentiment.POSITIVE
        elif negative_count > positive_count:
            return FeedbackSentiment.NEGATIVE
        else:
            return FeedbackSentiment.NEUTRAL

    def _calculate_priority(
        self,
        feedback_type: FeedbackType,
        sentiment: Optional[FeedbackSentiment],
        rating: Optional[int]
    ) -> float:
        """
        Calculate priority score (0-1)

        Higher score = higher priority
        """
        score = 0.5  # Base score

        # Type weighting
        type_weights = {
            FeedbackType.BUG_REPORT: 0.3,
            FeedbackType.COMPLAINT: 0.2,
            FeedbackType.FEATURE_REQUEST: 0.1,
            FeedbackType.IMPROVEMENT: 0.1,
            FeedbackType.SUGGESTION: 0.05,
            FeedbackType.QUESTION: 0.05,
            FeedbackType.PRAISE: -0.1
        }
        score += type_weights.get(feedback_type, 0)

        # Sentiment weighting
        if sentiment == FeedbackSentiment.NEGATIVE:
            score += 0.2
        elif sentiment == FeedbackSentiment.POSITIVE:
            score -= 0.1

        # Rating weighting
        if rating:
            if rating <= 2:
                score += 0.2
            elif rating >= 4:
                score -= 0.1

        # Clamp to 0-1
        return max(0.0, min(1.0, score))

    async def _notify_high_priority_feedback(self, feedback: FeedbackResponse):
        """Notify team of high priority feedback"""
        # In production, send notifications via Discord/Slack
        self.logger.warning(
            f"High priority feedback received: {feedback.title} "
            f"(Type: {feedback.feedback_type.value}, Sentiment: {feedback.sentiment.value if feedback.sentiment else 'unknown'})"
        )

    async def _update_feedback(self, feedback_id: UUID, update: FeedbackUpdate):
        """Update feedback record"""
        try:
            updates = []
            params = {"id": str(feedback_id)}

            if update.status:
                updates.append("status = :status")
                params["status"] = update.status.value

            if update.sentiment:
                updates.append("sentiment = :sentiment")
                params["sentiment"] = update.sentiment.value

            if update.admin_notes:
                updates.append("admin_notes = :admin_notes")
                params["admin_notes"] = update.admin_notes

            if update.priority_score is not None:
                updates.append("priority_score = :priority_score")
                params["priority_score"] = update.priority_score

            if update.resolved_at:
                updates.append("resolved_at = :resolved_at")
                params["resolved_at"] = update.resolved_at

            updates.append("updated_at = NOW()")

            if updates:
                query = f"UPDATE feedback SET {', '.join(updates)} WHERE id = :id"
                async with get_db_context() as db:
                    await db.execute(text(query), params)
                    await db.commit()

        except Exception as e:
            self.logger.error(f"Error updating feedback: {str(e)}")

    async def _build_feedback_response(self, row) -> FeedbackResponse:
        """Build feedback response from database row"""
        return FeedbackResponse(
            id=row.id,
            workspace_id=UUID(row.workspace_id),
            founder_id=UUID(row.founder_id),
            feedback_type=FeedbackType(row.feedback_type),
            category=FeedbackCategory(row.category),
            title=row.title,
            description=row.description,
            status=FeedbackStatus(row.status),
            sentiment=FeedbackSentiment(row.sentiment) if row.sentiment else None,
            context=row.context or {},
            rating=row.rating,
            attachments=row.attachments or [],
            contact_for_followup=row.contact_for_followup,
            admin_notes=row.admin_notes,
            priority_score=row.priority_score,
            related_tasks=[UUID(t) for t in (row.related_tasks or [])],
            upvotes=row.upvotes,
            created_at=row.created_at,
            updated_at=row.updated_at,
            resolved_at=row.resolved_at
        )
