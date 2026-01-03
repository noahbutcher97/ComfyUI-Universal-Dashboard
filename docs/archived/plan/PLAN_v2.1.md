# 🗺️ Project Roadmap: AI Universal Suite v2.1 (Research-Aligned)

**Current Status**: Phase 1A (UX Overhaul) - Starting
**Objective**: Implement research-validated recommendation UX and 3-layer algorithm architecture
**Research Reference**: "Building Recommendation Systems for AI Tool Configuration Wizards"

---

## Critical Research Findings Applied

| Finding | Original Design | Updated Design |
|---------|-----------------|----------------|
| 5-7 question threshold | ~25 questions | 5 questions max |
| 4±1 evaluable constructs | 40+ exposed dimensions | 5 aggregated factors |
| Presets + override pattern | No presets | 4 presets with customization |
| 3-layer architecture | Single-pass weighted scoring | Constraint → Content-Based → TOPSIS |
| <90 second first-run | Unspecified | 60-90 second target |
| Auto-detection priority | Manual hardware questions | Zero hardware questions |

---

## Phase 1A: Critical UX Fixes (IMMEDIATE - Week 1)
**Priority: BLOCKER - Research shows 74% of users won't complete >5 questions**

### Completed (from v2.0)
- [x] **UI Crash Fix**: Fixed `messagebox` import in `src/ui/views/comfyui.py`
- [x] **Apple Silicon Fix**: Rewrote `SystemService.get_gpu_info()` to use `sysctl` logic
- [x] **Hardware Scanning**: Implemented `scan_full_environment()` returning `EnvironmentReport`

### New Tasks
- [ ] **Streamlined Wizard UI**: Create `src/ui/wizard/streamlined_wizard.py`
  - Step 0: Hardware detection (automatic, 2-3 sec animation)
  - Step 1: Use case selection (single question)
  - Step 2: Experience level (single question)
  - Step 3: Priority slider (single slider)
  - Step 4: Preset confirmation (single selection with preview)
  - Step 5: API key (optional, skippable)
  
- [ ] **Preset System**: Create `src/services/preset_service.py`
  - Define 4 presets: Minimal, Balanced, Power User, Custom
  - Implement `select_default_preset()` logic
  - Create preset preview component
  
- [ ] **Factor Aggregation**: Create `src/services/factor_aggregation.py`
  - Implement `UserFactorScores` dataclass (5 factors)
  - Implement `ModelFactorScores.from_capability_scores()` aggregation
  - Pre-compute factor scores for all models in resources.json

### Success Criteria
- [ ] First-run flow completes in <90 seconds (questions only)
- [ ] Zero hardware-related questions asked
- [ ] Preset selection shown with transparent reasoning

---

## Phase 1B: Three-Layer Algorithm Architecture (Week 2)
**Priority: HIGH - Foundation for adaptive recommendations**

### Tasks
- [ ] **Layer 1 - Constraint Satisfaction**: Create `src/services/constraint_layer.py`
  ```python
  # Filter candidates by hard constraints
  # VRAM, RAM, storage, platform compatibility
  # Returns: viable_candidates, rejection_reasons
  ```

- [ ] **Layer 2 - Content-Based Matching**: Create `src/services/content_layer.py`
  ```python
  # Score candidates by feature similarity to user factors
  # Cosine similarity across 5 factors
  # No user history required (cold-start immune)
  ```

- [ ] **Layer 3 - TOPSIS Ranking**: Create `src/services/topsis_layer.py`
  ```python
  # Multi-criteria decision analysis
  # Vector normalization, weighted matrix, ideal/anti-ideal solutions
  # Output: closeness coefficients (interpretable scores)
  ```

- [ ] **Integration**: Create `src/services/recommendation_engine.py`
  - Orchestrate 3 layers in sequence
  - Compile reasoning trace from all layers
  - Generate explainable output

### Success Criteria
- [ ] Constraint layer eliminates infeasible options before scoring
- [ ] Content layer provides cold-start recommendations without user history
- [ ] TOPSIS layer produces interpretable "closeness to ideal" scores
- [ ] Reasoning trace explains each elimination and ranking decision

---

## Phase 2: Progressive Disclosure System (Week 3)
**Priority: MEDIUM - Research shows 80/20 pattern optimal**

### Tasks
- [ ] **Session Tracking**: Update `src/config/manager.py`
  - Track `session_count` in config
  - Track `advanced_settings_visible` flag
  - Track `calibration_prompt_shown` flag

