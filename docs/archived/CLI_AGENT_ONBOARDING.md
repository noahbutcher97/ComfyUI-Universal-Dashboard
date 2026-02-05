# AI Agent Onboarding Prompt

Use this prompt to onboard any AI coding agent (Claude CLI, Gemini CLI, Cursor, Aider, Copilot, etc.) to this project.

---

## Context Briefing

You're working on **AI Universal Suite**, a cross-platform desktop application that configures AI workstations through a guided wizard. The project has a comprehensive specification (SPEC_v3) that defines how everything should work, but the codebase was built during earlier iterations and needs to be aligned.

**Your job is to understand the gap between spec and implementation, then fix it.**

**Project Location**: This directory (or set your working directory to the project root)

---

## Phase 1: Build Your Own Understanding

Before making any changes, you need to understand what the spec requires vs what exists. Don't trust summaries - verify yourself.

### Step 1: Read the Specification

Read the complete technical specification. This is your source of truth.

**File:** `docs/spec/AI_UNIVERSAL_SUITE_SPEC_v3.md`

Pay special attention to:
- Section 4: Hardware Detection & Platform Support
- Section 5: Onboarding System (dual-path design)
- Section 6: Three-Layer Recommendation Engine
- Section 7: Model Database Schema
- Section 13: Project Structure

Take notes on:
1. What architecture does the spec define for the recommendation engine?
2. How should hardware detection work per-platform?
3. What is the onboarding flow supposed to look like?
4. Where should model data come from?

### Step 2: Read the Implementation Plan

**File:** `docs/plans/PLAN_v3.md`

Note:
1. What phase are we in?
2. What decisions have been made and locked?
3. What are the Phase 1 tasks?

### Step 3: Examine the Existing Codebase

Now compare what the spec says against what actually exists.

**Check the recommendation architecture:**

SPEC says: 3-layer (CSP → Content-Based → TOPSIS)

Examine these files:
- `src/services/scoring_service.py`
- `src/services/recommendation_service.py`

Check if these files exist:
- `src/services/constraint_layer.py`
- `src/services/content_layer.py`
- `src/services/topsis_layer.py`

**Check hardware detection:**

SPEC Section 4.2 says: Platform-specific detectors with proper Apple Silicon handling

Examine: `src/services/system_service.py`

Look for:
- How is Apple Silicon RAM detected?
- Is there a hardcoded fallback value?
- Are platform-specific constraints enforced?

**Check model data source:**

SPEC says: `data/models_database.yaml` is source of truth

Check what the code actually uses:
- Search for "resources.json" in `src/services/`
- Search for "models_database" in `src/services/`
- Compare schemas between `data/models_database.yaml` and `src/config/resources.json`

**Check the onboarding flow:**

SPEC Section 5 says: Dual-path (Quick 5 questions / Comprehensive 15-20 tiered)

Examine: `src/ui/wizard/setup_wizard.py`

What flow does it actually implement?

### Step 4: Document Your Findings

Create a file called `AUDIT_FINDINGS.md` in the project root with your comparison:

```markdown
# Spec vs Implementation Comparison

## Recommendation Engine

**SPEC_v3 Section 6 requires:**
- Layer 1: Constraint Satisfaction Programming (binary elimination)
- Layer 2: Content-Based Filtering (cosine similarity on 5 factors)
- Layer 3: TOPSIS Multi-Criteria Ranking (closeness coefficients)

**Current implementation:**
[YOUR FINDINGS - what does scoring_service.py actually do?]

**Gap:**
[YOUR ANALYSIS]

---

## Hardware Detection

**SPEC_v3 Section 4 requires:**
- Platform-specific detector classes
- Apple Silicon: sysctl for RAM, 75% memory ceiling, filter K-quants
- NVIDIA: CUDA compute capability detection for FP8 support
- AMD: ROCm detection

**Current implementation:**
[YOUR FINDINGS - what does system_service.py do?]

**Gap:**
[YOUR ANALYSIS - is there a hardcoded fallback? Missing detectors?]

---

## Model Data Source

**SPEC_v3 Section 7 requires:**
- models_database.yaml as single source of truth
- Schema with variants, platform_support, capabilities

**Current implementation:**
[YOUR FINDINGS - where does recommendation_service.py get model data?]

**Gap:**
[YOUR ANALYSIS]

---

## Onboarding Flow

**SPEC_v3 Section 5 requires:**
- Dual-path: Quick (5 questions) OR Comprehensive (15-20 tiered)
- Path selection screen
- Hardware auto-detection (zero hardware questions)
- 5 aggregated user factors

**Current implementation:**
[YOUR FINDINGS - what flow does setup_wizard.py implement?]

**Gap:**
[YOUR ANALYSIS]

---

## Priority Issues

Based on my analysis, these are the critical gaps (ranked):

1. [YOUR #1 PRIORITY]
2. [YOUR #2 PRIORITY]
3. [YOUR #3 PRIORITY]
```

