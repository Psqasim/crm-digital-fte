# Multi-Agent Patterns

Comprehensive patterns for building multi-agent systems with handoffs, orchestration, and complex workflows.

## Table of Contents
- Architecture Patterns Overview
- Manager/Orchestrator Pattern (Agents as Tools)
- Peer Handoff Pattern
- Hybrid Patterns
- Multi-Agent Context Sharing
- Advanced Multi-Agent Workflows

## Architecture Patterns Overview

Two primary patterns for multi-agent systems:

### 1. Manager Pattern (Centralized)

```
        Manager Agent
           /  |  \
          /   |   \
    Agent-A Agent-B Agent-C
```

**Characteristics:**
- Central orchestrator retains control
- Sub-agents are tools
- Manager aggregates results
- Better for parallel sub-tasks

**Use when:**
- Need to coordinate multiple independent tasks
- Results must be aggregated
- Central control is important
- Tasks can run in parallel

### 2. Peer Handoff Pattern (Decentralized)

```
Triage → Specialist-A
       → Specialist-B
       → Specialist-C
```

**Characteristics:**
- Peer agents hand off control
- Specialized conversational flows
- Decentralized decision-making
- Better for sequential workflows

**Use when:**
- Need specialized conversational agents
- Sequential workflow with context transfer
- Routing based on expertise
- Agent determines next step

## Manager/Orchestrator Pattern

### Basic Manager with Sub-Agents

```python
from agents import Agent, Runner
import asyncio

# Specialized worker agents
data_analyzer = Agent(
    name="Data Analyzer",
    instructions="Analyze data and provide insights. Return only the analysis.",
)

report_generator = Agent(
    name="Report Generator",
    instructions="Generate formatted reports. Return only the report.",
)

chart_creator = Agent(
    name="Chart Creator",
    instructions="Describe charts for data visualization. Return description only.",
)

# Manager orchestrates workers
manager = Agent(
    name="Analytics Manager",
    instructions="""You coordinate data analytics tasks.
    Use the available tools to analyze data, generate reports, and create charts.
    Aggregate all results into a comprehensive response.""",
    tools=[
        data_analyzer.as_tool(
            tool_name="analyze_data",
            tool_description="Analyze datasets and extract insights"
        ),
        report_generator.as_tool(
            tool_name="generate_report",
            tool_description="Create formatted analytical reports"
        ),
        chart_creator.as_tool(
            tool_name="create_chart",
            tool_description="Design data visualizations"
        ),
    ]
)

async def main():
    result = await Runner.run(
        manager,
        "Analyze sales data from Q4, generate a report, and suggest visualizations"
    )
    print(result.final_output)

asyncio.run(main())
```

### Manager with Context Passing

Pass context to sub-agents through the manager:

```python
from agents import Agent, Runner, RunContextWrapper
from dataclasses import dataclass

@dataclass
class ProjectContext:
    project_id: str
    client_name: str
    budget: float

# Sub-agents that use context
cost_estimator = Agent[ProjectContext](
    name="Cost Estimator",
    instructions="Estimate costs for project tasks within the budget.",
)

timeline_planner = Agent[ProjectContext](
    name="Timeline Planner",
    instructions="Plan project timeline based on scope.",
)

# Manager coordinates with context
project_manager = Agent[ProjectContext](
    name="Project Manager",
    instructions="Coordinate project planning using available tools.",
    tools=[
        cost_estimator.as_tool(
            tool_name="estimate_costs",
            tool_description="Estimate project costs"
        ),
        timeline_planner.as_tool(
            tool_name="plan_timeline",
            tool_description="Create project timeline"
        ),
    ]
)

async def main():
    context = ProjectContext(
        project_id="PROJ-123",
        client_name="Acme Corp",
        budget=50000.0
    )

    result = await Runner.run(
        project_manager,
        "Plan a website redesign project",
        context=context  # Available to all sub-agents
    )
    print(result.final_output)

asyncio.run(main())
```

### Manager with Custom Sub-Agent Configuration

Run sub-agents with custom settings:

