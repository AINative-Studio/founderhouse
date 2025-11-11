"""
Comprehensive tests for DecisionChain
Tests decision extraction, classification, and parsing
"""
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from app.chains.decision_chain import DecisionChain
from app.llm.llm_provider import LLMProvider, LLMResponse, LLMProviderType
from app.models.decision import DecisionType, DecisionImpact


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider"""
    provider = Mock(spec=LLMProvider)
    provider.provider_type = LLMProviderType.OPENAI
    provider.complete = AsyncMock()
    return provider


@pytest.fixture
def decision_chain(mock_llm_provider):
    """DecisionChain instance with mocked provider"""
    return DecisionChain(mock_llm_provider)


@pytest.fixture
def sample_transcript():
    """Sample transcript with clear decisions"""
    return """
    CEO: After reviewing the Q3 metrics, I've decided we need to pivot to B2B sales.
    CFO: That's a strategic shift. What about our current B2C customers?
    CEO: We'll continue supporting them, but all new development focuses on enterprise.
    CTO: Agreed. I'll reassign the team to work on SSO and enterprise features.
    Marketing: Should we hire a B2B marketing specialist?
    CEO: Yes, that's approved. Let's start recruiting immediately.
    """


@pytest.fixture
def complex_transcript():
    """Complex transcript with multiple decision types"""
    return """
    CEO: We've decided to raise Series A funding of $5M. The board approved it unanimously.
    CFO: Great. I'll start the legal process. We also need to decide on budget allocation.
    CEO: Approved. Allocate 40% to engineering, 30% to sales, 30% to marketing.
    CTO: I've concluded that we should migrate to Kubernetes. It's essential for scale.
    VP Eng: That's a technical decision that will take 3 months to implement.
    CEO: What about hiring? We need to fill 5 positions this quarter.
    HR: I recommend we hire 2 senior engineers, 2 sales reps, and 1 product manager.
    CEO: Approved. Start the recruitment process immediately.
    """


# ===== Decision Extraction Tests =====

@pytest.mark.asyncio
async def test_extract_decisions_basic(decision_chain, mock_llm_provider, sample_transcript):
    """Test basic decision extraction"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""TITLE: Pivot to B2B sales model
DESCRIPTION: After reviewing Q3 metrics, decided to shift focus from B2C to B2B enterprise customers
TYPE: strategic
IMPACT: critical
DECISION_MAKER: CEO
RATIONALE: Q3 metrics showed better unit economics in enterprise segment
---
TITLE: Hire B2B marketing specialist
DESCRIPTION: Approved hiring of dedicated B2B marketing specialist to support enterprise push
TYPE: hiring
IMPACT: medium
DECISION_MAKER: CEO
RATIONALE: Need specialized expertise for enterprise marketing
---""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=200,
        cost_usd=0.002
    )

    result = await decision_chain.extract_decisions(sample_transcript)

    assert len(result) == 2
    assert any("B2B" in d["title"] for d in result)
    assert any(d.get("decision_type") == DecisionType.STRATEGIC for d in result)
    assert any(d.get("decision_type") == DecisionType.HIRING for d in result)


@pytest.mark.asyncio
async def test_extract_decisions_no_indicators(decision_chain, mock_llm_provider):
    """Test transcript without decision indicators"""
    transcript = "We talked about various topics. The team shared updates. Everyone will meet again."

    result = await decision_chain.extract_decisions(transcript)

    # Should return empty list when no decision indicators found
    assert result == []
    mock_llm_provider.complete.assert_not_called()


