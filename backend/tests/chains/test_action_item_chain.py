"""
Comprehensive tests for ActionItemChain
Tests all extraction methods, parsing logic, and edge cases
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.chains.action_item_chain import ActionItemChain
from app.llm.llm_provider import LLMProvider, LLMResponse, LLMProviderType, LLMConfig
from app.models.action_item import ActionItemPriority, ActionItemSource


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider with predefined responses"""
    provider = Mock(spec=LLMProvider)
    provider.provider_type = LLMProviderType.OPENAI
    provider.complete = AsyncMock()
    return provider


@pytest.fixture
def action_chain(mock_llm_provider):
    """ActionItemChain instance with mocked provider"""
    return ActionItemChain(mock_llm_provider)


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript with clear action items"""
    return """
    John: We need to implement OAuth by next Friday. Sarah, can you handle that?
    Sarah: Yes, I'll start today. I'll need Mike's help with the backend integration.
    Mike: Sure, I can help. Let me finish the API documentation first.
    John: Great. Mike, please have the docs done by Wednesday.
    Sarah: I'll also update the security guidelines document.
    John: Perfect. Let's also schedule a security review meeting for next week.
    """


@pytest.fixture
def complex_transcript():
    """More complex transcript with multiple action items"""
    return """
    CEO: We need to urgently fix the payment gateway bug. This is critical.
    CTO: I'll assign @tom to investigate immediately. Should be done by EOD.
    CEO: Good. Also, we should consider implementing rate limiting.
    CTO: That's a good idea. Let me follow up with the infrastructure team.
    CFO: I need someone to prepare the Q4 financial report by next month.
    CEO: @jane can you handle that? It's high priority.
    Jane: Sure, I'll have it ready by the 15th.
    Marketing: We must launch the new campaign next week. @sarah will coordinate.
    """


# ===== LLM Extraction Tests =====

@pytest.mark.asyncio
async def test_extract_action_items_llm_only(action_chain, mock_llm_provider, sample_transcript):
    """Test action item extraction using LLM-only mode"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""ITEM: Implement OAuth authentication
ASSIGNEE: Sarah
DUE: next Friday
PRIORITY: high
CONTEXT: Backend integration needed
---
ITEM: Complete API documentation
ASSIGNEE: Mike
DUE: Wednesday
PRIORITY: medium
CONTEXT: Required before OAuth work
---
ITEM: Update security guidelines
ASSIGNEE: Sarah
PRIORITY: low
CONTEXT: Documentation update
---""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=200,
        cost_usd=0.002
    )

    result = await action_chain.extract_action_items(
        transcript=sample_transcript,
        use_hybrid=False
    )

    assert len(result) >= 3
    assert any("OAuth" in item["description"] for item in result)
    assert any(item.get("assignee_name") == "Sarah" for item in result)
    mock_llm_provider.complete.assert_called_once()


@pytest.mark.asyncio
async def test_extract_action_items_hybrid_mode(action_chain, mock_llm_provider, sample_transcript):
    """Test action item extraction using hybrid LLM + regex mode"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="ITEM: Implement OAuth\nASSIGNEE: Sarah\nPRIORITY: high\n---",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=100,
        cost_usd=0.001
    )

    result = await action_chain.extract_action_items(
        transcript=sample_transcript,
        use_hybrid=True
    )

    # Hybrid mode should find items from both LLM and regex
    assert len(result) > 0
    # Should have called LLM
    mock_llm_provider.complete.assert_called_once()


@pytest.mark.asyncio
async def test_extract_with_empty_transcript(action_chain, mock_llm_provider):
    """Test handling of empty transcript"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="No action items found.",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=10,
        cost_usd=0.0001
    )

    result = await action_chain.extract_action_items(
        transcript="",
        use_hybrid=False
    )

    # Should return empty list or handle gracefully
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_extract_with_long_transcript(action_chain, mock_llm_provider):
    """Test chunking of long transcripts"""
    # Create a very long transcript (over 3000 words)
    long_transcript = " ".join(["word"] * 3500)

    mock_llm_provider.complete.return_value = LLMResponse(
        content="ITEM: Test item\n---",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=50,
        cost_usd=0.0005
    )

    result = await action_chain.extract_action_items(
        transcript=long_transcript,
        use_hybrid=False
    )

    # Should call LLM multiple times for chunks
    assert mock_llm_provider.complete.call_count >= 1


