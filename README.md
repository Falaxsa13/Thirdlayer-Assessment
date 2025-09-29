# Browser Workflow Generation System

A system that captures browser interactions from a Chrome extension and automatically generates reusable, generalized workflows using Large Language Models (LLMs).

## 🏗️ Architecture Overview

The system follows a **hierarchical processing pipeline** that transforms raw browser events into meaningful, reusable workflows:

```
Browser Events → Page Sessions → Multi-Page Segments → Workflows → Validation → Deduplication → JSON Export
```

### Core Design Philosophy

1. **Multi-Page Workflow Processing**: Group related page sessions into coherent multi-page workflows
2. **Hierarchical Segmentation**: Events → Page Sessions → Page Segments → Workflows (three-tier processing)
3. **Token-Optimized LLM Integration**: Category-based tool loading reduces context size by 85%+
4. **Conservative Tool Usage**: Strict constraints prevent unnecessary automation suggestions for casual browsing
5. **JSON File Storage**: Database-free workflow persistence with individual JSON files
6. **Semantic Deduplication**: LLM-based comparison against existing workflows using purpose over text similarity

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/
│   │   └── events.py                 # Main API endpoint (/api/interactions)
│   ├── core/
│   │   └── config.py                 # Environment configuration
│   ├── schemas/                      # Pydantic data models
│   │   ├── browser_events.py         # Event data structures (simplified payload)
│   │   ├── page_sessions.py          # PageSession & PageSegment (multi-page workflows)
│   │   ├── workflows.py              # Workflow schemas with strict step types
│   │   ├── tools.py                  # Simplified tool definitions (name, label, description)
│   │   └── events.py                 # API request/response schemas
│   └── services/                     # Core business logic
│       ├── workflow_processor.py     # Main orchestration service
│       ├── segmentation/
│       │   ├── event_segmentation.py # Hierarchical segmentation
│       │   ├── page_service.py       # Page session creation
│       │   └── intent_classification_service.py # LLM intent analysis
│       ├── generalization_service.py # LLM workflow generation
│       ├── workflow_validator.py     # Validation and constraints
│       ├── workflow_deduplicator.py  # LLM-based deduplication
│       ├── workflow_exporter.py      # JSON file export
│       ├── tool_loader.py            # Dynamic tool loading
│       └── utils.py                  # Prompt management utilities
├── prompts/                          # LLM prompt templates
│   ├── intent_classification.txt     # Intent classification prompt
│   ├── workflow_generation.txt       # Workflow generation prompt
│   └── workflow_deduplication.txt    # Deduplication prompt
├── tools-dump/                       # Tool definitions (15 services, 237+ tools)
│   ├── gmail.txt, hubspot.txt, etc. # JSON-formatted tool definitions
└── workflows/                        # Generated workflow JSON files
    └── *.json                        # Individual workflow files
```

### 2. Hierarchical Segmentation (`EventSegmentationService`)

**Step 2.1: Page Session Creation (`PageService`)**

- Groups events by page (URL + tab)
- Applies lightweight denoising (removes rapid clicks, focus/blur noise)
- Creates `PageSession` objects with content summaries and metadata
- Extracts activities without hardcoded summarization (LLM handles analysis)

**Step 2.2: Multi-Page Workflow Boundary Detection**

- Detects breakpoints between page sessions based on:
  - Domain changes (different websites)
  - Large time gaps (>2 minutes of inactivity)
  - Tab switches (different browser tabs)
- Groups related page sessions into `PageSegment` objects (multi-page workflows)
- Allows workflows to span multiple pages for coherent automation patterns

**Step 2.3: Intent Classification (`IntentClassificationService`)**

- Uses LLM (`gpt-5-mini-2025-08-07`) to classify segment intent
- Returns intent type + relevant tool categories for optimization
- Categories: product_search, checkout_process, email_composition, form_filling, etc.
- Filters out "unknown" intents to focus on automatable workflows

### 3. Multi-Page Workflow Generation (`GeneralizationService`)

**Token-Optimized Tool Loading:**

- Loads only tools from categories identified by intent classifier (85%+ token reduction)
- `tool_loader.load_tools_by_categories(segment.tool_categories)` filters 237 tools to ~10-30 relevant ones
- Passes only tool names to LLM (not descriptions) to prevent hallucinated tool descriptions

**Multi-Page Context Processing:**

- Processes entire `PageSegment` (multiple related pages) in single LLM call
- Extracts content from all pages with smart truncation (300 chars/page)
- Combines user actions across pages for comprehensive workflow understanding

**LLM Workflow Creation:**

- Uses `gpt-5-mini-2025-08-07` with strict constraints and conservative tool usage
- Generates workflows that span multiple pages with coherent automation patterns
- Enforces step types: only "browser_context" or "tool" allowed
- Prevents tool suggestions for casual browsing activities

### 4. Validation (`WorkflowValidator`)

**Constraint Enforcement:**

- Tool availability validation (all tools must exist)
- URL pattern specificity (prevents overly broad patterns like `*://*/*`)
- Step structure validation (minimum 2 steps, first step must be browser_context)
- Step type validation (only "browser_context" or "tool" allowed)

