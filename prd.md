🧠 **Product Requirements Document (PRD)**

## **AI Agent — Chief of Staff for Startup Founders (v1.2, MCP Edition)**

**Stack:** FastAPI + Supabase (pgvector) + AgentFlow + LangChain + MCP Servers (ZeroDB, Notion, Zoom, Slack, Discord, Calendar)

---

## **1. Product Overview**

### **Purpose**

The **AI Chief of Staff** (AI-CoS) is a **multi-agent executive operations system** that acts as a founder’s **intelligent operator** — synthesizing meetings, communications, documents, and metrics across dozens of tools through **MCP servers**.
It provides real-time briefings, meeting summaries, and action routing across voice, video, and asynchronous channels (Zoom, Loom, Fireflies, Otter).

### **Vision**

> To give every startup founder a 24/7 Chief of Staff that never forgets, always follows up, and understands the entire company context.

---

## **2. Target Users**

| Persona           | Goals                                                |
| ----------------- | ---------------------------------------------------- |
| Founders / CEOs   | Stay focused on strategy while AI handles operations |
| Chiefs of Staff   | Centralize information across departments            |
| EA / Ops Managers | Automate scheduling, follow-ups, reporting           |
| VCs / Advisors    | Track founder and company progress asynchronously    |

---

## **3. Core Value Proposition**

| Capability                                             | Outcome                                      |
| ------------------------------------------------------ | -------------------------------------------- |
| MCP-powered unified context                            | One knowledge layer across all apps          |
| Async meeting summaries (Zoom, Loom, Fireflies, Otter) | No notes ever missed                         |
| Automatic delegation                                   | Tasks routed via Monday, Notion, or ZeroApps |
| Contextual investor CRM                                | Every touchpoint logged and recalled         |
| Strategic analysis                                     | Proactive insights drawn from real data      |
| Privacy-first                                          | MCP architecture ensures data sovereignty    |

---

## **4. Product Goals**

1. Reduce founder context switching by 80%
2. Provide a unified daily brief powered by MCP data fusion
3. Automate investor and team follow-ups from recorded meetings
4. Learn founder tone and communication style
5. Run autonomously using existing MCP agent orchestration (AgentFlow)

---

## **5. Core Features**

---

### 🧭 **A. Founder Command Center (MCP Dashboard)**

* Aggregates insights via MCP servers:

  * Gmail MCP, Outlook MCP, Slack MCP, Discord MCP, Zoom MCP, Notion MCP, Monday MCP, Granola MCP
* Generates **Morning Brief** + **Evening Wrap** summaries
* Pulls metrics from **Granola MCP** and investor updates from **ZeroCRM MCP**
* Prioritization Engine: Classifies all incoming signals (Urgent / Delegate / Monitor)

---

### 🎥 **B. Meeting & Media Intelligence (Zoom, Fireflies, Otter, Loom MCP)**

* MCP connectors handle ingestion of:

  * **Zoom** recordings and live transcripts
  * **Fireflies.ai** and **Otter.ai** summaries
  * **Loom** async video updates and demos
* Combines all sources into a **unified transcript memory** in ZeroDB vector store
* AI generates:

  * Summaries
  * Action items
  * Follow-up drafts
* Fireflies and Otter used as **secondary meeting MCP servers** for fallback / redundancy

---

### 📨 **C. Inbox & Messaging Summaries (Slack, Discord, Gmail, Outlook MCPs)**

* Aggregates unread messages across all MCPs
* Semantic analysis: tone, urgency, sentiment
* Generates summary digest + suggested replies in founder’s tone
* Integrates Discord + Slack summaries directly into Morning Brief

---

### 📋 **D. Task & Workflow Management (Monday.com + Notion MCPs)**

* Auto-creates structured tasks from:

  * Meeting summaries (Zoom MCP)
  * Inbox messages (Gmail/Slack MCP)
  * Voice or Loom commands
* Bi-directional sync with Monday MCP (Boards, Items, Subitems)
* Notion MCP handles project notes + linked documentation
* All completed actions logged to ZeroDB (event sourced for analytics)

---

### 💬 **E. Async Collaboration (Loom MCP)**

* Captures Loom video updates from founder/team
* Auto-summarizes video context + generates action list
* Option to embed summaries in Notion or Monday MCP
* Identifies recurring themes or blockers across Loom updates

---

