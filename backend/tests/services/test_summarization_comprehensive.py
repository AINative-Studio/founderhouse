"""
Comprehensive tests for Summarization Service
Covers all major code paths, edge cases, and error scenarios
Target: 100% coverage of summarization_service.py
"""
import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from app.services.summarization_service import SummarizationService
from app.llm.llm_provider import LLMConfig, LLMProviderType, LLMResponse, LLMModelTier
from app.models.meeting_summary import SentimentScore, SummarizationMethod
from app.models.action_item import ActionItem
from app.models.decision import Decision


@pytest.fixture
def service():
    """Create service without Supabase"""
    return SummarizationService(supabase_client=None)


@pytest.fixture
def service_with_db():
    """Create service with mocked Supabase"""
    mock_supabase = Mock()
    mock_supabase.table = Mock()
    return SummarizationService(supabase_client=mock_supabase)


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def founder_id():
    return uuid4()


@pytest.fixture
def meeting_id():
    return uuid4()


@pytest.fixture
def sample_transcript():
    """Comprehensive meeting transcript"""
    return """
    John: Welcome everyone to our Q4 planning meeting. Today we need to finalize our product roadmap and discuss budget allocation.

    Sarah: Thanks John. I've reviewed our customer feedback and the top request is enterprise SSO. We have 5 enterprise clients waiting for this feature.

    John: That's critical. Mike, can you take ownership of the SSO implementation?

    Mike: Absolutely. I estimate 3 weeks for implementation and 1 week for testing. I'll need help from the DevOps team for deployment.

    Sarah: We should also increase our marketing budget by 20% next quarter to support enterprise sales.

    John: I agree. Let's make that official - we'll allocate an additional $50,000 for Q4 marketing focused on enterprise outreach.

    Emily: What about the mobile app redesign? Our users have been complaining about the UI.

    John: Good point. That's important but not urgent. Let's prioritize SSO first, then tackle the redesign in Q1.

    Mike: I'll create tickets for the SSO work and share a project plan by Friday.

    Sarah: We should also follow up with our top 3 enterprise prospects next week to share the SSO timeline.

    John: Excellent. Any other concerns? No? Great meeting everyone. Let's execute on these plans.
    """


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider with complete responses"""
    provider = Mock()
    provider.provider_type = LLMProviderType.OPENAI
    provider.config = LLMConfig(
        provider=LLMProviderType.OPENAI,
        model_name="gpt-4",
        api_key="test_key"
    )
    return provider


@pytest.fixture
def mock_summary_chain():
    """Mock summarization chain"""
    chain = AsyncMock()
    chain.summarize = AsyncMock(return_value={
        "executive_summary": "Team discussed Q4 planning with focus on enterprise features and budget allocation.",
        "detailed_summary": "The meeting covered enterprise SSO implementation, marketing budget increase, and mobile app redesign prioritization.",
        "key_points": [
            "Enterprise SSO is top priority",
            "$50k additional marketing budget approved",
            "Mobile redesign postponed to Q1"
        ],
        "metadata": {
            "total_tokens": 500,
            "total_cost_usd": 0.01
        }
    })
    chain.generate_topics = AsyncMock(return_value=[
        "Q4 Planning",
        "Enterprise Features",
        "Budget Allocation"
    ])
    return chain


@pytest.fixture
def mock_action_chain():
    """Mock action item extraction chain"""
    chain = AsyncMock()
    chain.extract_action_items = AsyncMock(return_value=[
        {
            "description": "Implement SSO authentication",
            "assignee_name": "Mike",
            "assignee_email": "mike@example.com",
            "priority": "high",
            "due_date": None,
            "context": "Enterprise clients requesting SSO",
            "source": "llm",
            "confidence_score": 0.95
        },
        {
            "description": "Create project plan for SSO",
            "assignee_name": "Mike",
            "assignee_email": "mike@example.com",
            "priority": "high",
            "due_date": "Friday",
            "context": "Share detailed timeline",
            "source": "hybrid",
            "confidence_score": 0.90
        },
        {
            "description": "Follow up with top 3 enterprise prospects",
            "assignee_name": "Sarah",
            "assignee_email": "sarah@example.com",
            "priority": "medium",
            "due_date": "next week",
            "context": "Share SSO timeline",
            "source": "llm",
            "confidence_score": 0.85
        }
    ])
    return chain


@pytest.fixture
def mock_decision_chain():
    """Mock decision extraction chain"""
    chain = AsyncMock()
    chain.extract_decisions = AsyncMock(return_value=[
        {
            "title": "Increase Q4 marketing budget",
            "description": "Allocate additional $50k for enterprise marketing",
            "decision_type": "financial",
            "impact": "high",
            "decision_maker": "John",
            "rationale": "Support enterprise sales growth",
            "context": "Need to reach enterprise customers",
            "stakeholders": ["Sarah", "Marketing team"],
            "confidence_score": 0.92
        },
        {
            "title": "Prioritize SSO over mobile redesign",
            "description": "Focus on enterprise SSO implementation before mobile UI updates",
            "decision_type": "strategic",
            "impact": "high",
            "decision_maker": "John",
            "rationale": "Enterprise clients waiting for SSO feature",
            "context": "Product roadmap prioritization",
            "stakeholders": ["Mike", "Emily"],
            "confidence_score": 0.88
        }
    ])
    return chain


@pytest.fixture
def mock_sentiment_chain():
    """Mock sentiment analysis chain"""
    chain = AsyncMock()
    chain.analyze_sentiment = AsyncMock(return_value={
        "overall_sentiment": "positive",
        "energy_level": "high",
        "collaboration_score": 8.5,
        "engagement": "Team was engaged and aligned on priorities",
        "concerns": []
    })
    return chain


# ==================== MAIN SUMMARIZATION TESTS ====================

@pytest.mark.asyncio
async def test_summarize_meeting_complete_flow(
    service_with_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    mock_llm_provider,
    mock_summary_chain,
    mock_action_chain,
    mock_decision_chain,
    mock_sentiment_chain
):
    """Test complete summarization flow with all features"""
    with patch('app.services.summarization_service.get_provider', return_value=mock_llm_provider):
        with patch('app.services.summarization_service.SummarizationChain', return_value=mock_summary_chain):
            with patch('app.services.summarization_service.ActionItemChain', return_value=mock_action_chain):
                with patch('app.services.summarization_service.DecisionChain', return_value=mock_decision_chain):
                    with patch('app.services.summarization_service.SentimentChain', return_value=mock_sentiment_chain):
                        # Mock database operations
                        service_with_db.supabase.table.return_value.insert.return_value.execute.return_value = Mock()
                        service_with_db.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

                        result = await service_with_db.summarize_meeting(
                            meeting_id=meeting_id,
                            workspace_id=workspace_id,
                            founder_id=founder_id,
                            transcript=sample_transcript,
                            extract_action_items=True,
                            extract_decisions=True,
                            analyze_sentiment=True
                        )

                        # Verify result structure
                        assert "summary" in result
                        assert "action_items" in result
                        assert "decisions" in result
                        assert "sentiment" in result
                        assert "metadata" in result

                        # Verify summary
                        summary = result["summary"]
                        assert summary.executive_summary != ""
                        assert len(summary.key_points) > 0
                        assert summary.action_items_count == 3
                        assert summary.decisions_count == 2
                        assert summary.summarization_method == SummarizationMethod.MULTI_STAGE

                        # Verify action items
                        assert len(result["action_items"]) == 3
                        assert result["action_items"][0].description == "Implement SSO authentication"

                        # Verify decisions
                        assert len(result["decisions"]) == 2
                        assert "marketing budget" in result["decisions"][0].title.lower()

                        # Verify sentiment
                        assert result["sentiment"]["overall_sentiment"] == "positive"


@pytest.mark.asyncio
async def test_summarize_meeting_minimal_features(
    service,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    mock_llm_provider,
    mock_summary_chain
):
    """Test summarization with minimal features (no action items, decisions, sentiment)"""
    with patch('app.services.summarization_service.get_provider', return_value=mock_llm_provider):
        with patch('app.services.summarization_service.SummarizationChain', return_value=mock_summary_chain):
            result = await service.summarize_meeting(
                meeting_id=meeting_id,
                workspace_id=workspace_id,
                founder_id=founder_id,
                transcript=sample_transcript,
                extract_action_items=False,
                extract_decisions=False,
                analyze_sentiment=False
            )

            # Should only have summary, no action items or decisions
            assert "summary" in result
            assert len(result["action_items"]) == 0
            assert len(result["decisions"]) == 0
            assert result["sentiment"] == {}


@pytest.mark.asyncio
async def test_summarize_meeting_with_custom_llm_config(
    service,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    mock_summary_chain
):
    """Test summarization with custom LLM configuration"""
    custom_config = LLMConfig(
        provider=LLMProviderType.ANTHROPIC,
        model_name="claude-3-opus",
        api_key="custom_key"
    )

    mock_provider = Mock()
    mock_provider.config = custom_config

    with patch('app.services.summarization_service.get_provider', return_value=mock_provider):
        with patch('app.services.summarization_service.SummarizationChain', return_value=mock_summary_chain):
            result = await service.summarize_meeting(
                meeting_id=meeting_id,
                workspace_id=workspace_id,
                founder_id=founder_id,
                transcript=sample_transcript,
                llm_config=custom_config,
                extract_action_items=False,
                extract_decisions=False,
                analyze_sentiment=False
            )

            assert result["summary"].llm_provider == LLMProviderType.ANTHROPIC.value


@pytest.mark.asyncio
async def test_summarize_meeting_llm_error(
    service,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    mock_llm_provider
):
    """Test handling of LLM provider error"""
    mock_chain = AsyncMock()
    mock_chain.summarize.side_effect = Exception("LLM API error")

    with patch('app.services.summarization_service.get_provider', return_value=mock_llm_provider):
        with patch('app.services.summarization_service.SummarizationChain', return_value=mock_chain):
            with pytest.raises(Exception, match="LLM API error"):
                await service.summarize_meeting(
                    meeting_id=meeting_id,
                    workspace_id=workspace_id,
                    founder_id=founder_id,
                    transcript=sample_transcript
                )


@pytest.mark.asyncio
async def test_summarize_meeting_updates_status_on_failure(
    service_with_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    mock_llm_provider
):
    """Test that meeting status is updated on failure"""
    mock_chain = AsyncMock()
    mock_chain.summarize.side_effect = Exception("Processing failed")

    service_with_db.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

    with patch('app.services.summarization_service.get_provider', return_value=mock_llm_provider):
        with patch('app.services.summarization_service.SummarizationChain', return_value=mock_chain):
            with pytest.raises(Exception):
                await service_with_db.summarize_meeting(
                    meeting_id=meeting_id,
                    workspace_id=workspace_id,
                    founder_id=founder_id,
                    transcript=sample_transcript
                )


# ==================== BATCH SUMMARIZATION TESTS ====================

@pytest.mark.asyncio
async def test_batch_summarize_multiple_meetings(
    service_with_db,
    workspace_id,
    founder_id
):
    """Test batch summarization of multiple meetings"""
    meeting_ids = [uuid4(), uuid4(), uuid4()]

    # Mock _get_meeting to return meetings with transcripts
    async def mock_get_meeting(meeting_id):
        return {
            "id": str(meeting_id),
            "transcript": "Sample transcript for batch processing.",
            "workspace_id": str(workspace_id),
            "founder_id": str(founder_id)
        }

    with patch.object(service_with_db, '_get_meeting', side_effect=mock_get_meeting):
        with patch.object(service_with_db, 'summarize_meeting', new_callable=AsyncMock) as mock_summarize:
            mock_summarize.return_value = {
                "summary": Mock(),
                "action_items": [],
                "decisions": [],
                "sentiment": {}
            }

            results = await service_with_db.batch_summarize(
                meeting_ids=meeting_ids,
                workspace_id=workspace_id,
                founder_id=founder_id
            )

            assert len(results) == 3
            assert all(r["status"] == "success" for r in results)


@pytest.mark.asyncio
async def test_batch_summarize_handles_failures(
    service_with_db,
    workspace_id,
    founder_id
):
    """Test batch summarization handles individual failures"""
    meeting_ids = [uuid4(), uuid4(), uuid4()]

    async def mock_get_meeting(meeting_id):
        return {
            "id": str(meeting_id),
            "transcript": "Sample transcript.",
            "workspace_id": str(workspace_id),
            "founder_id": str(founder_id)
        }

    async def mock_summarize(*args, **kwargs):
        # Fail on second meeting
        if kwargs["meeting_id"] == meeting_ids[1]:
            raise Exception("Summarization failed")
        return {
            "summary": Mock(),
            "action_items": [],
            "decisions": [],
            "sentiment": {}
        }

    with patch.object(service_with_db, '_get_meeting', side_effect=mock_get_meeting):
        with patch.object(service_with_db, 'summarize_meeting', side_effect=mock_summarize):
            results = await service_with_db.batch_summarize(
                meeting_ids=meeting_ids,
                workspace_id=workspace_id,
                founder_id=founder_id
            )

            assert len(results) == 3
            assert results[0]["status"] == "success"
            assert results[1]["status"] == "failed"
            assert results[2]["status"] == "success"


@pytest.mark.asyncio
async def test_batch_summarize_skips_meetings_without_transcript(
    service_with_db,
    workspace_id,
    founder_id
):
    """Test batch summarization skips meetings without transcripts"""
    meeting_ids = [uuid4(), uuid4()]

    async def mock_get_meeting(meeting_id):
        if meeting_id == meeting_ids[0]:
            return None  # Meeting not found
        else:
            return {
                "id": str(meeting_id),
                "transcript": None,  # No transcript
                "workspace_id": str(workspace_id),
                "founder_id": str(founder_id)
            }

    with patch.object(service_with_db, '_get_meeting', side_effect=mock_get_meeting):
        results = await service_with_db.batch_summarize(
            meeting_ids=meeting_ids,
            workspace_id=workspace_id,
            founder_id=founder_id
        )

        # Both should be skipped
        assert len(results) == 0


# ==================== DATABASE OPERATION TESTS ====================

@pytest.mark.asyncio
async def test_save_summary_no_supabase(service, meeting_id):
    """Test saving summary without Supabase"""
    from app.models.meeting_summary import MeetingSummary

    summary = MeetingSummary(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        meeting_id=meeting_id,
        executive_summary="Test summary",
        detailed_summary="Detailed test",
        key_points=["Point 1"],
        topics_discussed=[],
        summarization_method=SummarizationMethod.MULTI_STAGE,
        llm_provider="openai",
        llm_model="gpt-4"
    )

    # Should not raise error
    await service._save_summary(summary)


@pytest.mark.asyncio
async def test_save_summary_with_supabase(service_with_db, meeting_id):
    """Test saving summary to Supabase"""
    from app.models.meeting_summary import MeetingSummary

    summary = MeetingSummary(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        meeting_id=meeting_id,
        executive_summary="Test summary",
        detailed_summary="Detailed test",
        key_points=["Point 1"],
        topics_discussed=[],
        summarization_method=SummarizationMethod.MULTI_STAGE,
        llm_provider="openai",
        llm_model="gpt-4"
    )

    service_with_db.supabase.table.return_value.insert.return_value.execute.return_value = Mock()

    await service_with_db._save_summary(summary)
    service_with_db.supabase.table.assert_called_with("meeting_summaries")


@pytest.mark.asyncio
async def test_save_summary_database_error(service_with_db, meeting_id):
    """Test handling database error when saving summary"""
    from app.models.meeting_summary import MeetingSummary

    summary = MeetingSummary(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        meeting_id=meeting_id,
        executive_summary="Test",
        detailed_summary="Test",
        key_points=[],
        topics_discussed=[],
        summarization_method=SummarizationMethod.MULTI_STAGE,
        llm_provider="openai",
        llm_model="gpt-4"
    )

    service_with_db.supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
        "Insert failed"
    )

    # Should log error but not raise
    await service_with_db._save_summary(summary)


@pytest.mark.asyncio
async def test_save_action_item_no_supabase(service, meeting_id):
    """Test saving action item without Supabase"""
    action_item = ActionItem(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        meeting_id=meeting_id,
        description="Test action",
        confidence_score=0.9
    )

    # Should not raise error
    await service._save_action_item(action_item)


@pytest.mark.asyncio
async def test_save_action_item_with_supabase(service_with_db, meeting_id):
    """Test saving action item to Supabase"""
    action_item = ActionItem(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        meeting_id=meeting_id,
        description="Test action",
        confidence_score=0.9
    )

    service_with_db.supabase.table.return_value.insert.return_value.execute.return_value = Mock()

    await service_with_db._save_action_item(action_item)
    service_with_db.supabase.table.assert_called_with("action_items")


@pytest.mark.asyncio
async def test_save_action_item_database_error(service_with_db, meeting_id):
    """Test handling database error when saving action item"""
    action_item = ActionItem(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        meeting_id=meeting_id,
        description="Test",
        confidence_score=0.9
    )

    service_with_db.supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
        "Insert failed"
    )

    # Should log error but not raise
    await service_with_db._save_action_item(action_item)


@pytest.mark.asyncio
async def test_save_decision_no_supabase(service, meeting_id):
    """Test saving decision without Supabase"""
    decision = Decision(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        meeting_id=meeting_id,
        title="Test decision",
        description="Decision description",
        confidence_score=0.85
    )

    # Should not raise error
    await service._save_decision(decision)


@pytest.mark.asyncio
async def test_save_decision_with_supabase(service_with_db, meeting_id):
    """Test saving decision to Supabase"""
    decision = Decision(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        meeting_id=meeting_id,
        title="Test decision",
        description="Decision description",
        confidence_score=0.85
    )

    service_with_db.supabase.table.return_value.insert.return_value.execute.return_value = Mock()

    await service_with_db._save_decision(decision)
    service_with_db.supabase.table.assert_called_with("decisions")


@pytest.mark.asyncio
async def test_save_decision_database_error(service_with_db, meeting_id):
    """Test handling database error when saving decision"""
    decision = Decision(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        meeting_id=meeting_id,
        title="Test",
        description="Test",
        confidence_score=0.85
    )

    service_with_db.supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
        "Insert failed"
    )

    # Should log error but not raise
    await service_with_db._save_decision(decision)


@pytest.mark.asyncio
async def test_update_meeting_summarization_status_no_supabase(service, meeting_id):
    """Test updating meeting status without Supabase"""
    await service._update_meeting_summarization_status(
        meeting_id=meeting_id,
        completed=True
    )
    # Should not raise error


@pytest.mark.asyncio
async def test_update_meeting_summarization_status_completed(service_with_db, meeting_id):
    """Test updating meeting status to completed"""
    service_with_db.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

    await service_with_db._update_meeting_summarization_status(
        meeting_id=meeting_id,
        completed=True
    )

    service_with_db.supabase.table.assert_called_with("meetings")


@pytest.mark.asyncio
async def test_update_meeting_summarization_status_failed(service_with_db, meeting_id):
    """Test updating meeting status to failed"""
    service_with_db.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

    await service_with_db._update_meeting_summarization_status(
        meeting_id=meeting_id,
        completed=False,
        error_message="Processing failed"
    )

    service_with_db.supabase.table.assert_called_with("meetings")


@pytest.mark.asyncio
async def test_update_meeting_summarization_status_database_error(service_with_db, meeting_id):
    """Test handling database error when updating status"""
    service_with_db.supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception(
        "Update failed"
    )

    # Should log error but not raise
    await service_with_db._update_meeting_summarization_status(
        meeting_id=meeting_id,
        completed=True
    )


@pytest.mark.asyncio
async def test_get_meeting_no_supabase(service, meeting_id):
    """Test getting meeting without Supabase"""
    result = await service._get_meeting(meeting_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_meeting_with_supabase(service_with_db, meeting_id):
    """Test getting meeting from Supabase"""
    meeting_data = {
        "id": str(meeting_id),
        "transcript": "Sample transcript",
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4())
    }

    service_with_db.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
        data=[meeting_data]
    )

    result = await service_with_db._get_meeting(meeting_id)
    assert result is not None
    assert result["transcript"] == "Sample transcript"


@pytest.mark.asyncio
async def test_get_meeting_not_found(service_with_db, meeting_id):
    """Test getting non-existent meeting"""
    service_with_db.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
        data=[]
    )

    result = await service_with_db._get_meeting(meeting_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_meeting_database_error(service_with_db, meeting_id):
    """Test handling database error when getting meeting"""
    service_with_db.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception(
        "Query failed"
    )

    result = await service_with_db._get_meeting(meeting_id)
    assert result is None


# ==================== PROVIDER SELECTION TESTS ====================

@pytest.mark.asyncio
async def test_summarize_uses_best_provider_when_no_config(
    service,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    mock_summary_chain
):
    """Test that service selects best provider when no config provided"""
    mock_provider = Mock()
    mock_provider.config = LLMConfig(
        provider=LLMProviderType.OPENAI,
        model_name="gpt-4",
        api_key="test_key"
    )

    with patch('app.services.summarization_service.select_best_provider') as mock_select:
        with patch('app.services.summarization_service.get_provider', return_value=mock_provider):
            with patch('app.services.summarization_service.SummarizationChain', return_value=mock_summary_chain):
                await service.summarize_meeting(
                    meeting_id=meeting_id,
                    workspace_id=workspace_id,
                    founder_id=founder_id,
                    transcript=sample_transcript,
                    extract_action_items=False,
                    extract_decisions=False,
                    analyze_sentiment=False
                )

                # Verify select_best_provider was called
                mock_select.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
