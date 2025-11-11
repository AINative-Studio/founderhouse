"""
Comprehensive tests for SentimentChain
Tests sentiment analysis, key moment detection, and transcript sampling
"""
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from app.chains.sentiment_chain import SentimentChain
from app.llm.llm_provider import LLMProvider, LLMResponse, LLMProviderType
from app.models.meeting_summary import SentimentScore


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider"""
    provider = Mock(spec=LLMProvider)
    provider.provider_type = LLMProviderType.OPENAI
    provider.complete = AsyncMock()
    return provider


@pytest.fixture
def sentiment_chain(mock_llm_provider):
    """SentimentChain instance with mocked provider"""
    return SentimentChain(mock_llm_provider)


@pytest.fixture
def positive_transcript():
    """Positive meeting transcript"""
    return """
    CEO: Great work everyone! I'm really impressed with our progress this quarter.
    CTO: Thanks! The team has been incredibly productive and collaborative.
    CFO: The numbers look fantastic. We exceeded our revenue targets by 20%.
    Marketing: The new campaign is performing amazingly well. Engagement is up 150%.
    CEO: This is exactly what we needed. Let's keep up this momentum!
    """


@pytest.fixture
def negative_transcript():
    """Negative meeting transcript"""
    return """
    CEO: I'm disappointed with our progress. We're falling behind schedule.
    CTO: The team is struggling with the technical debt. Morale is low.
    CFO: Revenue is down 15%. We need to make difficult decisions.
    Marketing: The campaign failed. We're not getting any traction.
    CEO: This is unacceptable. We need to turn this around immediately.
    """


@pytest.fixture
def tense_transcript():
    """Transcript with tension and disagreement"""
    return """
    CEO: I think we should pivot to B2B immediately.
    CTO: I disagree. That would be a huge mistake. We'd lose our current users.
    CEO: But the enterprise market is where the money is.
    CTO: That's short-sighted thinking. We haven't validated that market.
    CFO: Can we at least discuss this rationally? The arguing isn't helping.
    CTO: I'm just trying to prevent a disaster.
    CEO: Are you questioning my judgment?
    """


@pytest.fixture
def mixed_transcript():
    """Mixed sentiment transcript"""
    return """
    CEO: We had some wins and some losses this quarter.
    CTO: The product launch went well, but we had significant bugs.
    CFO: Revenue is stable but not growing as expected.
    Marketing: Some campaigns succeeded, others didn't resonate.
    CEO: Overall, we're making progress but need to accelerate.
    """


# ===== Basic Sentiment Analysis Tests =====

@pytest.mark.asyncio
async def test_analyze_sentiment_positive(sentiment_chain, mock_llm_provider, positive_transcript):
    """Test sentiment analysis on positive transcript"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""OVERALL_SENTIMENT: very_positive
ENERGY_LEVEL: high
COLLABORATION_SCORE: 9/10
TENSION_INDICATORS: none
POSITIVE_HIGHLIGHTS: Exceeded revenue targets by 20%; Team productivity exceptional; Campaign engagement up 150%
CONCERNS_RAISED: none
ENGAGEMENT: Team was highly engaged and enthusiastic""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=150,
        cost_usd=0.0015
    )

    result = await sentiment_chain.analyze_sentiment(positive_transcript)

    assert result["overall_sentiment"] == SentimentScore.VERY_POSITIVE
    assert result["energy_level"] == "high"
    assert result["collaboration_score"] == 9
    assert result["tension_indicators"] is None
    assert len(result["positive_highlights"]) > 0
    assert "analyzed_length" in result


@pytest.mark.asyncio
async def test_analyze_sentiment_negative(sentiment_chain, mock_llm_provider, negative_transcript):
    """Test sentiment analysis on negative transcript"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""OVERALL_SENTIMENT: negative
ENERGY_LEVEL: low
COLLABORATION_SCORE: 3/10
TENSION_INDICATORS: Disappointment with progress; Low team morale; Failed campaign
POSITIVE_HIGHLIGHTS: none
CONCERNS_RAISED: Behind schedule; Revenue down 15%; Technical debt issues
ENGAGEMENT: Team appeared discouraged and demotivated""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=150,
        cost_usd=0.0015
    )

    result = await sentiment_chain.analyze_sentiment(negative_transcript)

    assert result["overall_sentiment"] == SentimentScore.NEGATIVE
    assert result["energy_level"] == "low"
    assert result["collaboration_score"] == 3
    assert result["tension_indicators"] is not None
    assert len(result["concerns_raised"]) > 0


@pytest.mark.asyncio
async def test_analyze_sentiment_neutral(sentiment_chain, mock_llm_provider, mixed_transcript):
    """Test sentiment analysis on neutral transcript"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""OVERALL_SENTIMENT: neutral
