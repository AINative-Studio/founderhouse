"""
Comprehensive tests for LLM Chains
Tests action item, decision, summarization, and sentiment chains
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.llm_provider import LLMResponse, LLMProviderType, LLMConfig
from app.chains.action_item_chain import ActionItemChain
from app.chains.decision_chain import DecisionChain
from app.chains.summarization_chain import SummarizationChain
from app.chains.sentiment_chain import SentimentChain


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider"""
    provider = MagicMock()
    provider.provider_type = LLMProviderType.OPENAI
    provider.config = LLMConfig(
        provider=LLMProviderType.OPENAI,
        model_name="gpt-3.5-turbo"
    )
    return provider


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript for testing"""
    return """
    John: Let's start the meeting. We need to finalize the Q4 roadmap today.

    Sarah: I think we should prioritize the mobile app. Our users have been requesting it for months.
    Mike will start working on the iOS version next week.

    John: Agreed. Mike, can you commit to completing the iOS app by end of Q4?

    Mike: Yes, I can do that. I'll need Sarah to help with the UI design though.

    Sarah: Sure, I'll have the designs ready by next Friday.

    John: Perfect. We also need to decide on the pricing model. I propose we start with $49/month.

    Sarah: That sounds reasonable. We should follow up with the finance team to validate.

    Mike: One more thing - we must fix the authentication bug before launch. It's critical.

    John: Good catch. Let's make that our top priority. Meeting adjourned.
    """


class TestActionItemChain:
    """Tests for ActionItemChain"""

    @pytest.mark.asyncio
    async def test_extract_action_items_llm_only(self, mock_llm_provider, sample_transcript):
        """Test LLM-only action item extraction"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="""ITEM: Complete iOS app by end of Q4
ASSIGNEE: Mike
DUE: end of Q4
PRIORITY: high
CONTEXT: Users have been requesting mobile app for months
---
ITEM: Prepare UI designs
ASSIGNEE: Sarah
DUE: next Friday
PRIORITY: high
CONTEXT: Needed for iOS app development
---
ITEM: Fix authentication bug
ASSIGNEE: unassigned
DUE: before launch
PRIORITY: urgent
CONTEXT: Critical bug that must be fixed before launch
---""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=200,
            cost_usd=0.002
        ))

        chain = ActionItemChain(mock_llm_provider)

        # Act
        items = await chain.extract_action_items(sample_transcript, use_hybrid=False)

        # Assert
        assert len(items) == 3
        assert any("iOS" in item["description"] for item in items)
        assert any(item["priority"] == "urgent" for item in items)
        mock_llm_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_action_items_hybrid(self, mock_llm_provider, sample_transcript):
        """Test hybrid (regex + LLM) action item extraction"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="""ITEM: Complete iOS app
ASSIGNEE: Mike
DUE: Q4
PRIORITY: high
CONTEXT: Mobile app development
---""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=100,
            cost_usd=0.001
        ))

        chain = ActionItemChain(mock_llm_provider)

        # Act
        items = await chain.extract_action_items(sample_transcript, use_hybrid=True)

        # Assert
        assert len(items) > 0

    @pytest.mark.asyncio
    async def test_action_item_confidence_scoring(self, mock_llm_provider, sample_transcript):
        """Test action item confidence scoring"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="""ITEM: Fix authentication bug
ASSIGNEE: unassigned
DUE: before launch
PRIORITY: urgent
CONTEXT: Critical security issue
---""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=80,
            cost_usd=0.0008
        ))

        chain = ActionItemChain(mock_llm_provider)

        # Act
        items = await chain.extract_action_items(sample_transcript, use_hybrid=False)

        # Assert
        assert all("confidence_score" in item for item in items)
        assert all(0 <= item["confidence_score"] <= 1 for item in items)

    @pytest.mark.asyncio
    async def test_regex_extraction(self, mock_llm_provider):
        """Test regex-based action item extraction"""
        # Arrange
        transcript = "We need to implement SSO by next week. John should follow up with the security team."
        chain = ActionItemChain(mock_llm_provider)

        # Act
        items = chain._regex_extraction(transcript)

        # Assert
        assert len(items) > 0

    @pytest.mark.asyncio
    async def test_parse_llm_action_items(self, mock_llm_provider):
        """Test parsing LLM response into action items"""
        # Arrange
        llm_response = """ITEM: Deploy to production
ASSIGNEE: DevOps Team
DUE: Friday
PRIORITY: high
CONTEXT: Final deployment for release
---
ITEM: Update documentation
ASSIGNEE: Tech Writer
DUE: not specified
PRIORITY: normal
CONTEXT: User-facing documentation needs update
---"""
        chain = ActionItemChain(mock_llm_provider)

        # Act
        items = chain._parse_llm_action_items(llm_response)

        # Assert
        assert len(items) == 2
        assert items[0]["description"] == "Deploy to production"
        assert items[0]["assignee_name"] == "DevOps Team"
        assert items[1]["priority"] == "normal"


