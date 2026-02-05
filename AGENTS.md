# AI Universal Suite - Agent Context

> **For Claude Code**: Use `CLAUDE.md` instead (auto-loaded with full context)

## Source of Truth

**The specification defines how this project should work. Your job is to align the codebase with it.**

Read these files in order:
1. `docs/spec/AI_UNIVERSAL_SUITE_SPEC_v3.md` - Complete technical specification
2. `docs/spec/HARDWARE_DETECTION.md` - GPU, CPU, Storage, RAM detection methods
3. `docs/spec/CUDA_PYTORCH_INSTALLATION.md` - PyTorch/CUDA installation logic
4. `docs/plans/PLAN_v3.md` - Decision log, task tracker, current phase (see Section 0 for gaps)
5. `data/models_database.yaml` - Model definitions with variants and hardware requirements

If code contradicts the spec, the spec is correct (unless the spec has an obvious error, in which case flag it).

---

## Project Identity

**AI Universal Suite** is a cross-platform desktop application that configures AI workstations through a guided wizard. It detects hardware, asks about user needs, and recommends optimal configurations of models, tools, and workflows.

**Core Principle:** Zero terminal interaction - every action achievable through GUI.

## Current Status (2026-02-04 Audit Review)

The project has transitioned to a **Hybrid Edge-Cloud Roadmap**. Recent audits identified critical vulnerabilities in GIL-locked concurrency and YAML-based data scaling.

### Target Architecture (Phase 1-3 Focus)
- **Data Layer**: Relational SQLite core (`data/models.db`) to replace legacy YAML.
- **Concurrency**: `ProcessPoolExecutor` for all heavy I/O and hashing.
- **Persistence**: Persistent installation and task queues.
- **Security**: Bearer Token (JWT) auth for local agent endpoints.

### Prioritized Task List (Top 5)
1. **DB-01**: YAML to SQLite Migration (Startup latency < 50ms)
2. **SYS-01**: Multiprocessing Download Handler (Fix UI freezes)
3. **SYS-05**: Dynamic Storage Headroom Calculation (OS stability)
4. **API-04**: Bearer Token Auth Implementation (Security hardening)
5. **PAT-01**: Extract Recommendation Orchestrator Facade (Decoupling)

See `docs/audits/2_4_26/Executive_Refactoring_Report_2026-02-04.md` for the full 20-item roadmap.

---

## File Structure

```
AI-Universal-Suite/
├── data/
│   ├── models_database.yaml     # Source of Truth
│   └── models.db                # Target Relational DB (DB-01)
├── docs/
│   ├── spec/AI_UNIVERSAL_SUITE_SPEC_v3.md
│   ├── plans/PLAN_v3.md
│   └── audits/2_4_26/           # 2026-02-04 Architectural Audits
├── src/
│   ├── schemas/hardware.py      # Normalized HardwareProfile
│   ├── services/
│   │   ├── hardware/            # Platform Strategies
│   │   └── recommendation/      # 3-Layer Logic (CSP->Content->TOPSIS)
│   └── main_api.py              # Local Agent Server (SYS-04)
```

---

## Locked Decisions

These decisions are documented in `docs/plans/PLAN_v3.md` and should not be relitigated:

| Area | Decision | Rationale |
|------|----------|-----------|
| Document structure | Single consolidated spec | One source of truth |
| Onboarding | Dual-path (Quick + Comprehensive) | Self-selected commitment levels |
| Model database | Separate YAML file | 100+ models would bloat spec |
| Cloud APIs | Partner Nodes primary | Unified credits, native to ComfyUI 0.3.60+ |
| Recommendation | 3-layer architecture | Research-validated approach |
| Content Layer | Modular modality architecture | Multi-modal use cases, single responsibility |
| Platform weights | 40% Mac, 40% Windows, 20% Linux | Target user distribution |

## Decision Workflow for Architecture Changes

**Before implementing any architecture/spec change**, follow this workflow:

1. **Document Decision** → Add to `PLAN_v3.md` Section 1 (Decision Log)
2. **Document Deprecations** → Add to `PLAN_v3.md` Section 7 (Deprecation Tracker)
3. **Update Spec** → Modify `AI_UNIVERSAL_SUITE_SPEC_v3.md`
4. **Update Plan** → Add tasks to `PLAN_v3.md` Section 2 (Task Tracker)
5. **Update Agent Files** → `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`
6. **Implement** → Follow Migration Protocol

This ensures all documentation stays in sync with code changes.

---

## Platform Constraints (SPEC Section 4 + HARDWARE_DETECTION.md)

These are non-negotiable technical constraints:

### Apple Silicon
- GGUF K-quants crash MPS - only Q4_0, Q5_0, Q8_0 allowed
- 75% memory ceiling for effective VRAM calculation
- HunyuanVideo excluded (~16 min/clip)
- AnimateDiff is primary video option
- Memory bandwidth affects LLM inference speed

### NVIDIA
- FP8 requires compute capability 8.9+ (RTX 40 series)
- FP4/FP6 requires compute capability 12.0+ (RTX 50 series)
- Must detect CUDA capability
- Form factor detection: sqrt(power_ratio) for laptop performance scaling

### AMD ROCm
- Mark as experimental in UI
- May need HSA_OVERRIDE_GFX_VERSION for RDNA2

### CPU
- Tier classification: HIGH (16+), MEDIUM (8-15), LOW (4-7), MINIMAL (<4) cores
- AVX2 required for GGUF CPU offload
- Affects offload viability and performance

### Storage
- Tiers: FAST (NVMe), MODERATE (SATA SSD), SLOW (HDD)
- Affects model load times and recommendation `speed_fit` criterion
- Space constraints trigger priority-based model fitting

---

## Development Conventions

1. **Strict Separation**: UI files must NEVER contain business logic
2. **Hardware Awareness**: All recommendations validated against hardware constraints
3. **Schemas not Models**: Use `src/schemas/` for dataclasses (avoid "models" confusion with AI models)
4. **Async UI**: Long-running tasks in background threads
5. **Type Hints**: Required on all function signatures
6. **Spec Citations**: Reference spec sections in commit messages and comments
7. **Commit Messages**: Never add co-author tags, AI tool attribution, or "Generated with" footers to commit messages unless explicitly requested by the user

---

## Virtual Environment

```powershell
# Windows
.dashboard_env\venv\Scripts\activate

# macOS/Linux  
source .dashboard_env/venv/bin/activate
```

---

## Your Workflow

1. **Read the spec** for the area you're working on
2. **Compare** spec requirements against current code
3. **Document** gaps you find
4. **Propose** fixes with spec section citations
5. **Implement** after confirming approach
6. **Verify** changes work and align with spec

---

## Communication Style

- Be direct and concise
- Criticism over compliments when reviewing code
- Ask clarifying questions before assuming intent
- Push back with better approaches rather than just executing
- Always cite spec sections when discussing requirements

---

## When Something Seems Wrong

1. Check if the spec addresses it (search the spec document)
2. Check `docs/plans/PLAN_v3.md` for decision history
3. Check `docs/archived/` for context on past iterations
4. If spec seems incorrect, flag it rather than silently diverging
