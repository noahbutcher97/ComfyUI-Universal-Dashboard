# GEMINI.md

This file provides guidance to Gemini CLI when working with code in this repository.

## Commands

```bash
# Activate virtual environment
# Windows:
.dashboard_env\venv\Scripts\activate
# macOS/Linux:
source .dashboard_env/venv/bin/activate

# Run the application
python src/main.py

# First-time setup (auto-creates venv, installs deps, launches)
python launch.py
```

## Source of Truth

- **Specification**: `docs/spec/AI_UNIVERSAL_SUITE_SPEC_v3.md` - Architecture, algorithms, schemas
- **Hardware Detection**: `docs/spec/HARDWARE_DETECTION.md` - GPU, CPU, Storage, RAM detection
- **CUDA/PyTorch**: `docs/spec/CUDA_PYTORCH_INSTALLATION.md` - PyTorch installation logic
- **Task Tracker**: `docs/plans/PLAN_v3.md` - Current phase, decisions, gaps
- **Model Database**: `data/models_database.yaml` - 100+ model definitions

**If code contradicts the spec, the spec is correct.**

## Project Overview

**AI Universal Suite** is a cross-platform desktop app that configures AI workstations through a guided wizard.

Core principle: **Zero terminal interaction** - every action achievable through GUI.

Tech stack: Python 3.10+, CustomTkinter, Service-Oriented Architecture

## Current Gaps (Code vs Spec)

| Area | Current Code | Spec Requires | Files to Fix |
|------|--------------|---------------|--------------|
| Data Layer | Flat YAML (14k lines) | Relational SQLite (DB-01) | `model_database.py` |
| Concurrency | Threading (GIL Block) | Multiprocessing (SYS-01) | `download_service.py` |
| Resiliency | In-memory Queue | Persistent SQLite Queue (SYS-02) | `download_service.py` |
| Orchestration | "God Class" Service | Facade Pattern (PAT-01) | `recommendation_service.py` |
| Security | No local API auth | Bearer Token JWT (API-04) | `auth_service.py` |
| Storage | Static 50GB Check | Dynamic Headroom (SYS-05) | `system_service.py` |

## Architecture

### 1. Three-Layer Recommendation Engine [STABLE/STUBS]
*Current state: Files exist as functional stubs; integration into Orchestrator is pending.*
- **Layer 1: CSP** (Binary Rejection) - `constraint_layer.py` [STUB]
- **Layer 2: Content** (Modular Modality Scorer) - `content_layer.py` [FUNCTIONAL]
- **Layer 3: TOPSIS** (Multi-Criteria Ranking) - `topsis_layer.py` [STUB]

### 2. Target Architecture (2026-02-04 Audit Roadmap)
*These components are the primary focus of Phase 1-3 refactoring.*
- **Orchestration**: `RecommendationOrchestrator` Facade (PAT-01) - *To replace "God Class" Service*
- **Local Server**: FastAPI Desktop Agent for Mobile Sync (SYS-04)
- **Persistence**: SQLite-backed installation and task tracking (DB-03, SYS-02)
- **Performance**: Multiprocess file operations (SYS-01) - *Migration from Threads*

### Hardware → Recommendation Integration

| Hardware Element | Layer 1 | Layer 3 | Resolution | Warnings |
|------------------|---------|---------|------------|----------|
| VRAM | `_check_vram_constraint` | `hardware_fit` | Quantization | - |
| CPU Tier | `_can_offload_to_cpu` | - | `_try_cpu_offload` | Offload active |
| CPU AVX2 | GGUF offload check | - | - | Performance warning |
| Storage Space | `_check_storage_constraint` | - | `adjust_for_space` | - |
| Storage Speed | - | `speed_fit` | - | Speed warning |
| Form Factor | - | `hardware_fit` penalty | - | Laptop warning |
| RAM for Offload | Offload viability | - | CPU offload | Low RAM warning |
| Memory Bandwidth | - | LLM tok/s estimate | - | - |

### File Structure

```
src/
├── config/
│   ├── manager.py              # Config read/write
│   └── resources.json          # Legacy - migrate to models_database.yaml
├── schemas/
│   ├── environment.py          # EnvironmentReport dataclass
│   ├── recommendation.py       # UserProfile, candidates, results
│   └── installation.py         # InstallationManifest, items
├── services/
│   ├── system_service.py       # Hardware detection (HAS BUGS)
│   ├── scoring_service.py      # Old architecture (REPLACE)
│   ├── recommendation_service.py # Orchestrator (REFACTOR)
│   ├── comfy_service.py        # ComfyUI integration
│   ├── download_service.py     # File downloads (STUB)
│   └── shortcut_service.py     # Desktop shortcuts (STUB)
├── ui/
│   ├── app.py                  # Main window (CustomTkinter)
│   ├── wizard/
│   │   ├── setup_wizard.py     # Wizard flow (WRONG FLOW)
│   │   └── components/         # UI components (KEEP)
│   ├── views/                  # Module dashboards
│   └── components/             # Reusable UI components
└── utils/
    └── logger.py
```

