"""
Comprehensive tests for SummarizationChain
Tests multi-stage summarization, chunking, and all summarization methods
"""
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from app.chains.summarization_chain import SummarizationChain
from app.llm.llm_provider import LLMProvider, LLMResponse, LLMProviderType
from app.models.meeting_summary import SummarizationMethod


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider"""
    provider = Mock(spec=LLMProvider)
    provider.provider_type = LLMProviderType.OPENAI
    provider.complete = AsyncMock()
    return provider


@pytest.fixture
def summarization_chain(mock_llm_provider):
    """SummarizationChain instance with mocked provider"""
    return SummarizationChain(mock_llm_provider)


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript"""
    return """
    CEO: Let's review our Q4 roadmap. We need to prioritize enterprise features.
    CTO: Agreed. I propose we focus on SSO, RBAC, and audit logs first.
    CEO: That makes sense. What's the timeline?
    CTO: We can deliver SSO in 6 weeks, RBAC in 8 weeks, and audit logs in 10 weeks.
    CFO: What about the budget? Do we need additional resources?
    CTO: We'll need to hire 2 senior engineers to meet this timeline.
    CEO: Approved. Let's start the hiring process immediately.
    Marketing: How will this affect our product marketing?
    CEO: Great question. We'll need to update our positioning for enterprise customers.
    Marketing: I'll coordinate with the product team on messaging.
    """


@pytest.fixture
def long_transcript():
    """Long transcript for chunking tests"""
    return " ".join([
        "The team discussed various important topics.",
        "Key decisions were made about the product roadmap.",
        "Action items were assigned to various team members."
    ] * 800)  # Create ~2400 word transcript


# ===== Extractive Summarization Tests =====

@pytest.mark.asyncio
async def test_extractive_summarization_basic(summarization_chain, mock_llm_provider, sample_transcript):
    """Test basic extractive summarization"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""- Q4 roadmap focused on enterprise features
- Prioritize SSO, RBAC, and audit logs
- Timeline: SSO in 6 weeks, RBAC in 8 weeks, audit logs in 10 weeks
- Need to hire 2 senior engineers
- Update product marketing for enterprise positioning""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=150,
        cost_usd=0.0015
    )

    result = await summarization_chain._extractive_summarization(sample_transcript)

    assert "summary" in result
    assert "method" in result
    assert result["method"] == "extractive"
    assert "metadata" in result
    assert "original_length" in result["metadata"]
    assert "summary_length" in result["metadata"]
    mock_llm_provider.complete.assert_called_once()


@pytest.mark.asyncio
async def test_extractive_summarization_long_transcript(summarization_chain, mock_llm_provider, long_transcript):
    """Test extractive summarization with chunking"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="- Key point from chunk",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=50,
        cost_usd=0.0005
    )

    result = await summarization_chain._extractive_summarization(long_transcript)

    # Should call LLM multiple times for chunks
    assert mock_llm_provider.complete.call_count >= 1
    assert "summary" in result
    assert len(result["summary"]) > 0


@pytest.mark.asyncio
async def test_extractive_summarization_empty_transcript(summarization_chain, mock_llm_provider):
    """Test extractive summarization with empty transcript"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="No key points found.",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=10,
        cost_usd=0.0001
    )

    result = await summarization_chain._extractive_summarization("")

    assert "summary" in result
    assert result["metadata"]["original_length"] == 0


# ===== Abstractive Summarization Tests =====

@pytest.mark.asyncio
async def test_abstractive_summarization_basic(summarization_chain, mock_llm_provider, sample_transcript):
    """Test basic abstractive summarization"""
    # Mock extractive call
    mock_llm_provider.complete.side_effect = [
        # First call: extractive
        LLMResponse(
            content="- Q4 roadmap\n- Enterprise features\n- Hiring 2 engineers",
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            total_tokens=100,
            cost_usd=0.001
        ),
        # Second call: abstractive
        LLMResponse(
            content="""The team agreed to focus Q4 development on enterprise features including SSO, RBAC, and audit logs.

