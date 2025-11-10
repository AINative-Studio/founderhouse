# Sprint 5: Discord Bot, API Endpoints & Database Schemas

**Version:** 1.0
**Part:** 3 of Sprint 5 Architecture
**Focus:** Discord Integration, REST APIs, Database Design

---

## Discord Bot Architecture

### Overview

The Discord Bot delivers daily briefings and enables conversational interaction with the AI Chief of Staff directly within Discord.

```
Briefing Schedule              User Messages
     │                              │
     ▼                              ▼
┌──────────────────────────────────────────────┐
│         Discord Bot Application              │
│  ┌────────────────────────────────────────┐  │
│  │ Commands:                              │  │
│  │ /brief morning - Get morning brief     │  │
│  │ /brief evening - Get evening wrap      │  │
│  │ /brief investor - Get weekly summary   │  │
│  │ /ask <question> - Query AI CoS         │  │
│  │ /schedule - View today's schedule      │  │
│  │ /kpis - View key metrics               │  │
│  └────────────────────────────────────────┘  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│          Backend API Integration              │
│  - Authentication via workspace token         │
│  - Founder identification from Discord user   │
│  - Webhook for automated delivery             │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│         Briefing Service / AgentFlow          │
│  - Generate requested content                 │
│  - Format for Discord rich embeds             │
│  - Return structured response                 │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│          Discord Message Delivery             │
│  - Rich embeds with color coding              │
│  - Interactive buttons                        │
│  - Threaded responses                         │
└───────────────────────────────────────────────┘
```

### Discord Bot Implementation

