"""
Recommendation Chain
LangChain-based chain for generating strategic recommendations
"""
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

from app.models.recommendation import RecommendationContext


logger = logging.getLogger(__name__)


class RecommendationChain:
    """LangChain chain for generating strategic recommendations"""

    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.7):
        """
        Initialize recommendation chain

        Args:
            model_name: LLM model to use
            temperature: Temperature for generation
        """
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)

        # Define prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert business strategist and data analyst for startup founders.

Your task is to analyze KPI data, anomalies, trends, and business context to generate actionable strategic recommendations.

Guidelines:
1. Be specific and actionable - provide concrete steps
2. Prioritize recommendations based on potential impact
3. Consider both short-term wins and long-term strategy
4. Base recommendations on data patterns and anomalies
5. Include estimated effort and success metrics
6. Provide confidence scores based on data quality

Output Format (JSON):
{{
    "recommendations": [
        {{
            "title": "Brief title",
            "type": "strategic|operational|financial|marketing|sales|product",
            "priority": "low|medium|high|urgent",
            "description": "Detailed description",
            "confidence": 0.0-1.0,
            "expected_impact": "low|medium|high|transformational",
            "actionable_steps": ["Step 1", "Step 2", ...],
            "success_metrics": ["Metric 1", "Metric 2", ...],
            "estimated_effort": "e.g., 2 weeks",
            "estimated_cost": null or number
        }}
    ]
}}"""),
            ("human", """Analyze the following data and generate strategic recommendations:

Context:
{context}

KPI Data:
{kpi_data}

Anomalies Detected:
{anomalies}

Trends:
{trends}

Recent Meetings/Decisions:
{recent_context}

Generate 3-5 high-quality recommendations focusing on the most impactful actions.""")
        ])

        self.chain = self.prompt | self.llm | JsonOutputParser()

    async def generate_recommendations(
        self,
        context: RecommendationContext,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on context

        Args:
            context: RecommendationContext with all relevant data
            max_recommendations: Maximum number of recommendations

        Returns:
            List of recommendation dictionaries
        """
        try:
            # Prepare context for LLM
            chain_input = {
                "context": self._format_context(context),
                "kpi_data": self._format_kpi_data(context.kpi_data),
                "anomalies": self._format_anomalies(context.anomalies),
                "trends": self._format_trends(context.trends),
                "recent_context": self._format_recent_context(
                    context.recent_meetings,
                    context.sentiment_analysis
                )
            }

            # Generate recommendations
            result = await self.chain.ainvoke(chain_input)

            recommendations = result.get("recommendations", [])[:max_recommendations]

            self.logger.info(f"Generated {len(recommendations)} recommendations")

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {str(e)}")
            return []

    def _format_context(self, context: RecommendationContext) -> str:
        """Format general context"""
        parts = []

        if context.industry_benchmarks:
            parts.append(f"Industry Benchmarks: {context.industry_benchmarks}")

        if context.historical_recommendations:
            parts.append(
                f"Historical Recommendations: {len(context.historical_recommendations)} previous recommendations"
            )

        return "\n".join(parts) if parts else "No additional context"

    def _format_kpi_data(self, kpi_data: Dict[str, Any]) -> str:
        """Format KPI data for prompt"""
        if not kpi_data:
            return "No KPI data available"

        formatted = []
        for metric, data in kpi_data.items():
            if isinstance(data, dict):
                value = data.get("value", "N/A")
                change = data.get("change", "N/A")
                formatted.append(f"- {metric}: {value} (Change: {change})")
            else:
                formatted.append(f"- {metric}: {data}")

        return "\n".join(formatted)

    def _format_anomalies(self, anomalies: List[Dict[str, Any]]) -> str:
        """Format anomalies for prompt"""
        if not anomalies:
            return "No anomalies detected"

        formatted = []
        for anomaly in anomalies[:10]:  # Limit to top 10
            metric = anomaly.get("metric_name", "Unknown")
            atype = anomaly.get("type", "Unknown")
            severity = anomaly.get("severity", "Unknown")
            deviation = anomaly.get("deviation", 0)

            formatted.append(
                f"- {metric}: {atype} ({severity} severity, {deviation:.1f}% deviation)"
            )

        return "\n".join(formatted)

    def _format_trends(self, trends: List[Dict[str, Any]]) -> str:
        """Format trends for prompt"""
        if not trends:
            return "No significant trends detected"

        formatted = []
        for trend in trends[:10]:
            metric = trend.get("metric_name", "Unknown")
            direction = trend.get("direction", "Unknown")
            change = trend.get("percentage_change", 0)
            period = trend.get("period", "Unknown")

            formatted.append(
                f"- {metric}: {direction} {abs(change):.1f}% {period}"
            )

        return "\n".join(formatted)

    def _format_recent_context(
        self,
        meetings: List[Dict[str, Any]],
        sentiment: Dict[str, Any] = None
    ) -> str:
        """Format recent meetings and sentiment"""
        parts = []

        if meetings:
            parts.append(f"Recent Meetings: {len(meetings)} meetings")
            for meeting in meetings[:5]:
                title = meeting.get("title", "Unknown")
                summary = meeting.get("summary", "")
                parts.append(f"  - {title}: {summary[:100]}...")

        if sentiment:
            parts.append(f"Overall Sentiment: {sentiment.get('overall', 'neutral')}")

        return "\n".join(parts) if parts else "No recent context"