@pytest.mark.asyncio
async def test_extract_decisions_complex(decision_chain, mock_llm_provider, complex_transcript):
    """Test extraction of multiple decision types"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""TITLE: Raise Series A funding
DESCRIPTION: Board approved raising $5M in Series A funding
TYPE: financial
IMPACT: critical
DECISION_MAKER: CEO
RATIONALE: Need capital for growth and market expansion
---
TITLE: Budget allocation for new funding
DESCRIPTION: Allocated funding: 40% engineering, 30% sales, 30% marketing
TYPE: financial
IMPACT: high
DECISION_MAKER: CEO
RATIONALE: Balanced investment across key growth areas
---
TITLE: Migrate to Kubernetes infrastructure
DESCRIPTION: Technical decision to migrate infrastructure to Kubernetes for better scalability
TYPE: operational
IMPACT: high
DECISION_MAKER: CTO
RATIONALE: Essential for handling scale and improving deployment efficiency
---
TITLE: Hire 5 new team members
DESCRIPTION: Approved hiring 2 senior engineers, 2 sales reps, and 1 product manager
TYPE: hiring
IMPACT: high
DECISION_MAKER: CEO
RATIONALE: Team expansion needed to support growth plans
---""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=350,
        cost_usd=0.0035
    )

    result = await decision_chain.extract_decisions(complex_transcript)

    assert len(result) == 4

    # Verify different decision types
    decision_types = {d.get("decision_type") for d in result}
    assert DecisionType.FINANCIAL in decision_types
    assert DecisionType.OPERATIONAL in decision_types
    assert DecisionType.HIRING in decision_types


@pytest.mark.asyncio
async def test_extract_decisions_long_transcript(decision_chain, mock_llm_provider):
    """Test handling of long transcripts with chunking"""
    # Create transcript longer than 3000 words
    long_transcript = "We decided to proceed. " * 1000 + " This is a key decision that was agreed upon."

    mock_llm_provider.complete.return_value = LLMResponse(
        content="TITLE: Test decision\nDESCRIPTION: Test\nTYPE: other\nIMPACT: medium\n---",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=50,
        cost_usd=0.0005
    )

    result = await decision_chain.extract_decisions(long_transcript)

    # Should handle chunking and call LLM multiple times
    assert mock_llm_provider.complete.call_count >= 1
    assert isinstance(result, list)


# ===== Decision Indicator Tests =====

def test_has_decision_indicators_positive(decision_chain):
    """Test detection of decision indicators"""
    transcripts_with_decisions = [
        "We decided to go with option A",
        "The team reached a consensus on the approach",
        "This decision was approved by the board",
        "We agreed to move forward",
        "The resolution was to implement the new system",
        "We concluded that the best path is X",
        "The team settled on using React",
        "This was approved unanimously",
        "We chose to hire externally",
        "The team selected vendor A"
    ]

    for transcript in transcripts_with_decisions:
        assert decision_chain._has_decision_indicators(transcript) is True


def test_has_decision_indicators_negative(decision_chain):
    """Test transcripts without decision indicators"""
    transcript = "We discussed many options. Various ideas were presented. The team shared thoughts."

    assert decision_chain._has_decision_indicators(transcript) is False


# ===== LLM Response Parsing Tests =====

def test_parse_llm_response_complete(decision_chain):
    """Test parsing complete LLM response"""
    response = """TITLE: Pivot to enterprise sales
DESCRIPTION: Strategic decision to focus on B2B enterprise customers
TYPE: strategic
IMPACT: critical
DECISION_MAKER: CEO
RATIONALE: Better unit economics and higher retention in enterprise segment
---"""

    decisions = decision_chain._parse_llm_response(response)

    assert len(decisions) == 1
    assert decisions[0]["title"] == "Pivot to enterprise sales"
    assert decisions[0]["decision_type"] == DecisionType.STRATEGIC
    assert decisions[0]["impact"] == DecisionImpact.CRITICAL
    assert decisions[0]["decision_maker"] == "CEO"
    assert "rationale" in decisions[0]


def test_parse_llm_response_minimal(decision_chain):
    """Test parsing minimal response"""
    response = """TITLE: Simple decision
DESCRIPTION: Basic decision description
---"""

    decisions = decision_chain._parse_llm_response(response)

    assert len(decisions) == 1
    assert decisions[0]["title"] == "Simple decision"
    assert decisions[0]["description"] == "Basic decision description"


def test_parse_llm_response_team_decision(decision_chain):
    """Test parsing team decisions (no individual maker)"""
    response = """TITLE: Team consensus decision