### 📈 **F. Strategic Insights (Granola MCP + ZeroBooks MCP)**

* Connects via Granola MCP to pull real-time business KPIs
* Cross-references with financial metrics from ZeroBooks MCP
* Predicts runway, spend patterns, hiring needs
* Surfaces “Focus Alerts”:

  * “Marketing CAC increased 15% this week”
  * “Sales conversion rate up 20% MoM”

---

### 🧠 **G. Decision & Memory Engine (ZeroDB MCP + AgentFlow)**

* Stores context embeddings for every:

  * Meeting, transcript, email, Loom, or Fireflies note
* Uses **AgentFlow Orchestration** to reason and route:

  * “Draft investor update” → Email MCP
  * “Create task for dev team” → Monday MCP
  * “Record Loom summary” → Loom MCP
* Supports “explain my decision” chain: retrieves context trail of past reasoning

---

### 🗣️ **H. Multi-Modal Input (Voice + Text)**

* Accepts input via:

  * **ZeroVoice MCP (Twilio)** — voice-to-intent
  * **Cody IDE Chat** — structured agent commands
  * **Discord MCP or Slack MCP** — “/brief me” or “/update investors”
* Converts unstructured input to actionable context and routes via AgentFlow

---

## **6. Data Model (Supabase + ZeroDB MCP)**

```mermaid
erDiagram
    founders {
        uuid id PK
        text name
        text email
        jsonb preferences
        timestamp created_at
    }

    integrations {
        uuid id PK
        uuid founder_id FK
        text platform  // zoom, loom, fireflies, otter, monday, discord, etc.
        text connection_type // mcp, api
        jsonb credentials
        timestamp connected_at
    }

    transcripts {
        uuid id PK
        uuid founder_id FK
        text platform  // zoom, loom, fireflies, otter
        text title
        text url
        jsonb summary
        jsonb action_items
        jsonb vector_embedding
        timestamp recorded_at
    }

    communications {
        uuid id PK
        uuid founder_id FK
        text platform // slack, discord, gmail, outlook
        text sender
        text content
        jsonb sentiment
        boolean followup_needed
        timestamp received_at
    }

    tasks {
        uuid id PK
        uuid founder_id FK
        text description
        text platform // monday, notion
        text status
        timestamp due_date
    }

    insights {
        uuid id PK
        uuid founder_id FK
        text source // granola, meetings, loom
        text type // kpi, decision, recommendation
        jsonb content
        float confidence
        timestamp created_at
    }
```

---

## **7. Integrations (MCP-First Architecture)**

| **System**             | **Integration Type** | **Purpose**                        | **Notes**                         |
| ---------------------- | -------------------- | ---------------------------------- | --------------------------------- |
| **Zoom**               | MCP + REST           | Meetings, recordings, transcripts  | Primary meeting source            |
| **Loom**               | MCP                  | Async video updates                | Summarization + action extraction |
| **Fireflies.ai**       | MCP                  | Meeting transcription fallback     | Syncs with Zoom MCP               |
| **Otter.ai**           | MCP                  | Secondary transcript source        | Used for call + media             |
| **Gmail / Outlook**    | MCP                  | Email summary + follow-up          | OAuth + MCP                       |
| **Slack / Discord**    | MCP                  | Daily summaries + commands         | Cross-team ops                    |
| **Monday.com**         | MCP                  | Task + project management          | GraphQL via MCP wrapper           |
| **Notion**             | MCP                  | Docs, notes, summaries             | Notion MCP already available      |
| **Granola**            | MCP                  | KPI + dashboard data               | AI metrics feed                   |
| **ZeroDB**             | MCP                  | Vector memory + semantic search    | Core context engine               |
| **ZeroVoice (Twilio)** | MCP                  | Voice command → text intent        | Transcription gateway             |
| **AgentFlow**          | MCP                  | Agent orchestration & task routing | Cognitive kernel                  |

---

## **8. AI Architecture**

### **Pipeline**

1. **Ingestion Layer (MCP adapters)**
   Unified data ingestion from all tools via MCPs.
2. **Vectorization (ZeroDB MCP)**
   Every transcript, message, and document is embedded and indexed.
3. **Reasoning Engine (AgentFlow)**
   Agent reasoning chain (context retrieval → intent → action → reflection).
4. **Action Execution (Task Agents)**
   Calls MCPs to perform actions: create tasks, send emails, update notes.