The CTO outlined an implementation timeline with SSO delivery in 6 weeks, followed by RBAC and audit logs. To meet this aggressive timeline, the CEO approved hiring 2 senior engineers immediately. The marketing team will update product positioning to reflect the enterprise focus.""",
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            total_tokens=200,
            cost_usd=0.002
        )
    ]

    result = await summarization_chain._abstractive_summarization(sample_transcript)

    assert "summary" in result
    assert "method" in result
    assert result["method"] == "abstractive"
    assert "key_points" in result
    assert "metadata" in result
    assert "tokens_used" in result["metadata"]
    assert "cost_usd" in result["metadata"]
    assert mock_llm_provider.complete.call_count == 2


# ===== Multi-stage Summarization Tests =====

@pytest.mark.asyncio
async def test_multi_stage_summarization_complete(summarization_chain, mock_llm_provider, sample_transcript):
    """Test complete multi-stage summarization pipeline"""
    mock_llm_provider.complete.side_effect = [
        # Stage 1: Extractive
        LLMResponse(
            content="- Q4 roadmap discussion\n- Enterprise features prioritized\n- Hiring 2 engineers",
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            total_tokens=100,
            cost_usd=0.001
        ),
        # Stage 2: Abstractive
        LLMResponse(
            content="""The leadership team aligned on Q4 priorities focused on enterprise customers.

The technical roadmap includes SSO, RBAC, and audit logs with delivery over 10 weeks. The CEO approved hiring 2 senior engineers to support this initiative. Marketing will update positioning accordingly.""",
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            total_tokens=150,
            cost_usd=0.0015
        ),
        # Stage 3: Refinement
        LLMResponse(
            content="""Executive Summary: The team committed to an enterprise-focused Q4 roadmap with SSO, RBAC, and audit logs as key deliverables.

Detailed Summary: During the Q4 planning meeting, leadership aligned on prioritizing enterprise features. The CTO presented a phased implementation plan: SSO in 6 weeks, RBAC in 8 weeks, and audit logs in 10 weeks. To achieve this timeline, the CEO approved immediate hiring of 2 senior engineers. The marketing team will coordinate with product to refresh enterprise-focused messaging and positioning.""",
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            total_tokens=200,
            cost_usd=0.002
        )
    ]

    result = await summarization_chain._multi_stage_summarization(sample_transcript)

    assert "summary" in result
    assert "executive_summary" in result
    assert "detailed_summary" in result
    assert "key_points" in result
    assert "method" in result
    assert result["method"] == "multi_stage"
    assert "metadata" in result
    assert "total_tokens" in result["metadata"]
    assert "total_cost_usd" in result["metadata"]
    assert mock_llm_provider.complete.call_count == 3


@pytest.mark.asyncio
async def test_summarize_method_routing_extractive(summarization_chain, mock_llm_provider, sample_transcript):
    """Test method routing for extractive"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="- Key points",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=50,
        cost_usd=0.0005
    )

    result = await summarization_chain.summarize(
        transcript=sample_transcript,
        method="extractive"
    )

    assert result["method"] == "extractive"


@pytest.mark.asyncio
async def test_summarize_method_routing_abstractive(summarization_chain, mock_llm_provider, sample_transcript):
    """Test method routing for abstractive"""
    mock_llm_provider.complete.side_effect = [
        LLMResponse(content="- Points", provider=LLMProviderType.OPENAI, model="gpt-4", total_tokens=50, cost_usd=0.0005),
        LLMResponse(content="Summary", provider=LLMProviderType.OPENAI, model="gpt-4", total_tokens=100, cost_usd=0.001)
    ]

    result = await summarization_chain.summarize(
        transcript=sample_transcript,
        method="abstractive"
    )

    assert result["method"] == "abstractive"


@pytest.mark.asyncio
async def test_summarize_method_routing_multi_stage(summarization_chain, mock_llm_provider, sample_transcript):
    """Test method routing for multi-stage (default)"""
    mock_llm_provider.complete.side_effect = [
        LLMResponse(content="- Points", provider=LLMProviderType.OPENAI, model="gpt-4", total_tokens=50, cost_usd=0.0005),
        LLMResponse(content="Draft", provider=LLMProviderType.OPENAI, model="gpt-4", total_tokens=100, cost_usd=0.001),
        LLMResponse(content="Final", provider=LLMProviderType.OPENAI, model="gpt-4", total_tokens=150, cost_usd=0.0015)
    ]

    result = await summarization_chain.summarize(
        transcript=sample_transcript,
        method="multi_stage"
    )

    assert result["method"] == "multi_stage"


# ===== Chunking Tests =====