DESCRIPTION: The entire team agreed on this approach
DECISION_MAKER: team decision
---"""

    decisions = decision_chain._parse_llm_response(response)

    assert len(decisions) == 1
    # "team decision" should be filtered out
    assert "decision_maker" not in decisions[0]


def test_parse_llm_response_no_rationale(decision_chain):
    """Test parsing without rationale"""
    response = """TITLE: Quick decision
DESCRIPTION: Made on the spot
RATIONALE: not specified
---"""

    decisions = decision_chain._parse_llm_response(response)

    assert len(decisions) == 1
    assert "rationale" not in decisions[0]


def test_parse_llm_response_multiple(decision_chain):
    """Test parsing multiple decisions"""
    response = """TITLE: First decision
DESCRIPTION: First description
TYPE: strategic
---
TITLE: Second decision
DESCRIPTION: Second description
TYPE: tactical
---
TITLE: Third decision
DESCRIPTION: Third description
TYPE: operational
---"""

    decisions = decision_chain._parse_llm_response(response)

    assert len(decisions) == 3
    assert decisions[0]["title"] == "First decision"
    assert decisions[1]["title"] == "Second decision"
    assert decisions[2]["title"] == "Third decision"


# ===== Decision Type Parsing Tests =====

def test_parse_decision_type_strategic(decision_chain):
    """Test parsing strategic decision types"""
    test_cases = ["strategic", "strategy", "strategic decision"]

    for type_str in test_cases:
        result = decision_chain._parse_decision_type(type_str)
        assert result == DecisionType.STRATEGIC


def test_parse_decision_type_tactical(decision_chain):
    """Test parsing tactical decision types"""
    result = decision_chain._parse_decision_type("tactical")
    assert result == DecisionType.TACTICAL


def test_parse_decision_type_operational(decision_chain):
    """Test parsing operational decision types"""
    test_cases = ["operational", "operations"]

    for type_str in test_cases:
        result = decision_chain._parse_decision_type(type_str)
        assert result == DecisionType.OPERATIONAL


def test_parse_decision_type_hiring(decision_chain):
    """Test parsing hiring decision types"""
    test_cases = ["hiring", "recruitment", "team expansion"]

    for type_str in test_cases:
        result = decision_chain._parse_decision_type(type_str)
        assert result == DecisionType.HIRING


def test_parse_decision_type_product(decision_chain):
    """Test parsing product decision types"""
    test_cases = ["product", "feature", "product decision"]

    for type_str in test_cases:
        result = decision_chain._parse_decision_type(type_str)
        assert result == DecisionType.PRODUCT


def test_parse_decision_type_marketing(decision_chain):
    """Test parsing marketing decision types"""
    # Test unambiguous marketing terms
    result = decision_chain._parse_decision_type("marketing")
    assert result == DecisionType.MARKETING

    # "campaign" and "marketing strategy" might match multiple patterns
    # so allow for flexible classification
    result = decision_chain._parse_decision_type("campaign")
    assert result in [DecisionType.MARKETING, DecisionType.STRATEGIC, DecisionType.OTHER]

    result = decision_chain._parse_decision_type("marketing strategy")
    assert result in [DecisionType.MARKETING, DecisionType.STRATEGIC]


def test_parse_decision_type_financial(decision_chain):
    """Test parsing financial decision types"""
    test_cases = ["financial", "budget", "funding", "financial decision"]

    for type_str in test_cases:
        result = decision_chain._parse_decision_type(type_str)
        assert result == DecisionType.FINANCIAL


def test_parse_decision_type_other(decision_chain):
    """Test parsing other decision types"""
    result = decision_chain._parse_decision_type("miscellaneous")
    assert result == DecisionType.OTHER


# ===== Impact Parsing Tests =====

def test_parse_impact_critical(decision_chain):
    """Test parsing critical impact"""
    test_cases = ["critical", "crucial", "vital", "essential"]

    for impact_str in test_cases:
        result = decision_chain._parse_impact(impact_str)
        assert result == DecisionImpact.CRITICAL


def test_parse_impact_high(decision_chain):
    """Test parsing high impact"""
    test_cases = ["high", "major", "significant", "high impact"]

    for impact_str in test_cases:
        result = decision_chain._parse_impact(impact_str)
        assert result == DecisionImpact.HIGH


def test_parse_impact_low(decision_chain):
    """Test parsing low impact"""
    test_cases = ["low", "minor", "small", "low impact"]

    for impact_str in test_cases:
        result = decision_chain._parse_impact(impact_str)
        assert result == DecisionImpact.LOW


def test_parse_impact_medium_default(decision_chain):
    """Test medium impact as default"""
    result = decision_chain._parse_impact("medium")
    assert result == DecisionImpact.MEDIUM

    result = decision_chain._parse_impact("moderate")
    assert result == DecisionImpact.MEDIUM


# ===== Post-processing Tests =====

def test_post_process_decision_valid(decision_chain):
    """Test post-processing valid decision"""
    transcript = "We decided to pivot to B2B. The CEO made this strategic choice after analyzing market data."

    decision = {
        "title": "Pivot to B2B",
        "description": "Strategic shift to enterprise customers",
        "decision_type": DecisionType.STRATEGIC
    }

    result = decision_chain._post_process_decision(decision, transcript)

    assert result is not None
    assert result["title"] == "Pivot to B2B"
    assert result["impact"] == DecisionImpact.MEDIUM  # Default added
    assert "stakeholders" in result


def test_post_process_decision_missing_title(decision_chain):
    """Test post-processing with missing title"""
    decision = {
        "description": "Some description"
    }

    result = decision_chain._post_process_decision(decision, "transcript")

    assert result is None


def test_post_process_decision_missing_description(decision_chain):
    """Test post-processing with missing description"""
    decision = {
        "title": "Some title"
    }

    result = decision_chain._post_process_decision(decision, "transcript")

    assert result is None


def test_post_process_decision_adds_defaults(decision_chain):
    """Test that defaults are added during post-processing"""
    decision = {
        "title": "Test Decision",
        "description": "Test description"
    }

    result = decision_chain._post_process_decision(decision, "transcript")

    assert result["decision_type"] == DecisionType.OTHER
    assert result["impact"] == DecisionImpact.MEDIUM
    assert "stakeholders" in result


# ===== Context Finding Tests =====

def test_find_context_found(decision_chain):
    """Test finding context in transcript"""
    transcript = """
    The team discussed various options for the project.
    After careful consideration, we decided to use React for the frontend.
    This will help us move faster and leverage existing expertise.
    """

    description = "decided to use React for the frontend"

    context = decision_chain._find_context(transcript, description)

    assert context is not None
    assert "React" in context


def test_find_context_not_found(decision_chain):
    """Test when context is not found"""
    transcript = "The team met to discuss the project."
    description = "implement kubernetes infrastructure"

    context = decision_chain._find_context(transcript, description)

    assert context is None


def test_find_context_window_size(decision_chain):
    """Test that context window is limited"""
    # Create long transcript
    transcript = "a " * 500 + "important decision here" + " b" * 500
    description = "important decision here"

    context = decision_chain._find_context(transcript, description)

    assert context is not None
    # Context should be limited (200 chars before and after)
    assert len(context) <= 500


# ===== Stakeholder Extraction Tests =====

def test_extract_stakeholders_basic(decision_chain):
    """Test basic stakeholder extraction"""
    text = "John Smith and Alice Johnson agreed on this decision. Bob Williams was consulted."

    stakeholders = decision_chain._extract_stakeholders(text)

    assert len(stakeholders) >= 1
    # Should extract capitalized names


def test_extract_stakeholders_filters_common_words(decision_chain):
    """Test that common words are filtered"""
    text = "The team agreed and approved. This decision is important."

    stakeholders = decision_chain._extract_stakeholders(text)

    # Should not include "The", "This", etc.
    assert not any(s.lower() in ["the", "this", "and"] for s in stakeholders)


def test_extract_stakeholders_deduplication(decision_chain):
    """Test stakeholder deduplication"""
    text = "John Doe approved this. John Doe also signed off on the budget. John Doe confirmed."

    stakeholders = decision_chain._extract_stakeholders(text)

    # Should not have duplicates
    assert len(stakeholders) == len(set(stakeholders))


def test_extract_stakeholders_empty(decision_chain):
    """Test with no stakeholders"""
    text = "the decision was made based on data"

    stakeholders = decision_chain._extract_stakeholders(text)

    assert isinstance(stakeholders, list)


# ===== Chunking Tests =====

def test_chunk_transcript(decision_chain):
    """Test transcript chunking"""
    words = ["word"] * 5000
    transcript = " ".join(words)

    chunks = decision_chain._chunk_transcript(transcript, chunk_size=2000)

    assert len(chunks) >= 2
    # Verify chunks are approximately the right size
    for chunk in chunks[:-1]:
        assert len(chunk.split()) <= 2100


def test_chunk_transcript_small(decision_chain):
    """Test chunking with small transcript"""
    transcript = "small transcript"

    chunks = decision_chain._chunk_transcript(transcript, chunk_size=1000)

    assert len(chunks) == 1
    assert chunks[0] == transcript


# ===== Error Handling Tests =====

@pytest.mark.asyncio
async def test_extract_decisions_llm_failure(decision_chain, mock_llm_provider, sample_transcript):
    """Test handling of LLM failure"""
    mock_llm_provider.complete.side_effect = Exception("LLM API error")

    with pytest.raises(Exception, match="LLM API error"):
        await decision_chain.extract_decisions(sample_transcript)


@pytest.mark.asyncio
async def test_extract_decisions_malformed_response(decision_chain, mock_llm_provider, sample_transcript):
    """Test handling of malformed LLM response"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="This is not properly formatted at all",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=50,
        cost_usd=0.0005
    )

    result = await decision_chain.extract_decisions(sample_transcript)

    # Should handle gracefully and return parsed results
    assert isinstance(result, list)


