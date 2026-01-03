# AI Universal Suite - Specification Addendum v2.1

## Research-Aligned Recommendation Architecture

**Applies to**: AI_UNIVERSAL_SUITE_SPECS.md Section 13
**Status**: Supersedes original Section 13.9 (Onboarding Survey) and augments Section 13.5-13.6 (Scoring Algorithm)
**Research Basis**: "Building Recommendation Systems for AI Tool Configuration Wizards" (2025)

---

## 1. Executive Summary of Changes

The research identified critical thresholds that the original spec exceeds:

| Metric | Original Spec | Research Threshold | Updated Spec |
|--------|---------------|-------------------|--------------|
| Onboarding Questions | ~25+ across 5 screens | 5-7 maximum | 5 core questions |
| User-Facing Dimensions | 40+ exposed | 4±1 for comparison | 5 aggregated factors |
| Algorithm Architecture | Weighted scoring | 3-layer hybrid | Constraint → Content-Based → TOPSIS |
| First-Run Duration | Unspecified | <90 seconds | 60-90 seconds target |
| Preset System | None | Required | 4 presets with override |

---

## 2. Three-Layer Recommendation Architecture

**Replaces**: Section 13.5 scoring algorithm approach

The original weighted scoring approach combines hardware and preference evaluation into a single pass. Research indicates a **three-layer architecture** handles mixed constraints more robustly:

### Layer 1: Constraint Satisfaction Programming (Hard Filters)

**Purpose**: Eliminate infeasible configurations immediately

```python
class ConstraintSatisfactionLayer:
    """
    Layer 1: Binary elimination of candidates that violate hard constraints.
    Runs BEFORE any scoring to reduce candidate pool.
    """
    
    def filter_candidates(
        self, 
        candidates: List[ModelCandidate],
        hardware: HardwareConstraints
    ) -> Tuple[List[ModelCandidate], List[RejectionReason]]:
        """
        Returns (viable_candidates, rejections)
        """
        viable = []
        rejections = []
        
        for candidate in candidates:
            rejection = self._check_hard_constraints(candidate, hardware)
            if rejection:
                rejections.append(rejection)
            else:
                viable.append(candidate)
        
        return viable, rejections
    
    def _check_hard_constraints(
        self, 
        candidate: ModelCandidate,
        hardware: HardwareConstraints
    ) -> Optional[RejectionReason]:
        """
        Hard constraint checks - any failure = immediate rejection.
        """
        effective_vram = (
            hardware.ram_gb * 0.75 
            if hardware.unified_memory 
            else hardware.vram_gb
        )
        
        # VRAM check (with quantization fallback)
        if candidate.min_vram_gb > effective_vram:
            if not (candidate.has_gguf or candidate.has_fp8):
                return RejectionReason(
                    candidate_id=candidate.id,
                    constraint="vram",
                    required=candidate.min_vram_gb,
                    available=effective_vram,
                    message=f"Requires {candidate.min_vram_gb}GB VRAM, only {effective_vram:.1f}GB available"
                )
        
        # RAM check (absolute)
        if candidate.min_ram_gb > hardware.ram_gb:
            return RejectionReason(
                candidate_id=candidate.id,
                constraint="ram",
                required=candidate.min_ram_gb,
                available=hardware.ram_gb,
                message=f"Requires {candidate.min_ram_gb}GB RAM"
            )
        
        # Storage check (80% of free space)
        storage_limit = hardware.disk_free_gb * 0.8
        if candidate.size_gb > storage_limit:
            return RejectionReason(
                candidate_id=candidate.id,
                constraint="storage",
                required=candidate.size_gb,
                available=storage_limit,
                message=f"Model size {candidate.size_gb}GB exceeds safe storage limit"
            )
        
        # Platform compatibility
        if candidate.platform_restrictions:
            if hardware.os not in candidate.platform_restrictions:
                return RejectionReason(
                    candidate_id=candidate.id,
                    constraint="platform",
                    message=f"Not supported on {hardware.os}"
                )
        
        return None  # Passes all constraints
```

### Layer 2: Content-Based Feature Matching

**Purpose**: Score remaining viable options against user requirements

