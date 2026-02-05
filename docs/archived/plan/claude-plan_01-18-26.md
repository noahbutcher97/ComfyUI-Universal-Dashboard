# AI Universal Suite - Planning Document

This document tracks the evolution of planning for this project.

---

# CURRENT: Application Architecture & Wizard Redesign (v2)

**Status:** In Planning
**Created:** 2026-01-18

## Problem Statement

The current wizard was designed for a narrow scope (ComfyUI + CLI setup). The application's vision is much broader:

**What we're building:** An adaptive AI workstation that helps users of ANY level work in their field using AI, without falling prey to predatory subscriptions, ineffective techniques, or unrealistic setups.

**Core principles:**
- Educate without forcing - adapt instruction level to user desire
- Protect users - safety net for quick decisions, guardrails for bad ones
- Personalize - what's possible FOR THEM, not just in general
- Don't assume - offer wide options without overwhelming
- Expandable - current scope is not the upper limit

---

## MVP Scope Decision: Generation Focus ✅

**Decision:** Generation Focus MVP
**Date:** 2026-01-18

### Rationale

1. **Backend is ready, UI is the bottleneck** - `generate_parallel_recommendations()`, `CloudRecommendationLayer`, and 225-model database are implemented and tested. The wizard just never calls them.

2. **Minimal Fix won't work** - Current wizard displays module recommendations (ComfyUI, CLI Provider) in a step-by-step flow. Model recommendations are a different data shape. Patching would break UX.

3. **Full Dual-Track risks scope creep** - Dashboard states for CLI-only users, unified CLI interface design, etc. are undefined. These require substantial design decisions.

4. **Generation Focus validates core value** - The unique value prop is "personalized model recommendations with comparison lenses based on YOUR hardware and preferences." Generation is where this shines.

### MVP Capability Scope

| Category | In MVP | Notes |
|----------|--------|-------|
| **Generation** | ✅ Full | ComfyUI + 142 local models + 83 cloud APIs, comparison lenses |
| **Development** | ⚠️ Basic | CLI provider selection (gemini/claude), no unified interface |
| **Workflow** | ⚠️ Partial | ComfyUI setup only, no workflow generation |
| **Learning** | ❌ Future | Not in MVP |
| **Optimization** | ❌ Future | Not in MVP |

### Deferred Questions (Post-MVP)

1. **Dashboard for CLI-only users** - Defer until we see usage patterns
2. **Unified CLI Interface** - Defer, keep current separate providers
3. **Workflow generation / prompt optimization** - Future scope

---

## Phase 1: Generation Focus MVP Implementation

### New Wizard Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: Welcome + Journey Selection                           │
├─────────────────────────────────────────────────────────────────┤
│  [Express Setup]              [Explore First]                   │
│  Guided decisions              Browse capabilities              │
└─────────────────────────────────────────────────────────────────┘
                │                        │
                ▼                        ▼
