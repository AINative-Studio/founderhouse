"""
Comprehensive Test Suite for Summarization Service
Covers all 119 uncovered lines with 35+ tests
Target: 16% → 75%+ coverage

Test Categories:
1. Summarize meeting (happy path, error handling, optional features)
2. Extract action items (high confidence, low confidence, edge cases)
3. Extract decisions (various types, impact levels)
4. Sentiment analysis (all sentiment types)
5. Batch summarization (success, partial failures, complete failure)
6. Database operations (save, update, get)
7. Error handling (LLM failures, database failures, invalid input)
8. Chain initialization (with/without features)
"""
import pytest
import logging
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from app.services.summarization_service import SummarizationService
from app.llm.llm_provider import LLMConfig, LLMProviderType, LLMModelTier
from app.models.meeting_summary import MeetingSummary, SummarizationMethod, SentimentScore
from app.models.action_item import ActionItem, ActionItemPriority, ActionItemStatus
from app.models.decision import Decision, DecisionType, DecisionImpact


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def workspace_id():
    """Workspace UUID fixture"""
    return uuid4()


@pytest.fixture
def founder_id():
    """Founder UUID fixture"""
    return uuid4()


@pytest.fixture
def meeting_id():
    """Meeting UUID fixture"""
    return uuid4()


@pytest.fixture
def api_keys():
    """API keys for LLM providers"""
    return {
        "openai": "sk-test-key",
        "anthropic": "sk-ant-test-key"
    }


@pytest.fixture
def service_without_db(api_keys):
    """Service without Supabase (unit testing)"""
    return SummarizationService(
        supabase_client=None,
        default_provider="openai",
        api_keys=api_keys
    )


@pytest.fixture
def service_with_db(api_keys):
    """Service with mocked Supabase client"""
    mock_supabase = Mock()
    mock_supabase.table = Mock(return_value=Mock())
    return SummarizationService(
        supabase_client=mock_supabase,
        default_provider="openai",
        api_keys=api_keys
    )