- [ ] **Calibration Prompts**: Create `src/ui/components/calibration_prompt.py`
  - After 3 sessions: "How's your setup working?"
  - Option to adjust priority slider
  - Surface one recommendation based on patterns

- [ ] **Advanced Settings UI**: Create `src/ui/views/advanced_settings.py`
  - Hidden initially (`advanced_settings_visible = false`)
  - Revealed after 10 sessions OR manual toggle in Settings
  - Full 5-factor sliders
  - Factor drill-down (show underlying dimensions)

### Success Criteria
- [ ] New users see only 5 questions
- [ ] After 3 sessions, calibration prompt appears once
- [ ] After 10 sessions, "Advanced Settings" appears in sidebar
- [ ] Expert mode toggle available immediately in Settings

---

## Phase 3: Explainable Recommendations (Week 4)
**Priority: MEDIUM - Technical users want to understand "why"**

### Tasks
- [ ] **Reasoning Display**: Create `src/ui/components/reasoning_display.py`
  - Show constraint rejections with clear reasons
  - Show content similarity scores per factor
  - Show TOPSIS ranking breakdown

- [ ] **Factor Drill-Down**: Create `src/ui/components/factor_drilldown.py`
  - Expandable factor cards
  - Show underlying 40+ dimensions when expanded
  - Visual bars for each dimension score

- [ ] **Recommendation Comparison**: Create `src/ui/components/recommendation_compare.py`
  - Side-by-side preset comparison
  - Highlight differences in factor scores
  - Show hardware fit warnings

### Success Criteria
- [ ] Users can see WHY a preset was recommended
- [ ] Expert users can drill into full dimension set
- [ ] Hardware constraint failures are clearly explained

---

## Phase 4: Integration & Dynamic Manifest (Week 5)
**Priority: HIGH - Connect recommendation engine to installer**

### Tasks
- [ ] **Dynamic Manifest Generation**: Update `src/services/comfy_service.py`
  - Accept `RankedCandidate` as input (not hardcoded paths)
  - Generate manifest from recommendation engine output
  - Support all presets and custom configurations

- [ ] **CLI Provider Selection**: Update `src/services/dev_service.py`
  - Auto-select provider based on user factors
  - Writing-heavy → Claude
  - Code-heavy → Codex
  - Research-heavy → Gemini

- [ ] **Shortcut Service**: Create `src/services/shortcut_service.py`
  - Create desktop shortcuts after installation
  - OS-specific implementations (Windows .bat, macOS .command, Linux .desktop)

### Success Criteria
- [ ] Preset selection directly maps to installation manifest
- [ ] CLI provider auto-selected based on use case
- [ ] Desktop shortcuts created for all installed tools

---

## Technical Constraints & Validation

### Algorithm Constraints
- **No AHP**: Avoid Analytic Hierarchy Process (requires n²-n/2 comparisons = 780 for 40 dimensions)
- **TOPSIS preferred**: Scales linearly, interpretable "closeness to ideal" output
- **Content-based first**: No collaborative filtering until usage data accumulates

### UX Constraints
- **5 questions maximum** for first-run onboarding
- **5 factors maximum** exposed to users for comparison
- **Presets as starting points** with visible drill-down, not black boxes

### Validation Tests
```python
# tests/test_recommendation_engine.py

def test_beginner_low_vram_gets_minimal():
    """Verify constraint layer + content matching produces Minimal preset."""
    profile = UserProfile(
        experience_level="new_to_ai",
        priority_slider=0.3  # Speed bias
    )
    hardware = HardwareConstraints(vram_gb=4, ram_gb=8)
    
    result = recommendation_engine.recommend(profile, hardware)
    assert result.selected_preset == "minimal"
    assert "sd15" in result.model_tier

def test_expert_high_vram_gets_power_user():
    """Verify quality-focused expert gets Power User preset."""
    profile = UserProfile(
        experience_level="power_user",
        priority_slider=0.9  # Quality bias
    )
    hardware = HardwareConstraints(vram_gb=24, ram_gb=64)
    
    result = recommendation_engine.recommend(profile, hardware)
    assert result.selected_preset == "power_user"
    assert "flux" in result.model_tier or "sdxl" in result.model_tier

def test_apple_silicon_gets_gguf():
    """Verify Apple Silicon hardware triggers GGUF quantization."""
    profile = UserProfile(
        experience_level="regular",
        priority_slider=0.5
    )
    hardware = HardwareConstraints(
        gpu_vendor="apple",
        unified_memory=True,
        ram_gb=32
    )
    
    result = recommendation_engine.recommend(profile, hardware)
    assert result.requires_quantization == True
    assert any("gguf" in m.lower() for m in result.models)

def test_vram_constraint_rejects_flux():
    """Verify constraint layer rejects Flux for 8GB VRAM."""
    hardware = HardwareConstraints(vram_gb=8, ram_gb=16)
    
    rejections = constraint_layer.filter_candidates(
        [flux_candidate],
        hardware
    )
    
    assert flux_candidate.id in [r.candidate_id for r in rejections]
    assert "vram" in rejections[0].constraint

def test_question_count_under_threshold():
    """Verify first-run flow asks ≤5 questions."""
    wizard = StreamlinedWizard()
    question_count = wizard.get_total_question_count()
    
    assert question_count <= 5
```