```python
class ContentBasedLayer:
    """
    Layer 2: Score candidates based on feature similarity to user needs.
    Uses content attributes, not collaborative signals.
    """
    
    def score_candidates(
        self,
        candidates: List[ModelCandidate],
        user_factors: UserFactorScores  # 5 aggregated factors
    ) -> List[ScoredCandidate]:
        """
        Returns candidates with content_similarity_score (0-1).
        """
        scored = []
        
        for candidate in candidates:
            # Compute cosine similarity between user needs and model capabilities
            similarity = self._compute_feature_similarity(
                user_factors, 
                candidate.factor_scores
            )
            
            scored.append(ScoredCandidate(
                candidate=candidate,
                content_similarity=similarity,
                matching_factors=self._get_matching_factors(user_factors, candidate)
            ))
        
        return scored
    
    def _compute_feature_similarity(
        self,
        user: UserFactorScores,
        model: ModelFactorScores
    ) -> float:
        """
        Cosine similarity across 5 aggregated factors.
        """
        user_vec = [
            user.quality_priority,
            user.speed_priority, 
            user.control_priority,
            user.consistency_priority,
            user.simplicity_priority
        ]
        
        model_vec = [
            model.quality_score,
            model.speed_score,
            model.control_score,
            model.consistency_score,
            model.simplicity_score
        ]
        
        # Cosine similarity
        dot_product = sum(u * m for u, m in zip(user_vec, model_vec))
        user_magnitude = math.sqrt(sum(u**2 for u in user_vec))
        model_magnitude = math.sqrt(sum(m**2 for m in model_vec))
        
        if user_magnitude == 0 or model_magnitude == 0:
            return 0.0
        
        return dot_product / (user_magnitude * model_magnitude)
```

### Layer 3: TOPSIS Multi-Criteria Ranking

**Purpose**: Final ranking based on weighted soft preferences

```python
class TOPSISLayer:
    """
    Layer 3: TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)
    Provides final ranking with interpretable "closeness to ideal" scores.
    """
    
    def rank_candidates(
        self,
        scored_candidates: List[ScoredCandidate],
        preference_weights: Dict[str, float],  # User-adjusted weights
        hardware_penalties: Dict[str, float]   # Soft hardware penalties
    ) -> List[RankedCandidate]:
        """
        Returns candidates ranked by TOPSIS closeness coefficient.
        """
        if not scored_candidates:
            return []
        
        # Step 1: Build decision matrix
        # Rows = candidates, Columns = criteria
        criteria = ['content_similarity', 'hardware_fit', 'approach_fit', 'ecosystem_maturity']
        matrix = self._build_decision_matrix(scored_candidates, criteria, hardware_penalties)
        
        # Step 2: Normalize matrix (vector normalization)
        normalized = self._vector_normalize(matrix)
        
        # Step 3: Apply weights
        weights = self._get_criteria_weights(preference_weights)
        weighted = normalized * weights
        
        # Step 4: Determine ideal and anti-ideal solutions
        ideal = weighted.max(axis=0)      # Best value per criterion
        anti_ideal = weighted.min(axis=0)  # Worst value per criterion
        
        # Step 5: Calculate distances
        dist_to_ideal = np.sqrt(((weighted - ideal) ** 2).sum(axis=1))
        dist_to_anti = np.sqrt(((weighted - anti_ideal) ** 2).sum(axis=1))
        
        # Step 6: Calculate closeness coefficient
        closeness = dist_to_anti / (dist_to_ideal + dist_to_anti + 1e-10)
        
        # Build ranked results
        ranked = []
        for i, candidate in enumerate(scored_candidates):
            ranked.append(RankedCandidate(
                candidate=candidate.candidate,
                topsis_score=float(closeness[i]),
                content_similarity=candidate.content_similarity,
                rank=0  # Set after sorting
            ))
        
        # Sort by TOPSIS score descending
        ranked.sort(key=lambda x: x.topsis_score, reverse=True)
        for i, r in enumerate(ranked):
            r.rank = i + 1
        
        return ranked
```

### Integrated Resolution Flow