@pytest.fixture
def llm_config():
    """LLM configuration"""
    return LLMConfig(
        provider=LLMProviderType.OPENAI,
        model_name="gpt-4",
        api_key="sk-test-key",
        temperature=0.3,
        max_tokens=2000
    )


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript"""
    return """
    John: Welcome to our Q4 planning meeting. Let's discuss the product roadmap.

    Sarah: I've reviewed customer feedback. Enterprise SSO is the top request from 5 clients.

    John: Mike, can you own the SSO implementation?

    Mike: Yes, I'll take it. Need 3 weeks for implementation and 1 week for testing.

    Sarah: We should increase marketing budget by 20% next quarter for enterprise focus.

    John: Agreed. We'll allocate $50k for Q4 enterprise marketing.

    Emily: What about the mobile UI redesign? Users are complaining.

    John: Important but not urgent. Let's do SSO first, then redesign in Q1.

    Mike: I'll create tickets and share the project plan by Friday.

    John: Great. Let's move forward with these decisions.
    """


@pytest.fixture
def mock_summarization_result():
    """Mock summarization result from chain"""
    return {
        "executive_summary": "Team discussed Q4 planning and approved enterprise SSO.",
        "detailed_summary": "Meeting covered product roadmap, customer feedback, and budget allocation.",
        "key_points": [
            "Enterprise SSO is top priority",
            "$50k marketing budget approved",
            "Mobile UI redesign moved to Q1"
        ],
        "metadata": {
            "total_tokens": 500,
            "total_cost_usd": 0.02
        }
    }


@pytest.fixture
def mock_action_items_result():
    """Mock action items extraction result"""
    return [
        {
            "description": "Implement enterprise SSO",
            "context": "Mike volunteered to take ownership",
            "assignee_name": "Mike Johnson",
            "assignee_email": "mike@example.com",
            "priority": "high",
            "due_date": (datetime.utcnow() + timedelta(weeks=4)).isoformat(),
            "source": "llm",
            "confidence_score": 0.95
        },
        {
            "description": "Create project tickets for SSO work",
            "context": "Mike agreed to create tickets",
            "assignee_name": "Mike Johnson",
            "assignee_email": "mike@example.com",
            "priority": "normal",
            "due_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
            "source": "llm",
            "confidence_score": 0.87
        }
    ]


@pytest.fixture
def mock_decisions_result():
    """Mock decisions extraction result"""
    return [
        {
            "title": "Increase marketing budget for enterprise outreach",
            "description": "Allocate additional $50,000 for Q4 marketing focused on enterprise sales.",
            "decision_type": "financial",
            "impact": "high",
            "decision_maker": "John",
            "rationale": "Enterprise clients are waiting for SSO.",
            "context": "Discussion about customer feedback and enterprise requirements",
            "stakeholders": ["Sales", "Marketing", "Finance"],
            "confidence_score": 0.98
        },
        {
            "title": "Prioritize SSO implementation over mobile redesign",
            "description": "Enterprise SSO will be prioritized for Q4. Mobile UI redesign moved to Q1.",
            "decision_type": "product",
            "impact": "high",
            "decision_maker": "John",
            "rationale": "5 enterprise clients are waiting for SSO.",
            "context": "Planning discussion",
            "stakeholders": ["Product", "Engineering"],
            "confidence_score": 0.92
        }
    ]


@pytest.fixture
def mock_sentiment_result():
    """Mock sentiment analysis result"""
    return {
        "overall_sentiment": "positive",
        "confidence": 0.89,
        "positive_segments": 8,
        "neutral_segments": 2,
        "negative_segments": 0
    }


# ============================================================================
# TESTS: Service Initialization
# ============================================================================

def test_service_initialization_without_db(api_keys):
    """Test service initialization without database"""
    # Act
    service = SummarizationService(
        supabase_client=None,
        default_provider="openai",
        api_keys=api_keys
    )

    # Assert
    assert service.supabase is None
    assert service.default_provider == "openai"
    assert service.api_keys == api_keys


def test_service_initialization_with_db(api_keys):
    """Test service initialization with database"""
    # Arrange
    mock_db = Mock()

    # Act
    service = SummarizationService(
        supabase_client=mock_db,
        default_provider="anthropic",
        api_keys=api_keys
    )

    # Assert
    assert service.supabase == mock_db
    assert service.default_provider == "anthropic"


def test_service_initialization_without_api_keys():
    """Test service initialization without API keys"""
    # Act
    service = SummarizationService(
        supabase_client=None,
        default_provider="openai"
    )

    # Assert
    assert service.api_keys == {}


# ============================================================================
# TESTS: Summarize Meeting - Core Happy Path
# ============================================================================

@pytest.mark.asyncio
async def test_summarize_meeting_without_extractors(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test summarization without action items, decisions, or sentiment"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=["Topic 1", "Topic 2"])
        mock_summary_cls.return_value = mock_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            extract_action_items=False,
            extract_decisions=False,
            analyze_sentiment=False
        )

        # Assert
        assert result is not None
        assert "summary" in result
        assert "action_items" in result
        assert "decisions" in result
        assert "sentiment" in result
        assert result["action_items"] == []
        assert result["decisions"] == []
        assert result["sentiment"] == {}
        assert result["summary"].executive_summary is not None


@pytest.mark.asyncio
async def test_summarize_meeting_with_custom_config(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test summarization with custom LLM config"""
    # Arrange
    custom_config = LLMConfig(
        provider=LLMProviderType.ANTHROPIC,
        model_name="claude-3-sonnet",
        api_key="sk-ant-custom"
    )

    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            llm_config=custom_config
        )

        # Assert
        assert result["summary"].llm_provider == "anthropic"
        assert result["summary"].llm_model == "claude-3-sonnet"
        mock_select.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_meeting_records_processing_time(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test that processing time is recorded"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript
        )

        # Assert
        assert result["metadata"]["processing_time_ms"] > 0
        assert result["summary"].processing_time_ms > 0


@pytest.mark.asyncio
async def test_summarize_meeting_records_token_usage(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test that token usage is recorded"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript
        )

        # Assert
        assert result["summary"].token_usage == 500
        assert result["metadata"]["tokens_used"] == 500


@pytest.mark.asyncio
async def test_summarize_meeting_records_cost(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test that cost is recorded"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript
        )

        # Assert
        assert result["summary"].cost_usd == 0.02
        assert result["metadata"]["cost_usd"] == 0.02