┌───────────────────────────────────────────────────────────────────┐
│  STAGE 2: Experience Survey (unchanged)                           │
│  - AI experience (1-5)                                            │
│  - Technical experience (1-5)                                     │
│  - Cloud willingness (4 options)                                  │
│  - Cost sensitivity (1-5)                                         │
└───────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│  STAGE 3: Hardware Scan (unchanged but with better feedback)      │
│  Shows: GPU, VRAM, CPU tier, Storage space                        │
│  NEW: Hardware-based capability preview                           │
└───────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│  STAGE 4: Capability Selection (REPLACES use-case cards)          │
│  "What do you want to create?"                                    │
│  ☑ Images    ☑ Video    ☐ Audio    ☐ Text                        │
│  Shows available modalities based on hardware/cloud prefs         │
└───────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│  STAGE 5: Model Selection (NEW - replaces module config)          │
│  Comparison lenses: [Quality] [Speed] [Cost] [Size]               │
│  Split view: LOCAL | CLOUD (based on cloud_willingness)           │
│  Each model card shows: name, size, capabilities, warnings        │
│  Progressive reveal: "Tell me more" expands details               │
└───────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│  STAGE 6: CLI Provider Selection (existing, simplified)           │
│  Quick selection: Gemini / Claude / Both / Skip                   │
└───────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│  STAGE 7: Review & Install (similar to current)                   │
│  Shows: Selected models, estimated download size, time            │
│  Progress panel with per-item tracking                            │
└───────────────────────────────────────────────────────────────────┘
```

### Critical Files to Modify

| File | Changes |
|------|---------|
| `src/ui/wizard/setup_wizard.py` | Replace stage flow, call `generate_parallel_recommendations()` |
| `src/ui/wizard/components/` | Add new components: `capability_selector.py`, `model_comparison.py`, `model_card.py` |
| `src/services/setup_wizard_service.py` | Wire to `RecommendationResults` instead of `List[ModuleRecommendation]` |
| `src/services/recommendation_service.py` | Already has `generate_parallel_recommendations()` - ensure it's production-ready |

### Implementation Steps

#### Step 1: Capability Selector Component
Create `src/ui/wizard/components/capability_selector.py`:
- Checkbox grid for modalities (image, video, audio, text)
- Grey out unavailable modalities based on hardware profile
- "Why is this unavailable?" tooltip with hardware explanation

#### Step 2: Model Comparison View Component
Create `src/ui/wizard/components/model_comparison.py`:
- Tab bar with comparison lenses (Quality, Speed, Cost, Size)
- Split view for Local vs Cloud (controlled by cloud_willingness)
- Sorting and filtering based on active lens

#### Step 3: Model Card Component
Create `src/ui/wizard/components/model_card.py`:
- Compact view: name, size badge, capability icons, "Recommended" badge
- Expanded view: full description, hardware requirements, warnings
- Selection checkbox with quantity selector for variants

#### Step 4: Wire Wizard to New Backend
Modify `src/ui/wizard/setup_wizard.py`:
- Remove `show_welcome_stage()` use-case cards → replace with capability selector
- Remove `show_next_module()` module loop → replace with model comparison view
- Call `generate_parallel_recommendations()` instead of `generate_recommendations()`
- Pass selected modalities to recommendation engine

#### Step 5: Update SetupWizardService
Modify `src/services/setup_wizard_service.py`:
- Change `recommendations` type from `List[ModuleRecommendation]` to `RecommendationResults`
- Update `generate_manifest()` to handle `LocalRankedCandidate` / `CloudRankedCandidate`
- Add cloud API setup to manifest (API key configuration, not just downloads)

### Verification Plan

1. **Unit tests**: Ensure `generate_parallel_recommendations()` returns expected structure for all `cloud_willingness` values
2. **Integration test**: Run wizard end-to-end with different hardware profiles (mock NVIDIA, Apple Silicon, low VRAM)
3. **Manual test matrix**:
   - `local_only` user with 8GB VRAM → should see quantized local models only
   - `cloud_fallback` user with 24GB VRAM → should see local first, cloud as fallback
   - `cloud_preferred` user → should see cloud first, local as option
   - `cloud_only` user → should see NO local models, only cloud APIs
4. **Comparison lens test**: Verify sorting changes when switching lenses

---

## Design Principles (From User Feedback)

### 1. Tiered Autonomy
- **Quick Path:** Curated safe choices, minimal decisions
- **Advanced Mode:** Full control with consequences explained
- Progressive reveal enables transition between modes

### 2. Adaptive Learning
- Progressive reveal (start simple, expand on demand)
- Contextual sidebars that expand both information AND control
- Allow users with preexisting knowledge to inject that into recommendations

### 3. Multiple Comparison Lenses
Users can explore comparisons through different filters:
- Cost vs Quality vs Speed
- Local vs Cloud vs Hybrid
- Use-case groupings (what can I make?)
All filters are sensitive to user profile from survey

### 4. Context-Sensitive Presentation
- Local workflow users → capabilities matter most
- Cloud-only users → cost/reliability matter most
- Low cost sensitivity → quality/speed matter most
- Recommendations are nuanced: what you have vs what you want vs happy medium

### 5. Asynchronous Exploration + Express Install
- Allow exploration mode (learn what's possible before committing)
- Also provide express installation (guided conversation with button selections)
- Helps rigid users relax assumptions through optional curiosity

---

## Wizard Architecture (High Level Concept)

### Journey Model: Asynchronous + Express Hybrid

```
┌─────────────────────────────────────────────────────────────────┐
│                     ENTRY POINT                                  │
├─────────────────────────────────────────────────────────────────┤
│  "How would you like to set up your AI workstation?"            │
│                                                                 │
│  [Express Setup]              [Explore First]                   │
│  "Guide me through            "Let me browse what's             │
│   quick decisions"             possible first"                   │
└─────────────────────────────────────────────────────────────────┘
                │                        │
                ▼                        ▼
        ┌───────────────┐      ┌─────────────────────┐
        │ GUIDED FLOW   │      │ EXPLORATION HUB     │
        │ (Conversation)│      │ (Hub & Spoke)       │
        └───────────────┘      └─────────────────────┘
                │                        │
                ▼                        ▼
        ┌───────────────────────────────────────────┐
        │         CAPABILITY SELECTION              │
        │  (Same destination, different journey)    │
        └───────────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────────┐
        │         MODEL/TOOL SELECTION              │
        │  (Comparison lenses available)            │
        └───────────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────────┐
        │         CONFIGURATION & INSTALL           │
        └───────────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────────┐
        │         POST-INSTALL DASHBOARD            │
        │  (Adapts to what was installed)           │
        └───────────────────────────────────────────┘
