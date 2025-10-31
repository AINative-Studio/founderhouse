"""
Action Item Chain
Extract action items from meeting transcripts
"""
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from langchain.prompts import PromptTemplate

from app.llm.llm_provider import LLMProvider
from app.models.action_item import ActionItemPriority, ActionItemSource


logger = logging.getLogger(__name__)


class ActionItemChain:
    """
    Extract action items using hybrid approach:
    - Regex patterns for common action item language
    - LLM for contextual understanding and extraction
    """

    ACTION_ITEM_PROMPT = PromptTemplate(
        input_variables=["transcript"],
        template="""Extract all action items from this meeting transcript.

For each action item, provide:
1. Description: What needs to be done
2. Assignee: Who is responsible (if mentioned)
3. Due date: When it's due (if mentioned)
4. Priority: urgent, high, normal, or low
5. Context: Brief surrounding context

Format each action item as:
ITEM: [description]
ASSIGNEE: [person's name or "unassigned"]
DUE: [date/timeframe or "not specified"]
PRIORITY: [urgent/high/normal/low]
CONTEXT: [1-2 sentences of context]
---

Transcript:
{transcript}

Action Items:"""
    )

    # Regex patterns for common action item indicators
    ACTION_PATTERNS = [
        r"(?:need to|should|must|have to|going to|will)\s+(.+?)(?:\.|,|\n)",
        r"(?:action item|todo|task):\s*(.+?)(?:\.|,|\n)",
        r"(?:@\w+)\s+(?:to|will|should)\s+(.+?)(?:\.|,|\n)",
        r"(?:assigned to|assign)\s+(\w+)\s+to\s+(.+?)(?:\.|,|\n)",
        r"(?:follow up|followup)\s+(?:with|on)\s+(.+?)(?:\.|,|\n)",
    ]

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize action item chain

        Args:
            llm_provider: LLM provider instance
        """
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def extract_action_items(
        self,
        transcript: str,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extract action items from transcript

        Args:
            transcript: Meeting transcript
            use_hybrid: Use both regex and LLM (recommended)

        Returns:
            List of action item dictionaries
        """
        try:
            if use_hybrid:
                # Get regex-based candidates
                regex_items = self._regex_extraction(transcript)

                # Get LLM-based items
                llm_items = await self._llm_extraction(transcript)

                # Merge and deduplicate
                all_items = self._merge_action_items(regex_items, llm_items)
            else:
                # LLM only
                all_items = await self._llm_extraction(transcript)

            # Post-process items
            processed_items = []
            for item in all_items:
                processed = self._post_process_item(item)
                if processed:
                    processed_items.append(processed)

            self.logger.info(f"Extracted {len(processed_items)} action items")
            return processed_items

        except Exception as e:
            self.logger.error(f"Action item extraction failed: {str(e)}")
            raise

    def _regex_extraction(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract action items using regex patterns"""
        items = []

        for pattern in self.ACTION_PATTERNS:
            matches = re.finditer(pattern, transcript, re.IGNORECASE)
            for match in matches:
                description = match.group(1).strip()

                # Skip very short matches
                if len(description) < 10:
                    continue

                # Extract assignee if present
                assignee = self._extract_assignee(match.group(0))

                items.append({
                    "description": description,
                    "assignee_name": assignee,
                    "source": ActionItemSource.REGEX,
                    "confidence_score": 0.6,  # Lower confidence for regex
                    "context": self._get_context(transcript, match.start(), match.end())
                })

        return items

    async def _llm_extraction(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract action items using LLM"""
        # For long transcripts, chunk them
        if len(transcript.split()) > 3000:
            chunks = self._chunk_transcript(transcript, chunk_size=3000)
            all_items = []

            for chunk in chunks:
                chunk_items = await self._extract_from_chunk(chunk)
                all_items.extend(chunk_items)

            return all_items
        else:
            return await self._extract_from_chunk(transcript)

    async def _extract_from_chunk(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract action items from a single transcript chunk"""
        prompt = self.ACTION_ITEM_PROMPT.format(transcript=transcript)
        response = await self.llm_provider.complete(prompt)

        # Parse structured output
        items = self._parse_llm_response(response.content)

        # Add metadata
        for item in items:
            item["source"] = ActionItemSource.LLM
            item["confidence_score"] = 0.85  # Higher confidence for LLM

        return items

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse structured action items from LLM response"""
        items = []
        current_item = {}

        for line in response.split("\n"):
            line = line.strip()

            if line.startswith("ITEM:"):
                if current_item:
                    items.append(current_item)
                current_item = {"description": line[5:].strip()}

            elif line.startswith("ASSIGNEE:"):
                assignee = line[9:].strip()
                if assignee.lower() not in ["unassigned", "not specified", "none", ""]:
                    current_item["assignee_name"] = assignee

            elif line.startswith("DUE:"):
                due_str = line[4:].strip()
                due_date = self._parse_due_date(due_str)
                if due_date:
                    current_item["due_date"] = due_date

            elif line.startswith("PRIORITY:"):
                priority_str = line[9:].strip().lower()
                current_item["priority"] = self._parse_priority(priority_str)

            elif line.startswith("CONTEXT:"):
                current_item["context"] = line[8:].strip()

            elif line == "---":
                if current_item:
                    items.append(current_item)
                    current_item = {}

        # Add last item
        if current_item:
            items.append(current_item)

        return items

    def _merge_action_items(
        self,
        regex_items: List[Dict[str, Any]],
        llm_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge and deduplicate action items from multiple sources

        Priority: LLM items > Regex items (LLM has better context)
        """
        all_items = []
        seen_descriptions = set()

        # Add LLM items first (higher priority)
        for item in llm_items:
            desc = item.get("description", "").lower()
            if desc and desc not in seen_descriptions:
                item["source"] = ActionItemSource.HYBRID
                all_items.append(item)
                seen_descriptions.add(desc)

        # Add unique regex items
        for item in regex_items:
            desc = item.get("description", "").lower()
            # Check for similar descriptions (not just exact match)
            is_duplicate = any(
                self._similarity(desc, seen_desc) > 0.8
                for seen_desc in seen_descriptions
            )

            if not is_duplicate:
                all_items.append(item)
                seen_descriptions.add(desc)

        return all_items

    def _post_process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Post-process and validate action item"""
        # Ensure description exists
        if not item.get("description"):
            return None

        # Set default priority if not specified
        if "priority" not in item:
            item["priority"] = ActionItemPriority.NORMAL

        # Clean up description
        item["description"] = item["description"].strip()

        # Extract email from assignee if present
        if item.get("assignee_name"):
            email = self._extract_email(item["assignee_name"])
            if email:
                item["assignee_email"] = email

        return item

    def _extract_assignee(self, text: str) -> Optional[str]:
        """Extract assignee name from text"""
        # Look for @mentions
        mention_match = re.search(r"@(\w+)", text)
        if mention_match:
            return mention_match.group(1)

        # Look for "assigned to X"
        assigned_match = re.search(r"assigned to (\w+)", text, re.IGNORECASE)
        if assigned_match:
            return assigned_match.group(1)

        return None

    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text"""
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        return email_match.group(0) if email_match else None

    def _parse_due_date(self, due_str: str) -> Optional[datetime]:
        """Parse due date from natural language"""
        if not due_str or due_str.lower() in ["not specified", "none", ""]:
            return None

        due_str = due_str.lower()
        now = datetime.utcnow()

        # Relative dates
        if "today" in due_str:
            return now
        elif "tomorrow" in due_str:
            return now + timedelta(days=1)
        elif "next week" in due_str:
            return now + timedelta(days=7)
        elif "this week" in due_str:
            return now + timedelta(days=3)
        elif "end of week" in due_str or "eow" in due_str:
            days_until_friday = (4 - now.weekday()) % 7
            return now + timedelta(days=days_until_friday)
        elif "next month" in due_str:
            return now + timedelta(days=30)

        # Try parsing specific date formats
        from dateutil import parser
        try:
            return parser.parse(due_str, fuzzy=True)
        except:
            return None

    def _parse_priority(self, priority_str: str) -> ActionItemPriority:
        """Parse priority level"""
        priority_str = priority_str.lower()

        if any(word in priority_str for word in ["urgent", "asap", "critical", "immediate"]):
            return ActionItemPriority.URGENT
        elif any(word in priority_str for word in ["high", "important"]):
            return ActionItemPriority.HIGH
        elif any(word in priority_str for word in ["low", "minor"]):
            return ActionItemPriority.LOW
        else:
            return ActionItemPriority.NORMAL

    def _get_context(self, transcript: str, start: int, end: int, window: int = 100) -> str:
        """Get surrounding context for a match"""
        context_start = max(0, start - window)
        context_end = min(len(transcript), end + window)
        return transcript[context_start:context_end].strip()

    def _chunk_transcript(self, transcript: str, chunk_size: int = 3000) -> List[str]:
        """Split transcript into chunks"""
        words = transcript.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))

        return chunks

    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (simple implementation)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)