```
                    RESEARCH-ALIGNED RESOLUTION FLOW
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  INPUT: UserFactorScores (5 factors) + HardwareConstraints (auto)       │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER 1: CONSTRAINT SATISFACTION                                       │
│  ─────────────────────────────────                                      │
│  • Filter candidates by hard constraints (VRAM, RAM, storage, platform) │
│  • Output: Viable candidates only                                       │
│  • Complexity: O(n) - single pass elimination                           │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER 2: CONTENT-BASED MATCHING                                        │
│  ────────────────────────────────                                       │
│  • Compute feature similarity to user's 5 factor scores                 │
│  • No user history required (cold-start immune)                         │
│  • Output: Similarity-scored candidates                                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER 3: TOPSIS RANKING                                                │
│  ───────────────────────                                                │
│  • Multi-criteria decision analysis                                     │
│  • Weights: content_similarity (0.40), hardware_fit (0.35),             │
│             approach_fit (0.15), ecosystem_maturity (0.10)              │
│  • Output: Final ranked list with closeness coefficients                │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  OUTPUT: RankedCandidates with explainable scores                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Five Aggregated User-Facing Factors

**Replaces**: Section 13.4.3 UserPreferences (40+ fields)

Research shows humans can meaningfully evaluate **4±1 constructs** simultaneously. The original spec exposes 40+ dimensions directly to users, causing cognitive overload.

### Factor Aggregation Mapping

Each user-facing factor aggregates multiple internal dimensions:

```python
@dataclass
class UserFactorScores:
    """
    5 user-facing factors that aggregate 40+ internal dimensions.
    Users set these; internal matching uses full dimension set.
    """
    
    quality_priority: float  # 0.0-1.0
    """
    Aggregates: photorealism, artistic_stylization, output_fidelity, 
    prompt_adherence, text_rendering, anatomy_accuracy
    
    User prompt: "How important is output quality?"
    Scale: Speed/Draft ←→ Maximum Quality
    """
    
    speed_priority: float  # 0.0-1.0
    """
    Aggregates: generation_speed, vram_efficiency, batch_capability
    
    User prompt: "How important is fast generation?"
    Scale: Quality First ←→ Speed First
    """
    
    control_priority: float  # 0.0-1.0
    """
    Aggregates: pose_control, edge_control, depth_control, 
    composition_control, segmentation_control, inpainting, outpainting,
    holistic_editing, localized_editing
    
    User prompt: "How much control do you need over output?"
    Scale: Simple/Automatic ←→ Precise Control
    """
    
    consistency_priority: float  # 0.0-1.0
    """
    Aggregates: character_consistency, face_id_preservation,
    style_consistency, subject_consistency, temporal_coherence
    
    User prompt: "How important is consistency across outputs?"
    Scale: One-off Outputs ←→ Consistent Series
    """
    
    simplicity_priority: float  # 0.0-1.0
    """
    Aggregates: (inverse of) node_count, setup_complexity, 
    maintenance_burden, learning_curve
    
    User prompt: "How simple should the setup be?"
    Scale: Full Capability ←→ Minimal Setup
    """


@dataclass  
class ModelFactorScores:
    """
    Model's scores on the same 5 factors (computed from 40+ dimensions).
    Pre-computed and stored in resources.json.
    """
    
    quality_score: float
    speed_score: float
    control_score: float
    consistency_score: float
    simplicity_score: float
    
    @classmethod
    def from_capability_scores(cls, caps: ModelCapabilityScores) -> "ModelFactorScores":
        """
        Aggregate 40+ internal dimensions into 5 user-facing factors.
        """
        return cls(
            quality_score=np.mean([
                caps.photorealism, 
                caps.artistic_stylization,
                caps.output_fidelity,
                caps.prompt_adherence,
                caps.text_rendering,
                caps.anatomy_accuracy
            ]),
            speed_score=np.mean([
                caps.generation_speed,
                caps.vram_efficiency,
                caps.batch_capability
            ]),
            control_score=np.mean([
                caps.pose_control,
                caps.edge_control,
                caps.depth_control,
                caps.composition_control,
                caps.inpainting,
                caps.outpainting,
                caps.holistic_editing,
                caps.localized_editing
            ]),
            consistency_score=np.mean([
                caps.character_consistency,
                caps.face_id_preservation,
                caps.style_consistency,
                caps.subject_consistency,
                caps.temporal_coherence
            ]),
            simplicity_score=1.0 - caps.setup_complexity  # Inverted
        )
```

### Expert Drill-Down

Advanced users can access the full 40+ dimensions via "Show Details" expansion:

```
┌─────────────────────────────────────────────────────────────────┐
│ Quality Factor: 8.5/10                           [Show Details] │
├─────────────────────────────────────────────────────────────────┤
│ (Expanded when clicked)                                         │
│                                                                 │
│   Photorealism:        ████████░░  9.0                         │
│   Artistic Style:      ███████░░░  7.5                         │
│   Output Fidelity:     ████████░░  8.5                         │
│   Prompt Adherence:    █████████░  9.5                         │
│   Text Rendering:      ███████░░░  7.0                         │
│   Anatomy Accuracy:    ████████░░  8.5                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Streamlined First-Run Flow (5 Questions)