class TestDecisionChain:
    """Tests for DecisionChain"""

    @pytest.mark.asyncio
    async def test_extract_decisions(self, mock_llm_provider, sample_transcript):
        """Test decision extraction from transcript"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="""TITLE: Pricing model decision
DESCRIPTION: Set monthly subscription price to $49
TYPE: financial
IMPACT: high
DECISION_MAKER: John
RATIONALE: Competitive pricing for market entry
STAKEHOLDERS: Finance team, Product team
---
TITLE: Prioritize mobile app
DESCRIPTION: Focus development on iOS app for Q4
TYPE: strategic
IMPACT: high
DECISION_MAKER: Team
RATIONALE: High user demand for mobile access
STAKEHOLDERS: Development team, Product team
---""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=150,
            cost_usd=0.0015
        ))

        chain = DecisionChain(mock_llm_provider)

        # Act
        decisions = await chain.extract_decisions(sample_transcript)

        # Assert
        assert len(decisions) == 2
        assert any("pricing" in d["title"].lower() for d in decisions)
        assert any(d["impact"] == "high" for d in decisions)

    @pytest.mark.asyncio
    async def test_decision_parsing(self, mock_llm_provider):
        """Test decision parsing from LLM response"""
        # Arrange
        llm_response = """TITLE: Architecture decision
DESCRIPTION: Migrate to microservices
TYPE: technical
IMPACT: high
DECISION_MAKER: CTO
RATIONALE: Better scalability and maintainability
CONTEXT: Current monolith is becoming hard to maintain
STAKEHOLDERS: Engineering team
---"""
        chain = DecisionChain(mock_llm_provider)

        # Act
        decisions = chain._parse_llm_decisions(llm_response)

        # Assert
        assert len(decisions) == 1
        assert decisions[0]["title"] == "Architecture decision"
        assert decisions[0]["decision_type"] == "technical"
        assert decisions[0]["impact"] == "high"

    @pytest.mark.asyncio
    async def test_decision_confidence_scoring(self, mock_llm_provider, sample_transcript):
        """Test decision confidence scoring"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="""TITLE: Test decision
DESCRIPTION: Sample decision
TYPE: strategic
IMPACT: medium
DECISION_MAKER: Team
RATIONALE: Test rationale
---""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=100,
            cost_usd=0.001
        ))

        chain = DecisionChain(mock_llm_provider)

        # Act
        decisions = await chain.extract_decisions(sample_transcript)

        # Assert
        assert all("confidence_score" in d for d in decisions)
        assert all(0 <= d["confidence_score"] <= 1 for d in decisions)