ENERGY_LEVEL: medium
COLLABORATION_SCORE: 5/10
TENSION_INDICATORS: none
POSITIVE_HIGHLIGHTS: Product launch successful
CONCERNS_RAISED: Significant bugs; Revenue not growing as expected
ENGAGEMENT: Team was moderately engaged""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=150,
        cost_usd=0.0015
    )

    result = await sentiment_chain.analyze_sentiment(mixed_transcript)

    assert result["overall_sentiment"] == SentimentScore.NEUTRAL
    assert result["energy_level"] == "medium"
    assert result["collaboration_score"] == 5


@pytest.mark.asyncio
async def test_analyze_sentiment_with_tension(sentiment_chain, mock_llm_provider, tense_transcript):
    """Test sentiment analysis detecting tension"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""OVERALL_SENTIMENT: negative
ENERGY_LEVEL: high
COLLABORATION_SCORE: 2/10
TENSION_INDICATORS: Strong disagreement between CEO and CTO; Questioning of judgment; Defensive communication
POSITIVE_HIGHLIGHTS: none
CONCERNS_RAISED: Lack of alignment on strategy; Poor communication dynamics
ENGAGEMENT: High engagement but contentious""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=150,
        cost_usd=0.0015
    )

    result = await sentiment_chain.analyze_sentiment(tense_transcript)

    assert result["overall_sentiment"] in [SentimentScore.NEGATIVE, SentimentScore.VERY_NEGATIVE]
    assert result["collaboration_score"] <= 3
    assert result["tension_indicators"] is not None
    assert "disagreement" in result["tension_indicators"].lower() or "tension" in result["tension_indicators"].lower()


# ===== Transcript Sampling Tests =====

def test_sample_transcript_short(sentiment_chain):
    """Test sampling with short transcript"""
    short_transcript = "This is a short meeting transcript."

    sampled = sentiment_chain._sample_transcript(short_transcript, sample_size=2000)

    # Should return unchanged for short transcripts
    assert sampled == short_transcript


def test_sample_transcript_long(sentiment_chain):
    """Test sampling with long transcript"""
    # Create transcript with 3000 words
    words = [f"word{i}" for i in range(3000)]
    long_transcript = " ".join(words)

    sampled = sentiment_chain._sample_transcript(long_transcript, sample_size=300)

    # Should sample sections
    assert len(sampled.split()) < len(long_transcript.split())
    assert "..." in sampled  # Should have ellipsis markers


def test_sample_transcript_includes_sections(sentiment_chain):
    """Test that sampling includes beginning, middle, and end"""
    words = [f"word{i}" for i in range(3000)]
    long_transcript = " ".join(words)

    sampled = sentiment_chain._sample_transcript(long_transcript, sample_size=300)

    # Check for beginning
    assert "word0" in sampled
    # Check for middle section marker
    assert "..." in sampled
    # Check for end
    assert "word2999" in sampled


def test_sample_transcript_respects_size(sentiment_chain):
    """Test that sampled transcript respects size limit"""
    words = ["word"] * 5000
    long_transcript = " ".join(words)

    sampled = sentiment_chain._sample_transcript(long_transcript, sample_size=600)

    # Should be approximately sample_size
    word_count = len(sampled.split())
    assert word_count <= 700  # Allow some margin for ellipsis


@pytest.mark.asyncio
async def test_analyze_sentiment_long_transcript(sentiment_chain, mock_llm_provider):
    """Test sentiment analysis with long transcript (triggers sampling)"""
    # Create very long transcript
    long_transcript = "The team discussed many topics. " * 1000

    mock_llm_provider.complete.return_value = LLMResponse(
        content="""OVERALL_SENTIMENT: neutral
ENERGY_LEVEL: medium
COLLABORATION_SCORE: 5/10
TENSION_INDICATORS: none
POSITIVE_HIGHLIGHTS: none
CONCERNS_RAISED: none
ENGAGEMENT: moderate""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=100,
        cost_usd=0.001
    )

    result = await sentiment_chain.analyze_sentiment(long_transcript)

    # Should still analyze successfully
    assert "overall_sentiment" in result
    assert "analyzed_length" in result


# ===== Sentiment Score Parsing Tests =====

def test_parse_sentiment_score_very_positive(sentiment_chain):
    """Test parsing very positive sentiment"""
    test_cases = ["very positive", "very_positive", "VERY_POSITIVE"]

    for sentiment_str in test_cases:
        result = sentiment_chain._parse_sentiment_score(sentiment_str)
        assert result == SentimentScore.VERY_POSITIVE


def test_parse_sentiment_score_positive(sentiment_chain):
    """Test parsing positive sentiment"""
    result = sentiment_chain._parse_sentiment_score("positive")
    assert result == SentimentScore.POSITIVE


