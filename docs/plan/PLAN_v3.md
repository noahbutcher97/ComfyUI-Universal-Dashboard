# AI Universal Suite - Implementation Plan v3.0

**Status**: Active  
**Last Updated**: January 2026  
**Reference Spec**: AI_UNIVERSAL_SUITE_SPEC_v3.md

---

## 1. Decision Log

Capturing key decisions made during planning and implementation. Reference this when asking "why did we do it this way?"

| Date | Decision | Options Considered | Rationale |
|------|----------|-------------------|-----------|
| 2026-01-03 | Single consolidated SPEC document | A) Single doc (~300K) B) Modular docs C) Wiki | One source of truth, easier to maintain, prevents sync issues between documents |
| 2026-01-03 | Dual-path onboarding (Quick + Comprehensive) | A) Fixed 5 questions B) Progressive 15-20 C) Dual-path | Self-selected users installing desktop AI workstation have high commitment; dual path allows both exploration and optimization |
| 2026-01-03 | Tiered progressive for Comprehensive path | Flat 20 questions vs tiered by use case | Reduces cognitive load; users only see relevant questions; each tier ~30-60 seconds |
| 2026-01-03 | Separate models.yaml database | Inline in spec vs external file | 100+ models would bloat spec; external file easier to update; schema in spec, data in YAML |
| 2026-01-03 | Partner Nodes as primary cloud integration | A) Unified Partner Nodes B) Individual API keys C) Hybrid | ComfyUI's unified credit system simpler UX, one account, native to 0.3.60+; third-party keys only for edge cases |
| 2026-01-03 | Cost estimates shown during recommendation | A) No costs B) Estimates C) Full calculator | Informs local vs cloud decision without over-engineering; Partner Nodes already display credit costs |
| 2026-01-03 | Two-tier API key management | Unified vs separate | Partner Nodes (unified credits) and third-party APIs (keys in ComfyUI/keys/) are fundamentally different auth models |

---

## 2. Task Tracker

### Phase 1: Core Infrastructure (Weeks 1-2)

#### Week 1: Platform Detection
- [ ] Implement `HardwareDetector` base class
- [ ] Implement `AppleSiliconDetector` with sysctl calls
- [ ] **CRITICAL FIX**: Apple Silicon RAM detection (currently hardcoded to 16GB)
- [ ] Implement `NVIDIADetector` with CUDA capability detection
- [ ] Implement `AMDROCmDetector` with ROCm detection
- [ ] Add storage type detection (NVMe/SATA/HDD)
- [ ] Create `HardwareProfile` dataclass with all fields
- [ ] Add hardware tier classification logic
- [ ] Write unit tests for hardware detection

#### Week 2: Configuration & Services
- [ ] Implement `ConfigManager` with v3.0 schema
- [ ] Implement `DownloadService` with retry and progress
- [ ] Implement `ShortcutService` for all platforms
- [ ] Create base `SetupWizardService` skeleton
- [ ] Add logging infrastructure
- [ ] Integration tests for config persistence

### Phase 2: Onboarding System (Weeks 3-4)

#### Week 3: Question System
- [ ] Define question schemas in `onboarding_questions.yaml`
- [ ] Implement `QuestionCard` component
- [ ] Implement `OptionGrid` for multi-select
- [ ] Implement `SliderInput` for priority slider
- [ ] Implement `PathSelectorView` (Quick vs Comprehensive)
- [ ] Implement `HardwareDisplayView`

#### Week 4: Tiered Flow
- [ ] Implement `TieredQuestionFlow` widget
- [ ] Implement tier visibility logic (`show_if` conditions)
- [ ] Implement `RecommendationPreview` sidebar
- [ ] Implement `APIKeyInput` with provider selection
- [ ] Connect onboarding to `UserProfile` generation
- [ ] Integration tests for both paths (Quick + Comprehensive)

### Phase 3: Recommendation Engine (Weeks 5-6)

#### Week 5: Layers 1 & 2
- [ ] Implement `ConstraintSatisfactionLayer`
  - [ ] VRAM constraint with quantization fallback
  - [ ] Platform compatibility checks (Apple Silicon exclusions)
  - [ ] Compute capability requirements (FP8 on CC 8.9+)
  - [ ] Storage constraints
- [ ] Implement `ContentBasedLayer`
  - [ ] User feature vector construction (from 5 aggregated factors)
  - [ ] Model capability vector construction
  - [ ] Cosine similarity calculation
  - [ ] Feature matching identification

#### Week 6: Layer 3 & Resolution
- [ ] Implement `TOPSISLayer`
  - [ ] Decision matrix construction
  - [ ] Vector normalization
  - [ ] Ideal/anti-ideal solution calculation
  - [ ] Closeness coefficient computation
