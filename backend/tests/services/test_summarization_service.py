"""
Tests for Summarization Service
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from app.services.summarization_service import SummarizationService
from app.llm.llm_provider import LLMConfig, LLMProviderType, LLMResponse
from app.models.meeting_summary import SentimentScore


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider"""
    provider = Mock()
    provider.provider_type = LLMProviderType.OPENAI
    provider.config = LLMConfig(
        provider=LLMProviderType.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key="test_key"
    )
    return provider


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript"""
    return """
    John: Welcome everyone to our Q4 planning meeting. Today we need to decide on our product roadmap.

    Sarah: I think we should prioritize the enterprise features. Our biggest clients are asking for SSO and RBAC.

    John: Good point. Mike, can you handle the SSO implementation?

    Mike: Yes, I can start on that next week. I'll need about 3 weeks to complete it.

    Sarah: We also need to increase our marketing budget by 20% to support the enterprise push.

    John: Agreed. Let's make that decision official. We'll allocate an additional $50k for Q4 marketing.

    Mike: One more thing - we should follow up with the design team about the new dashboard mockups.

    John: Great meeting everyone. Let's execute on these plans.
    """


@pytest.mark.asyncio
async def test_summarize_meeting_basic(mock_llm_provider, sample_transcript):
    """Test basic meeting summarization"""
    # Setup mock responses
    mock_llm_provider.complete = AsyncMock(side_effect=[
        # Extractive stage
        LLMResponse(
            content="- Prioritize enterprise features\n- SSO implementation by Mike\n- Increase marketing budget by $50k",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=150,
            cost_usd=0.001
        ),
        # Abstractive stage
        LLMResponse(
            content="The team discussed Q4 planning with focus on enterprise features. Key decision to increase marketing budget by $50k.",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=100,
            cost_usd=0.0008
        ),
        # Refinement stage
        LLMResponse(
            content="Executive Summary: Q4 planning focused on enterprise growth with budget allocation.\n\nThe team agreed to prioritize enterprise features including SSO and RBAC.",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=120,
            cost_usd=0.0009
        ),
        # Topics
        LLMResponse(
            content="Q4 Planning\nEnterprise Features\nMarketing Budget",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=50,
            cost_usd=0.0003
        ),
        # Action items
        LLMResponse(
            content="""ITEM: Implement SSO authentication
ASSIGNEE: Mike
DUE: next week
PRIORITY: high
CONTEXT: Enterprise clients requesting SSO
---""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=80,
            cost_usd=0.0005
        ),
        # Decisions
        LLMResponse(
            content="""TITLE: Increase marketing budget
DESCRIPTION: Allocate additional $50k for Q4 marketing
TYPE: financial
IMPACT: high
DECISION_MAKER: John
RATIONALE: Support enterprise push
---""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=90,
            cost_usd=0.0006
        ),
        # Sentiment
        LLMResponse(
            content="""OVERALL_SENTIMENT: positive
ENERGY_LEVEL: high
COLLABORATION_SCORE: 8/10
ENGAGEMENT: Team was engaged and productive""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=60,
            cost_usd=0.0004
        )
    ])

    # Mock get_provider
    with patch('app.services.summarization_service.get_provider', return_value=mock_llm_provider):
        service = SummarizationService()

        result = await service.summarize_meeting(
            meeting_id=uuid4(),
            workspace_id=uuid4(),
            founder_id=uuid4(),
            transcript=sample_transcript
        )

    # Assertions
    assert result is not None
    assert "summary" in result
    assert "action_items" in result
    assert "decisions" in result
    assert "sentiment" in result

    # Check summary
    summary = result["summary"]
    assert summary.executive_summary != ""
    assert summary.action_items_count >= 1
    assert summary.decisions_count >= 1
    assert summary.overall_sentiment == SentimentScore.POSITIVE

    # Check action items
    assert len(result["action_items"]) >= 1
    action_item = result["action_items"][0]
    assert "SSO" in action_item.description or "Implement" in action_item.description

    # Check decisions
    assert len(result["decisions"]) >= 1
    decision = result["decisions"][0]
    assert "marketing" in decision.title.lower() or "budget" in decision.title.lower()


@pytest.mark.asyncio
async def test_summarize_empty_transcript():
    """Test handling of empty transcript"""
    service = SummarizationService()

    with pytest.raises(Exception):
        await service.summarize_meeting(
            meeting_id=uuid4(),
            workspace_id=uuid4(),
            founder_id=uuid4(),
            transcript=""
        )


@pytest.mark.asyncio
async def test_cost_tracking(mock_llm_provider, sample_transcript):
    """Test that cost is properly tracked"""
    mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
        content="Test summary",
        provider=LLMProviderType.OPENAI,
        model="gpt-3.5-turbo",
        total_tokens=100,
        cost_usd=0.001
    ))

    with patch('app.services.summarization_service.get_provider', return_value=mock_llm_provider):
        service = SummarizationService()

        result = await service.summarize_meeting(
            meeting_id=uuid4(),
            workspace_id=uuid4(),
            founder_id=uuid4(),
            transcript=sample_transcript,
            extract_action_items=False,
            extract_decisions=False,
            analyze_sentiment=False
        )

    assert result["summary"].cost_usd is not None
    assert result["summary"].cost_usd > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