def test_parse_sentiment_score_neutral(sentiment_chain):
    """Test parsing neutral sentiment"""
    result = sentiment_chain._parse_sentiment_score("neutral")
    assert result == SentimentScore.NEUTRAL


def test_parse_sentiment_score_negative(sentiment_chain):
    """Test parsing negative sentiment"""
    result = sentiment_chain._parse_sentiment_score("negative")
    assert result == SentimentScore.NEGATIVE


def test_parse_sentiment_score_very_negative(sentiment_chain):
    """Test parsing very negative sentiment"""
    test_cases = ["very negative", "very_negative", "VERY_NEGATIVE"]

    for sentiment_str in test_cases:
        result = sentiment_chain._parse_sentiment_score(sentiment_str)
        assert result == SentimentScore.VERY_NEGATIVE


def test_parse_sentiment_score_default(sentiment_chain):
    """Test default to neutral for unknown sentiment"""
    result = sentiment_chain._parse_sentiment_score("unknown")
    assert result == SentimentScore.NEUTRAL


# ===== Response Parsing Tests =====

def test_parse_sentiment_response_complete(sentiment_chain):
    """Test parsing complete sentiment response"""
    response = """OVERALL_SENTIMENT: positive
ENERGY_LEVEL: high
COLLABORATION_SCORE: 8/10
TENSION_INDICATORS: none
POSITIVE_HIGHLIGHTS: Great teamwork; Exceeded goals
CONCERNS_RAISED: Budget constraints; Timeline pressure
ENGAGEMENT: Team was highly engaged"""

    analysis = sentiment_chain._parse_sentiment_response(response)

    assert analysis["overall_sentiment"] == SentimentScore.POSITIVE
    assert analysis["energy_level"] == "high"
    assert analysis["collaboration_score"] == 8
    assert analysis["tension_indicators"] is None
    assert len(analysis["positive_highlights"]) == 2
    assert len(analysis["concerns_raised"]) == 2
    assert "engaged" in analysis["engagement"]


def test_parse_sentiment_response_minimal(sentiment_chain):
    """Test parsing minimal response"""
    response = """OVERALL_SENTIMENT: neutral"""

    analysis = sentiment_chain._parse_sentiment_response(response)

    # Should have defaults for missing fields
    assert analysis["overall_sentiment"] == SentimentScore.NEUTRAL
    assert analysis["energy_level"] == "medium"
    assert analysis["collaboration_score"] == 5


def test_parse_sentiment_response_invalid_score(sentiment_chain):
    """Test parsing with invalid collaboration score"""
    response = """OVERALL_SENTIMENT: positive
COLLABORATION_SCORE: invalid/10"""

    analysis = sentiment_chain._parse_sentiment_response(response)

    # Should use default score
    assert analysis["collaboration_score"] == 5


def test_parse_sentiment_response_semicolon_lists(sentiment_chain):
    """Test parsing semicolon-separated lists"""
    response = """POSITIVE_HIGHLIGHTS: Item 1; Item 2; Item 3
CONCERNS_RAISED: Concern A; Concern B"""

    analysis = sentiment_chain._parse_sentiment_response(response)

    assert len(analysis["positive_highlights"]) == 3
    assert len(analysis["concerns_raised"]) == 2


def test_parse_sentiment_response_filters_none(sentiment_chain):
    """Test that 'none' values are filtered out"""
    response = """TENSION_INDICATORS: none
POSITIVE_HIGHLIGHTS: none
CONCERNS_RAISED: not specified"""

    analysis = sentiment_chain._parse_sentiment_response(response)

    assert analysis["tension_indicators"] is None
    assert len(analysis["positive_highlights"]) == 0
    assert len(analysis["concerns_raised"]) == 0


# ===== Key Moments Detection Tests =====

@pytest.mark.asyncio
async def test_identify_key_moments(sentiment_chain, mock_llm_provider, positive_transcript):
    """Test identifying key moments"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""MOMENT: Team exceeded revenue targets by 20% | SIGNIFICANCE: Shows strong business performance | LOCATION: middle
MOMENT: New campaign engagement up 150% | SIGNIFICANCE: Marketing strategy is working | LOCATION: middle
MOMENT: CEO praised team's productivity | SIGNIFICANCE: Boosts team morale and momentum | LOCATION: beginning""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=150,
        cost_usd=0.0015
    )

    moments = await sentiment_chain.identify_key_moments(positive_transcript)

    assert len(moments) == 3
    assert all("description" in m for m in moments)
    assert all("significance" in m for m in moments)
    assert all("location" in m for m in moments)


@pytest.mark.asyncio
async def test_identify_key_moments_malformed(sentiment_chain, mock_llm_provider, positive_transcript):
    """Test handling malformed key moments response"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""MOMENT: Some moment without proper formatting