```python
import discord
from discord.ext import commands, tasks
from typing import Optional, Dict, Any
from datetime import datetime, time
import pytz

class AIChiefOfStaffBot(commands.Bot):
    """
    Discord bot for AI Chief of Staff

    Features:
    - Slash commands for briefings and queries
    - Scheduled briefing delivery
    - Interactive embeds
    - Thread-based conversations
    """

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix='/',
            intents=intents,
            description='AI Chief of Staff - Your intelligent business assistant'
        )

        self.api_client = BackendAPIClient()
        self.user_workspace_map = {}  # Discord User ID → Workspace ID

    async def setup_hook(self):
        """Initialize bot"""
        # Register slash commands
        await self.tree.sync()

        # Start scheduled tasks
        self.deliver_morning_briefs.start()
        self.deliver_evening_wraps.start()

    @tasks.loop(time=time(hour=7, minute=0, tzinfo=pytz.UTC))
    async def deliver_morning_briefs(self):
        """Deliver morning briefs at 7 AM user's local time"""

        # Get all registered Discord users with morning brief enabled
        users = await self.get_registered_users_for_briefing('morning')

        for user_info in users:
            try:
                # Check if it's 7 AM in user's timezone
                user_tz = pytz.timezone(user_info['timezone'])
                user_time = datetime.now(user_tz)

                if user_time.hour == 7:
                    await self.send_briefing(
                        user_id=user_info['discord_user_id'],
                        briefing_type='morning',
                        workspace_id=user_info['workspace_id'],
                        founder_id=user_info['founder_id']
                    )

            except Exception as e:
                print(f"Error delivering morning brief to {user_info['discord_user_id']}: {e}")

    @tasks.loop(time=time(hour=18, minute=0, tzinfo=pytz.UTC))
    async def deliver_evening_wraps(self):
        """Deliver evening wraps at 6 PM user's local time"""

        users = await self.get_registered_users_for_briefing('evening')

        for user_info in users:
            try:
                user_tz = pytz.timezone(user_info['timezone'])
                user_time = datetime.now(user_tz)

                if user_time.hour == 18:
                    await self.send_briefing(
                        user_id=user_info['discord_user_id'],
                        briefing_type='evening',
                        workspace_id=user_info['workspace_id'],
                        founder_id=user_info['founder_id']
                    )

            except Exception as e:
                print(f"Error delivering evening wrap to {user_info['discord_user_id']}: {e}")

    async def send_briefing(
        self,
        user_id: int,
        briefing_type: str,
        workspace_id: str,
        founder_id: str
    ):
        """Send briefing to Discord user"""

        # Get user
        user = await self.fetch_user(user_id)
        if not user:
            return

        # Fetch briefing from backend
        briefing = await self.api_client.get_briefing(
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type=briefing_type
        )

        if not briefing:
            await user.send("Unable to generate briefing at this time.")
            return

        # Create Discord embed
        embed = self.create_briefing_embed(briefing, briefing_type)

        # Send via DM
        await user.send(embed=embed)

    def create_briefing_embed(
        self,
        briefing: Dict[str, Any],
        briefing_type: str
    ) -> discord.Embed:
        """Create rich Discord embed for briefing"""

        # Color coding
        colors = {
            'morning': discord.Color.blue(),
            'evening': discord.Color.purple(),
            'investor': discord.Color.gold()
        }

        embed = discord.Embed(
            title=briefing.get('title', f'{briefing_type.capitalize()} Brief'),
            description=briefing.get('summary', ''),
            color=colors.get(briefing_type, discord.Color.default()),
            timestamp=datetime.utcnow()
        )

        # Add sections as fields
        for section in briefing.get('sections', []):
            embed.add_field(
                name=section['title'],
                value=section['content'][:1024],  # Discord limit
                inline=False
            )

        # Add key highlights
        if briefing.get('key_highlights'):
            highlights_text = '\n'.join([
                f"• {h}" for h in briefing['key_highlights'][:5]
            ])
            embed.add_field(
                name='🌟 Key Highlights',
                value=highlights_text,
                inline=False
            )

        # Add action items
        if briefing.get('action_items'):
            actions_text = '\n'.join([
                f"☐ {a}" for a in briefing['action_items'][:5]
            ])
            embed.add_field(
                name='✅ Action Items',
                value=actions_text,
                inline=False
            )

        embed.set_footer(text='AI Chief of Staff • Generated by AgentFlow')

        return embed

    async def get_registered_users_for_briefing(
        self,
        briefing_type: str
    ) -> List[Dict[str, Any]]:
        """Get Discord users registered for automatic briefings"""

        users = await self.api_client.get_discord_subscriptions(
            briefing_type=briefing_type
        )

        return users


# Slash Commands

@discord.app_commands.command(
    name='brief',
    description='Get a briefing (morning, evening, or investor)'
)
@discord.app_commands.describe(
    type='Type of briefing to generate'
)
@discord.app_commands.choices(type=[
    discord.app_commands.Choice(name='Morning', value='morning'),
    discord.app_commands.Choice(name='Evening', value='evening'),
    discord.app_commands.Choice(name='Investor', value='investor')
])
async def brief_command(
    interaction: discord.Interaction,
    type: discord.app_commands.Choice[str]
):
    """Generate and send briefing"""

    await interaction.response.defer(thinking=True)

    # Get user's workspace info
    user_info = await bot.get_user_workspace(interaction.user.id)

    if not user_info:
        await interaction.followup.send(
            "Please link your Discord account to your workspace first using `/setup`"
        )
        return

    # Fetch briefing
    briefing = await bot.api_client.get_briefing(
        workspace_id=user_info['workspace_id'],
        founder_id=user_info['founder_id'],
        briefing_type=type.value
    )

    if not briefing:
        await interaction.followup.send("Unable to generate briefing.")
        return

    # Create embed
    embed = bot.create_briefing_embed(briefing, type.value)

    await interaction.followup.send(embed=embed)


@discord.app_commands.command(
    name='ask',
    description='Ask your AI Chief of Staff a question'
)
@discord.app_commands.describe(
    question='Your question or command'
)
async def ask_command(
    interaction: discord.Interaction,
    question: str
):
    """Query AI Chief of Staff via AgentFlow"""

    await interaction.response.defer(thinking=True)

    user_info = await bot.get_user_workspace(interaction.user.id)

    if not user_info:
        await interaction.followup.send(
            "Please link your Discord account first using `/setup`"
        )
        return

    # Send to AgentFlow orchestrator
    response = await bot.api_client.process_query(
        workspace_id=user_info['workspace_id'],
        founder_id=user_info['founder_id'],
        query=question,
        source='discord'
    )

    if not response:
        await interaction.followup.send("Unable to process query.")
        return

    # Format response
    embed = discord.Embed(
        title='AI Chief of Staff',
        description=response.get('summary', ''),
        color=discord.Color.green()
    )

    if response.get('details'):
        embed.add_field(
            name='Details',
            value=response['details'][:1024],
            inline=False
        )

    if response.get('actions'):
        actions_text = '\n'.join([f"• {a}" for a in response['actions']])
        embed.add_field(
            name='Suggested Actions',
            value=actions_text,
            inline=False
        )

    await interaction.followup.send(embed=embed)


@discord.app_commands.command(
    name='kpis',
    description='View key performance metrics'
)
async def kpis_command(interaction: discord.Interaction):
    """Display current KPIs"""

    await interaction.response.defer(thinking=True)

    user_info = await bot.get_user_workspace(interaction.user.id)

    if not user_info:
        await interaction.followup.send(
            "Please link your Discord account first"
        )
        return

    # Fetch KPI snapshot
    kpis = await bot.api_client.get_kpi_snapshot(
        workspace_id=user_info['workspace_id'],
        founder_id=user_info['founder_id']
    )

    # Create KPI embed
    embed = discord.Embed(
        title='📊 Key Metrics',
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )

    for metric in kpis.get('metrics', []):
        value_text = f"{metric['value']} {metric.get('unit', '')}"

        # Add change indicator
        if metric.get('change_percent'):
            change = metric['change_percent']
            emoji = '📈' if change > 0 else '📉'
            value_text += f"\n{emoji} {change:+.1f}% WoW"

        embed.add_field(
            name=metric['name'],
            value=value_text,
            inline=True
        )

    await interaction.followup.send(embed=embed)


@discord.app_commands.command(
    name='setup',
    description='Link your Discord account to your workspace'
)
@discord.app_commands.describe(
    workspace_token='Your workspace authentication token'
)
async def setup_command(
    interaction: discord.Interaction,
    workspace_token: str
):
    """Link Discord account to workspace"""

    await interaction.response.defer(ephemeral=True)

    # Validate token and create link
    result = await bot.api_client.link_discord_account(
        discord_user_id=interaction.user.id,
        workspace_token=workspace_token
    )

    if result['success']:
        bot.user_workspace_map[interaction.user.id] = {
            'workspace_id': result['workspace_id'],
            'founder_id': result['founder_id']
        }

        await interaction.followup.send(
            f"✅ Successfully linked to workspace: {result['workspace_name']}",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"❌ Failed to link account: {result.get('error', 'Invalid token')}",
            ephemeral=True
        )


# Webhook Endpoint for Backend-Initiated Messages

from fastapi import FastAPI, Request
import hmac
import hashlib

webhook_app = FastAPI()

@webhook_app.post("/discord/webhook/message")
async def discord_webhook_message(request: Request):
    """
    Receive backend-initiated messages to send via Discord

    Used for alerts, notifications, etc.
    """

    # Verify webhook signature
    signature = request.headers.get('X-Webhook-Signature')
    body = await request.body()

    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if signature != expected_sig:
        return {"error": "Invalid signature"}, 401

    # Parse payload
    payload = await request.json()

    user_id = payload.get('discord_user_id')
    message_type = payload.get('type')  # 'text', 'embed', 'alert'
    content = payload.get('content')

    # Get Discord user
    user = await bot.fetch_user(user_id)
    if not user:
        return {"error": "User not found"}, 404

    # Send message based on type
    if message_type == 'embed':
        embed = discord.Embed.from_dict(content)
        await user.send(embed=embed)
    elif message_type == 'text':
        await user.send(content=content['text'])
    elif message_type == 'alert':
        embed = discord.Embed(
            title='⚠️ Alert',
            description=content['message'],
            color=discord.Color.red()
        )
        await user.send(embed=embed)

    return {"success": True}
```