---

## File Structure Updates

```
src/
├── services/
│   ├── constraint_layer.py          # NEW: Layer 1 - Hard constraint filtering
│   ├── content_layer.py             # NEW: Layer 2 - Content-based matching
│   ├── topsis_layer.py              # NEW: Layer 3 - TOPSIS multi-criteria ranking
│   ├── recommendation_engine.py      # NEW: Orchestrates 3 layers
│   ├── preset_service.py            # NEW: Preset definitions and selection
│   ├── factor_aggregation.py        # NEW: 40→5 factor aggregation
│   ├── shortcut_service.py          # NEW: Desktop shortcut creation
│   ├── comfy_service.py             # MODIFY: Accept RankedCandidate input
│   ├── dev_service.py               # MODIFY: Auto-select CLI provider
│   └── system_service.py            # EXISTING: Hardware detection (enhanced)
│
├── ui/
│   ├── wizard/
│   │   ├── streamlined_wizard.py    # NEW: 5-question first-run flow
│   │   └── components/
│   │       ├── use_case_cards.py    # NEW: Step 1 UI
│   │       ├── experience_selector.py  # NEW: Step 2 UI
│   │       ├── priority_slider.py   # NEW: Step 3 UI
│   │       ├── preset_preview.py    # NEW: Step 4 UI
│   │       └── api_key_input.py     # EXISTING: Step 5 UI
│   │
│   ├── components/
│   │   ├── reasoning_display.py     # NEW: Explainable recommendations
│   │   ├── factor_drilldown.py      # NEW: 5→40 dimension drill-down
│   │   ├── calibration_prompt.py    # NEW: Post-3-session prompt
│   │   └── recommendation_compare.py  # NEW: Side-by-side preset comparison
│   │
│   └── views/
│       └── advanced_settings.py     # NEW: Full factor configuration
│
├── config/
│   └── resources.json               # MODIFY: Add pre-computed factor scores
│
└── tests/
    ├── test_constraint_layer.py     # NEW
    ├── test_content_layer.py        # NEW
    ├── test_topsis_layer.py         # NEW
    ├── test_recommendation_engine.py  # NEW
    └── test_preset_selection.py     # NEW
```

---

## Research-Backed Decisions Log

| Decision | Research Citation | Alternative Rejected |
|----------|-------------------|---------------------|
| 5 questions max | "74% of users only willing to answer 5 questions or fewer" - InMoment | Original 25+ question survey |
| 5 aggregated factors | "4±1 constructs evaluable simultaneously" - Cowan 2001 | 40+ exposed dimensions |
| Presets with override | "Preset plus override outperforms either alone" - Game settings research | No presets / granular-only |
| 3-layer architecture | "Constraint satisfaction + content-based + TOPSIS" - MCDA research | Single-pass weighted scoring |
| Content-based over collaborative | "Technical tools have well-defined attributes" | Collaborative filtering |
| No AHP | "780 pairwise comparisons for 40 dimensions" | Analytic Hierarchy Process |
| Auto-detect hardware | "Netflix asks 3-5 selections, immediately recommends" | Hardware questions in survey |
| TOPSIS for ranking | "Scales linearly, interpretable results" | ELECTRE, PROMETHEE |

---

## Success Metrics

### Onboarding (Target: Week 1)
- [ ] Question count: ≤5 ✓
- [ ] First-run completion rate: >90%
- [ ] Time to first use: <90 seconds (questions only)

### Recommendation Quality (Target: Week 3)
- [ ] Preset acceptance rate: >80%
- [ ] Constraint rejection accuracy: 100% (no impossible configs)
- [ ] Expert override frequency: <20%

### Progressive Disclosure (Target: Week 4)
- [ ] Session tracking functional
- [ ] Calibration prompt appears after session 3
- [ ] Advanced settings visible after session 10

---

*Last Updated: Applied research findings from "Building Recommendation Systems for AI Tool Configuration Wizards"*