5. **Feedback & Memory Loop**
   Learns from founder corrections to refine tone, summary style, and routing accuracy.

---

## **9. Example User Stories (BDD)**

### **Story 1 — Unified Brief via MCP**

**Given** all MCP servers are connected (Zoom, Loom, Granola, Monday)
**When** the founder says “Hey Chief, brief me for today”
**Then** the AI-CoS returns a structured Morning Brief compiled from all MCPs:

* Meeting summaries (Zoom/Fireflies/Otter)
* Async Loom updates
* Slack/Discord summaries
* KPI snapshot from Granola

---

### **Story 2 — Meeting Summary + Action Sync**

**Given** a meeting was recorded on Zoom
**When** Fireflies MCP delivers transcript
**Then** the agent summarizes and routes action items to Monday MCP and sends follow-up drafts via Outlook MCP.

---

### **Story 3 — Loom Context Recall**

**Given** the founder recorded a Loom product demo two weeks ago
**When** asked “What did I say about investor onboarding last week?”
**Then** the AI-CoS retrieves that Loom transcript from ZeroDB MCP and summarizes key talking points.

---

### **Story 4 — Voice Command Execution**

**Given** the founder says via ZeroVoice MCP:

> “Remind me to ping Alex after the board meeting.”
> **Then** the AI-CoS creates a Monday.com task and drafts the email using Outlook MCP.

---

## **10. API Specification (FastAPI)**

| **Method** | **Endpoint**              | **Description**                                    |
| ---------- | ------------------------- | -------------------------------------------------- |
| `GET`      | `/briefings/{founder_id}` | Retrieve latest daily brief                        |
| `POST`     | `/briefings/generate`     | Trigger AI summary from all MCPs                   |
| `POST`     | `/meetings/ingest`        | Ingest meeting transcript (Zoom, Fireflies, Otter) |
| `POST`     | `/loom/ingest`            | Process Loom async video summary                   |
| `POST`     | `/communications/sync`    | Sync new messages via Slack/Discord MCP            |
| `POST`     | `/tasks/create`           | Create/update Monday/Notion task                   |
| `GET`      | `/insights/granola`       | Retrieve KPIs from Granola MCP                     |
| `POST`     | `/voice/command`          | Process ZeroVoice command via MCP                  |
| `POST`     | `/decisions/recommend`    | Generate strategic recommendation                  |

---

## **11. Security & Compliance**

* OAuth2 for connected MCP servers
* End-to-end encryption for vector embeddings in ZeroDB
* Supabase Row Level Security (RLS)
* GDPR & CCPA-compliant data deletion and retention
* Multi-tenant workspace isolation per founder

---

## **12. Success Metrics**

| Metric                                | Target           |
| ------------------------------------- | ---------------- |
| Summary accuracy                      | ≥ 93% factual    |
| Time saved per founder                | ≥ 12 hrs/week    |
| MCP uptime                            | ≥ 99.5%          |
| Response time                         | < 1.5 sec median |
| Learning satisfaction (feedback loop) | ≥ 80% positive   |

---

## **13. Future Enhancements**

* Real-time transcript streaming via Zoom MCP
* AI-generated Loom responses (“Reply with Loom”)
* VC portfolio tracking dashboard via shared MCP contexts
* Cross-founder collaboration memory layer
* QNN-powered strategic forecasting (via AWS Braket integration)

---

## **14. Tech Stack**

| Layer            | Tooling                                                        |
| ---------------- | -------------------------------------------------------------- |
| Backend          | FastAPI + LangChain + AgentFlow                                |
| Database         | Supabase (Postgres) + ZeroDB MCP (pgvector)                    |
| AI Models        | GPT-4o, Claude 3.5, DeepSeek, Ollama                           |
| MCP Integrations | Zoom, Loom, Fireflies, Otter, Monday, Discord, Granola, Notion |
| Orchestration    | AgentFlow MCP                                                  |
| Deployment       | Railway / Docker / Vercel                                      |
| Testing          | pytest + BDD (behave)                                          |

---

## **15. Deliverables**

1. PRD (this document)
2. FastAPI backend scaffolding with MCP connectors
3. Supabase + ZeroDB schema
4. LangChain/AgentFlow orchestration templates
5. MCP integration stubs (Zoom, Loom, Fireflies, Otter, Monday, Discord)
6. Unit & behavior tests (TDD/BDD)
7. Developer README + OpenAPI YAML

---