---

## API Endpoint Specifications

### Overview

REST API endpoints for Sprint 5 features.

#### Base URL
```
https://api.founderhouse.ai/v1
```

### Agent Orchestration Endpoints

#### 1. Execute Agent Graph

**POST** `/orchestration/graphs/execute`

Execute an agent routing graph.

```json
{
  "graph_id": "uuid",
  "initial_state": {
    "user_query": "Show me this month's financials",
    "date_range": {
      "start": "2025-11-01",
      "end": "2025-11-30"
    }
  },
  "founder_id": "uuid",
  "workspace_id": "uuid"
}
```

**Response 200 OK:**
```json
{
  "request_id": "uuid",
  "status": "completed",
  "final_state": {
    "financials": {...},
    "insights": [...],
    "summary": "..."
  },
  "execution_log": [
    {
      "node_id": "fetch_financials",
      "agent_type": "zerobooks",
      "status": "success",
      "duration_ms": 1250
    }
  ],
  "started_at": "2025-11-05T10:00:00Z",
  "completed_at": "2025-11-05T10:00:05Z"
}
```

#### 2. Create Agent Graph

**POST** `/orchestration/graphs`

Create new agent routing graph.

```json
{
  "name": "Financial Analysis Workflow",
  "description": "Analyze financial metrics and generate insights",
  "workspace_id": "uuid",
  "nodes": [
    {
      "node_id": "fetch_financials",
      "agent_type": "zerobooks",
      "condition": "always",
      "depends_on": [],
      "timeout_seconds": 300,
      "input_mapping": {
        "query": "state.user_query"
      },
      "output_mapping": {
        "financial_data": "state.financials"
      }
    }
  ],
  "entry_node": "fetch_financials"
}
```