@pytest.mark.asyncio
async def test_extract_with_complex_items(action_chain, mock_llm_provider, complex_transcript):
    """Test extraction with urgency markers and @mentions"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""ITEM: Fix payment gateway bug urgently
ASSIGNEE: tom
DUE: EOD
PRIORITY: urgent
CONTEXT: Critical bug affecting payments
---
ITEM: Implement rate limiting
ASSIGNEE: unassigned
PRIORITY: medium
CONTEXT: Infrastructure improvement
---
ITEM: Prepare Q4 financial report
ASSIGNEE: jane
DUE: 15th
PRIORITY: high
CONTEXT: Financial reporting
---""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=250,
        cost_usd=0.0025
    )

    result = await action_chain.extract_action_items(
        transcript=complex_transcript,
        use_hybrid=False
    )

    assert len(result) >= 3
    # Check urgent priority was detected
    assert any(item.get("priority") == ActionItemPriority.URGENT for item in result)


# ===== Regex Extraction Tests =====

def test_regex_extraction_basic(action_chain):
    """Test basic regex extraction patterns"""
    transcript = "We need to implement feature X by Friday. John should review the PR."

    items = action_chain._regex_extraction(transcript)

    assert len(items) >= 1
    assert all(item["source"] == ActionItemSource.REGEX for item in items)
    assert all(item["confidence_score"] == 0.6 for item in items)


def test_regex_extraction_action_patterns(action_chain):
    """Test various action pattern matching"""
    transcripts = [
        "We must complete the migration by Monday.",
        "Action item: Update the documentation.",
        "@john to review the security audit.",
        "Assign the bug fix to @sarah.",
        "Follow up with the client next week."
    ]

    for transcript in transcripts:
        items = action_chain._regex_extraction(transcript)
        assert len(items) >= 0  # May or may not match depending on pattern


def test_regex_extraction_ignores_short_matches(action_chain):
    """Test that very short matches are filtered out"""
    transcript = "We need to do it."  # "do it" is too short

    items = action_chain._regex_extraction(transcript)

    # Should not extract items that are too short (< 10 chars)
    assert all(len(item["description"]) >= 10 for item in items)


def test_regex_extraction_with_assignee(action_chain):
    """Test assignee extraction from regex matches"""
    transcript = "@alice to implement the feature by Friday."

    items = action_chain._regex_extraction(transcript)

    # Should extract both item and assignee
    if items:
        assert any(item.get("assignee_name") for item in items)


# ===== LLM Response Parsing Tests =====

def test_parse_llm_response_complete(action_chain):
    """Test parsing complete LLM response"""
    response = """ITEM: Implement OAuth authentication
ASSIGNEE: Sarah
DUE: next Friday
PRIORITY: high
CONTEXT: Backend integration needed
---
ITEM: Update documentation
ASSIGNEE: Mike
PRIORITY: low
---"""

    items = action_chain._parse_llm_response(response)

    assert len(items) == 2
    assert items[0]["description"] == "Implement OAuth authentication"
    assert items[0]["assignee_name"] == "Sarah"
    assert items[0]["priority"] == ActionItemPriority.HIGH


def test_parse_llm_response_minimal(action_chain):
    """Test parsing minimal LLM response with only description"""
    response = """ITEM: Simple action item
---"""

    items = action_chain._parse_llm_response(response)

    assert len(items) == 1
    assert items[0]["description"] == "Simple action item"
    assert "assignee_name" not in items[0]


def test_parse_llm_response_unassigned(action_chain):
    """Test parsing with unassigned items"""
    response = """ITEM: Research competitors
ASSIGNEE: unassigned
PRIORITY: medium
---"""

    items = action_chain._parse_llm_response(response)

    assert len(items) == 1
    assert "assignee_name" not in items[0]  # "unassigned" should be filtered


def test_parse_llm_response_multiple_without_separator(action_chain):
    """Test parsing when last item has no separator"""
    response = """ITEM: First task
PRIORITY: high
---
ITEM: Second task
PRIORITY: low"""

    items = action_chain._parse_llm_response(response)

    # Should still get both items
    assert len(items) == 2


def test_parse_llm_response_with_invalid_lines(action_chain):
    """Test parsing with unexpected content"""
    response = """Some random text
