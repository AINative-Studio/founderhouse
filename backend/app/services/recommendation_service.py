"""
Recommendation Service
Service for generating and managing strategic recommendations
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.chains.recommendation_chain import RecommendationChain
from app.models.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
    RecommendationContext,
    GenerateRecommendationRequest,
    RecommendationType,
    RecommendationPriority,
    RecommendationStatus,
    ImpactLevel
)
from app.database import get_supabase_client


logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for generating and managing recommendations"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.logger = logging.getLogger(__name__)
        self.recommendation_chain = RecommendationChain()

    async def generate_recommendations(
        self,
        request: GenerateRecommendationRequest
    ) -> List[RecommendationResponse]:
        """
        Generate new recommendations based on data analysis

        Args:
            request: Generation request with parameters

        Returns:
            List of generated recommendations
        """
        try:
            # Build context
            context = await self._build_context(
                workspace_id=request.workspace_id,
                founder_id=request.founder_id,
                time_range_days=request.time_range_days,
                include_metrics=request.include_metrics,
                include_anomalies=request.include_anomalies
            )

            # Generate recommendations using LLM
            raw_recommendations = await self.recommendation_chain.generate_recommendations(
                context=context,
                max_recommendations=request.max_recommendations
            )

            # Create and save recommendations
            recommendations = []
            for rec_data in raw_recommendations:
                # Filter by confidence threshold
                if rec_data.get("confidence", 0) < request.min_confidence:
                    continue

                # Filter by focus areas if specified
                if request.focus_areas:
                    rec_type = rec_data.get("type", "")
                    if rec_type not in [fa.value for fa in request.focus_areas]:
                        continue

                recommendation = await self._create_recommendation(
                    workspace_id=request.workspace_id,
                    founder_id=request.founder_id,
                    rec_data=rec_data,
                    context=context
                )

                if recommendation:
                    recommendations.append(recommendation)

            self.logger.info(
                f"Generated {len(recommendations)} recommendations for founder {request.founder_id}"
            )

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {str(e)}")
            return []

    async def _build_context(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        time_range_days: int,
        include_metrics: Optional[List[UUID]] = None,
        include_anomalies: Optional[List[UUID]] = None
    ) -> RecommendationContext:
        """Build context for recommendation generation"""
        try:
            start_date = datetime.utcnow() - timedelta(days=time_range_days)

            # Get KPI data
            kpi_data = await self._get_kpi_data(workspace_id, include_metrics)

            # Get anomalies
            anomalies = await self._get_anomalies(workspace_id, start_date, include_anomalies)

            # Get trends
            trends = await self._get_trends(workspace_id, start_date)

            # Get recent meetings (if available)
            recent_meetings = await self._get_recent_meetings(workspace_id, founder_id, days=7)

            # Get sentiment analysis (if available)
            sentiment_analysis = await self._get_sentiment_analysis(workspace_id, founder_id)

            # Get historical recommendations
            historical = await self._get_historical_recommendations(
                workspace_id, founder_id, days=90
            )

            return RecommendationContext(
                kpi_data=kpi_data,
                anomalies=anomalies,
                trends=trends,
                recent_meetings=recent_meetings,
                sentiment_analysis=sentiment_analysis,
                historical_recommendations=historical
            )

        except Exception as e:
            self.logger.error(f"Error building context: {str(e)}")
            return RecommendationContext()

    async def _create_recommendation(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        rec_data: Dict[str, Any],
        context: RecommendationContext
    ) -> Optional[RecommendationResponse]:
        """Create and save a recommendation"""
        try:
            # Map LLM output to model
            recommendation = RecommendationCreate(
                workspace_id=workspace_id,
                founder_id=founder_id,
                title=rec_data.get("title", ""),
                recommendation_type=RecommendationType(rec_data.get("type", "strategic")),
                priority=RecommendationPriority(rec_data.get("priority", "medium")),
                description=rec_data.get("description", ""),
                confidence_score=rec_data.get("confidence", 0.7),
                expected_impact=ImpactLevel(rec_data.get("expected_impact", "medium")),
                actionable_steps=rec_data.get("actionable_steps", []),
                success_metrics=rec_data.get("success_metrics", []),
                estimated_effort=rec_data.get("estimated_effort"),
                estimated_cost=rec_data.get("estimated_cost"),
                source_data={
                    "kpi_count": len(context.kpi_data),
                    "anomaly_count": len(context.anomalies),
                    "trend_count": len(context.trends)
                }
            )

            # Save to database
            result = self.supabase.table("recommendations").insert(
                recommendation.model_dump(mode="json")
            ).execute()

            if result.data:
                return RecommendationResponse(**result.data[0])

            return None

        except Exception as e:
            self.logger.error(f"Error creating recommendation: {str(e)}")
            return None

    async def _get_kpi_data(
        self,
        workspace_id: UUID,
        metric_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """Get current KPI data"""
        kpi_data = {}
        try:
            query = self.supabase.table("kpi_metrics").select("*").eq(
                "workspace_id", str(workspace_id)
            ).eq("is_active", True)

            if metric_ids:
                query = query.in_("id", [str(mid) for mid in metric_ids])

            metrics = query.execute()

            for metric in metrics.data:
                # Get latest value
                latest = self.supabase.table("kpi_data_points").select("value,timestamp").eq(
                    "metric_id", metric["id"]
                ).order("timestamp", desc=True).limit(1).execute()

                if latest.data:
                    kpi_data[metric["name"]] = {
                        "value": latest.data[0]["value"],
                        "timestamp": latest.data[0]["timestamp"]
                    }

        except Exception as e:
            self.logger.error(f"Error getting KPI data: {str(e)}")

        return kpi_data

    async def _get_anomalies(
        self,
        workspace_id: UUID,
        start_date: datetime,
        anomaly_ids: Optional[List[UUID]] = None
    ) -> List[Dict[str, Any]]:
        """Get recent anomalies"""
        try:
            query = self.supabase.table("anomalies").select("*").eq(
                "workspace_id", str(workspace_id)
            ).gte("detected_at", start_date.isoformat())

            if anomaly_ids:
                query = query.in_("id", [str(aid) for aid in anomaly_ids])

            result = query.execute()
            return result.data

        except Exception as e:
            self.logger.error(f"Error getting anomalies: {str(e)}")
            return []

    async def _get_trends(
        self,
        workspace_id: UUID,
        start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get recent trends"""
        try:
            result = self.supabase.table("trends").select("*").eq(
                "workspace_id", str(workspace_id)
            ).gte("created_at", start_date.isoformat()).eq(
                "is_significant", True
            ).execute()

            return result.data

        except Exception as e:
            self.logger.error(f"Error getting trends: {str(e)}")
            return []

    async def _get_recent_meetings(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get recent meetings"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            result = self.supabase.table("meeting_summaries").select("*").eq(
                "workspace_id", str(workspace_id)
            ).gte("meeting_date", start_date.isoformat()).execute()

            return result.data

        except Exception as e:
            self.logger.error(f"Error getting meetings: {str(e)}")
            return []

    async def _get_sentiment_analysis(
        self,
        workspace_id: UUID,
        founder_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get sentiment analysis"""
        # Placeholder - would integrate with communications sentiment
        return {"overall": "neutral"}

    async def _get_historical_recommendations(
        self,
        workspace_id: UUID,
        founder_id: UUID,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """Get historical recommendations"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            result = self.supabase.table("recommendations").select("*").eq(
                "workspace_id", str(workspace_id)
            ).eq("founder_id", str(founder_id)).gte(
                "created_at", start_date.isoformat()
            ).execute()

            return result.data

        except Exception as e:
            self.logger.error(f"Error getting historical recommendations: {str(e)}")
            return []
