"""
Summarization Service
Orchestrates meeting summarization using LLM providers and LangChain chains
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.llm.llm_provider import get_provider, select_best_provider, LLMConfig, LLMModelTier
from app.chains.summarization_chain import SummarizationChain
from app.chains.action_item_chain import ActionItemChain
from app.chains.decision_chain import DecisionChain
from app.chains.sentiment_chain import SentimentChain
from app.models.meeting_summary import MeetingSummary, SummarizationMethod
from app.models.action_item import ActionItem, ActionItemCreate
from app.models.decision import Decision, DecisionCreate


logger = logging.getLogger(__name__)


class SummarizationService:
    """
    Comprehensive meeting summarization service

    Features:
    - Multi-stage summarization (extractive → abstractive)
    - Action item extraction with confidence scoring
    - Decision extraction
    - Sentiment analysis
    - Cost tracking per summarization
    - Multiple LLM provider support
    """

    def __init__(
        self,
        supabase_client=None,
        default_provider: Optional[str] = None,
        api_keys: Optional[Dict[str, str]] = None
    ):
        """
        Initialize summarization service

        Args:
            supabase_client: Supabase client for database operations
            default_provider: Default LLM provider (openai, anthropic, deepseek, ollama)
            api_keys: Dictionary of API keys for providers
        """
        self.supabase = supabase_client
        self.api_keys = api_keys or {}
        self.default_provider = default_provider
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def summarize_meeting(
        self,
        meeting_id: UUID,
        workspace_id: UUID,
        founder_id: UUID,
        transcript: str,
        extract_action_items: bool = True,
        extract_decisions: bool = True,
        analyze_sentiment: bool = True,
        llm_config: Optional[LLMConfig] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive meeting summarization

        Args:
            meeting_id: Meeting UUID
            workspace_id: Workspace UUID
            founder_id: Founder UUID
            transcript: Meeting transcript text
            extract_action_items: Extract action items
            extract_decisions: Extract decisions
            analyze_sentiment: Analyze sentiment
            llm_config: Optional custom LLM config

        Returns:
            Dictionary with summary, action items, decisions, and sentiment
        """
        try:
            start_time = datetime.utcnow()
            self.logger.info(f"Starting summarization for meeting {meeting_id}")

            # Select LLM provider
            if not llm_config:
                llm_config = select_best_provider(
                    task_type="summarization",
                    budget_tier=LLMModelTier.STANDARD,
                    api_keys=self.api_keys
                )

            # Get provider instance
            llm_provider = get_provider(llm_config)

            # Initialize chains
            summary_chain = SummarizationChain(llm_provider)
            action_chain = ActionItemChain(llm_provider) if extract_action_items else None
            decision_chain = DecisionChain(llm_provider) if extract_decisions else None
            sentiment_chain = SentimentChain(llm_provider) if analyze_sentiment else None

            # Run summarization
            summary_result = await summary_chain.summarize(
                transcript,
                method="multi_stage"
            )

            # Extract topics
            topics = await summary_chain.generate_topics(transcript)

            # Extract action items
            action_items = []
            if action_chain:
                self.logger.info("Extracting action items")
                action_items_data = await action_chain.extract_action_items(
                    transcript,
                    use_hybrid=True
                )

                # Convert to ActionItem models
                for item_data in action_items_data:
                    action_item = ActionItem(
                        workspace_id=workspace_id,
                        founder_id=founder_id,
                        meeting_id=meeting_id,
                        description=item_data.get("description", ""),
                        context=item_data.get("context"),
                        assignee_name=item_data.get("assignee_name"),
                        assignee_email=item_data.get("assignee_email"),
                        priority=item_data.get("priority"),
                        due_date=item_data.get("due_date"),
                        source=item_data.get("source"),
                        confidence_score=item_data.get("confidence_score", 0.0)
                    )
                    action_items.append(action_item)

                    # Save to database
                    if self.supabase:
                        await self._save_action_item(action_item)

            # Extract decisions
            decisions = []
            if decision_chain:
                self.logger.info("Extracting decisions")
                decisions_data = await decision_chain.extract_decisions(transcript)

                # Convert to Decision models
                for decision_data in decisions_data:
                    decision = Decision(
                        workspace_id=workspace_id,
                        founder_id=founder_id,
                        meeting_id=meeting_id,
                        title=decision_data.get("title", ""),
                        description=decision_data.get("description", ""),
                        decision_type=decision_data.get("decision_type"),
                        impact=decision_data.get("impact"),
                        decision_maker=decision_data.get("decision_maker"),
                        rationale=decision_data.get("rationale"),
                        context=decision_data.get("context"),
                        stakeholders=decision_data.get("stakeholders", []),
                        confidence_score=decision_data.get("confidence_score", 0.0)
                    )
                    decisions.append(decision)

                    # Save to database
                    if self.supabase:
                        await self._save_decision(decision)

            # Analyze sentiment
            sentiment_analysis = {}
            if sentiment_chain:
                self.logger.info("Analyzing sentiment")
                sentiment_analysis = await sentiment_chain.analyze_sentiment(transcript)

            # Create meeting summary
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            meeting_summary = MeetingSummary(
                workspace_id=workspace_id,
                founder_id=founder_id,
                meeting_id=meeting_id,
                executive_summary=summary_result.get("executive_summary", ""),
                detailed_summary=summary_result.get("detailed_summary", ""),
                key_points=summary_result.get("key_points", []),
                topics_discussed=topics,
                overall_sentiment=sentiment_analysis.get("overall_sentiment"),
                sentiment_details=sentiment_analysis,
                action_items_count=len(action_items),
                decisions_count=len(decisions),
                summarization_method=SummarizationMethod.MULTI_STAGE,
                llm_provider=llm_config.provider.value,
                llm_model=llm_config.model_name,
                processing_time_ms=processing_time,
                token_usage=summary_result.get("metadata", {}).get("total_tokens"),
                cost_usd=summary_result.get("metadata", {}).get("total_cost_usd"),
                status="completed"
            )

            # Save summary to database
            if self.supabase:
                await self._save_summary(meeting_summary)

            # Update meeting status
            if self.supabase:
                await self._update_meeting_summarization_status(
                    meeting_id,
                    completed=True
                )

            self.logger.info(
                f"Summarization completed for meeting {meeting_id} in {processing_time}ms. "
                f"Extracted {len(action_items)} action items and {len(decisions)} decisions."
            )

            return {
                "summary": meeting_summary,
                "action_items": action_items,
                "decisions": decisions,
                "sentiment": sentiment_analysis,
                "metadata": {
                    "processing_time_ms": processing_time,
                    "cost_usd": meeting_summary.cost_usd,
                    "tokens_used": meeting_summary.token_usage
                }
            }

        except Exception as e:
            self.logger.error(f"Summarization failed for meeting {meeting_id}: {str(e)}")

            # Update meeting status to failed
            if self.supabase:
                await self._update_meeting_summarization_status(
                    meeting_id,
                    completed=False,
                    error_message=str(e)
                )

            raise

    async def batch_summarize(
        self,
        meeting_ids: List[UUID],
        workspace_id: UUID,
        founder_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Batch summarize multiple meetings

        Args:
            meeting_ids: List of meeting UUIDs
            workspace_id: Workspace UUID
            founder_id: Founder UUID

        Returns:
            List of summarization results
        """
        results = []

        for meeting_id in meeting_ids:
            try:
                # Fetch meeting transcript
                meeting = await self._get_meeting(meeting_id)
                if not meeting or not meeting.get("transcript"):
                    self.logger.warning(f"No transcript for meeting {meeting_id}")
                    continue

                # Summarize
                result = await self.summarize_meeting(
                    meeting_id=meeting_id,
                    workspace_id=workspace_id,
                    founder_id=founder_id,
                    transcript=meeting["transcript"]
                )

                results.append({
                    "meeting_id": meeting_id,
                    "status": "success",
                    "result": result
                })

            except Exception as e:
                self.logger.error(f"Failed to summarize meeting {meeting_id}: {str(e)}")
                results.append({
                    "meeting_id": meeting_id,
                    "status": "failed",
                    "error": str(e)
                })

        return results

    async def _save_summary(self, summary: MeetingSummary) -> None:
        """Save meeting summary to database"""
        if not self.supabase:
            return

        try:
            summary_dict = summary.model_dump(mode='json')
            summary_dict["id"] = str(summary.id)
            summary_dict["workspace_id"] = str(summary.workspace_id)
            summary_dict["founder_id"] = str(summary.founder_id)
            summary_dict["meeting_id"] = str(summary.meeting_id)

            self.supabase.table("meeting_summaries").insert(summary_dict).execute()
            self.logger.info(f"Saved summary to database: {summary.id}")

        except Exception as e:
            self.logger.error(f"Failed to save summary: {str(e)}")

    async def _save_action_item(self, action_item: ActionItem) -> None:
        """Save action item to database"""
        if not self.supabase:
            return

        try:
            item_dict = action_item.model_dump(mode='json')
            item_dict["id"] = str(action_item.id)
            item_dict["workspace_id"] = str(action_item.workspace_id)
            item_dict["founder_id"] = str(action_item.founder_id)
            item_dict["meeting_id"] = str(action_item.meeting_id)

            self.supabase.table("action_items").insert(item_dict).execute()

        except Exception as e:
            self.logger.error(f"Failed to save action item: {str(e)}")

    async def _save_decision(self, decision: Decision) -> None:
        """Save decision to database"""
        if not self.supabase:
            return

        try:
            decision_dict = decision.model_dump(mode='json')
            decision_dict["id"] = str(decision.id)
            decision_dict["workspace_id"] = str(decision.workspace_id)
            decision_dict["founder_id"] = str(decision.founder_id)
            decision_dict["meeting_id"] = str(decision.meeting_id)

            self.supabase.table("decisions").insert(decision_dict).execute()

        except Exception as e:
            self.logger.error(f"Failed to save decision: {str(e)}")

    async def _update_meeting_summarization_status(
        self,
        meeting_id: UUID,
        completed: bool,
        error_message: Optional[str] = None
    ) -> None:
        """Update meeting summarization status"""
        if not self.supabase:
            return

        try:
            update_data = {
                "updated_at": datetime.utcnow().isoformat()
            }

            if completed:
                update_data["summarization_completed_at"] = datetime.utcnow().isoformat()
                update_data["status"] = "completed"
            else:
                update_data["status"] = "failed"
                if error_message:
                    update_data["error_message"] = error_message

            self.supabase.table("meetings").update(update_data).eq(
                "id", str(meeting_id)
            ).execute()

        except Exception as e:
            self.logger.error(f"Failed to update meeting status: {str(e)}")

    async def _get_meeting(self, meeting_id: UUID) -> Optional[Dict[str, Any]]:
        """Fetch meeting from database"""
        if not self.supabase:
            return None

        try:
            result = self.supabase.table("meetings").select("*").eq(
                "id", str(meeting_id)
            ).execute()

            return result.data[0] if result.data else None

        except Exception as e:
            self.logger.error(f"Failed to fetch meeting: {str(e)}")
            return None