**Response 201 Created:**
```json
{
  "graph_id": "uuid",
  "name": "Financial Analysis Workflow",
  "version": 1,
  "created_at": "2025-11-05T10:00:00Z"
}
```

#### 3. Get Graph Execution Status

**GET** `/orchestration/executions/{request_id}`

Get status of running or completed graph execution.

**Response 200 OK:**
```json
{
  "request_id": "uuid",
  "status": "running",  // "running", "completed", "failed"
  "current_node": "analyze_metrics",
  "completed_nodes": ["fetch_financials"],
  "progress_percent": 50,
  "started_at": "2025-11-05T10:00:00Z",
  "estimated_completion": "2025-11-05T10:00:10Z"
}
```

### Voice Command Endpoints

#### 4. Process Voice Command

**POST** `/voice/process`

Process voice command via ZeroVoice MCP.

**Request:**
```
Content-Type: multipart/form-data

audio: <audio_file.wav>
founder_id: uuid
workspace_id: uuid
context: {"location": "office"}
```

**Response 200 OK:**
```json
{
  "transcript": "Show me this week's revenue",
  "intent": "financial_query",
  "entities": {
    "metric": "revenue",
    "period": "this_week"
  },
  "confidence": 0.95,
  "agent_response": {
    "summary": "Revenue this week: $125,000",
    "details": {...}
  },
  "voice_response_url": "https://cdn.../response.mp3"
}
```

#### 5. Text-to-Speech

**POST** `/voice/synthesize`

Generate voice response from text.

```json
{
  "text": "Your revenue this week is $125,000",
  "voice_profile": "default",
  "founder_id": "uuid"
}
```

**Response 200 OK:**
```json
{
  "audio_url": "https://cdn.../voice_response.mp3",
  "duration_seconds": 5.2,
  "format": "mp3"
}
```

### Loom Video Endpoints

#### 6. Process Loom Video

**POST** `/videos/loom/process`

Process Loom video for summarization.