class TestSummarizationChain:
    """Tests for SummarizationChain"""

    @pytest.mark.asyncio
    async def test_multi_stage_summarization(self, mock_llm_provider, sample_transcript):
        """Test multi-stage summarization (extractive -> abstractive -> refinement)"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(side_effect=[
            # Extractive stage
            LLMResponse(
                content="- Prioritize mobile app\n- Set pricing at $49/month\n- Fix authentication bug",
                provider=LLMProviderType.OPENAI,
                model="gpt-3.5-turbo",
                total_tokens=100,
                cost_usd=0.001
            ),
            # Abstractive stage
            LLMResponse(
                content="Team decided to prioritize iOS app development and set subscription pricing at $49/month.",
                provider=LLMProviderType.OPENAI,
                model="gpt-3.5-turbo",
                total_tokens=80,
                cost_usd=0.0008
            ),
            # Refinement stage
            LLMResponse(
                content="Executive Summary: Q4 roadmap finalized with focus on mobile app.\n\nThe team committed to delivering iOS app by Q4, with $49/month pricing model.",
                provider=LLMProviderType.OPENAI,
                model="gpt-3.5-turbo",
                total_tokens=90,
                cost_usd=0.0009
            )
        ])

        chain = SummarizationChain(mock_llm_provider)

        # Act
        result = await chain.summarize(sample_transcript, method="multi_stage")

        # Assert
        assert "executive_summary" in result
        assert "detailed_summary" in result
        assert "key_points" in result
        assert len(result["key_points"]) > 0
        assert mock_llm_provider.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_extractive_summarization(self, mock_llm_provider, sample_transcript):
        """Test extractive-only summarization"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="- Mobile app prioritization\n- Pricing decision\n- Bug fix needed",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=50,
            cost_usd=0.0005
        ))

        chain = SummarizationChain(mock_llm_provider)

        # Act
        result = await chain.summarize(sample_transcript, method="extractive")

        # Assert
        assert "key_points" in result
        assert len(result["key_points"]) > 0

    @pytest.mark.asyncio
    async def test_generate_topics(self, mock_llm_provider, sample_transcript):
        """Test topic generation"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="Q4 Roadmap\nMobile App Development\nPricing Strategy\nBug Fixes",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=40,
            cost_usd=0.0004
        ))

        chain = SummarizationChain(mock_llm_provider)

        # Act
        topics = await chain.generate_topics(sample_transcript)

        # Assert
        assert len(topics) > 0
        assert any("roadmap" in topic.lower() for topic in topics)

    @pytest.mark.asyncio
    async def test_cost_tracking(self, mock_llm_provider, sample_transcript):
        """Test that summarization tracks costs"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="Summary",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=100,
            cost_usd=0.001
        ))

        chain = SummarizationChain(mock_llm_provider)

        # Act
        result = await chain.summarize(sample_transcript, method="extractive")

        # Assert
        assert "metadata" in result
        assert "total_cost_usd" in result["metadata"]
        assert result["metadata"]["total_cost_usd"] > 0


class TestSentimentChain:
    """Tests for SentimentChain"""

    @pytest.mark.asyncio
    async def test_analyze_sentiment(self, mock_llm_provider, sample_transcript):
        """Test sentiment analysis"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="""OVERALL_SENTIMENT: positive
ENERGY_LEVEL: high
COLLABORATION_SCORE: 9/10
ENGAGEMENT: Team was highly engaged and productive
KEY_EMOTIONS: Enthusiastic, Focused, Collaborative
TONE: Professional and constructive
CONCERNS: Authentication bug mentioned as critical concern""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=120,
            cost_usd=0.0012
        ))

        chain = SentimentChain(mock_llm_provider)

        # Act
        result = await chain.analyze_sentiment(sample_transcript)

        # Assert
        assert "overall_sentiment" in result
        assert result["overall_sentiment"] == "positive"
        assert "energy_level" in result
        assert "collaboration_score" in result

    @pytest.mark.asyncio
    async def test_sentiment_parsing(self, mock_llm_provider):
        """Test sentiment response parsing"""
        # Arrange
        llm_response = """OVERALL_SENTIMENT: negative
ENERGY_LEVEL: low
COLLABORATION_SCORE: 3/10
ENGAGEMENT: Low engagement, many distractions
KEY_EMOTIONS: Frustrated, Confused
TONE: Tense and defensive"""

        chain = SentimentChain(mock_llm_provider)

        # Act
        result = chain._parse_sentiment_response(llm_response)

        # Assert
        assert result["overall_sentiment"] == "negative"
        assert result["energy_level"] == "low"
        assert "collaboration_score" in result

    @pytest.mark.asyncio
    async def test_speaker_sentiment_analysis(self, mock_llm_provider, sample_transcript):
        """Test per-speaker sentiment analysis"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="""OVERALL_SENTIMENT: positive