```python
from agents import Agent, Runner, ModelSettings, function_tool

@function_tool
async def run_creative_writer(prompt: str) -> str:
    """Generate creative content.

    Args:
        prompt: The writing prompt
    """
    creative_agent = Agent(
        name="Creative Writer",
        instructions="Write creatively and imaginatively.",
        model_settings=ModelSettings(
            temperature=0.9,      # High creativity
            max_tokens=2000       # Longer output
        )
    )

    result = await Runner.run(
        creative_agent,
        prompt,
        max_turns=3  # Custom turn limit
    )

    return str(result.final_output)

@function_tool
async def run_fact_checker(claim: str) -> str:
    """Verify factual claims.

    Args:
        claim: The claim to verify
    """
    fact_checker = Agent(
        name="Fact Checker",
        instructions="Verify facts accurately and cite sources.",
        model_settings=ModelSettings(
            temperature=0.1,      # Low temperature for accuracy
            max_tokens=500
        )
    )

    result = await Runner.run(fact_checker, claim)
    return str(result.final_output)

# Manager uses these tools
content_manager = Agent(
    name="Content Manager",
    instructions="Create and verify content using specialized agents.",
    tools=[run_creative_writer, run_fact_checker]
)
```

## Peer Handoff Pattern

### Basic Triage and Handoff

```python
from agents import Agent, Runner
import asyncio

# Specialist agents
technical_support = Agent(
    name="Technical Support",
    handoff_description="Handles technical issues, bugs, and troubleshooting",
    instructions="""You are a technical support specialist.
    Help users resolve technical problems with detailed step-by-step guidance."""
)

billing_support = Agent(
    name="Billing Support",
    handoff_description="Handles billing questions, payments, and invoices",
    instructions="""You are a billing specialist.
    Help users with payment issues, invoice questions, and subscription management."""
)

general_support = Agent(
    name="General Support",
    handoff_description="Handles account questions and general inquiries",
    instructions="""You are a general support specialist.
    Help users with account settings, general questions, and non-technical issues."""
)

# Triage agent routes to specialists
triage_agent = Agent(
    name="Support Triage",
    instructions="""You are the first point of contact for support.
    Determine the type of issue and hand off to the appropriate specialist:
    - Technical issues → Technical Support
    - Billing/payment → Billing Support
    - Account/general → General Support""",
    handoffs=[technical_support, billing_support, general_support]
)

async def main():
    # Technical issue
    result = await Runner.run(
        triage_agent,
        "My app keeps crashing when I try to upload files"
    )
    print("Technical issue:", result.final_output)

    # Billing issue
    result = await Runner.run(
        triage_agent,
        "I was charged twice for my subscription this month"
    )
    print("Billing issue:", result.final_output)

asyncio.run(main())
```

### Multi-Level Handoffs

Agents can hand off to other agents that also have handoffs:

```python
# Level 2 specialists
ios_specialist = Agent(
    name="iOS Specialist",
    instructions="Expert in iOS app issues and troubleshooting."
)

android_specialist = Agent(
    name="Android Specialist",
    instructions="Expert in Android app issues and troubleshooting."
)

web_specialist = Agent(
    name="Web Specialist",
    instructions="Expert in web application issues."
)

# Level 1 technical support (can hand off further)
technical_support = Agent(
    name="Technical Support",
    handoff_description="Handles technical issues",
    instructions="""Diagnose technical issues.
    If platform-specific, hand off to the appropriate platform specialist.""",
    handoffs=[ios_specialist, android_specialist, web_specialist]
)

# Top-level triage
triage = Agent(
    name="Support Triage",
    instructions="Route to technical support for technical issues.",
    handoffs=[technical_support]  # Can indirectly reach platform specialists
)
```

### Handoff with Structured Routing Logic

Use output types to make routing decisions explicit:

```python
from pydantic import BaseModel, Field

class RoutingDecision(BaseModel):
    category: str = Field(description="Issue category: technical, billing, or general")
    urgency: str = Field(description="Urgency level: low, medium, high")
    reasoning: str = Field(description="Why this routing decision was made")

router_agent = Agent(
    name="Router",
    instructions="Analyze the user's issue and determine routing.",
    output_type=RoutingDecision
)

async def route_request(user_input: str) -> str:
    """Route user request to appropriate specialist."""
    # Get routing decision
    routing_result = await Runner.run(router_agent, user_input)
    decision = routing_result.final_output_as(RoutingDecision)

    # Select appropriate specialist based on decision
    if decision.category == "technical":
        specialist = technical_support
    elif decision.category == "billing":
        specialist = billing_support
    else:
        specialist = general_support

    # Run specialist with context about routing
    print(f"Routing to {specialist.name}: {decision.reasoning}")
    result = await Runner.run(specialist, user_input)
    return result.final_output
```