### 5. Deduplication (`WorkflowDeduplicator`)

**Efficient JSON File-Based Deduplication:**

- Reads existing workflows from `workflows/*.json` files (no database dependency)
- Groups by domain and sorts by modification time for efficient comparison
- Uses batch LLM analysis to compare new workflows against existing ones (limit: 100 per domain)
- Similarity threshold: 0.7 (configurable) for semantic similarity detection

### 6. Export (`WorkflowExporter`)

**Simplified JSON File Storage:**

- Creates individual JSON files in single `workflows/` folder
- Each file contains complete workflow with metadata, steps, and analysis
- Naming convention: `01_Workflow_Summary_Title.json`, `02_Another_Workflow.json`
- No additional summary or metadata files - just individual workflow JSONs
- Database-free persistence enables easy inspection and portability

## 🧠 LLM Integration & Prompting Strategy

### Three Specialized LLM Calls

1. **Intent Classification** (`gpt-5-mini-2025-08-07`)

   - **Purpose**: Classify multi-page segment intent and select relevant tool categories
   - **Input**: Combined page content + user actions across all pages in segment
   - **Output**: Intent type (product_search, checkout_process, etc.) + tool categories list
   - **Token Optimization**: Returns only category names for 85%+ context reduction

2. **Multi-Page Workflow Generation** (`gpt-5-mini-2025-08-07`)

   - **Purpose**: Generate coherent workflow from multi-page segment
   - **Input**: `PageSegment` with multiple related pages + category-filtered tools
   - **Output**: Structured workflow JSON spanning multiple pages
   - **Key Feature**: Single LLM call processes entire multi-page sequence
   - **Constraints**: Conservative tool usage, no tools for casual browsing, specific URL patterns

3. **Batch Workflow Deduplication** (`gpt-5-mini-2025-08-07`)
   - **Purpose**: Compare new workflows against existing JSON files
   - **Input**: New workflows + existing workflows from `workflows/*.json` (up to 100 per domain)
   - **Output**: Groupings of semantically similar workflows
   - **Efficiency**: Batch processing, domain filtering, modification time sorting

## 📊 Key Design Decisions & Rationale

### ✅ What Worked Well

#### 1. **Multi-Page Hierarchical Segmentation**

- **Decision**: Process events → page sessions → page segments → workflows (three-tier approach)
- **Rationale**: Multi-page segments capture complete user journeys (e.g., search → product → cart)
- **Result**: Coherent workflows spanning multiple pages with single LLM call, reduced fragmentation

#### 2. **Category-Based Tool Loading**

- **Decision**: Intent classification → tool category selection → filtered tool loading
- **Rationale**: Reduces LLM context from 237 tools to ~10-30 relevant tools per workflow
- **Result**: 85%+ token reduction, faster processing, maintained accuracy

#### 3. **Conservative Tool Usage**

- **Decision**: Strict constraints against suggesting tools for casual browsing
- **Rationale**: Prevents unnecessary CRM calls for simple navigation
- **Result**: More realistic and useful workflow suggestions

#### 4. **JSON File Storage**

- **Decision**: Store workflows as individual JSON files instead of database
- **Rationale**: Simplifies deployment, enables easy inspection, reduces dependencies
- **Result**: Clean, portable workflow storage with no database overhead

#### 5. **Modular Service Architecture**

- **Decision**: Single-responsibility services with clear interfaces
- **Rationale**: Enables independent testing, modification, and scaling
- **Result**: Maintainable codebase with clean separation of concerns

### ❌ What Didn't Work Initially

#### 1. **Single-Page Workflow Limitation**

- **Problem**: Single-page workflows missed complete user journeys and automation opportunities
- **Solution**: Implemented multi-page segments that group related page sessions
- **Learning**: Users' workflows naturally span multiple pages (search → product → checkout)
- **Result**: More meaningful, actionable workflows with better automation potential

#### 2. **Rule-Based Deduplication**

- **Problem**: Text similarity failed to detect semantically identical workflows
- **Solution**: Replaced with LLM-based semantic comparison
- **Learning**: Domain-specific similarity requires semantic understanding
- **Future Work**: Embbed workflows into a vector table and conduct similarity search

#### 3. **Tool Hallucination and Over-Suggestion**

- **Problem**: LLM suggested non-existent tools and CRM tools for casual browsing
- **Solution**: Pass only tool names (not descriptions), added strict constraints against casual browsing automation
- **Learning**: LLMs need explicit tool boundaries and conservative automation principles
- **Result**: More realistic tool suggestions, reduced false positives

### Optimization Strategies Implemented

1. **Category-Based Tool Loading**: 85%+ reduction in LLM context (237 tools → ~10-30 relevant)
2. **Multi-Page Processing**: Single LLM call per segment instead of per page
3. **JSON File Deduplication**: Efficient comparison against existing workflows with domain filtering
4. **Content Truncation**: Smart 300 chars/page limit for large segments
5. **Tool Name-Only Context**: Prevents LLM tool hallucination by excluding descriptions
6. **Batch Processing**: Up to 100 existing workflows per domain for efficient comparison