---

## Phase 2: Verify Specific Flagged Issues

A prior audit flagged these specific concerns. Verify whether they're actually problems:

### Issue 1: Apple Silicon RAM Fallback

**Concern:** If sysctl fails, code may fall back to hardcoded 16GB, breaking recommendations for 8GB machines (over-recommends) and 128GB machines (under-recommends).

**Verify:** Search `src/services/system_service.py` for "16.0" or "Fallback"

Is this actually a problem? What happens if detection fails?

### Issue 2: Wrong Recommendation Architecture

**Concern:** Code uses single-pass weighted scoring instead of 3-layer architecture.

**Verify:** In `src/services/scoring_service.py`, look for how the composite score is calculated. Does it match SPEC_v3 Section 6?

### Issue 3: Model Source Mismatch

**Concern:** Code reads from `resources.json` instead of `models_database.yaml`.

**Verify:** In `src/services/recommendation_service.py`, trace where model candidates come from.

---

## Phase 3: Plan Your Fixes

Based on YOUR analysis (not assumptions), add to your `AUDIT_FINDINGS.md`:

```markdown
---

## Fix Plan

### Immediate (Critical Path Blockers)

1. **[Issue]**: [Description]
   - File: [path]
   - Current: [what it does]
   - Required: [what spec says]
   - Fix approach: [how to fix]

### Phase 1 Week 1 (Platform Detection)

[List tasks based on your analysis]

### Phase 1 Week 2 (Services)

[List tasks based on your analysis]
```

---

## Phase 4: Implement Fixes

Only after you understand WHY something is wrong should you fix it.

### Fix Template

For each fix:
1. State what the spec requires (cite section number)
2. Show what the current code does
3. Explain why that's wrong
4. Implement the fix
5. Verify it works

Example format:
```
## Fixing [Component Name]

**SPEC_v3 Section X.X requires:**
> [Quote or paraphrase the requirement]

**Current code ([filename]:[line]):**
[Show the problematic code]

**Why this is wrong:**
[Explain the impact]

**Fix:**
[Your implementation]

**Verification:**
[How you tested it]
```

---

## Key Constraints (Reference)

These are locked decisions from the spec - don't try to change them:

| Decision | Choice | Spec Section |
|----------|--------|--------------|
| Recommendation architecture | 3-layer (CSP→Content→TOPSIS) | Section 6 |
| Onboarding | Dual-path (Quick/Comprehensive) | Section 5 |
| Model source | models_database.yaml | Section 7 |
| Platform weights | 40% Mac, 40% Windows, 20% Linux | Section 4 |
| Apple Silicon GGUF | Non-K quants only (Q4_0, Q5_0, Q8_0) | Section 4.2 |
| Apple Silicon ceiling | 75% of unified memory | Section 4.2 |

---

## Project Conventions

1. **Strict Separation**: UI files must NEVER contain business logic
2. **Type Hints**: Required on all function signatures
3. **Spec Citations**: Reference spec sections in commits and comments
4. **Virtual Environment**: Use `.dashboard_env/venv/` for Python

### Activating the Environment

**Windows (PowerShell/CMD):**
```
.dashboard_env\venv\Scripts\activate
```

**macOS/Linux (Bash/Zsh):**
```
source .dashboard_env/venv/bin/activate
```

---

## Communication Style

When working on this project:
- Be direct and concise
- Criticism over compliments when reviewing code
- Ask clarifying questions before assuming intent
- Push back with better approaches rather than just executing
- Always cite spec sections when discussing requirements

---

## Files to Update When Done

After completing your analysis and fixes:

1. Update `CLAUDE.md` or `GEMINI.md` if you discover new context
2. Commit with messages referencing spec sections:
   - `fix(hardware): Apple Silicon RAM detection per SPEC_v3 4.2`
   - `refactor(recommendation): implement Layer 1 CSP per SPEC_v3 6.2`

---

## Getting Help

If something in the spec is unclear or seems wrong:
1. Check `docs/archived/` for historical context
2. Check `docs/plans/PLAN_v3.md` decision log for rationale
3. Flag the issue rather than assuming or silently diverging