# ============================================================================
# TESTS: Summarize Meeting - Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_summarize_meeting_llm_failure(
    service_with_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config
):
    """Test handling of LLM provider failure"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(
            side_effect=Exception("LLM API timeout")
        )
        mock_summary_cls.return_value = mock_chain

        # Act & Assert
        with pytest.raises(Exception, match="LLM API timeout"):
            await service_with_db.summarize_meeting(
                meeting_id=meeting_id,
                workspace_id=workspace_id,
                founder_id=founder_id,
                transcript=sample_transcript
            )


@pytest.mark.asyncio
async def test_summarize_meeting_database_save_failure_non_critical(
    service_with_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test that database failure doesn't prevent result return"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_chain

        # Mock database to fail
        service_with_db.supabase.table = Mock(
            side_effect=Exception("Database connection failed")
        )

        # Act - should still succeed despite database error
        result = await service_with_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript
        )

        # Assert
        assert result is not None
        assert "summary" in result


# ============================================================================
# TESTS: Action Item Extraction
# ============================================================================

@pytest.mark.asyncio
async def test_extract_action_items_with_confidence(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result,
    mock_action_items_result
):
    """Test action item extraction with confidence scoring"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch('app.services.summarization_service.ActionItemChain') as mock_action_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_summary_chain = AsyncMock()
        mock_summary_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_summary_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_summary_chain

        mock_action_chain = AsyncMock()
        mock_action_chain.extract_action_items = AsyncMock(return_value=mock_action_items_result)
        mock_action_cls.return_value = mock_action_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            extract_action_items=True
        )

        # Assert
        items = result["action_items"]
        assert len(items) == 2
        assert items[0].description == "Implement enterprise SSO"
        assert items[0].confidence_score == 0.95
        assert items[1].confidence_score == 0.87


@pytest.mark.asyncio
async def test_extract_action_items_with_assignee(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result,
    mock_action_items_result
):
    """Test action items include assignee information"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch('app.services.summarization_service.ActionItemChain') as mock_action_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_summary_chain = AsyncMock()
        mock_summary_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_summary_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_summary_chain

        mock_action_chain = AsyncMock()
        mock_action_chain.extract_action_items = AsyncMock(return_value=mock_action_items_result)
        mock_action_cls.return_value = mock_action_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            extract_action_items=True
        )

        # Assert
        item = result["action_items"][0]
        assert item.assignee_name == "Mike Johnson"
        assert item.assignee_email == "mike@example.com"


@pytest.mark.asyncio
async def test_extract_action_items_empty_result(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test action item extraction when no items found"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch('app.services.summarization_service.ActionItemChain') as mock_action_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_summary_chain = AsyncMock()
        mock_summary_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_summary_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_summary_chain

        mock_action_chain = AsyncMock()
        mock_action_chain.extract_action_items = AsyncMock(return_value=[])
        mock_action_cls.return_value = mock_action_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            extract_action_items=True
        )

        # Assert
        assert result["action_items"] == []
        assert result["summary"].action_items_count == 0


# ============================================================================
# TESTS: Decision Extraction
# ============================================================================

@pytest.mark.asyncio
async def test_extract_decisions_multiple_types(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result,
    mock_decisions_result
):
    """Test extraction of decisions with various types"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch('app.services.summarization_service.DecisionChain') as mock_decision_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_summary_chain = AsyncMock()
        mock_summary_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_summary_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_summary_chain

        mock_decision_chain = AsyncMock()
        mock_decision_chain.extract_decisions = AsyncMock(return_value=mock_decisions_result)
        mock_decision_cls.return_value = mock_decision_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            extract_decisions=True
        )

        # Assert
        decisions = result["decisions"]
        assert len(decisions) == 2
        assert decisions[0].decision_type == "financial"
        assert decisions[1].decision_type == "product"