```json
{
  "video_url": "https://loom.com/share/xxxxx",
  "workspace_id": "uuid",
  "founder_id": "uuid",
  "requested_by": "uuid"
}
```

**Response 202 Accepted:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "estimated_completion": "2025-11-05T10:05:00Z",
  "status_url": "/videos/loom/jobs/uuid"
}
```

#### 7. Get Video Summary

**GET** `/videos/loom/{video_id}/summary`

Get processed video summary.

**Response 200 OK:**
```json
{
  "video_id": "uuid",
  "title": "Product Demo",
  "duration_seconds": 1800,
  "summary": {
    "summary": "...",
    "key_points": [...],
    "action_items": [...],
    "topics": [...],
    "sentiment": {...}
  },
  "transcript": {...},
  "processed_at": "2025-11-05T10:03:00Z"
}
```

### Discord Integration Endpoints

#### 8. Link Discord Account

**POST** `/discord/link`

Link Discord account to workspace.

```json
{
  "discord_user_id": "123456789",
  "workspace_token": "ws_xxxxx"
}
```

**Response 200 OK:**
```json
{
  "success": true,
  "workspace_id": "uuid",
  "workspace_name": "Acme Inc",
  "founder_id": "uuid"
}
```

#### 9. Get Discord Briefing Subscriptions

**GET** `/discord/subscriptions?briefing_type=morning`

Get Discord users subscribed to automated briefings.

**Response 200 OK:**
```json
{
  "subscriptions": [
    {
      "discord_user_id": "123456789",
      "workspace_id": "uuid",
      "founder_id": "uuid",
      "briefing_type": "morning",
      "timezone": "America/New_York",
      "delivery_time": "07:00"
    }
  ]
}
```

### Feedback Endpoints

#### 10. Submit Agent Feedback

**POST** `/orchestration/feedback`

Submit user feedback on agent output.

```json
{
  "request_id": "uuid",
  "agent_type": "zerobooks",
  "feedback_type": "thumbs_down",
  "rating": 2,
  "correction": {
    "incorrect_value": "...",
    "correct_value": "..."
  },
  "comment": "The date range was wrong",
  "founder_id": "uuid",
  "workspace_id": "uuid"
}
```

**Response 201 Created:**
```json
{
  "feedback_id": "uuid",
  "created_at": "2025-11-05T10:00:00Z"
}
```

---

## Database Schema Design

### Migration 006: Agent Orchestration & Voice Features

```sql
-- =====================================================
-- Migration 006: Agent Orchestration & Voice Features
-- Sprint 5: Orchestration, Voice & Async Collaboration
-- =====================================================

-- Create orchestration schema
CREATE SCHEMA IF NOT EXISTS orchestration;

-- =====================================================
-- Agent Routing Graphs
-- =====================================================

CREATE TABLE orchestration.agent_graphs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,

    -- Graph definition
    nodes JSONB NOT NULL,  -- Array of AgentNodeDefinition
    entry_node TEXT NOT NULL,
    initial_state JSONB DEFAULT '{}',

    -- Metadata
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES core.founders(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT valid_nodes CHECK (jsonb_typeof(nodes) = 'array'),
    CONSTRAINT valid_initial_state CHECK (jsonb_typeof(initial_state) = 'object')
);

CREATE INDEX idx_agent_graphs_workspace ON orchestration.agent_graphs(workspace_id);
CREATE INDEX idx_agent_graphs_active ON orchestration.agent_graphs(workspace_id, is_active);

-- =====================================================
-- Graph Execution Tracking
-- =====================================================

CREATE TYPE orchestration.execution_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed',
    'cancelled'
);