## Hybrid Patterns

### Manager with Handoff Capability

Combine both patterns - manager can delegate AND hand off:

```python
# Tools for the manager
@function_tool
async def search_knowledge_base(query: str) -> str:
    """Search internal knowledge base.

    Args:
        query: Search query
    """
    # Simulated search
    return f"Knowledge base results for: {query}"

# Specialists for handoff
expert_consultant = Agent(
    name="Expert Consultant",
    handoff_description="Senior expert for complex cases",
    instructions="Provide expert-level analysis and recommendations."
)

# Manager can use tools AND hand off
support_agent = Agent(
    name="Support Agent",
    instructions="""Help users by:
    1. Searching the knowledge base for solutions
    2. If the issue is complex, hand off to the Expert Consultant""",
    tools=[search_knowledge_base],
    handoffs=[expert_consultant]
)
```

### Sequential Workflow with Manager Coordination

```python
# Stage 1: Research
researcher = Agent(
    name="Researcher",
    instructions="Research topics and gather information. Return findings only."
)

# Stage 2: Analysis
analyst = Agent(
    name="Analyst",
    instructions="Analyze research and extract insights. Return analysis only."
)

# Stage 3: Writer
writer = Agent(
    name="Writer",
    instructions="Write articles based on analysis. Return article only."
)

# Coordinator manages the pipeline
coordinator = Agent(
    name="Content Coordinator",
    instructions="""Coordinate content creation through stages:
    1. Research the topic
    2. Analyze findings
    3. Write the article
    Use each agent in sequence and pass outputs forward.""",
    tools=[
        researcher.as_tool(tool_name="research", tool_description="Research topics"),
        analyst.as_tool(tool_name="analyze", tool_description="Analyze findings"),
        writer.as_tool(tool_name="write", tool_description="Write articles"),
    ]
)

async def main():
    result = await Runner.run(
        coordinator,
        "Create an article about renewable energy trends in 2026"
    )
    print(result.final_output)

asyncio.run(main())
```

## Multi-Agent Context Sharing

### Shared Session Across Agents

Multiple agents can access the same conversation history:

```python
from agents import SQLiteSession

support_agent = Agent(name="Support Agent")
billing_agent = Agent(name="Billing Agent")
technical_agent = Agent(name="Technical Agent")

async def multi_agent_conversation():
    # Shared session for all agents
    session = SQLiteSession("customer_123", "support.db")

    # Agent 1 starts conversation
    result1 = await Runner.run(
        support_agent,
        "I need help with my account",
        session=session
    )

    # Agent 2 continues with full context
    result2 = await Runner.run(
        billing_agent,
        "What are my recent charges?",
        session=session  # Sees previous messages
    )

    # Agent 3 also has full history
    result3 = await Runner.run(
        technical_agent,
        "Can you also check why my app is slow?",
        session=session  # Sees all previous exchanges
    )

    return result3.final_output
```

### Context Inheritance in Handoffs

Context automatically flows through handoffs:

```python
@dataclass
class CustomerContext:
    customer_id: str
    tier: str  # "bronze", "silver", "gold"
    account_age_days: int

def determine_priority(ctx: CustomerContext) -> str:
    """Calculate priority based on customer tier."""
    if ctx.tier == "gold":
        return "high"
    elif ctx.tier == "silver":
        return "medium"
    else:
        return "normal"

# Specialist agents access context
vip_support = Agent[CustomerContext](
    name="VIP Support",
    handoff_description="Premium support for VIP customers",
    instructions="Provide white-glove support with priority handling."
)

standard_support = Agent[CustomerContext](
    name="Standard Support",
    handoff_description="Support for standard customers",
    instructions="Provide helpful support following standard procedures."
)

# Triage uses context to route
triage = Agent[CustomerContext](
    name="Triage",
    instructions="""Route based on customer tier:
    - Gold tier → VIP Support
    - Silver/Bronze → Standard Support""",
    handoffs=[vip_support, standard_support]
)

async def main():
    context = CustomerContext(
        customer_id="CUST-789",
        tier="gold",
        account_age_days=720
    )

    result = await Runner.run(
        triage,
        "I need help with my account",
        context=context  # Flows through handoff automatically
    )
    print(result.final_output)

asyncio.run(main())
```

