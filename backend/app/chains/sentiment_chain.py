"""
Sentiment Chain
Analyze meeting sentiment and tone
"""
import logging
from typing import Dict, Any, Optional

from langchain.prompts import PromptTemplate

from app.llm.llm_provider import LLMProvider
from app.models.meeting_summary import SentimentScore


logger = logging.getLogger(__name__)


class SentimentChain:
    """Analyze sentiment and tone of meetings"""

    SENTIMENT_PROMPT = PromptTemplate(
        input_variables=["transcript"],
        template="""Analyze the overall sentiment and tone of this meeting transcript.

Provide:
1. Overall Sentiment: very_positive, positive, neutral, negative, or very_negative
2. Energy Level: high, medium, or low
3. Collaboration Score: 1-10 (how collaborative was the discussion)
4. Tension Indicators: Any signs of disagreement or tension
5. Positive Highlights: Key positive moments
6. Concerns Raised: Any concerns or issues mentioned
7. Engagement: How engaged were participants

Transcript:
{transcript}

Analysis:
OVERALL_SENTIMENT: [sentiment]
ENERGY_LEVEL: [level]
COLLABORATION_SCORE: [score]/10
TENSION_INDICATORS: [description or "none"]
POSITIVE_HIGHLIGHTS: [highlights]
CONCERNS_RAISED: [concerns or "none"]
ENGAGEMENT: [description]
"""
    )

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize sentiment chain

        Args:
            llm_provider: LLM provider instance
        """
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def analyze_sentiment(self, transcript: str) -> Dict[str, Any]:
        """
        Analyze meeting sentiment

        Args:
            transcript: Meeting transcript

        Returns:
            Dictionary with sentiment analysis
        """
        try:
            # For very long transcripts, sample key sections
            if len(transcript.split()) > 3000:
                transcript = self._sample_transcript(transcript)

            # Get LLM analysis
            prompt = self.SENTIMENT_PROMPT.format(transcript=transcript)
            response = await self.llm_provider.complete(
                prompt,
                system_prompt="You are an expert at analyzing meeting dynamics and sentiment. Provide objective, data-driven analysis."
            )

            # Parse response
            analysis = self._parse_sentiment_response(response.content)

            # Add metadata
            analysis["analyzed_length"] = len(transcript.split())

            self.logger.info(f"Sentiment analysis completed: {analysis.get('overall_sentiment')}")
            return analysis

        except Exception as e:
            self.logger.error(f"Sentiment analysis failed: {str(e)}")
            raise

    def _parse_sentiment_response(self, response: str) -> Dict[str, Any]:
        """Parse sentiment analysis from LLM response"""
        analysis = {
            "overall_sentiment": SentimentScore.NEUTRAL,
            "energy_level": "medium",
            "collaboration_score": 5,
            "tension_indicators": None,
            "positive_highlights": [],
            "concerns_raised": [],
            "engagement": "moderate"
        }

        for line in response.split("\n"):
            line = line.strip()

            if line.startswith("OVERALL_SENTIMENT:"):
                sentiment_str = line[18:].strip().lower()
                analysis["overall_sentiment"] = self._parse_sentiment_score(sentiment_str)

            elif line.startswith("ENERGY_LEVEL:"):
                analysis["energy_level"] = line[13:].strip().lower()

            elif line.startswith("COLLABORATION_SCORE:"):
                score_str = line[20:].strip().split("/")[0]
                try:
                    analysis["collaboration_score"] = int(score_str)
                except:
                    pass

            elif line.startswith("TENSION_INDICATORS:"):
                tension = line[19:].strip()
                if tension.lower() not in ["none", "not specified", ""]:
                    analysis["tension_indicators"] = tension

            elif line.startswith("POSITIVE_HIGHLIGHTS:"):
                highlights = line[20:].strip()
                if highlights.lower() not in ["none", "not specified", ""]:
                    analysis["positive_highlights"] = [h.strip() for h in highlights.split(";") if h.strip()]

            elif line.startswith("CONCERNS_RAISED:"):
                concerns = line[16:].strip()
                if concerns.lower() not in ["none", "not specified", ""]:
                    analysis["concerns_raised"] = [c.strip() for c in concerns.split(";") if c.strip()]

            elif line.startswith("ENGAGEMENT:"):
                analysis["engagement"] = line[11:].strip()

        return analysis

    def _parse_sentiment_score(self, sentiment_str: str) -> SentimentScore:
        """Parse sentiment score from string"""
        sentiment_str = sentiment_str.lower()

        if "very positive" in sentiment_str or "very_positive" in sentiment_str:
            return SentimentScore.VERY_POSITIVE
        elif "very negative" in sentiment_str or "very_negative" in sentiment_str:
            return SentimentScore.VERY_NEGATIVE
        elif "positive" in sentiment_str:
            return SentimentScore.POSITIVE
        elif "negative" in sentiment_str:
            return SentimentScore.NEGATIVE
        else:
            return SentimentScore.NEUTRAL

    def _sample_transcript(self, transcript: str, sample_size: int = 2000) -> str:
        """
        Sample key sections from a long transcript

        Takes beginning, middle, and end sections
        """
        words = transcript.split()
        total_words = len(words)

        if total_words <= sample_size:
            return transcript

        # Take sections from beginning, middle, and end
        section_size = sample_size // 3

        beginning = " ".join(words[:section_size])
        middle_start = (total_words - section_size) // 2
        middle = " ".join(words[middle_start:middle_start + section_size])
        end = " ".join(words[-section_size:])

        return f"{beginning}\n...\n{middle}\n...\n{end}"

    async def identify_key_moments(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Identify key emotional or significant moments in the meeting

        Returns:
            List of key moments with timestamp and description
        """
        try:
            prompt = f"""Identify 3-5 key moments in this meeting where there was:
- A significant decision
- Strong emotional response
- Important insight shared
- Critical question raised
- Conflict or disagreement
- Breakthrough or aha moment

For each moment, provide:
- Description: What happened
- Significance: Why it matters
- Approximate location: beginning, middle, or end of meeting

Transcript:
{transcript[:2000]}

Key Moments (one per line, format: "MOMENT: [description] | SIGNIFICANCE: [why] | LOCATION: [when]"):"""

            response = await self.llm_provider.complete(prompt)

            # Parse moments
            moments = []
            for line in response.content.split("\n"):
                if line.startswith("MOMENT:"):
                    parts = line.split("|")
                    if len(parts) >= 3:
                        moments.append({
                            "description": parts[0].replace("MOMENT:", "").strip(),
                            "significance": parts[1].replace("SIGNIFICANCE:", "").strip(),
                            "location": parts[2].replace("LOCATION:", "").strip()
                        })

            return moments

        except Exception as e:
            self.logger.error(f"Key moments identification failed: {str(e)}")
            return []