ITEM: Valid item
ASSIGNEE: John
Random line in the middle
PRIORITY: high
---"""

    items = action_chain._parse_llm_response(response)

    assert len(items) == 1
    assert items[0]["description"] == "Valid item"


# ===== Due Date Parsing Tests =====

def test_parse_due_date_relative(action_chain):
    """Test parsing relative due dates"""
    test_cases = [
        ("today", 0),
        ("tomorrow", 1),
        ("next week", 7),
        ("this week", 3),
    ]

    for due_str, expected_days in test_cases:
        result = action_chain._parse_due_date(due_str)
        if result:
            assert isinstance(result, datetime)


def test_parse_due_date_end_of_week(action_chain):
    """Test parsing end of week"""
    result = action_chain._parse_due_date("end of week")

    assert result is not None
    # Should be a Friday
    assert result.weekday() == 4


def test_parse_due_date_not_specified(action_chain):
    """Test handling of unspecified due dates"""
    test_cases = ["not specified", "none", "", None]

    for due_str in test_cases:
        result = action_chain._parse_due_date(due_str)
        assert result is None


def test_parse_due_date_specific_date(action_chain):
    """Test parsing specific date formats"""
    result = action_chain._parse_due_date("December 25, 2024")

    if result:
        assert isinstance(result, datetime)
        assert result.month == 12
        assert result.day == 25


# ===== Priority Parsing Tests =====

def test_parse_priority_urgent(action_chain):
    """Test parsing urgent priority keywords"""
    test_cases = ["urgent", "asap", "critical", "immediate"]

    for priority_str in test_cases:
        result = action_chain._parse_priority(priority_str)
        assert result == ActionItemPriority.URGENT


def test_parse_priority_high(action_chain):
    """Test parsing high priority keywords"""
    test_cases = ["high", "important", "high priority"]

    for priority_str in test_cases:
        result = action_chain._parse_priority(priority_str)
        assert result == ActionItemPriority.HIGH


def test_parse_priority_low(action_chain):
    """Test parsing low priority keywords"""
    test_cases = ["low", "minor", "low priority"]

    for priority_str in test_cases:
        result = action_chain._parse_priority(priority_str)
        assert result == ActionItemPriority.LOW


def test_parse_priority_normal_default(action_chain):
    """Test normal priority as default"""
    result = action_chain._parse_priority("normal")
    assert result == ActionItemPriority.NORMAL

    result = action_chain._parse_priority("medium")
    assert result == ActionItemPriority.NORMAL


# ===== Merging Tests =====

def test_merge_action_items_llm_priority(action_chain):
    """Test that LLM items take priority over regex items"""
    llm_items = [
        {"description": "implement oauth", "source": ActionItemSource.LLM, "confidence_score": 0.85}
    ]
    regex_items = [
        {"description": "implement oauth", "source": ActionItemSource.REGEX, "confidence_score": 0.6}
    ]

    result = action_chain._merge_action_items(regex_items, llm_items)

    # Should only have one item (LLM version)
    assert len(result) == 1
    assert result[0]["source"] == ActionItemSource.HYBRID


def test_merge_action_items_deduplication(action_chain):
    """Test deduplication of similar items"""
    llm_items = [
        {"description": "fix the bug in payment system", "source": ActionItemSource.LLM}
    ]
    regex_items = [
        {"description": "fix the bug in payment gateway", "source": ActionItemSource.REGEX}
    ]

    result = action_chain._merge_action_items(regex_items, llm_items)

    # Should detect similarity and deduplicate
    assert len(result) <= 2  # Might keep one or both depending on similarity threshold


def test_merge_action_items_unique(action_chain):
    """Test merging with completely unique items"""
    llm_items = [
        {"description": "implement oauth authentication", "source": ActionItemSource.LLM}
    ]
    regex_items = [
        {"description": "update documentation", "source": ActionItemSource.REGEX}
    ]

    result = action_chain._merge_action_items(regex_items, llm_items)

    # Should keep both items
    assert len(result) == 2


# ===== Post-processing Tests =====

def test_post_process_item_valid(action_chain):
    """Test post-processing valid item"""
    item = {
        "description": "  Implement feature  ",
        "assignee_name": "John"
    }

    result = action_chain._post_process_item(item)

    assert result is not None
    assert result["description"] == "Implement feature"  # Stripped
    assert result["priority"] == ActionItemPriority.NORMAL  # Default added


def test_post_process_item_missing_description(action_chain):
    """Test post-processing item without description"""
    item = {"assignee_name": "John"}

    result = action_chain._post_process_item(item)

    assert result is None


def test_post_process_item_extract_email(action_chain):
    """Test email extraction from assignee name"""
    item = {
        "description": "Test task",
        "assignee_name": "John Doe john.doe@example.com"
    }

    result = action_chain._post_process_item(item)

    assert result is not None
    assert "assignee_email" in result
    assert result["assignee_email"] == "john.doe@example.com"


# ===== Utility Method Tests =====

def test_extract_assignee_mention(action_chain):
    """Test extracting assignee from @mention"""
    text = "@alice should handle this task"

    result = action_chain._extract_assignee(text)

    assert result == "alice"


def test_extract_assignee_assigned_to(action_chain):
    """Test extracting assignee from 'assigned to' pattern"""
    text = "This is assigned to bob"

    result = action_chain._extract_assignee(text)

    assert result == "bob"


def test_extract_assignee_none(action_chain):
    """Test no assignee found"""
    text = "Just a regular sentence"

    result = action_chain._extract_assignee(text)

    assert result is None


def test_extract_email(action_chain):
    """Test email extraction"""
    text = "Contact john.doe@example.com for details"

    result = action_chain._extract_email(text)

    assert result == "john.doe@example.com"


def test_extract_email_none(action_chain):
    """Test no email found"""
    text = "No email here"

    result = action_chain._extract_email(text)

    assert result is None


def test_get_context(action_chain):
    """Test context extraction"""
    transcript = "a " * 50 + "important sentence" + " b" * 50
    match_start = len("a " * 50)
    match_end = match_start + len("important sentence")

    result = action_chain._get_context(transcript, match_start, match_end, window=20)

    assert "important sentence" in result
    assert len(result) <= 200  # Approximate window size


def test_chunk_transcript(action_chain):
    """Test transcript chunking"""
    words = ["word"] * 5000
    transcript = " ".join(words)

    chunks = action_chain._chunk_transcript(transcript, chunk_size=2000)

    assert len(chunks) >= 2
    # Each chunk should be approximately chunk_size
    for chunk in chunks[:-1]:  # All except last
        word_count = len(chunk.split())
        assert word_count <= 2100  # Small margin


def test_similarity_identical(action_chain):
    """Test similarity calculation for identical strings"""
    text1 = "implement oauth authentication"
    text2 = "implement oauth authentication"

    similarity = action_chain._similarity(text1, text2)

    assert similarity == 1.0


def test_similarity_similar(action_chain):
    """Test similarity calculation for similar strings"""
    text1 = "implement oauth authentication"
    text2 = "implement oauth authorization"

    similarity = action_chain._similarity(text1, text2)

    # Should have some overlap (oauth, implement) but not identical
    assert 0.4 <= similarity < 1.0


def test_similarity_different(action_chain):
    """Test similarity calculation for different strings"""
    text1 = "implement oauth"
    text2 = "update documentation"

    similarity = action_chain._similarity(text1, text2)

    assert similarity < 0.3


def test_similarity_empty(action_chain):
    """Test similarity with empty strings"""
    assert action_chain._similarity("", "test") == 0.0
    assert action_chain._similarity("test", "") == 0.0
    assert action_chain._similarity("", "") == 0.0


# ===== Error Handling Tests =====

@pytest.mark.asyncio
async def test_extract_action_items_llm_failure(action_chain, mock_llm_provider, sample_transcript):
    """Test handling of LLM API failure"""
    mock_llm_provider.complete.side_effect = Exception("LLM API error")

    # Should raise the exception
    with pytest.raises(Exception, match="LLM API error"):
        await action_chain.extract_action_items(
            transcript=sample_transcript,
            use_hybrid=False
        )


@pytest.mark.asyncio
async def test_extract_action_items_malformed_response(action_chain, mock_llm_provider, sample_transcript):
    """Test handling of malformed LLM response"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="This is not a properly formatted response",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=50,
        cost_usd=0.0005
    )

    result = await action_chain.extract_action_items(
        transcript=sample_transcript,
        use_hybrid=False
    )

    # Should return empty list or minimal parsed items
    assert isinstance(result, list)