CREATE TABLE orchestration.graph_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    graph_id UUID NOT NULL REFERENCES orchestration.agent_graphs(id),
    workspace_id UUID NOT NULL REFERENCES core.workspaces(id),
    founder_id UUID NOT NULL REFERENCES core.founders(id),

    -- Execution state
    status orchestration.execution_status NOT NULL DEFAULT 'pending',
    current_node TEXT,
    completed_nodes TEXT[] DEFAULT '{}',
    failed_nodes TEXT[] DEFAULT '{}',

    -- State snapshots
    initial_state JSONB NOT NULL,
    current_state JSONB,
    final_state JSONB,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    estimated_completion TIMESTAMPTZ,

    -- Error tracking
    error_message TEXT,
    error_details JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_executions_workspace ON orchestration.graph_executions(workspace_id);
CREATE INDEX idx_executions_founder ON orchestration.graph_executions(founder_id);
CREATE INDEX idx_executions_status ON orchestration.graph_executions(status, created_at DESC);
CREATE INDEX idx_executions_graph ON orchestration.graph_executions(graph_id);

-- =====================================================
-- Node Execution Logs
-- =====================================================

CREATE TABLE orchestration.node_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES orchestration.graph_executions(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,

    -- Execution details
    attempt_number INT DEFAULT 1,
    status TEXT NOT NULL,  -- 'success', 'failed', 'timeout'

    -- Input/Output
    input_data JSONB,
    output_data JSONB,

    -- Reflection
    validation_passed BOOLEAN,
    validation_issues TEXT[],
    reflection_applied BOOLEAN DEFAULT false,

    -- Timing
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INT,

    -- Error tracking
    error_message TEXT,
    error_traceback TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_node_logs_execution ON orchestration.node_execution_logs(execution_id);
CREATE INDEX idx_node_logs_agent ON orchestration.node_execution_logs(agent_type);
CREATE INDEX idx_node_logs_status ON orchestration.node_execution_logs(status);

-- =====================================================
-- Agent Feedback
-- =====================================================

CREATE TYPE orchestration.feedback_type_enum AS ENUM (
    'thumbs_up',
    'thumbs_down',
    'correction',
    'rating',
    'implicit_usage'
);

CREATE TABLE orchestration.agent_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID REFERENCES orchestration.graph_executions(id),
    request_id UUID,  -- Can reference non-graph requests too
    agent_type TEXT NOT NULL,

    -- Feedback data
    feedback_type orchestration.feedback_type_enum NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    correction JSONB,
    comment TEXT,

    -- Context
    founder_id UUID NOT NULL REFERENCES core.founders(id),
    workspace_id UUID NOT NULL REFERENCES core.workspaces(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_feedback_agent ON orchestration.agent_feedback(agent_type);
CREATE INDEX idx_feedback_founder ON orchestration.agent_feedback(founder_id);
CREATE INDEX idx_feedback_type ON orchestration.agent_feedback(feedback_type);
CREATE INDEX idx_feedback_created ON orchestration.agent_feedback(created_at DESC);

-- =====================================================
-- Agent Training Examples (from corrections)
-- =====================================================

CREATE TABLE orchestration.agent_training_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type TEXT NOT NULL,

    -- Training data
    input_data JSONB NOT NULL,
    incorrect_output JSONB NOT NULL,
    corrected_output JSONB NOT NULL,

    -- Metadata
    founder_id UUID REFERENCES core.founders(id),
    feedback_id UUID REFERENCES orchestration.agent_feedback(id),

    -- Usage tracking
    used_in_training BOOLEAN DEFAULT false,
    quality_score FLOAT,  -- How good this example is

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_training_agent ON orchestration.agent_training_examples(agent_type);
CREATE INDEX idx_training_unused ON orchestration.agent_training_examples(agent_type, used_in_training);

-- =====================================================
-- Intent Patterns (for voice/text classification)
-- =====================================================

CREATE TABLE orchestration.intent_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID REFERENCES core.founders(id),  -- Personalized patterns

    -- Intent data
    intent_type TEXT NOT NULL,
    example_text TEXT NOT NULL,
    embedding vector(1536),  -- For similarity search

    -- Entity schema
    entity_schema JSONB DEFAULT '{}',

    -- Usage stats
    usage_count INT DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_intent_founder ON orchestration.intent_patterns(founder_id);
CREATE INDEX idx_intent_type ON orchestration.intent_patterns(intent_type);
CREATE INDEX idx_intent_embedding ON orchestration.intent_patterns
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE embedding IS NOT NULL;

-- =====================================================
-- Routing Preferences (learned from feedback)
-- =====================================================

CREATE TABLE orchestration.routing_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID NOT NULL REFERENCES core.founders(id),

    -- Preference data
    intent_pattern TEXT NOT NULL,
    preferred_agent TEXT,
    avoid_agent TEXT,
    graph_id UUID REFERENCES orchestration.agent_graphs(id),

    -- Reasoning
    reason TEXT,
    confidence FLOAT DEFAULT 0.5,

    -- Timing
    learned_from INT,  -- Number of feedback instances
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (founder_id, intent_pattern, preferred_agent)
);

CREATE INDEX idx_routing_prefs_founder ON orchestration.routing_preferences(founder_id);

-- =====================================================
-- Graph State Checkpoints
-- =====================================================

CREATE TABLE orchestration.graph_states (
    execution_id UUID NOT NULL REFERENCES orchestration.graph_executions(id) ON DELETE CASCADE,
    checkpoint_name TEXT NOT NULL,
    state_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (execution_id, checkpoint_name)
);

CREATE INDEX idx_graph_states_execution ON orchestration.graph_states(execution_id);

-- =====================================================
-- Loom Video Summaries
-- =====================================================

CREATE SCHEMA IF NOT EXISTS media;

CREATE TABLE media.loom_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES core.workspaces(id),
    founder_id UUID NOT NULL REFERENCES core.founders(id),

    -- Video metadata
    loom_video_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    video_url TEXT NOT NULL,
    thumbnail_url TEXT,
    duration_seconds INT,

    -- Owner info
    owner_email TEXT,

    -- Processing status
    processing_status TEXT DEFAULT 'pending',
    processed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_loom_workspace ON media.loom_videos(workspace_id);
CREATE INDEX idx_loom_founder ON media.loom_videos(founder_id);
CREATE INDEX idx_loom_status ON media.loom_videos(processing_status);

CREATE TABLE media.loom_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES media.loom_videos(id) ON DELETE CASCADE,

    -- Transcript data
    full_text TEXT NOT NULL,
    words JSONB,  -- Word-level timing

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_loom_transcripts_video ON media.loom_transcripts(video_id);

CREATE TABLE media.loom_transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES media.loom_transcripts(id) ON DELETE CASCADE,

    -- Chunk data
    chunk_index INT NOT NULL,
    text TEXT NOT NULL,
    start_time FLOAT,
    end_time FLOAT,

    -- Vector embedding
    embedding vector(1536),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (transcript_id, chunk_index)
);

