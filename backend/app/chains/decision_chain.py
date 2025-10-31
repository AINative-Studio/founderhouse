"""
Decision Chain
Extract key decisions from meeting transcripts
"""
import logging
import re
from typing import Dict, Any, List, Optional

from langchain.prompts import PromptTemplate

from app.llm.llm_provider import LLMProvider
from app.models.decision import DecisionType, DecisionImpact


logger = logging.getLogger(__name__)


class DecisionChain:
    """Extract decisions made during meetings"""

    DECISION_PROMPT = PromptTemplate(
        input_variables=["transcript"],
        template="""Extract all key decisions made in this meeting transcript.

For each decision, provide:
1. Title: Short summary of the decision (5-10 words)
2. Description: Full context of what was decided
3. Type: strategic, tactical, operational, hiring, product, marketing, financial, or other
4. Impact: critical, high, medium, or low
5. Decision Maker: Who made or approved the decision
6. Rationale: Why this decision was made (if mentioned)

Format each decision as:
TITLE: [brief title]
DESCRIPTION: [full description]
TYPE: [decision type]
IMPACT: [impact level]
DECISION_MAKER: [person's name or "team decision"]
RATIONALE: [reasoning or "not specified"]
---

Transcript:
{transcript}

Decisions:"""
    )

    # Patterns indicating decisions
    DECISION_INDICATORS = [
        "decided",
        "decision",
        "agreed",
        "consensus",
        "resolution",
        "concluded",
        "settled on",
        "approved",
        "chose to",
        "selected",
        "going with",
        "commitment to"
    ]

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize decision chain

        Args:
            llm_provider: LLM provider instance
        """
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def extract_decisions(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Extract decisions from transcript

        Args:
            transcript: Meeting transcript

        Returns:
            List of decision dictionaries
        """
        try:
            # Check if transcript likely contains decisions
            if not self._has_decision_indicators(transcript):
                self.logger.info("No decision indicators found in transcript")
                return []

            # Extract using LLM
            decisions = await self._llm_extraction(transcript)

            # Post-process
            processed_decisions = []
            for decision in decisions:
                processed = self._post_process_decision(decision, transcript)
                if processed:
                    processed_decisions.append(processed)

            self.logger.info(f"Extracted {len(processed_decisions)} decisions")
            return processed_decisions

        except Exception as e:
            self.logger.error(f"Decision extraction failed: {str(e)}")
            raise

    def _has_decision_indicators(self, transcript: str) -> bool:
        """Check if transcript contains decision indicators"""
        transcript_lower = transcript.lower()
        return any(indicator in transcript_lower for indicator in self.DECISION_INDICATORS)

    async def _llm_extraction(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract decisions using LLM"""
        # For long transcripts, chunk them
        if len(transcript.split()) > 3000:
            chunks = self._chunk_transcript(transcript, chunk_size=3000)
            all_decisions = []

            for chunk in chunks:
                chunk_decisions = await self._extract_from_chunk(chunk)
                all_decisions.extend(chunk_decisions)

            return all_decisions
        else:
            return await self._extract_from_chunk(transcript)

    async def _extract_from_chunk(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract decisions from a single transcript chunk"""
        prompt = self.DECISION_PROMPT.format(transcript=transcript)
        response = await self.llm_provider.complete(
            prompt,
            system_prompt="You are an expert at identifying key business decisions from meeting transcripts. Be precise and focus on actual decisions, not just discussions."
        )

        # Parse structured output
        decisions = self._parse_llm_response(response.content)

        # Add confidence scores
        for decision in decisions:
            decision["confidence_score"] = 0.85

        return decisions

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse structured decisions from LLM response"""
        decisions = []
        current_decision = {}

        for line in response.split("\n"):
            line = line.strip()

            if line.startswith("TITLE:"):
                if current_decision:
                    decisions.append(current_decision)
                current_decision = {"title": line[6:].strip()}

            elif line.startswith("DESCRIPTION:"):
                current_decision["description"] = line[12:].strip()

            elif line.startswith("TYPE:"):
                type_str = line[5:].strip().lower()
                current_decision["decision_type"] = self._parse_decision_type(type_str)

            elif line.startswith("IMPACT:"):
                impact_str = line[7:].strip().lower()
                current_decision["impact"] = self._parse_impact(impact_str)

            elif line.startswith("DECISION_MAKER:"):
                maker = line[15:].strip()
                if maker.lower() not in ["not specified", "none", "", "team decision"]:
                    current_decision["decision_maker"] = maker

            elif line.startswith("RATIONALE:"):
                rationale = line[10:].strip()
                if rationale.lower() not in ["not specified", "none", ""]:
                    current_decision["rationale"] = rationale

            elif line == "---":
                if current_decision:
                    decisions.append(current_decision)
                    current_decision = {}

        # Add last decision
        if current_decision:
            decisions.append(current_decision)

        return decisions

    def _post_process_decision(self, decision: Dict[str, Any], transcript: str) -> Optional[Dict[str, Any]]:
        """Post-process and validate decision"""
        # Ensure required fields exist
        if not decision.get("title") or not decision.get("description"):
            return None

        # Set defaults
        if "decision_type" not in decision:
            decision["decision_type"] = DecisionType.OTHER

        if "impact" not in decision:
            decision["impact"] = DecisionImpact.MEDIUM

        # Try to find context in transcript
        if "context" not in decision:
            decision["context"] = self._find_context(transcript, decision["description"])

        # Extract stakeholders mentioned in decision
        decision["stakeholders"] = self._extract_stakeholders(decision["description"])

        return decision

    def _parse_decision_type(self, type_str: str) -> DecisionType:
        """Parse decision type from string"""
        type_str = type_str.lower()

        if "strategic" in type_str or "strategy" in type_str:
            return DecisionType.STRATEGIC
        elif "tactical" in type_str:
            return DecisionType.TACTICAL
        elif "operational" in type_str or "operations" in type_str:
            return DecisionType.OPERATIONAL
        elif "hiring" in type_str or "recruitment" in type_str or "team" in type_str:
            return DecisionType.HIRING
        elif "product" in type_str or "feature" in type_str:
            return DecisionType.PRODUCT
        elif "marketing" in type_str or "campaign" in type_str:
            return DecisionType.MARKETING
        elif "financial" in type_str or "budget" in type_str or "funding" in type_str:
            return DecisionType.FINANCIAL
        else:
            return DecisionType.OTHER

    def _parse_impact(self, impact_str: str) -> DecisionImpact:
        """Parse impact level from string"""
        impact_str = impact_str.lower()

        if any(word in impact_str for word in ["critical", "crucial", "vital", "essential"]):
            return DecisionImpact.CRITICAL
        elif any(word in impact_str for word in ["high", "major", "significant"]):
            return DecisionImpact.HIGH
        elif any(word in impact_str for word in ["low", "minor", "small"]):
            return DecisionImpact.LOW
        else:
            return DecisionImpact.MEDIUM

    def _find_context(self, transcript: str, description: str) -> Optional[str]:
        """Find surrounding context in transcript"""
        # Look for key phrases from description in transcript
        key_words = description.lower().split()[:5]  # First 5 words
        search_phrase = " ".join(key_words)

        # Find the phrase in transcript
        transcript_lower = transcript.lower()
        index = transcript_lower.find(search_phrase)

        if index != -1:
            # Extract context window
            start = max(0, index - 200)
            end = min(len(transcript), index + len(search_phrase) + 200)
            return transcript[start:end].strip()

        return None

    def _extract_stakeholders(self, text: str) -> List[str]:
        """Extract stakeholder names from text"""
        stakeholders = []

        # Look for common name patterns
        # This is a simple implementation; you might want to use NER for better results
        words = text.split()
        for i, word in enumerate(words):
            # Capitalized words that might be names
            if word[0].isupper() and len(word) > 2 and word.lower() not in [
                "the", "and", "but", "for", "with", "this", "that"
            ]:
                # Check if followed by another capitalized word (full name)
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    stakeholders.append(f"{word} {words[i + 1]}")

        return list(set(stakeholders))  # Remove duplicates

    def _chunk_transcript(self, transcript: str, chunk_size: int = 3000) -> List[str]:
        """Split transcript into chunks"""
        words = transcript.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))

        return chunks