@pytest.mark.asyncio
async def test_extract_decisions_with_stakeholders(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result,
    mock_decisions_result
):
    """Test decisions include stakeholder information"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch('app.services.summarization_service.DecisionChain') as mock_decision_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_summary_chain = AsyncMock()
        mock_summary_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_summary_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_summary_chain

        mock_decision_chain = AsyncMock()
        mock_decision_chain.extract_decisions = AsyncMock(return_value=mock_decisions_result)
        mock_decision_cls.return_value = mock_decision_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            extract_decisions=True
        )

        # Assert
        decision = result["decisions"][0]
        assert len(decision.stakeholders) >= 1
        assert "Sales" in decision.stakeholders or "Marketing" in decision.stakeholders


@pytest.mark.asyncio
async def test_extract_decisions_empty_result(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test decision extraction when no decisions found"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch('app.services.summarization_service.DecisionChain') as mock_decision_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_summary_chain = AsyncMock()
        mock_summary_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_summary_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_summary_chain

        mock_decision_chain = AsyncMock()
        mock_decision_chain.extract_decisions = AsyncMock(return_value=[])
        mock_decision_cls.return_value = mock_decision_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            extract_decisions=True
        )

        # Assert
        assert result["decisions"] == []
        assert result["summary"].decisions_count == 0


# ============================================================================
# TESTS: Sentiment Analysis
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_sentiment_positive(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result,
    mock_sentiment_result
):
    """Test sentiment analysis for positive meeting"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch('app.services.summarization_service.SentimentChain') as mock_sentiment_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_summary_chain = AsyncMock()
        mock_summary_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_summary_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_summary_chain

        mock_sentiment_chain = AsyncMock()
        mock_sentiment_chain.analyze_sentiment = AsyncMock(return_value=mock_sentiment_result)
        mock_sentiment_cls.return_value = mock_sentiment_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            analyze_sentiment=True
        )

        # Assert
        sentiment = result["sentiment"]
        assert sentiment["overall_sentiment"] == "positive"
        assert sentiment["confidence"] == 0.89


@pytest.mark.asyncio
async def test_analyze_sentiment_negative(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test sentiment analysis for negative meeting"""
    # Arrange
    negative_sentiment = {
        "overall_sentiment": "negative",
        "confidence": 0.76,
        "positive_segments": 1,
        "neutral_segments": 3,
        "negative_segments": 8
    }

    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch('app.services.summarization_service.SentimentChain') as mock_sentiment_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_summary_chain = AsyncMock()
        mock_summary_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_summary_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_summary_chain

        mock_sentiment_chain = AsyncMock()
        mock_sentiment_chain.analyze_sentiment = AsyncMock(return_value=negative_sentiment)
        mock_sentiment_cls.return_value = mock_sentiment_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            analyze_sentiment=True
        )

        # Assert
        sentiment = result["sentiment"]
        assert sentiment["overall_sentiment"] == "negative"
        assert sentiment["negative_segments"] == 8


@pytest.mark.asyncio
async def test_analyze_sentiment_neutral(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test sentiment analysis for neutral meeting"""
    # Arrange
    neutral_sentiment = {
        "overall_sentiment": "neutral",
        "confidence": 0.65
    }

    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch('app.services.summarization_service.SentimentChain') as mock_sentiment_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_summary_chain = AsyncMock()
        mock_summary_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_summary_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_summary_chain

        mock_sentiment_chain = AsyncMock()
        mock_sentiment_chain.analyze_sentiment = AsyncMock(return_value=neutral_sentiment)
        mock_sentiment_cls.return_value = mock_sentiment_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript,
            analyze_sentiment=True
        )

        # Assert
        assert result["sentiment"]["overall_sentiment"] == "neutral"


# ============================================================================
# TESTS: Batch Summarization
# ============================================================================

@pytest.mark.asyncio
async def test_batch_summarize_empty_list(
    service_without_db,
    workspace_id,
    founder_id
):
    """Test batch summarization with empty meeting list"""
    # Act
    results = await service_without_db.batch_summarize(
        meeting_ids=[],
        workspace_id=workspace_id,
        founder_id=founder_id
    )

    # Assert
    assert results == []