**Replaces**: Section 13.9 Onboarding Survey UI Flow

Research shows 74% of users are only willing to answer 5 questions or fewer, with completion rates dropping 18% when increasing from 3 to 4 questions.

### New First-Run Flow (~60-90 seconds)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    STREAMLINED FIRST-RUN FLOW                           │
│                         (5 Questions Total)                             │
└─────────────────────────────────────────────────────────────────────────┘

STEP 0: Hardware Detection (AUTOMATIC - 0 questions)
════════════════════════════════════════════════════
• GPU/VRAM detection
• RAM detection  
• Storage scan
• Platform identification
• Form factor inference

Duration: 2-3 seconds (background)
User sees: Brief "Scanning your system..." animation

────────────────────────────────────────────────────────────────────────

STEP 1: Use Case Selection (1 question)
════════════════════════════════════════
"What do you want to create?"

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  🖼️ Images      │  │  🎬 Video       │  │  ✏️ Edit        │
│                 │  │                 │  │                 │
│ Generate images │  │ Animate photos, │  │ Modify existing │
│ from prompts    │  │ create clips    │  │ images          │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│  💬 AI Writing  │  │  🎯 Everything  │
│                 │  │                 │
│ Writing, coding │  │ Full AI        │
│ assistant       │  │ workstation    │
└─────────────────┘  └─────────────────┘

(Single selection OR "Everything")

────────────────────────────────────────────────────────────────────────

STEP 2: Experience Level (1 question)
═════════════════════════════════════
"How would you describe yourself?"

 ○ New to AI tools - Never used image/video AI
 ○ Tried a few tools - Used ChatGPT, Midjourney, etc.
 ● Regular user - Use AI tools weekly
 ○ Power user - Deep knowledge, customize workflows

(Single selection - maps to preset tier)

────────────────────────────────────────────────────────────────────────

STEP 3: Priority Slider (1 question)
════════════════════════════════════
"What matters more to you?"

    Speed / Simplicity ←───────●───────→ Quality / Control
                              ↑
                         (Balanced)

(Single slider - primary differentiating preference)

────────────────────────────────────────────────────────────────────────

STEP 4: Preset Selection with Preview (1 question)
═══════════════════════════════════════════════════
"Based on your answers, here's our recommendation:"

┌──────────────────────────────────────────────────────────────────────┐
│  ✨ RECOMMENDED: Balanced Setup                                      │
│                                                                      │
│  "Perfect for regular users who want good quality without hassle"   │
│                                                                      │
│  ├── Model: SDXL Juggernaut                                         │
│  ├── Workflow: Standard Image Generation                            │
│  ├── Download: ~6.5 GB                                              │
│  └── Est. install time: 5-10 minutes                                │
│                                                                      │
│  Quality: ████████░░  Speed: ██████░░░░  Control: █████░░░░░        │
│                                                                      │
│              [Use This Setup]  [See Other Options]                  │
└──────────────────────────────────────────────────────────────────────┘

Other options (collapsed, expandable):
┌────────────────────────────────────────────────────────────────────┐
│ ○ Minimal Setup - Fastest to start, basic features                │
│ ○ Balanced Setup ● - Good quality, reasonable download            │
│ ○ Power User - Maximum capability, larger download                │
│ ○ Custom - Choose everything yourself                              │
└────────────────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────

STEP 5: Optional API Key (1 question, skippable)
════════════════════════════════════════════════
(Only shown if use case includes AI Writing)

"Enter your API key (or skip for now)"

Provider: [Claude ▼]
API Key:  [________________________] [Get Key →]

[Skip for Now]  [Verify & Continue]

────────────────────────────────────────────────────────────────────────

