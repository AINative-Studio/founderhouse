"""
Summarization Chain
Multi-stage meeting summarization using LangChain
"""
import logging
from typing import Dict, Any, List, Optional

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.llm.llm_provider import LLMProvider, LLMResponse


logger = logging.getLogger(__name__)


class SummarizationChain:
    """
    Multi-stage summarization chain

    Stages:
    1. Extractive: Pull key sentences from transcript
    2. Abstractive: Generate coherent summary
    3. Refinement: Polish and structure the summary
    """

    EXTRACTIVE_PROMPT = PromptTemplate(
        input_variables=["transcript"],
        template="""Extract the most important sentences and key points from this meeting transcript.
Focus on:
- Main topics discussed
- Important decisions or conclusions
- Key statements from participants
- Critical information shared

Transcript:
{transcript}

Key Points (bullet points):"""
    )

    ABSTRACTIVE_PROMPT = PromptTemplate(
        input_variables=["key_points", "transcript_length"],
        template="""Based on these key points from a meeting transcript, write a clear and concise summary.

The original transcript was approximately {transcript_length} words.

Key Points:
{key_points}

Write a well-structured summary that:
1. Provides a 2-3 sentence executive summary at the top
2. Covers the main topics discussed
3. Highlights important decisions or conclusions
4. Notes any action items or next steps mentioned
5. Maintains a professional, objective tone

Summary:"""
    )

    REFINEMENT_PROMPT = PromptTemplate(
        input_variables=["draft_summary"],
        template="""Review and refine this meeting summary. Ensure it is:
- Clear and well-structured
- Free of redundancy
- Professionally written
- Factually accurate based on the content
- Properly formatted with sections if needed

Draft Summary:
{draft_summary}

Refined Summary:"""
    )

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize summarization chain

        Args:
            llm_provider: LLM provider instance
        """
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def summarize(
        self,
        transcript: str,
        method: str = "multi_stage",
        max_length: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Summarize meeting transcript

        Args:
            transcript: Full meeting transcript
            method: Summarization method (extractive, abstractive, multi_stage)
            max_length: Maximum summary length in words

        Returns:
            Dict with summary and metadata
        """
        try:
            if method == "extractive":
                return await self._extractive_summarization(transcript)
            elif method == "abstractive":
                return await self._abstractive_summarization(transcript)
            else:  # multi_stage
                return await self._multi_stage_summarization(transcript)

        except Exception as e:
            self.logger.error(f"Summarization failed: {str(e)}")
            raise

    async def _extractive_summarization(self, transcript: str) -> Dict[str, Any]:
        """Extract key sentences from transcript"""
        try:
            # For very long transcripts, chunk them first
            if len(transcript.split()) > 3000:
                chunks = self._chunk_transcript(transcript, chunk_size=3000)
                key_points = []

                for chunk in chunks:
                    prompt = self.EXTRACTIVE_PROMPT.format(transcript=chunk)
                    response = await self.llm_provider.complete(prompt)
                    key_points.append(response.content)

                summary = "\n\n".join(key_points)
            else:
                prompt = self.EXTRACTIVE_PROMPT.format(transcript=transcript)
                response = await self.llm_provider.complete(prompt)
                summary = response.content

            return {
                "summary": summary,
                "method": "extractive",
                "metadata": {
                    "original_length": len(transcript.split()),
                    "summary_length": len(summary.split())
                }
            }

        except Exception as e:
            self.logger.error(f"Extractive summarization failed: {str(e)}")
            raise

    async def _abstractive_summarization(self, transcript: str) -> Dict[str, Any]:
        """Generate abstractive summary"""
        try:
            # First extract key points
            extractive_result = await self._extractive_summarization(transcript)
            key_points = extractive_result["summary"]

            # Generate abstractive summary
            prompt = self.ABSTRACTIVE_PROMPT.format(
                key_points=key_points,
                transcript_length=len(transcript.split())
            )

            response = await self.llm_provider.complete(prompt)

            return {
                "summary": response.content,
                "method": "abstractive",
                "key_points": key_points,
                "metadata": {
                    "original_length": len(transcript.split()),
                    "summary_length": len(response.content.split()),
                    "tokens_used": response.total_tokens,
                    "cost_usd": response.cost_usd
                }
            }

        except Exception as e:
            self.logger.error(f"Abstractive summarization failed: {str(e)}")
            raise

    async def _multi_stage_summarization(self, transcript: str) -> Dict[str, Any]:
        """Multi-stage summarization with refinement"""
        try:
            # Stage 1: Extractive
            self.logger.info("Stage 1: Extractive summarization")
            extractive_result = await self._extractive_summarization(transcript)
            key_points = extractive_result["summary"]

            # Stage 2: Abstractive
            self.logger.info("Stage 2: Abstractive summarization")
            prompt = self.ABSTRACTIVE_PROMPT.format(
                key_points=key_points,
                transcript_length=len(transcript.split())
            )
            draft_response = await self.llm_provider.complete(prompt)
            draft_summary = draft_response.content

            # Stage 3: Refinement
            self.logger.info("Stage 3: Refinement")
            refinement_prompt = self.REFINEMENT_PROMPT.format(
                draft_summary=draft_summary
            )
            final_response = await self.llm_provider.complete(refinement_prompt)

            # Extract structured sections from final summary
            final_summary = final_response.content
            sections = self._parse_summary_sections(final_summary)

            return {
                "summary": final_summary,
                "executive_summary": sections.get("executive_summary", ""),
                "detailed_summary": sections.get("detailed_summary", final_summary),
                "key_points": self._extract_bullet_points(key_points),
                "method": "multi_stage",
                "metadata": {
                    "original_length": len(transcript.split()),
                    "summary_length": len(final_summary.split()),
                    "total_tokens": draft_response.total_tokens + final_response.total_tokens,
                    "total_cost_usd": (draft_response.cost_usd or 0) + (final_response.cost_usd or 0)
                }
            }

        except Exception as e:
            self.logger.error(f"Multi-stage summarization failed: {str(e)}")
            raise

    def _chunk_transcript(self, transcript: str, chunk_size: int = 3000) -> List[str]:
        """Split transcript into chunks for processing"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size * 4,  # Approximate characters per word
            chunk_overlap=200,
            length_function=lambda text: len(text.split())
        )
        return splitter.split_text(transcript)

    def _parse_summary_sections(self, summary: str) -> Dict[str, str]:
        """Parse summary into structured sections"""
        sections = {}

        # Try to extract executive summary (first paragraph)
        paragraphs = summary.split("\n\n")
        if paragraphs:
            sections["executive_summary"] = paragraphs[0].strip()
            sections["detailed_summary"] = "\n\n".join(paragraphs[1:]).strip() if len(paragraphs) > 1 else ""

        return sections

    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points from text"""
        points = []
        for line in text.split("\n"):
            line = line.strip()
            # Match common bullet point formats
            if line.startswith(("- ", "* ", "• ", "· ")):
                points.append(line[2:].strip())
            elif line and line[0].isdigit() and (". " in line[:3] or ") " in line[:3]):
                # Numbered list
                points.append(line.split(". ", 1)[-1].split(") ", 1)[-1].strip())

        return points

    async def generate_topics(self, transcript: str) -> List[str]:
        """Extract main topics discussed"""
        prompt = PromptTemplate(
            input_variables=["transcript"],
            template="""Extract the main topics and themes discussed in this meeting.
List 3-7 topics, each as a short phrase (2-5 words).

Transcript:
{transcript}

Topics (one per line):"""
        ).format(transcript=transcript[:2000])  # Limit transcript length

        response = await self.llm_provider.complete(prompt)

        # Parse topics from response
        topics = []
        for line in response.content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove bullet points and numbers
                topic = line.lstrip("- *•·0123456789.)").strip()
                if topic:
                    topics.append(topic)

        return topics[:7]  # Return max 7 topics