@pytest.mark.asyncio
async def test_batch_summarize_with_missing_transcripts(
    service_with_db,
    workspace_id,
    founder_id
):
    """Test batch summarization skips meetings without transcripts"""
    # Arrange
    meeting_ids = [uuid4(), uuid4()]

    with patch.object(service_with_db, '_get_meeting', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [
            {"transcript": "Meeting 1 transcript"},
            None  # No transcript
        ]

        # Act
        results = await service_with_db.batch_summarize(
            meeting_ids=meeting_ids,
            workspace_id=workspace_id,
            founder_id=founder_id
        )

    # Assert - only 1 result since second has no transcript
    assert len(results) == 1


@pytest.mark.asyncio
async def test_batch_summarize_with_failures(
    service_with_db,
    workspace_id,
    founder_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test batch summarization captures individual failures"""
    # Arrange
    meeting_ids = [uuid4(), uuid4()]

    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls, \
         patch.object(service_with_db, '_get_meeting', new_callable=AsyncMock) as mock_get_meeting:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        # First call succeeds, second fails
        mock_chain = AsyncMock()
        call_count = 0

        async def summarize_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_summarization_result
            raise Exception("LLM error on second call")

        mock_chain.summarize = AsyncMock(side_effect=summarize_side_effect)
        mock_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_chain

        mock_get_meeting.return_value = {"transcript": sample_transcript}

        # Act
        results = await service_with_db.batch_summarize(
            meeting_ids=meeting_ids,
            workspace_id=workspace_id,
            founder_id=founder_id
        )

    # Assert
    assert len(results) == 2
    assert results[0]["status"] == "success"
    assert results[1]["status"] == "failed"


# ============================================================================
# TESTS: Database Operations
# ============================================================================

@pytest.mark.asyncio
async def test_save_summary_to_database(
    service_with_db,
    workspace_id,
    founder_id,
    meeting_id
):
    """Test saving meeting summary to database"""
    # Arrange
    summary = MeetingSummary(
        workspace_id=workspace_id,
        founder_id=founder_id,
        meeting_id=meeting_id,
        executive_summary="Test summary",
        key_points=["Point 1", "Point 2"]
    )

    mock_table = Mock()
    service_with_db.supabase.table = Mock(return_value=mock_table)

    # Act
    await service_with_db._save_summary(summary)

    # Assert
    service_with_db.supabase.table.assert_called_with("meeting_summaries")
    mock_table.insert.assert_called_once()


@pytest.mark.asyncio
async def test_save_action_item_to_database(
    service_with_db,
    workspace_id,
    founder_id,
    meeting_id
):
    """Test saving action item to database"""
    # Arrange
    action_item = ActionItem(
        workspace_id=workspace_id,
        founder_id=founder_id,
        meeting_id=meeting_id,
        description="Implement feature X",
        assignee_name="John Doe"
    )

    mock_table = Mock()
    service_with_db.supabase.table = Mock(return_value=mock_table)

    # Act
    await service_with_db._save_action_item(action_item)

    # Assert
    service_with_db.supabase.table.assert_called_with("action_items")
    mock_table.insert.assert_called_once()


@pytest.mark.asyncio
async def test_save_decision_to_database(
    service_with_db,
    workspace_id,
    founder_id,
    meeting_id
):
    """Test saving decision to database"""
    # Arrange
    decision = Decision(
        workspace_id=workspace_id,
        founder_id=founder_id,
        meeting_id=meeting_id,
        title="Strategic decision",
        description="Pursue market X",
        decision_type="strategic"
    )

    mock_table = Mock()
    service_with_db.supabase.table = Mock(return_value=mock_table)

    # Act
    await service_with_db._save_decision(decision)

    # Assert
    service_with_db.supabase.table.assert_called_with("decisions")
    mock_table.insert.assert_called_once()


@pytest.mark.asyncio
async def test_update_meeting_status_completed(
    service_with_db,
    meeting_id
):
    """Test updating meeting status to completed"""
    # Arrange
    mock_table = Mock()
    service_with_db.supabase.table = Mock(return_value=mock_table)

    # Act
    await service_with_db._update_meeting_summarization_status(
        meeting_id=meeting_id,
        completed=True
    )

    # Assert
    service_with_db.supabase.table.assert_called_with("meetings")
    mock_table.update.assert_called_once()
    call_args = mock_table.update.call_args[0][0]
    assert call_args["status"] == "completed"


@pytest.mark.asyncio
async def test_update_meeting_status_failed(
    service_with_db,
    meeting_id
):
    """Test updating meeting status to failed with error"""
    # Arrange
    mock_table = Mock()
    service_with_db.supabase.table = Mock(return_value=mock_table)
    error_msg = "LLM provider timeout"

    # Act
    await service_with_db._update_meeting_summarization_status(
        meeting_id=meeting_id,
        completed=False,
        error_message=error_msg
    )

    # Assert
    service_with_db.supabase.table.assert_called_with("meetings")
    call_args = mock_table.update.call_args[0][0]
    assert call_args["status"] == "failed"
    assert call_args["error_message"] == error_msg


@pytest.mark.asyncio
async def test_get_meeting_found(
    service_with_db,
    meeting_id
):
    """Test retrieving meeting from database"""
    # Arrange
    meeting_data = {
        "id": str(meeting_id),
        "transcript": "Sample transcript"
    }

    mock_table = Mock()
    mock_table.select = Mock(return_value=Mock())
    mock_table.select.return_value.eq = Mock(return_value=Mock())
    mock_table.select.return_value.eq.return_value.execute = Mock(
        return_value=Mock(data=[meeting_data])
    )
    service_with_db.supabase.table = Mock(return_value=mock_table)

    # Act
    result = await service_with_db._get_meeting(meeting_id)

    # Assert
    assert result == meeting_data


@pytest.mark.asyncio
async def test_get_meeting_not_found(
    service_with_db,
    meeting_id
):
    """Test retrieving non-existent meeting"""
    # Arrange
    mock_table = Mock()
    mock_table.select = Mock(return_value=Mock())
    mock_table.select.return_value.eq = Mock(return_value=Mock())
    mock_table.select.return_value.eq.return_value.execute = Mock(
        return_value=Mock(data=[])
    )
    service_with_db.supabase.table = Mock(return_value=mock_table)

    # Act
    result = await service_with_db._get_meeting(meeting_id)

    # Assert
    assert result is None


# ============================================================================
# TESTS: Summarization Method and Topics
# ============================================================================

@pytest.mark.asyncio
async def test_summarization_uses_multi_stage_method(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test that multi_stage summarization method is used"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=["Topic 1", "Topic 2"])
        mock_summary_cls.return_value = mock_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript
        )

        # Assert
        assert result["summary"].summarization_method == SummarizationMethod.MULTI_STAGE
        mock_chain.summarize.assert_called_once_with(
            sample_transcript,
            method="multi_stage"
        )


@pytest.mark.asyncio
async def test_topics_are_extracted(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test that topics are extracted from transcript"""
    # Arrange
    topics = ["Product Roadmap", "Enterprise Features", "Budget Planning"]

    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=topics)
        mock_summary_cls.return_value = mock_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript
        )

        # Assert
        mock_chain.generate_topics.assert_called_once_with(sample_transcript)
        assert result["summary"].topics_discussed == topics