DONE → Installation begins
```

### Question Count Verification

| Step | Questions | Notes |
|------|-----------|-------|
| 0: Hardware | 0 | Automatic |
| 1: Use Case | 1 | Single selection |
| 2: Experience | 1 | Single selection |
| 3: Priority | 1 | Single slider |
| 4: Preset | 1 | Confirmation with override option |
| 5: API Key | 0-1 | Skippable, only if relevant |
| **Total** | **4-5** | Within research threshold |

---

## 5. Preset System with Customization

**New Section**: Implements "presets plus override" pattern from research

### Preset Definitions

```python
CONFIGURATION_PRESETS = {
    "minimal": {
        "display_name": "Minimal Setup",
        "description": "Fastest to start, works on any hardware",
        "target_proficiency": ["beginner", "novice"],
        "target_hardware": ["low", "medium", "high"],
        
        "default_factors": {
            "quality_priority": 0.4,
            "speed_priority": 0.8,
            "control_priority": 0.2,
            "consistency_priority": 0.3,
            "simplicity_priority": 0.9
        },
        
        "comfyui_config": {
            "model_tier": "sd15",
            "custom_nodes": [],  # Manager only
            "features": []
        },
        
        "cli_config": {
            "provider": None,  # Skip CLI setup
        }
    },
    
    "balanced": {
        "display_name": "Balanced Setup",
        "description": "Good quality, reasonable download, recommended for most users",
        "target_proficiency": ["novice", "intermediate"],
        "target_hardware": ["medium", "high"],
        
        "default_factors": {
            "quality_priority": 0.7,
            "speed_priority": 0.5,
            "control_priority": 0.5,
            "consistency_priority": 0.5,
            "simplicity_priority": 0.6
        },
        
        "comfyui_config": {
            "model_tier": "sdxl",
            "custom_nodes": ["ComfyUI-Manager"],
            "features": []
        },
        
        "cli_config": {
            "provider": "auto",  # Based on use case
        }
    },
    
    "power_user": {
        "display_name": "Power User",
        "description": "Maximum capability, full control, larger downloads",
        "target_proficiency": ["intermediate", "advanced", "expert"],
        "target_hardware": ["high"],
        
        "default_factors": {
            "quality_priority": 0.9,
            "speed_priority": 0.3,
            "control_priority": 0.9,
            "consistency_priority": 0.8,
            "simplicity_priority": 0.2
        },
        
        "comfyui_config": {
            "model_tier": "flux",  # Or GGUF on Apple Silicon
            "custom_nodes": ["ComfyUI-Manager", "ComfyUI-IPAdapter-Plus", "comfyui_controlnet_aux"],
            "features": ["ipadapter", "controlnet"]
        },
        
        "cli_config": {
            "provider": "claude",
        }
    },
    
    "custom": {
        "display_name": "Custom",
        "description": "Choose everything yourself",
        "target_proficiency": ["advanced", "expert"],
        "target_hardware": ["any"],
        
        "default_factors": None,  # User specifies all
        
        "comfyui_config": None,  # User specifies all
        "cli_config": None
    }
}
```

### Preset Selection Logic

```python
def select_default_preset(
    use_case: str,
    experience_level: str,
    hardware: HardwareConstraints,
    priority_slider: float  # 0=speed, 1=quality
) -> str:
    """
    Auto-select appropriate preset based on first-run answers.
    """
    
    # Hardware capability tier
    if hardware.vram_score >= 0.7 and hardware.compute_score >= 0.6:
        hw_tier = "high"
    elif hardware.vram_score >= 0.4 or hardware.unified_memory:
        hw_tier = "medium"
    else:
        hw_tier = "low"
    
    # Map experience to proficiency
    proficiency_map = {
        "new_to_ai": "beginner",
        "tried_few": "novice", 
        "regular": "intermediate",
        "power_user": "advanced"
    }
    proficiency = proficiency_map.get(experience_level, "intermediate")
    
    # Decision matrix
    if proficiency == "beginner" or hw_tier == "low":
        return "minimal"
    
    if proficiency == "advanced" and hw_tier == "high":
        return "power_user"
    
    if priority_slider >= 0.7 and hw_tier in ["medium", "high"]:
        return "power_user"
    
    if priority_slider <= 0.3:
        return "minimal"
    
    return "balanced"  # Default