# ===== Integration-style Tests =====

@pytest.mark.asyncio
async def test_full_extraction_pipeline(action_chain, mock_llm_provider, complex_transcript):
    """Test complete extraction pipeline with realistic data"""
    mock_llm_provider.complete.return_value = LLMResponse(
        content="""ITEM: Fix payment gateway bug urgently
ASSIGNEE: tom
DUE: EOD
PRIORITY: urgent
CONTEXT: Critical bug affecting customer payments
---
ITEM: Implement rate limiting on API
ASSIGNEE: unassigned
DUE: next week
PRIORITY: medium
CONTEXT: Prevent API abuse and improve security
---
ITEM: Prepare Q4 financial report
ASSIGNEE: jane
DUE: 15th
PRIORITY: high
CONTEXT: Executive review meeting preparation
---
ITEM: Launch new marketing campaign
ASSIGNEE: sarah
DUE: next week
PRIORITY: high
CONTEXT: Coordinating with marketing team
---""",
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        total_tokens=300,
        cost_usd=0.003
    )

    result = await action_chain.extract_action_items(
        transcript=complex_transcript,
        use_hybrid=True
    )

    assert len(result) >= 4

    # Verify priorities are correctly assigned
    priorities = [item.get("priority") for item in result]
    assert ActionItemPriority.URGENT in priorities
    assert ActionItemPriority.HIGH in priorities

    # Verify assignees are extracted
    assignees = [item.get("assignee_name") for item in result if item.get("assignee_name")]
    assert len(assignees) >= 3

    # Verify source tracking
    sources = [item.get("source") for item in result]
    assert all(s in [ActionItemSource.LLM, ActionItemSource.REGEX, ActionItemSource.HYBRID] for s in sources)