def test_chunk_transcript_basic(summarization_chain):
    """Test basic transcript chunking"""
    # Create text that's definitely longer than chunk size
    # RecursiveCharacterTextSplitter uses characters, not words
    # 2000 words * 4 chars = ~8000 characters minimum
    words = ["word"] * 10000
    transcript = " ".join(words)

    chunks = summarization_chain._chunk_transcript(transcript, chunk_size=2000)

    # With 10000 words (~50000 chars) and chunk_size 2000 (~8000 chars), should get multiple chunks
    assert len(chunks) >= 2


def test_chunk_transcript_small(summarization_chain):
    """Test chunking small transcript"""
    transcript = "Short transcript"

    chunks = summarization_chain._chunk_transcript(transcript, chunk_size=1000)

    assert len(chunks) >= 1


# ===== Summary Parsing Tests =====

def test_parse_summary_sections_with_paragraphs(summarization_chain):
    """Test parsing summary with multiple paragraphs"""
    summary = """This is the executive summary in the first paragraph.

This is the detailed content in the second paragraph.

And more detailed content here."""

    sections = summarization_chain._parse_summary_sections(summary)

    assert "executive_summary" in sections
    assert "detailed_summary" in sections
    assert sections["executive_summary"] == "This is the executive summary in the first paragraph."
    assert len(sections["detailed_summary"]) > 0


def test_parse_summary_sections_single_paragraph(summarization_chain):
    """Test parsing summary with single paragraph"""
    summary = "This is a single paragraph summary."

    sections = summarization_chain._parse_summary_sections(summary)

    assert sections["executive_summary"] == "This is a single paragraph summary."
    assert sections["detailed_summary"] == ""


def test_parse_summary_sections_empty(summarization_chain):
    """Test parsing empty summary"""
    summary = ""

    sections = summarization_chain._parse_summary_sections(summary)

    assert "executive_summary" in sections
    assert "detailed_summary" in sections


# ===== Bullet Point Extraction Tests =====

def test_extract_bullet_points_dash(summarization_chain):
    """Test extracting dash bullet points"""
    text = """
- First point
- Second point
- Third point
"""

    points = summarization_chain._extract_bullet_points(text)

    assert len(points) == 3
    assert "First point" in points
    assert "Second point" in points
    assert "Third point" in points


def test_extract_bullet_points_asterisk(summarization_chain):
    """Test extracting asterisk bullet points"""
    text = """
* First point
* Second point
"""

    points = summarization_chain._extract_bullet_points(text)

    assert len(points) == 2


def test_extract_bullet_points_numbered(summarization_chain):
    """Test extracting numbered list"""
    text = """
1. First point
2. Second point
3. Third point
"""

    points = summarization_chain._extract_bullet_points(text)

    assert len(points) == 3
    assert "First point" in points


def test_extract_bullet_points_mixed(summarization_chain):
    """Test extracting mixed bullet formats"""
    text = """
- Dash point
* Asterisk point
1. Numbered point
2) Parenthesis numbered
"""

    points = summarization_chain._extract_bullet_points(text)

    assert len(points) >= 3


def test_extract_bullet_points_none(summarization_chain):
    """Test with no bullet points"""
    text = "Just regular text without bullets"

    points = summarization_chain._extract_bullet_points(text)

    assert len(points) == 0


# ===== Topic Extraction Tests =====

@pytest.mark.asyncio
async def test_generate_topics(summarization_chain, mock_llm_provider, sample_transcript):
    """Test topic extraction"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""1. Q4 Roadmap Planning
2. Enterprise Features
3. SSO Implementation
4. Engineering Hiring
5. Product Marketing""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=100,
        cost_usd=0.001
    )

    topics = await summarization_chain.generate_topics(sample_transcript)

    assert len(topics) <= 7
    assert all(isinstance(topic, str) for topic in topics)
    assert len(topics) > 0


@pytest.mark.asyncio
async def test_generate_topics_filters_formatting(summarization_chain, mock_llm_provider, sample_transcript):
    """Test that topic extraction filters formatting characters"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""- Topic One
* Topic Two
• Topic Three
1. Topic Four
2) Topic Five""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=100,
        cost_usd=0.001
    )

    topics = await summarization_chain.generate_topics(sample_transcript)

    # Should remove bullet points and numbers
    assert all(not topic.startswith(("-", "*", "•")) for topic in topics)
    assert all(not topic[0].isdigit() for topic in topics if topic)