## Platform Constraints (HARDWARE_DETECTION.md)

### Apple Silicon (40% of users)
- GGUF K-quants crash MPS: **Filter to Q4_0, Q5_0, Q8_0 only**
- Memory ceiling: **75% of unified memory** for effective VRAM
- **Exclude HunyuanVideo** (~16 min/clip) - use AnimateDiff instead

### NVIDIA - Blackwell (RTX 50 series)
- Compute capability: **sm_120** (12.0)
- Requires: **CUDA 12.8+** or **CUDA 13.x** (preferred)
- PyTorch: `cu128` or `cu130` builds
- Supports: FP4, FP6, FP8 (2nd gen), BF16

### NVIDIA - Form Factor Detection
- Mobile GPUs have lower sustained performance than desktop
- Detect power limit via `nvidia-smi --query-gpu=power.limit`
- Performance ratio = sqrt(actual_power / reference_tdp)
- Example: RTX 4090 Laptop (175W) = ~62% of RTX 4090 Desktop (450W)

### NVIDIA - Ada Lovelace (RTX 40 series)
- Compute capability: **sm_89** (8.9)
- FP8 requires compute capability 8.9+

### NVIDIA - Older (RTX 30/20 series)
- Ampere (sm_80/86): BF16, no FP8
- Turing (sm_75): FP16 Tensor Cores only

### AMD ROCm (20% of users)
- Mark as **experimental** in UI
- RDNA2 may need `HSA_OVERRIDE_GFX_VERSION`

### CPU Detection
- Detect cores, model, AVX support
- Tiers: HIGH (16+), MEDIUM (8-15), LOW (4-7), MINIMAL (<4)
- Affects GGUF viability and offload capacity

### Storage Detection
- Types: NVMe Gen3/4/5, SATA SSD, HDD
- Tiers: FAST (NVMe), MODERATE (SATA), SLOW (HDD)
- Affects model load times and space constraints

## Development Conventions

1. **Strict Separation**: UI files must NEVER contain business logic
2. **Type Hints**: Required on all function signatures
3. **Schemas not Models**: Use `src/schemas/` for dataclasses
4. **Spec Citations**: Reference in commits: `fix(hardware): Apple Silicon RAM per SPEC_v3 4.2`
5. **Model Data**: Use `data/models_database.yaml`, NOT `resources.json`
6. **Migration Protocol**: See `docs/spec/MIGRATION_PROTOCOL.md` - don't break working app during refactor
7. **Commit Messages**: Never add co-author tags, AI tool attribution, or "Generated with" footers to commit messages unless explicitly requested by the user

## Locked Decisions (Do Not Relitigate)

| Area | Decision |
|------|----------|
| Recommendation | 3-layer (CSP→Content→TOPSIS) |
| Content Layer | Modular modality architecture (per-modality scorers) |
| Onboarding | Dual-path (Quick 5 / Comprehensive 15-20) |
| Model database | `data/models_database.yaml` |
| Cloud APIs | Partner Nodes primary (ComfyUI 0.3.60+) |
| Platform split | 40% Mac, 40% Windows, 20% Linux |

## Decision Workflow for Architecture Changes

**Before implementing any architecture/spec change**, follow this workflow:

1. **Document Decision** → Add to `PLAN_v3.md` Section 1 (Decision Log)
2. **Document Deprecations** → Add to `PLAN_v3.md` Section 7 (Deprecation Tracker)
3. **Update Spec** → Modify `AI_UNIVERSAL_SUITE_SPEC_v3.md`
4. **Update Plan** → Add tasks to `PLAN_v3.md` Section 2 (Task Tracker)
5. **Update Agent Files** → `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`
6. **Implement** → Follow Migration Protocol

This ensures all documentation stays in sync with code changes.

## Current Phase

**Phase 1: Core Infrastructure & Resiliency** - IN PROGRESS

Priority tasks (from 2026-02-04 Refactoring Roadmap):
1. **DB-01**: Migrate YAML to SQLite (Foundation for all relational logic)
2. **SYS-01**: Implement Multiprocessing Download Handler (Fix UI Freezes)
3. **SYS-05**: Implement Dynamic Storage Headroom Calculation (Fix OS stability)
4. **API-04**: Secure Local API with Bearer Token Auth (Security hardening)
5. **PAT-01**: Extract Recommendation Orchestrator Facade (Decouple logic)

See `docs/audits/2_4_26/Executive_Refactoring_Report_2026-02-04.md` for full 20-item roadmap.

See `docs/plans/PLAN_v3.md` Section 2 for full task list.