SPEAKER_SENTIMENTS:
- John: Positive, leadership tone
- Sarah: Enthusiastic, collaborative
- Mike: Focused, committed""",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=100,
            cost_usd=0.001
        ))

        chain = SentimentChain(mock_llm_provider)

        # Act
        result = await chain.analyze_sentiment(sample_transcript)

        # Assert
        assert "overall_sentiment" in result


class TestErrorHandling:
    """Tests for error handling in chains"""

    @pytest.mark.asyncio
    async def test_action_item_chain_llm_error(self, mock_llm_provider, sample_transcript):
        """Test action item chain handles LLM errors"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(side_effect=Exception("LLM API error"))
        chain = ActionItemChain(mock_llm_provider)

        # Act & Assert
        with pytest.raises(Exception):
            await chain.extract_action_items(sample_transcript, use_hybrid=False)

    @pytest.mark.asyncio
    async def test_summarization_chain_empty_transcript(self, mock_llm_provider):
        """Test summarization with empty transcript"""
        # Arrange
        chain = SummarizationChain(mock_llm_provider)

        # Act & Assert
        with pytest.raises(Exception):
            await chain.summarize("", method="multi_stage")

    @pytest.mark.asyncio
    async def test_malformed_llm_response(self, mock_llm_provider, sample_transcript):
        """Test handling of malformed LLM responses"""
        # Arrange
        mock_llm_provider.complete = AsyncMock(return_value=LLMResponse(
            content="Invalid response without proper formatting",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            total_tokens=50,
            cost_usd=0.0005
        ))

        chain = ActionItemChain(mock_llm_provider)

        # Act
        items = await chain.extract_action_items(sample_transcript, use_hybrid=False)

        # Assert - should handle gracefully and return empty or partial results
        assert isinstance(items, list)


class TestIntegration:
    """Integration tests combining multiple chains"""

    @pytest.mark.asyncio
    async def test_full_meeting_analysis(self, mock_llm_provider, sample_transcript):
        """Test full meeting analysis using all chains"""
        # Arrange - Mock all chain responses
        mock_llm_provider.complete = AsyncMock(side_effect=[
            # Summarization
            LLMResponse(content="Summary", provider=LLMProviderType.OPENAI, model="gpt-3.5-turbo", total_tokens=100, cost_usd=0.001),
            LLMResponse(content="Detailed", provider=LLMProviderType.OPENAI, model="gpt-3.5-turbo", total_tokens=100, cost_usd=0.001),
            LLMResponse(content="Executive", provider=LLMProviderType.OPENAI, model="gpt-3.5-turbo", total_tokens=100, cost_usd=0.001),
            # Topics
            LLMResponse(content="Topics", provider=LLMProviderType.OPENAI, model="gpt-3.5-turbo", total_tokens=50, cost_usd=0.0005),
            # Action items
            LLMResponse(content="ITEM: Test\nASSIGNEE: User\nDUE: Soon\nPRIORITY: high\nCONTEXT: Context\n---",
                       provider=LLMProviderType.OPENAI, model="gpt-3.5-turbo", total_tokens=80, cost_usd=0.0008),
            # Decisions
            LLMResponse(content="TITLE: Test\nDESCRIPTION: Desc\nTYPE: strategic\nIMPACT: high\nDECISION_MAKER: Team\nRATIONALE: Reason\n---",
                       provider=LLMProviderType.OPENAI, model="gpt-3.5-turbo", total_tokens=90, cost_usd=0.0009),
            # Sentiment
            LLMResponse(content="OVERALL_SENTIMENT: positive\nENERGY_LEVEL: high\nCOLLABORATION_SCORE: 8/10\nENGAGEMENT: Good",
                       provider=LLMProviderType.OPENAI, model="gpt-3.5-turbo", total_tokens=60, cost_usd=0.0006)
        ])

        sum_chain = SummarizationChain(mock_llm_provider)
        action_chain = ActionItemChain(mock_llm_provider)
        decision_chain = DecisionChain(mock_llm_provider)
        sentiment_chain = SentimentChain(mock_llm_provider)

        # Act
        summary = await sum_chain.summarize(sample_transcript, method="multi_stage")
        topics = await sum_chain.generate_topics(sample_transcript)
        actions = await action_chain.extract_action_items(sample_transcript, use_hybrid=False)
        decisions = await decision_chain.extract_decisions(sample_transcript)
        sentiment = await sentiment_chain.analyze_sentiment(sample_transcript)

        # Assert
        assert summary is not None
        assert len(topics) > 0
        assert len(actions) > 0
        assert len(decisions) > 0
        assert sentiment["overall_sentiment"] == "positive"