CREATE INDEX idx_loom_chunks_transcript ON media.loom_transcript_chunks(transcript_id);
CREATE INDEX idx_loom_chunks_embedding ON media.loom_transcript_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE embedding IS NOT NULL;

CREATE TABLE media.loom_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES media.loom_videos(id) ON DELETE CASCADE,

    -- Summary content
    summary TEXT NOT NULL,
    key_points TEXT[],
    action_items JSONB,
    topics TEXT[],

    -- Sentiment analysis
    sentiment JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (video_id)
);

CREATE INDEX idx_loom_summaries_video ON media.loom_summaries(video_id);

-- =====================================================
-- Discord Integration
-- =====================================================

CREATE TABLE core.discord_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_user_id TEXT NOT NULL UNIQUE,
    workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    founder_id UUID NOT NULL REFERENCES core.founders(id) ON DELETE CASCADE,

    -- Preferences
    briefing_subscriptions TEXT[] DEFAULT '{}',  -- ['morning', 'evening']
    notification_preferences JSONB DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_discord_links_workspace ON core.discord_links(workspace_id);
CREATE INDEX idx_discord_links_founder ON core.discord_links(founder_id);
CREATE INDEX idx_discord_links_active ON core.discord_links(is_active);

-- =====================================================
-- Row-Level Security Policies
-- =====================================================