- [ ] Implement `ResolutionCascade`
  - [ ] Quantization downgrade path (FP16 → FP8 → GGUF Q8 → Q5 → Q4)
  - [ ] Variant substitution logic
  - [ ] Cloud offload suggestion
- [ ] Implement `RecommendationExplainer`
- [ ] Comprehensive recommendation tests (all hardware tiers)

### Phase 4: Model Management (Week 7)

- [ ] Populate `models_database.yaml` with remaining models
- [ ] Implement `ModelDatabase` with querying
- [ ] Implement `ModelManagerService`
- [ ] Implement `ModelCard` component
- [ ] Implement download queue with progress
- [ ] Implement model deletion with cleanup
- [ ] Add model update checking
- [ ] Write model management tests

### Phase 5: Cloud Integration (Week 8)

- [ ] Implement `PartnerNodeManager`
  - [ ] Account status checking
  - [ ] Service availability listing
- [ ] Implement `ThirdPartyAPIManager`
  - [ ] Key storage in `ComfyUI/keys/`
  - [ ] Provider configuration UI
- [ ] Implement `CloudOffloadStrategy`
- [ ] Implement `CloudAPIsView`
- [ ] Add cost estimation display
- [ ] Write cloud integration tests

### Phase 6: Polish & Testing (Weeks 9-10)

#### Week 9: Integration
- [ ] Full wizard flow integration testing
- [ ] Cross-platform testing
  - [ ] Windows 10/11 + NVIDIA (RTX 20/30/40 series)
  - [ ] macOS + Apple Silicon (M1/M2/M3/M4)
  - [ ] Linux + AMD ROCm (RX 6000/7000)
- [ ] Error handling and recovery flows
- [ ] Performance optimization
- [ ] UI polish and consistency

#### Week 10: Documentation & Release
- [ ] Update all documentation
- [ ] Create user guide
- [ ] Create troubleshooting guide
- [ ] Package for distribution (Windows installer, macOS .app, Linux .deb/.AppImage)
- [ ] Beta testing
- [ ] Release v1.0

---

## 3. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Apple Silicon GGUF K-quant crashes | High | Medium | Filter to non-K quants (Q4_0, Q5_0, Q8_0) for MPS; already in spec |
| HuggingFace rate limiting during downloads | Medium | High | Implement retry with exponential backoff; show clear error messages; suggest HF token |
| Partner Node API changes | Low | High | Abstract behind service layer; monitor ComfyUI release notes |
| Model URLs become stale | Medium | Medium | Implement URL verification on startup; fallback URLs; community-maintained model registry |
| ROCm compatibility issues on RDNA2 | High | Low | Warn users; provide HSA_OVERRIDE env var; mark as "experimental" |
| Recommendation engine suggests wrong models | Medium | High | Extensive testing across hardware tiers; user feedback mechanism; easy override in UI |
| Disk space exhaustion during install | Medium | Medium | Pre-flight space check; staged downloads with confirmation; cleanup on failure |

---

## 4. Open Questions

Track questions that need resolution during implementation:

| Question | Context | Status |
|----------|---------|--------|
| ~~Document structure~~ | Single vs modular | **Resolved**: Single consolidated spec |
| ~~Onboarding question count~~ | How many questions acceptable | **Resolved**: Dual-path (5 quick / 15-20 comprehensive) |
| ~~Cloud API auth model~~ | Unified vs per-provider | **Resolved**: Partner Nodes (unified) + third-party (keys) |
| Model database format | YAML vs JSON vs SQLite | **Resolved**: YAML for human-readability; load into memory at startup |
| Telemetry opt-in | What to collect, how to present | Open |
| Update mechanism | How to update models/app | Open |
| Workflow bundling | Which workflows to include OOTB | Open |

---

## 5. Progress Summary

**Overall Progress**: Phase 0 (Planning) ✅

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 0: Planning & Spec | ✅ Complete | 100% |
| Phase 1: Core Infrastructure | ⬜ Not Started | 0% |
| Phase 2: Onboarding System | ⬜ Not Started | 0% |
| Phase 3: Recommendation Engine | ⬜ Not Started | 0% |
| Phase 4: Model Management | ⬜ Not Started | 0% |
| Phase 5: Cloud Integration | ⬜ Not Started | 0% |
| Phase 6: Polish & Testing | ⬜ Not Started | 0% |

---

## 6. References

- **Specification**: `AI_UNIVERSAL_SUITE_SPEC_v3.md` - Complete technical specification
- **Model Database**: `models_database.yaml` - All model entries with variants and capabilities
- **Research Transcripts**: `/mnt/transcripts/` - Detailed research session logs

---

*This is a living document. Update as tasks complete and decisions are made.*