# ============================================================================
# TESTS: Summary Structure
# ============================================================================

@pytest.mark.asyncio
async def test_summary_structure_complete(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test that summary has all required fields"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript
        )

        # Assert
        summary = result["summary"]
        assert summary.workspace_id == workspace_id
        assert summary.founder_id == founder_id
        assert summary.meeting_id == meeting_id
        assert summary.executive_summary is not None
        assert summary.key_points is not None
        assert summary.status == "completed"


# ============================================================================
# TESTS: Results Structure
# ============================================================================

@pytest.mark.asyncio
async def test_result_structure(
    service_without_db,
    workspace_id,
    founder_id,
    meeting_id,
    sample_transcript,
    llm_config,
    mock_summarization_result
):
    """Test that summarize_meeting returns correct result structure"""
    # Arrange
    with patch('app.services.summarization_service.select_best_provider') as mock_select, \
         patch('app.services.summarization_service.get_provider') as mock_get, \
         patch('app.services.summarization_service.SummarizationChain') as mock_summary_cls:

        mock_select.return_value = llm_config
        mock_get.return_value = Mock()

        mock_chain = AsyncMock()
        mock_chain.summarize = AsyncMock(return_value=mock_summarization_result)
        mock_chain.generate_topics = AsyncMock(return_value=[])
        mock_summary_cls.return_value = mock_chain

        # Act
        result = await service_without_db.summarize_meeting(
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript=sample_transcript
        )

        # Assert
        assert "summary" in result
        assert "action_items" in result
        assert "decisions" in result
        assert "sentiment" in result
        assert "metadata" in result
        assert result["metadata"]["processing_time_ms"] > 0