ALTER TABLE orchestration.agent_graphs ENABLE ROW LEVEL SECURITY;
ALTER TABLE orchestration.graph_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE orchestration.node_execution_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE orchestration.agent_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE orchestration.intent_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE orchestration.routing_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE media.loom_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE media.loom_transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE media.loom_transcript_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE media.loom_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.discord_links ENABLE ROW LEVEL SECURITY;

-- Workspace isolation policies (using existing auth.user_workspaces())

CREATE POLICY agent_graphs_select_policy ON orchestration.agent_graphs
    FOR SELECT TO authenticated
    USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY graph_executions_select_policy ON orchestration.graph_executions
    FOR SELECT TO authenticated
    USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY node_logs_select_policy ON orchestration.node_execution_logs
    FOR SELECT TO authenticated
    USING (execution_id IN (
        SELECT id FROM orchestration.graph_executions
        WHERE workspace_id IN (SELECT auth.user_workspaces())
    ));

CREATE POLICY feedback_select_policy ON orchestration.agent_feedback
    FOR SELECT TO authenticated
    USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY loom_videos_select_policy ON media.loom_videos
    FOR SELECT TO authenticated
    USING (workspace_id IN (SELECT auth.user_workspaces()));

CREATE POLICY discord_links_select_policy ON core.discord_links
    FOR SELECT TO authenticated
    USING (workspace_id IN (SELECT auth.user_workspaces()));

-- =====================================================
-- Triggers
-- =====================================================

-- Update updated_at timestamps
CREATE TRIGGER update_agent_graphs_updated_at
    BEFORE UPDATE ON orchestration.agent_graphs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_graph_executions_updated_at
    BEFORE UPDATE ON orchestration.graph_executions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_intent_patterns_updated_at
    BEFORE UPDATE ON orchestration.intent_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Comments
-- =====================================================

COMMENT ON TABLE orchestration.agent_graphs IS 'Agent routing graph definitions';
COMMENT ON TABLE orchestration.graph_executions IS 'Track agent graph executions';
COMMENT ON TABLE orchestration.node_execution_logs IS 'Detailed logs for each node execution';
COMMENT ON TABLE orchestration.agent_feedback IS 'User feedback on agent outputs';
COMMENT ON TABLE orchestration.intent_patterns IS 'Voice/text intent classification patterns';
COMMENT ON TABLE media.loom_videos IS 'Loom video metadata';
COMMENT ON TABLE media.loom_summaries IS 'AI-generated video summaries';
COMMENT ON TABLE core.discord_links IS 'Discord account links to workspaces';
```

---

## Summary

This comprehensive architecture document covers:

1. **AgentFlow Orchestration** - DAG-based multi-agent coordination
2. **Reflection & Feedback Loops** - Self-correction and learning
3. **Voice Command Integration** - ZeroVoice MCP processing
4. **Loom Video Summarization** - Async video content extraction
5. **Discord Bot** - Rich interactive briefing delivery
6. **REST API Endpoints** - Complete API specifications
7. **Database Schemas** - Migration 006 with all tables and policies

### Key Features Delivered

- Graph-based agent routing with conditional logic
- Reflection loops for output validation and self-correction
- User feedback collection and learning from corrections
- Voice-to-text-to-action pipeline with ZeroVoice
- Loom video processing with semantic chunking
- Discord bot with slash commands and scheduled briefings
- Comprehensive REST API for all features
- Complete database schema with RLS policies

### Next Steps

1. Implement agent connectors (ZeroBooks, ZeroCRM, ZeroSchedule)
2. Build reflection validation logic
3. Integrate ZeroVoice MCP connector
4. Deploy Discord bot
5. Create background tasks for scheduled operations
6. Set up monitoring and alerting
7. Write integration tests

---

**Document Version:** 1.0
**Last Updated:** 2025-11-05
**Maintained By:** System Architect