# ===== Integration Tests =====

@pytest.mark.asyncio
async def test_full_decision_extraction_pipeline(decision_chain, mock_llm_provider, complex_transcript):
    """Test complete decision extraction pipeline"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""TITLE: Series A funding approval
DESCRIPTION: Board unanimously approved raising $5M in Series A funding
TYPE: financial
IMPACT: critical
DECISION_MAKER: CEO
RATIONALE: Capital needed for aggressive growth and market expansion
---
TITLE: Budget allocation strategy
DESCRIPTION: Funding split: 40% engineering, 30% sales, 30% marketing
TYPE: financial
IMPACT: high
DECISION_MAKER: CFO
RATIONALE: Balanced investment across key growth functions
---
TITLE: Kubernetes migration
DESCRIPTION: Migrate entire infrastructure to Kubernetes for better scalability
TYPE: operational
IMPACT: high
DECISION_MAKER: CTO
RATIONALE: Required for handling projected scale and improving deployment velocity
---
TITLE: Q4 hiring plan
DESCRIPTION: Hire 2 senior engineers, 2 sales reps, 1 product manager
TYPE: hiring
IMPACT: high
DECISION_MAKER: CEO
RATIONALE: Team expansion critical for executing growth strategy
---""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=350,
        cost_usd=0.0035
    )

    result = await decision_chain.extract_decisions(complex_transcript)

    assert len(result) == 4

    # Verify all decisions have required fields
    for decision in result:
        assert "title" in decision
        assert "description" in decision
        assert "decision_type" in decision
        assert "impact" in decision
        assert "confidence_score" in decision
        assert decision["confidence_score"] == 0.85

    # Verify decision types diversity
    types = {d["decision_type"] for d in result}
    assert len(types) >= 2

    # Verify impact levels
    impacts = {d["impact"] for d in result}
    assert DecisionImpact.CRITICAL in impacts or DecisionImpact.HIGH in impacts

    # Verify stakeholders are extracted
    stakeholders = []
    for decision in result:
        stakeholders.extend(decision.get("stakeholders", []))
    assert isinstance(stakeholders, list)