## Advanced Multi-Agent Workflows

### Parallel Agent Execution

Run multiple agents concurrently:

```python
import asyncio

async def parallel_analysis(data: str):
    """Run multiple analyses in parallel."""

    sentiment_agent = Agent(
        name="Sentiment Analyzer",
        instructions="Analyze sentiment in text. Return sentiment only."
    )

    topic_agent = Agent(
        name="Topic Extractor",
        instructions="Extract main topics. Return topics only."
    )

    summary_agent = Agent(
        name="Summarizer",
        instructions="Summarize text concisely. Return summary only."
    )

    # Run all agents in parallel
    results = await asyncio.gather(
        Runner.run(sentiment_agent, data),
        Runner.run(topic_agent, data),
        Runner.run(summary_agent, data)
    )

    return {
        "sentiment": results[0].final_output,
        "topics": results[1].final_output,
        "summary": results[2].final_output
    }

async def main():
    analysis = await parallel_analysis(
        "The new product launch exceeded expectations..."
    )
    print(analysis)

asyncio.run(main())
```

### Agent Chain with Error Recovery

```python
from agents.exceptions import MaxTurnsExceeded

async def resilient_chain(user_input: str):
    """Chain agents with fallback handling."""

    primary_agent = Agent(
        name="Primary Agent",
        instructions="Handle requests efficiently."
    )

    fallback_agent = Agent(
        name="Fallback Agent",
        instructions="Handle requests that the primary agent couldn't complete."
    )

    try:
        # Try primary agent
        result = await Runner.run(
            primary_agent,
            user_input,
            max_turns=5
        )
        return result.final_output
    except MaxTurnsExceeded:
        print("Primary agent exceeded turns, using fallback...")
        # Fallback to secondary agent
        result = await Runner.run(
            fallback_agent,
            user_input,
            max_turns=10
        )
        return result.final_output
```

### Consensus Pattern

Multiple agents vote on a decision:

```python
async def consensus_decision(question: str) -> str:
    """Get consensus from multiple expert agents."""

    expert1 = Agent(name="Expert 1", instructions="Provide expert opinion.")
    expert2 = Agent(name="Expert 2", instructions="Provide expert opinion.")
    expert3 = Agent(name="Expert 3", instructions="Provide expert opinion.")

    # Gather opinions
    opinions = await asyncio.gather(
        Runner.run(expert1, question),
        Runner.run(expert2, question),
        Runner.run(expert3, question)
    )

    # Aggregator makes final decision
    aggregator = Agent(
        name="Aggregator",
        instructions="Synthesize multiple expert opinions into a final decision."
    )

    consensus_input = f"""
    Question: {question}

    Expert 1: {opinions[0].final_output}
    Expert 2: {opinions[1].final_output}
    Expert 3: {opinions[2].final_output}

    Provide final consensus decision.
    """

    result = await Runner.run(aggregator, consensus_input)
    return result.final_output
```

## Pattern Selection Guide

| Scenario | Recommended Pattern | Why |
|----------|-------------------|-----|
| Multiple independent tasks | Manager pattern | Parallel execution, result aggregation |
| Conversational routing | Peer handoff | Natural conversation flow, specialization |
| Pipeline/stages | Manager pattern | Sequential coordination |
| Expertise-based routing | Peer handoff | Decentralized domain expertise |
| Need result aggregation | Manager pattern | Central control over outputs |
| Context-aware routing | Either (use context) | Both support context passing |
| Escalation workflow | Multi-level handoff | Hierarchical specialization |
| Parallel analysis | Manager or parallel | Concurrent execution |
| Decision consensus | Custom (parallel + aggregation) | Multiple perspectives |

## Best Practices

1. **Choose the right pattern** - Manager for coordination, handoff for conversation
2. **Use context wisely** - Share state without exposing to LLM
3. **Clear handoff descriptions** - Help LLM decide when to hand off
4. **Limit handoff depth** - Avoid too many levels (2-3 max)
5. **Handle errors** - Use try/except for max_turns and guardrails
6. **Use sessions** - Share conversation history across agents
7. **Set max_turns** - Prevent infinite loops in complex workflows
8. **Monitor with tracing** - Essential for debugging multi-agent systems