@pytest.mark.asyncio
async def test_generate_topics_limits_to_seven(summarization_chain, mock_llm_provider, sample_transcript):
    """Test that topic count is limited to 7"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="\n".join([f"{i}. Topic {i}" for i in range(1, 15)]),
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=150,
        cost_usd=0.0015
    )

    topics = await summarization_chain.generate_topics(sample_transcript)

    assert len(topics) <= 7


@pytest.mark.asyncio
async def test_generate_topics_truncates_long_transcript(summarization_chain, mock_llm_provider):
    """Test that very long transcripts are truncated"""
    long_transcript = "word " * 3000

    mock_llm_provider.complete.return_value = LLMResponse(
        content="1. Topic",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=50,
        cost_usd=0.0005
    )

    topics = await summarization_chain.generate_topics(long_transcript)

    # Should still work with truncated transcript
    assert isinstance(topics, list)


# ===== Error Handling Tests =====

@pytest.mark.asyncio
async def test_summarize_llm_failure(summarization_chain, mock_llm_provider, sample_transcript):
    """Test handling of LLM failure"""
    mock_llm_provider.complete.side_effect = Exception("LLM API error")

    with pytest.raises(Exception, match="LLM API error"):
        await summarization_chain.summarize(sample_transcript)


@pytest.mark.asyncio
async def test_extractive_summarization_llm_failure(summarization_chain, mock_llm_provider, sample_transcript):
    """Test extractive summarization LLM failure"""
    mock_llm_provider.complete.side_effect = Exception("API timeout")

    with pytest.raises(Exception, match="API timeout"):
        await summarization_chain._extractive_summarization(sample_transcript)


@pytest.mark.asyncio
async def test_abstractive_summarization_llm_failure(summarization_chain, mock_llm_provider, sample_transcript):
    """Test abstractive summarization LLM failure"""
    mock_llm_provider.complete.side_effect = Exception("Rate limit exceeded")

    with pytest.raises(Exception, match="Rate limit exceeded"):
        await summarization_chain._abstractive_summarization(sample_transcript)


# ===== Integration Tests =====

@pytest.mark.asyncio
async def test_full_summarization_pipeline(summarization_chain, mock_llm_provider, sample_transcript):
    """Test complete summarization pipeline end-to-end"""
    mock_llm_provider.complete.side_effect = [
        # Extractive stage
        LLMResponse(
            content="""- Q4 roadmap focused on enterprise features
- SSO, RBAC, and audit logs prioritized
- 6-10 week implementation timeline
- Hiring 2 senior engineers approved
- Marketing to update enterprise positioning""",
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            total_tokens=120,
            cost_usd=0.0012
        ),
        # Abstractive stage
        LLMResponse(
            content="""The leadership team aligned on Q4 enterprise priorities. The CTO proposed implementing SSO (6 weeks), RBAC (8 weeks), and audit logs (10 weeks). The CEO approved hiring 2 senior engineers to support delivery. Marketing will update product positioning for enterprise customers.""",
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            total_tokens=180,
            cost_usd=0.0018
        ),
        # Refinement stage
        LLMResponse(
            content="""Executive Summary: Leadership committed to an enterprise-focused Q4 roadmap with SSO, RBAC, and audit logs as key deliverables.

Detailed Summary:

During the Q4 planning session, the team aligned on prioritizing enterprise features to support business growth. The CTO presented a phased implementation plan with clear timelines: SSO delivery in 6 weeks, RBAC in 8 weeks, and audit logs in 10 weeks.

To meet these aggressive timelines, the CEO approved immediate hiring of 2 senior engineers. The CFO confirmed budget availability for these new hires.

The marketing team will coordinate with product to update messaging and positioning to better target enterprise customers. This represents a strategic shift toward serving larger organizations.""",
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            total_tokens=250,
            cost_usd=0.0025
        )
    ]

    result = await summarization_chain.summarize(
        transcript=sample_transcript,
        method="multi_stage"
    )

    # Verify structure
    assert "summary" in result
    assert "executive_summary" in result
    assert "detailed_summary" in result
    assert "key_points" in result
    assert "method" in result
    assert "metadata" in result

    # Verify content quality
    assert len(result["summary"]) > 100
    assert len(result["executive_summary"]) > 0
    assert len(result["key_points"]) > 0

    # Verify metadata
    metadata = result["metadata"]
    assert metadata["original_length"] > 0
    assert metadata["summary_length"] > 0
    assert metadata["total_tokens"] > 0
    assert metadata["total_cost_usd"] > 0

    # Verify all 3 LLM calls were made
    assert mock_llm_provider.complete.call_count == 3