```

---

## 6. Progressive Disclosure Pattern

### First-Run (Day 0)
- 5 questions only
- Preset selection with transparent summary
- "Customize" option hidden but available

### After 3 Sessions
- Prompt: "How's your setup working?"
- Option to adjust priority slider
- Surface one recommendation based on usage patterns

### After 10 Sessions  
- "Advanced Settings" option becomes visible in sidebar
- Can access full factor sliders
- Can drill into 40+ dimensions

### Expert Mode Toggle
- Accessible immediately via Settings
- Exposes all configuration options
- Shows recommendation reasoning in detail

---

## 7. Updated Data Schemas

### Simplified UserProfile

```python
@dataclass
class UserProfile:
    """
    Streamlined user profile for 5-question onboarding.
    """
    
    # Step 1: Use case (single selection or "everything")
    use_case: Literal["images", "video", "edit", "writing", "everything"]
    
    # Step 2: Experience level
    experience_level: Literal["new_to_ai", "tried_few", "regular", "power_user"]
    
    # Step 3: Priority slider (0.0 = speed, 1.0 = quality)
    priority_slider: float
    
    # Step 4: Selected preset (may be auto-selected)
    selected_preset: Literal["minimal", "balanced", "power_user", "custom"]
    
    # Step 5: API key (optional)
    api_key_provider: Optional[str] = None
    api_key_set: bool = False
    
    # Derived: Factor scores (computed from preset + slider adjustment)
    factor_scores: Optional[UserFactorScores] = None
    
    def compute_factor_scores(self) -> UserFactorScores:
        """
        Derive 5 factor scores from preset + priority slider adjustment.
        """
        preset = CONFIGURATION_PRESETS[self.selected_preset]
        base_factors = preset["default_factors"]
        
        if base_factors is None:  # Custom preset
            # User must specify manually
            return self.factor_scores or UserFactorScores(0.5, 0.5, 0.5, 0.5, 0.5)
        
        # Adjust based on priority slider
        # Slider at 0.0 = speed bias, at 1.0 = quality bias
        quality_adjustment = (self.priority_slider - 0.5) * 0.3
        speed_adjustment = -quality_adjustment
        
        return UserFactorScores(
            quality_priority=min(1.0, max(0.0, base_factors["quality_priority"] + quality_adjustment)),
            speed_priority=min(1.0, max(0.0, base_factors["speed_priority"] + speed_adjustment)),
            control_priority=base_factors["control_priority"],
            consistency_priority=base_factors["consistency_priority"],
            simplicity_priority=base_factors["simplicity_priority"]
        )
```

### Config Schema Update

```json
{
  "version": "2.1",
  "first_run": true,
  "wizard_completed": false,
  "wizard_version": "2.1",
  
  "user_profile": {
    "use_case": "images",
    "experience_level": "regular",
    "priority_slider": 0.5,
    "selected_preset": "balanced",
    "api_key_provider": null,
    "api_key_set": false
  },
  
  "factor_scores": {
    "quality_priority": 0.7,
    "speed_priority": 0.5,
    "control_priority": 0.5,
    "consistency_priority": 0.5,
    "simplicity_priority": 0.6
  },
  
  "progressive_disclosure": {
    "session_count": 0,
    "advanced_settings_visible": false,
    "calibration_prompt_shown": false
  },
  
  "paths": {
    "comfyui": "~/ComfyUI",
    "shortcuts": "~/Desktop"
  },
  
  "modules": {}
}
```

---

## 8. Implementation Priority Update

Based on research findings, reprioritize implementation:

### Phase 1A: Critical UX Fixes (IMMEDIATE)
- [ ] Implement 5-question first-run flow
- [ ] Create preset selection UI
- [ ] Auto-detect hardware (remove all hardware questions)

### Phase 1B: Algorithm Architecture
- [ ] Implement 3-layer recommendation engine
- [ ] Create factor aggregation functions
- [ ] Pre-compute model factor scores

### Phase 2: Progressive Disclosure
- [ ] Track session count
- [ ] Implement calibration prompts
- [ ] Build "Advanced Settings" UI (hidden initially)

### Phase 3: Expert Features
- [ ] Factor drill-down UI
- [ ] Full dimension access
- [ ] Reasoning display

---

## 9. Validation Criteria

### Onboarding Success Metrics
- First-run completion rate > 90%
- Time to first use < 90 seconds (questions only, not download)
- Question abandonment rate < 10%

### Recommendation Quality Metrics
- Recommendation acceptance rate > 80% (users don't immediately switch presets)
- Post-session satisfaction (prompt after 3 sessions)
- Override frequency < 20% on first selection

### Warning Signs (Per Research)
Indicating over-engineering:
- Users cannot explain what factors mean
- Recommendation quality doesn't improve with additional input
- Users consistently skip or ignore preset selection

Indicating under-engineering:
- Users frequently ask "what about X?"
- Cannot meaningfully distinguish between presets
- Expert users consistently override all recommendations

---

## 10. Migration Path

For users of v2.0 spec (if any implementations exist):

1. **Existing UserPreferences** → Aggregate to UserFactorScores
2. **Existing scoring weights** → Map to 3-layer architecture
3. **Existing survey data** → Retain internally, don't re-ask

The 40+ internal dimensions remain valid for matching. Only the user-facing collection changes.

---

*End of Addendum v2.1*