Random text
MOMENT: Another moment | SIGNIFICANCE: Why it matters""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=100,
        cost_usd=0.001
    )

    moments = await sentiment_chain.identify_key_moments(positive_transcript)

    # Should handle gracefully and parse what it can
    assert isinstance(moments, list)


@pytest.mark.asyncio
async def test_identify_key_moments_llm_failure(sentiment_chain, mock_llm_provider, positive_transcript):
    """Test handling LLM failure in key moments"""
    mock_llm_provider.complete.side_effect = Exception("LLM API error")

    moments = await sentiment_chain.identify_key_moments(positive_transcript)

    # Should return empty list on error
    assert moments == []


@pytest.mark.asyncio
async def test_identify_key_moments_empty_response(sentiment_chain, mock_llm_provider, positive_transcript):
    """Test handling empty response"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="No key moments identified.",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=50,
        cost_usd=0.0005
    )

    moments = await sentiment_chain.identify_key_moments(positive_transcript)

    assert moments == []


# ===== Error Handling Tests =====

@pytest.mark.asyncio
async def test_analyze_sentiment_llm_failure(sentiment_chain, mock_llm_provider, positive_transcript):
    """Test handling LLM failure"""
    mock_llm_provider.complete.side_effect = Exception("API timeout")

    with pytest.raises(Exception, match="API timeout"):
        await sentiment_chain.analyze_sentiment(positive_transcript)


@pytest.mark.asyncio
async def test_analyze_sentiment_malformed_response(sentiment_chain, mock_llm_provider, positive_transcript):
    """Test handling malformed response"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="This is not a properly formatted sentiment analysis",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=50,
        cost_usd=0.0005
    )

    result = await sentiment_chain.analyze_sentiment(positive_transcript)

    # Should return defaults for unparseable fields
    assert "overall_sentiment" in result
    assert result["overall_sentiment"] == SentimentScore.NEUTRAL  # Default


# ===== Integration Tests =====

@pytest.mark.asyncio
async def test_full_sentiment_analysis_pipeline(sentiment_chain, mock_llm_provider, positive_transcript):
    """Test complete sentiment analysis pipeline"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""OVERALL_SENTIMENT: very_positive
ENERGY_LEVEL: high
COLLABORATION_SCORE: 9/10
TENSION_INDICATORS: none
POSITIVE_HIGHLIGHTS: Revenue exceeded targets by 20%; Team collaboration exceptional; Campaign performing amazingly
CONCERNS_RAISED: none
ENGAGEMENT: Team highly engaged and enthusiastic about progress""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=180,
        cost_usd=0.0018
    )

    result = await sentiment_chain.analyze_sentiment(positive_transcript)

    # Verify complete structure
    assert "overall_sentiment" in result
    assert "energy_level" in result
    assert "collaboration_score" in result
    assert "tension_indicators" in result
    assert "positive_highlights" in result
    assert "concerns_raised" in result
    assert "engagement" in result
    assert "analyzed_length" in result

    # Verify data types
    assert isinstance(result["overall_sentiment"], SentimentScore)
    assert isinstance(result["energy_level"], str)
    assert isinstance(result["collaboration_score"], int)
    assert isinstance(result["positive_highlights"], list)
    assert isinstance(result["concerns_raised"], list)

    # Verify sentiment values
    assert result["overall_sentiment"] == SentimentScore.VERY_POSITIVE
    assert result["energy_level"] == "high"
    assert result["collaboration_score"] >= 8
    assert result["tension_indicators"] is None
    assert len(result["positive_highlights"]) >= 3

    # Verify analyzed length is tracked
    assert result["analyzed_length"] > 0


@pytest.mark.asyncio
async def test_sentiment_analysis_all_types(sentiment_chain, mock_llm_provider):
    """Test sentiment analysis with all sentiment types"""
    test_cases = [
        ("very_positive", SentimentScore.VERY_POSITIVE),
        ("positive", SentimentScore.POSITIVE),
        ("neutral", SentimentScore.NEUTRAL),
        ("negative", SentimentScore.NEGATIVE),
        ("very_negative", SentimentScore.VERY_NEGATIVE),
    ]

    for sentiment_str, expected_score in test_cases:
        mock_llm_provider.complete.return_value = LLMResponse(
            content=f"""OVERALL_SENTIMENT: {sentiment_str}
ENERGY_LEVEL: medium
COLLABORATION_SCORE: 5/10
TENSION_INDICATORS: none
POSITIVE_HIGHLIGHTS: none
CONCERNS_RAISED: none
ENGAGEMENT: moderate""",
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            total_tokens=100,
            cost_usd=0.001
        )

        result = await sentiment_chain.analyze_sentiment("test transcript")
        assert result["overall_sentiment"] == expected_score