```

---

## Decision Log (v2)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-18 | Define capability map before wizard | Can't design wizard without knowing what it configures |
| 2026-01-18 | Tiered autonomy (quick vs advanced) | Respect user time while enabling power users |
| 2026-01-18 | Multiple comparison lenses | Different users prioritize different tradeoffs |
| 2026-01-18 | Progressive reveal + contextual sidebars | Adapt to learning preference without forcing |
| 2026-01-18 | Asynchronous exploration + express install | Some users want to learn first, others want speed |
| 2026-01-18 | Preserve old plan for version tracking | User requested deprecation instead of overwrite |
| 2026-01-18 | **MVP Scope: Generation Focus** | Backend ready, validates core value prop, reduces scope creep risk |

---
---
---

# DEPRECATED: Cloud API Integration Plan (v1)

**Status:** Deprecated (superseded by v2 above)
**Created:** 2026-01-15
**Completed Phases:** 1 (Schema & Survey), 2 (Recommendation Logic)
**Reason for Deprecation:** Scope expanded beyond just cloud integration to full wizard redesign

## Original Problem Statement

The recommendation system currently assumes users want to download models locally, factoring in hardware constraints as primary decision criteria. However, many users:
- Don't want to troubleshoot local setups
- Prefer quick, reliable cloud-based workflows
- Are willing to pay per-usage (which can be cheaper than subscriptions)
- Want guidance on cloud APIs, not just downloads

The recent two-tier database restructure (142 local + 83 cloud models) created the foundation, but the recommendation engine doesn't leverage it yet.

---

## Locked Decisions (v1) ✅

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Question Count** | 2 questions | Keeps it simple for non-technical users |
| **Timing** | Upfront in survey | Shapes all recommendations from the start |
| **Cloud Options** | 4 options | Include "Cloud Only" for users who don't want any downloads |
| **Scoring Approach** | Hybrid criteria | Shared content criteria + cloud-specific (cost, reliability, limits, latency) |
| **Storage Interaction** | Boost + Warnings | Boost cloud scores when storage tight + show warnings on large local models |
| **Cost Sensitivity** | Weight + Soft Filter | Primary: adjust weights. Secondary: suggest alternatives. Tertiary: soft filter expensive |

---

## Implementation Status (v1)

### Phase 1: Schema & Survey Foundation ✅ COMPLETE
- Added `CloudAPIPreferences` dataclass to `src/schemas/recommendation.py`
- Added survey questions to `src/ui/wizard/components/experience_survey.py`
- Wired to `UserProfile.cloud_api_preferences`

### Phase 2: Recommendation Logic ✅ COMPLETE
- Created `CloudRecommendationLayer` at `src/services/recommendation/cloud_layer.py`
- Added `generate_parallel_recommendations()` to `src/services/recommendation_service.py`
- Added `CloudRankedCandidate`, `RecommendationResults` schemas

### Phase 3: Explainer & Display ❌ NOT STARTED
- Was going to add cloud-specific explanations
- Superseded by broader wizard redesign

### Phase 4: Resolution Cascade Integration ❌ NOT STARTED
### Phase 5: Cloud Infrastructure ❌ NOT STARTED

---

## What Was Built (Reusable in v2)

| Component | Location | Can Reuse |
|-----------|----------|-----------|
| `CloudAPIPreferences` schema | `src/schemas/recommendation.py` | Yes |
| `CloudRankedCandidate` schema | `src/schemas/recommendation.py` | Yes |
| `RecommendationResults` schema | `src/schemas/recommendation.py` | Yes |
| `CloudRecommendationLayer` | `src/services/recommendation/cloud_layer.py` | Yes |
| `generate_parallel_recommendations()` | `src/services/recommendation_service.py` | Yes |
| Cloud preference survey questions | `src/ui/wizard/components/experience_survey.py` | Yes |

**Key insight:** The backend is ready. The wizard UI just needs to call `generate_parallel_recommendations()` instead of `generate_recommendations()`.

---

## Original Phase Details (For Reference)

<details>
<summary>Click to expand full original plan details</summary>

### The Two Questions

#### Question 1: Cloud API Willingness
**Type:** 4-choice selector (segmented control)
**Prompt:** "How would you like to run AI models?"

| Option | Value | Description |
|--------|-------|-------------|
| **Local Only** | `local_only` | "I'll download and run everything on my hardware" |
| **Open to Both** | `cloud_fallback` | "Prefer local, but show me cloud options if my hardware can't handle it" (DEFAULT) |
| **Prefer Cloud** | `cloud_preferred` | "Prefer cloud APIs, but show me local options if I want to tinker" |
| **Cloud Only** | `cloud_only` | "No downloads - I'll use cloud APIs exclusively" |

#### Question 2: Cost Sensitivity
**Type:** 1-5 slider with labels
**Prompt:** "How important is keeping costs low?"

### Hybrid Scoring Criteria

| Criterion | Type | Weight (cost_sens=1) | Weight (cost_sens=5) |
|-----------|------|----------------------|----------------------|
| content_similarity | Shared | 0.25 | 0.20 |
| style_fit | Shared | 0.15 | 0.10 |
| approach_fit | Shared | 0.10 | 0.05 |
| ecosystem_maturity | Shared | 0.10 | 0.05 |
| cost_efficiency | Cloud | 0.05 | 0.30 |
| provider_reliability | Cloud | 0.15 | 0.15 |
| rate_limits | Cloud | 0.10 | 0.05 |
| latency | Cloud | 0.10 | 0.10 |

### Pathway Selection by cloud_willingness

| Willingness | What User Sees | Hardware Detection |
|-------------|----------------|-------------------|
| `local_only` | Only local pathway results | Full detection |
| `cloud_fallback` | Local results first, cloud as "Also available" section | Full detection |
| `cloud_preferred` | Cloud results first, local as "If you prefer local" section | Full detection |
| `cloud_only` | Only cloud pathway results, no local models | Minimal (storage + RAM only) |

</details>
