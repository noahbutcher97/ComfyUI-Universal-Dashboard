# AI Universal Suite: Comprehensive Research Report for Model Configuration Engine

## Research Addendum v2.0 - Expanded Coverage

**Purpose**: Address gaps in initial research report covering CUDA compute capability analysis, expanded image/video model landscape, user feature specification architecture, and cloud offload strategies.

---

## Part 1: CUDA Compute Capability Analysis and Resolution Strategies

### 1.1 Compute Capability Feature Matrix

The recommendation engine must map CUDA compute capability to available optimizations and fallback strategies when features are unavailable.

| CC | Architecture | Tensor Core Gen | Supported Precision | Key Features |
|----|-------------|-----------------|---------------------|--------------|
| 7.5 | Turing (RTX 20) | 2nd | FP32, FP16, INT8, INT4 | Basic mixed precision, no BF16 |
| 8.0 | Ampere (A100) | 3rd | FP32, FP16, BF16, TF32, INT8, INT4 | Flash Attention 2, sparsity |
| 8.6 | Ampere (RTX 30) | 3rd | FP32, FP16, BF16, TF32, INT8, INT4 | Consumer Tensor Cores |
| 8.9 | Ada (RTX 40) | 4th | FP32, FP16, BF16, TF32, INT8, FP8, INT4 | FP8 E4M3/E5M2, Transformer Engine |
| 9.0 | Hopper (H100) | 4th+ | All above + FP64 | Flash Attention 3, MXFP4 |
| 10.0 | Blackwell (B200) | 5th | All above + NVFP4, FP6 | Native FP4, 3.5x memory reduction |
| 12.0 | Blackwell (RTX 50) | 5th | All above | Consumer NVFP4 |

### 1.2 Feature Detection and Fallback Strategy

```python
class ComputeCapabilityResolver:
    """
    Maps detected GPU compute capability to available optimizations
    and provides fallback strategies when features are unavailable.
    """
    
    FEATURE_REQUIREMENTS = {
        'flash_attention_2': {'min_cc': 8.0, 'fallback': 'sdp_math'},
        'flash_attention_3': {'min_cc': 9.0, 'fallback': 'flash_attention_2'},
        'bf16_native': {'min_cc': 8.0, 'fallback': 'fp16'},
        'tf32_mode': {'min_cc': 8.0, 'fallback': 'fp32'},
        'fp8_inference': {'min_cc': 8.9, 'fallback': 'fp16'},
        'nvfp4': {'min_cc': 10.0, 'fallback': 'gguf_q4'},
        'mxfp4': {'min_cc': 9.0, 'fallback': 'gguf_q4'},
        'transformer_engine': {'min_cc': 8.9, 'fallback': None},
    }
    
    PRECISION_FALLBACK_CHAIN = {
        # If model is available in precision X, fall back to Y
        'fp4': ['fp8', 'gguf_q4', 'gguf_q5', 'fp16'],
        'fp8': ['gguf_q8', 'fp16', 'bf16'],
        'bf16': ['fp16', 'fp32'],
        'fp16': ['fp32'],
    }
    
    def resolve_optimal_precision(
        self,
        model_id: str,
        available_precisions: List[str],
        compute_capability: float
    ) -> Tuple[str, List[str]]:
        """
        Returns (selected_precision, warnings)
        """
        warnings = []
        
        # Check what precisions are hardware-accelerated
        if compute_capability < 8.0:
            # Turing: No BF16, limited FP16 Tensor Core support
            preferred_order = ['fp16', 'fp32', 'gguf_q8', 'gguf_q5']
            warnings.append("BF16 not hardware-accelerated on this GPU")
        elif compute_capability < 8.9:
            # Ampere: BF16/FP16/TF32, no FP8
            preferred_order = ['bf16', 'fp16', 'gguf_q8', 'fp8', 'gguf_q5']
            if 'fp8' in available_precisions:
                warnings.append("FP8 will run via software emulation (slower)")
        elif compute_capability < 9.0:
            # Ada: Full FP8 support
            preferred_order = ['fp8', 'bf16', 'fp16', 'gguf_q8', 'gguf_q5']
        else:
            # Hopper+: MXFP4/NVFP4 potential
            preferred_order = ['fp4', 'fp8', 'bf16', 'fp16']
        
        for precision in preferred_order:
            if precision in available_precisions:
                return precision, warnings
        
        # Last resort: whatever is available
        return available_precisions[0], warnings + ["Using non-optimal precision"]
```

### 1.3 PyTorch Backend Configuration by CC

```python
def configure_pytorch_backends(compute_capability: float) -> Dict[str, Any]:
    """
    Configure PyTorch backends based on detected compute capability.
    Returns configuration dict and any warnings.
    """
    config = {
        'torch.backends.cuda.matmul.allow_tf32': False,
        'torch.backends.cudnn.allow_tf32': False,
        'torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction': False,
        'torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction': False,
    }
    warnings = []
    
    if compute_capability >= 8.0:
        # Enable TF32 for Ampere+
        config['torch.backends.cuda.matmul.allow_tf32'] = True
        config['torch.backends.cudnn.allow_tf32'] = True
        # Note: TF32 provides ~10x speedup with negligible accuracy loss
    
    if compute_capability >= 8.0:
        # BF16 reduced precision is safe on Ampere+
        config['torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction'] = True
    
    if compute_capability >= 8.9:
        # FP16 reduced precision safe on Ada+
        config['torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction'] = True
    
    # Check Flash Attention availability
    if compute_capability < 8.0:
        warnings.append("Flash Attention unavailable - using math backend (slower)")
    
    return config, warnings
```

### 1.4 Resolution Strategy When Hardware Insufficient

The recommendation engine should implement a **resolution cascade** when detected hardware cannot run requested models:

```
RESOLUTION CASCADE (in order of preference):
1. QUANTIZATION DOWNGRADE
   - fp16 → fp8 (if CC >= 8.9)
   - fp16 → gguf_q8 → gguf_q5 → gguf_q4
   - Surface quality impact: "Q4 retains ~88% quality on transformer models"

2. MODEL VARIANT SUBSTITUTION  
   - Flux.1 Dev → Flux.1 Schnell (faster, similar quality)
   - SDXL → SD 1.5 (lower VRAM, different aesthetic)
   - Wan 14B → Wan 5B (lower VRAM, shorter videos)

3. WORKFLOW OPTIMIZATION
   - Enable tiled VAE processing
   - Reduce batch size to 1
   - Lower resolution with upscale post-process

4. CLOUD OFFLOAD SUGGESTION
   - "This model exceeds your hardware. Consider cloud options."
   - Surface cost estimate per generation
```

---

## Part 2: Expanded Image Generation and Editing Models

### 2.1 Qwen Image Family - Complete Breakdown

| Model | Release | Parameters | VRAM (FP16) | VRAM (FP8) | VRAM (GGUF Q4) | Key Capability |
|-------|---------|------------|-------------|------------|----------------|----------------|
| Qwen-Image-2512 | Dec 2025 | 20B | 40GB+ | ~20GB | ~13GB | Best open-source T2I, realistic humans |
| Qwen-Image-Edit-2511 | Dec 2025 | 20B | 40GB+ | ~20GB | ~12GB | Multi-person editing, text editing |
| Qwen-Image-Edit-2509 | Sep 2025 | 20B | 40GB+ | ~20GB | ~12GB | Earlier version, single-subject focus |
| Qwen-Image-Layered | Dec 2025 | 20B | 40GB+ | ~20GB | ~12GB | Layer decomposition for editing |
| Qwen-Image ControlNets | Aug 2025 | Patch | +2-4GB | - | - | Canny, Depth, Inpaint control |

**Qwen-Image-Edit-2511 vs 2509 Differences:**
- **2511**: Multi-person consistency, stronger text editing, "consistency-first" approach
- **2509**: Better for single-subject edits, faster iteration
- **Recommendation**: Default to 2511, offer 2509 as "lightweight edit" option

**GGUF Availability (via Unsloth):**
- Q4_K_M: ~13GB total (diffusion + Qwen2.5-VL-7B encoder)
- Q8: Higher quality, ~18GB total
- ComfyUI: Use ComfyUI-GGUF (city96) with native Qwen-Image workflow

### 2.2 OmniGen Family - Unified Editing

| Model | Parameters | VRAM Native | VRAM Offload | Key Capability |
|-------|------------|-------------|--------------|----------------|
| OmniGen v1 | ~15.5B | ~15.5GB | ~8GB | Unified T2I + editing, no separate ControlNet |
| OmniGen2 | ~7B (3B text + 4B image) | ~17GB | ~8GB | Instruction-based editing, multi-image composition |

**OmniGen2 Capabilities:**
- Natural language editing: "Change the dress to blue", "Raise the hand"
- Multi-image composition: Combine elements from multiple images
- Text-in-image generation
- CPU offload support for <17GB VRAM systems

**ComfyUI Integration:**
- Native support in ComfyUI 0.3.60+
- Official nodes: Load Diffusion Model + ReferenceLatent for multi-image

### 2.3 Chroma - Apache 2.0 Alternative

| Model | Parameters | VRAM | License | Key Capability |
|-------|------------|------|---------|----------------|
| Chroma1-HD | 8.9B | ~10GB FP16, ~6GB FP8 | Apache 2.0 | FLUX.1-schnell based, commercially viable |
| Chroma1-Radiance | 8.9B | ~10GB | Apache 2.0 | No VAE needed, direct pixel generation |

**Why Chroma Matters:**
- Apache 2.0 license (commercial use without restrictions)
- Built on FLUX.1-schnell architecture
- ComfyUI native support (0.3.60+)
- GGUF quantized versions available

### 2.4 Other Notable Models

| Model | VRAM | Style Strength | Key Use Case |
|-------|------|----------------|--------------|
| HiDream-I1 | 17B params, ~20GB | Versatile | State-of-art benchmark performance |
| Playground v2.5 | ~8GB | Aesthetic | Strong visual quality, weaker photorealism |
| Kolors | 8-13GB (by quant) | Bilingual | English/Chinese prompts |
| PixArt-Σ | ~6GB (int8) | Clean | Direct 4K, good prompt adherence |

---

## Part 3: User Feature Specification Architecture

### 3.1 Image Generation Feature Taxonomy

The user should be able to specify requirements across these dimensions:

```python
@dataclass
class ImageGenerationFeatures:
    """
    User-specifiable features for image generation workflow selection.
    """
    
    # === Art Style Preferences ===
    style_preference: Literal[
        "photorealistic",      # Real photographs, portraits
        "cinematic",           # Film-like, dramatic lighting
        "anime_illustration",  # Anime/manga style
        "digital_art",         # Digital painting, concept art
        "traditional_art",     # Oil painting, watercolor effect
        "3d_rendered",         # CGI, 3D renders
        "stylized",            # Unique artistic styles
        "no_preference"        # Auto-select based on prompt
    ]
    
    # === Editing Capabilities ===
    requires_image_editing: bool = False
    editing_features: Optional[Set[Literal[
        "inpainting",              # Fill masked regions
        "outpainting",             # Extend image boundaries
        "instruction_editing",     # "Make him smile" style
        "background_replacement",  # Replace/remove background
        "object_removal",          # Remove specific objects
        "style_transfer",          # Apply style to existing image
        "face_swap",               # Replace faces
        "relighting",              # Change lighting conditions
        "text_editing",            # Edit text within images
        "multi_person_editing",    # Edit multiple subjects consistently
        "layer_decomposition"      # Separate into editable layers
    ]]] = None
    
    # === Control Features ===
    requires_controlnet: bool = False
    controlnet_types: Optional[Set[Literal[
        "canny",           # Edge detection control
        "depth",           # Depth map control
        "pose",            # Human pose control
        "segmentation",    # Semantic segmentation
        "lineart",         # Line art extraction
        "softedge",        # Soft edge detection
        "normal",          # Normal map control
        "reference",       # Reference image style
        "inpaint"          # Inpainting mask
    ]]] = None
    
    # === Character Consistency ===
    requires_character_consistency: bool = False
    consistency_method: Optional[Literal[
        "ip_adapter",      # General reference
        "ip_adapter_face", # Face-specific
        "instant_id",      # Identity preservation
        "pulid",           # Flux-compatible identity
        "reference_only"   # Built-in reference
    ]] = None
    
    # === Text Rendering ===
    requires_text_rendering: bool = False
    text_language: Optional[Set[str]] = None  # ["en", "zh", "ja", "ko"]
    
    # === Output Specifications ===
    target_resolution: Literal[
        "512x512",
        "768x768", 
        "1024x1024",
        "1536x1536",
        "2048x2048",
        "custom"
    ] = "1024x1024"
    batch_generation: bool = False
    batch_size_typical: int = 1
```

### 3.2 Video Generation Feature Taxonomy

```python
@dataclass
class VideoGenerationFeatures:
    """
    User-specifiable features for video generation workflow selection.
    """
    
    # === Generation Mode ===
    generation_mode: Literal[
        "text_to_video",           # T2V: Generate from text only
        "image_to_video",          # I2V: Animate single image
        "first_last_frame",        # FLF2V: Interpolate between keyframes
        "video_to_video",          # V2V: Transform existing video
        "multi_image_interpolation" # Interpolate between N images
    ]
    
    # === I2V Specific Features ===
    i2v_features: Optional[Set[Literal[
        "first_frame_control",     # Control starting frame
        "last_frame_control",      # Control ending frame (FLF2V)
        "keyframe_interpolation",  # Multiple keyframes
        "motion_guidance",         # Control motion type
        "camera_motion",           # Specify camera movement
        "subject_motion"           # Specify subject movement
    ]]] = None
    
    # === Frame Interpolation ===
    requires_frame_interpolation: bool = False
    interpolation_method: Optional[Literal[
        "rife",            # RIFE frame interpolation
        "film",            # Google FILM
        "gimm_vfi"         # GIMM-VFI
    ]] = None
    target_fps: int = 24
    
    # === Audio Integration ===
    requires_audio: bool = False
    audio_features: Optional[Set[Literal[
        "lip_sync",        # LatentSync lip synchronization
        "audio_reactive",  # Motion synced to audio beats
        "voice_clone",     # F5-TTS voice cloning
        "ambient_audio",   # Generated ambient sound
        "music_sync"       # Sync to music track
    ]]] = None
    
    # === Complexity Assessment ===
    workflow_complexity: Literal[
        "simple",          # Single model, basic output
        "standard",        # Model + upscaling
        "advanced",        # Multi-model, interpolation, audio
        "production"       # Full pipeline, maximum quality
    ] = "standard"
    
    # === Output Specifications ===
    target_resolution: Literal[
        "480p",    # 640x480 or 854x480
        "720p",    # 1280x720
        "1080p"    # 1920x1080 (may require upscaling)
    ] = "720p"
    target_duration_seconds: float = 5.0
    target_fps: int = 24
```

### 3.3 Feature-to-Model Mapping

```python
IMAGE_EDITING_MODEL_MAP = {
    # Feature set -> Recommended models (in preference order)
    frozenset(["inpainting"]): [
        "qwen_image_edit_2511",
        "sdxl_inpaint",
        "omnigen2"
    ],
    frozenset(["instruction_editing"]): [
        "omnigen2",  # Best for natural language instructions
        "qwen_image_edit_2511"
    ],
    frozenset(["multi_person_editing"]): [
        "qwen_image_edit_2511"  # Only reliable option
    ],
    frozenset(["text_editing"]): [
        "qwen_image_edit_2511",
        "qwen_image_2512"  # For generation with text
    ],
    frozenset(["layer_decomposition"]): [
        "qwen_image_layered"
    ],
    frozenset(["style_transfer", "relighting"]): [
        "qwen_image_edit_2511",
        "omnigen2"
    ]
}

VIDEO_FEATURE_MODEL_MAP = {
    frozenset(["first_frame_control"]): [
        "wan_2.2_i2v",
        "hunyuan_video_i2v",
        "ltx_video_2b"
    ],
    frozenset(["first_frame_control", "last_frame_control"]): [
        "wan_2.2_flf2v"  # Only option for true FLF
    ],
    frozenset(["lip_sync"]): [
        "latentsync_1.6"  # Requires separate lip-sync pass
    ],
    frozenset(["audio_reactive"]): [
        "ltx_video_2b"  # Native audio generation
    ]
}
```

---

## Part 4: Cloud Offload and External API Strategy

### 4.1 Cloud Options for Hardware-Insufficient Users

When user requirements exceed local hardware capabilities, the recommendation engine should surface cloud options:

**Cloud ComfyUI Platforms (Pay-Per-Use):**

| Platform | Pricing Model | Best For | Integration |
|----------|--------------|----------|-------------|
| ComfyICU | Per-execution | Experimentation, API dev | True serverless |
| RunComfy | Per-minute + execution | Workflow development | Full ComfyUI UI |
| RunningHub | Per-execution (credits) | Batch production | API + App builder |
| RunPod | Per-hour | Extended sessions | Raw GPU access |
| Replicate | Per-second | API integration | Hosted models |

**Cost Estimates (approximate):**

| Task | Local (per gen) | Cloud (per gen) | Break-even |
|------|-----------------|-----------------|------------|
| SDXL 1024x1024 | Free | ~$0.01-0.02 | N/A |
| Flux.1 Dev | Free (if hardware) | ~$0.02-0.05 | N/A |
| Wan 2.2 14B Video | Free (24GB+ VRAM) | ~$0.10-0.30 | ~500 videos |
| HunyuanVideo | Free (24GB+) | ~$0.20-0.50 | ~300 videos |

### 4.2 ComfyUI Partner Nodes (Official API Integration)

ComfyUI now supports **Partner Nodes** for direct API integration with paid models:

```
SUPPORTED PARTNER MODELS:
├── Black Forest Labs
│   ├── Flux 1.1[pro] Ultra
│   ├── Flux.1 Kontext Pro/Max
│   └── Flux.1 Canny/Depth/Expand/Fill Control
├── Google
│   ├── Veo 2, Veo 3.0 (video)
│   └── Gemini 2.5 Pro/Flash
├── OpenAI
│   ├── DALL·E 2, DALL·E 3
│   ├── GPT-Image-1
│   └── GPT-4o, o1, o3
└── Stability AI
    ├── Stable Image Ultra
    └── SD 3.5 Large/Medium

INTEGRATION METHOD:
- ComfyUI Account required (prepaid credits)
- No separate API key management
- Direct node integration in workflows
```

### 4.3 Third-Party API Nodes (fal.ai, Replicate)

**ComfyUI-Cloud-APIs** extension enables:
- fal.ai integration (Flux, Auraflow, etc.)
- Replicate.com integration (any ComfyUI workflow)
- Local + cloud hybrid workflows

**Setup Pattern:**
```
1. Install ComfyUI-Cloud-APIs via Manager
2. Add API key to ComfyUI-Cloud-APIs/keys/
3. Use cloud nodes alongside local nodes
4. Route heavy tasks to cloud, lightweight local
```

### 4.4 Recommendation Engine Integration

```python
class CloudOffloadStrategy:
    """
    Determines when and how to suggest cloud offload.
    """
    
    OFFLOAD_THRESHOLDS = {
        # Model requires more VRAM than user has
        'vram_exceeded': True,
        # Generation would take >5 minutes locally
        'time_threshold_minutes': 5,
        # User explicitly requests cloud option
        'user_preference': True
    }
    
    def evaluate_offload(
        self,
        model_requirements: ModelRequirements,
        hardware: HardwareConstraints,
        user_prefs: UserPreferences
    ) -> CloudRecommendation:
        """
        Returns recommendation for cloud offload if appropriate.
        """
        
        # Check if cloud is even an option
        if not user_prefs.cloud_willing:
            return CloudRecommendation(
                suggested=False,
                reason="User prefers local-only"
            )
        
        # Check VRAM constraint
        if model_requirements.vram_gb > hardware.effective_vram_gb:
            # Calculate quantization alternatives first
            quantized_options = self._find_quantized_alternatives(
                model_requirements, 
                hardware
            )
            
            if quantized_options:
                return CloudRecommendation(
                    suggested=False,
                    alternative=quantized_options[0],
                    reason=f"Quantized version fits your {hardware.effective_vram_gb}GB"
                )
            else:
                return CloudRecommendation(
                    suggested=True,
                    platforms=self._rank_platforms(model_requirements),
                    estimated_cost=self._estimate_cost(model_requirements),
                    reason=f"Model requires {model_requirements.vram_gb}GB, you have {hardware.effective_vram_gb}GB"
                )
        
        # Check time threshold
        estimated_time = self._estimate_generation_time(
            model_requirements, 
            hardware
        )
        if estimated_time > self.OFFLOAD_THRESHOLDS['time_threshold_minutes'] * 60:
            return CloudRecommendation(
                suggested=True,
                optional=True,  # Not required, just faster
                platforms=self._rank_platforms(model_requirements),
                local_time=estimated_time,
                cloud_time=estimated_time / 4,  # Cloud typically 4x faster
                reason=f"Local: ~{estimated_time//60}min, Cloud: ~{estimated_time//240}min"
            )
        
        return CloudRecommendation(suggested=False)
```

### 4.5 User Onboarding Question for API Willingness

Add to the 5-question onboarding flow:

```python
# Question 4 (optional, shown after preset selection)
CLOUD_API_QUESTION = {
    "question": "Are you open to using cloud APIs for models that exceed your hardware?",
    "type": "multiple_choice",
    "options": [
        {
            "value": "no_cloud",
            "label": "Local only",
            "description": "I'll use quantized versions or skip incompatible models"
        },
        {
            "value": "cloud_fallback", 
            "label": "Cloud as fallback",
            "description": "Suggest cloud when local isn't possible"
        },
        {
            "value": "cloud_preferred",
            "label": "Cloud preferred for heavy tasks",
            "description": "Route demanding models to cloud automatically"
        }
    ],
    "default": "cloud_fallback",
    "show_if": "hardware.vram_gb < 16 OR use_case == 'video_generation'"
}
```

---

## Part 5: Updated Model Metadata Structure

Based on all research, here's the expanded model metadata schema:

```yaml
model:
  id: "qwen_image_edit_2511"
  name: "Qwen-Image-Edit-2511"
  family: "qwen_image"
  release_date: "2025-12-23"
  license: "apache-2.0"
  
  # Architecture info (affects quantization quality)
  architecture:
    type: "mmdit"  # transformer, unet, mmdit, dit
    parameters_b: 20
    text_encoder: "qwen2.5_vl_7b"
    vae: "qwen_image_vae"
  
  # Available variants with hardware requirements
  variants:
    - id: "fp16"
      precision: "fp16"
      vram_min_mb: 40000
      vram_recommended_mb: 48000
      download_size_gb: 38
      platform_support:
        windows_nvidia: {min_cc: 7.0}
        mac_mps: false
        linux_rocm: true
      
    - id: "fp8_scaled"
      precision: "fp8"
      vram_min_mb: 20000
      vram_recommended_mb: 24000
      download_size_gb: 19
      platform_support:
        windows_nvidia: {min_cc: 8.9, optimal_cc: 9.0}
        mac_mps: false
        linux_rocm: false
      
    - id: "gguf_q4_k_m"
      precision: "q4_k_m"
      vram_min_mb: 12000
      vram_recommended_mb: 16000
      download_size_gb: 11
      quality_retention_percent: 88
      platform_support:
        windows_nvidia: true
        mac_mps: true  # GGUF works on Mac
        linux_rocm: true
      requires_nodes: ["ComfyUI-GGUF"]
  
  # Feature capabilities
  capabilities:
    primary: ["image_editing", "instruction_editing"]
    features:
      - id: "inpainting"
        quality: "excellent"
      - id: "multi_person_editing"
        quality: "excellent"
        notes: "Unique capability, state-of-art"
      - id: "text_editing"
        quality: "excellent"
      - id: "style_transfer"
        quality: "good"
      - id: "background_replacement"
        quality: "excellent"
    
    style_strengths:
      - "photorealistic"
      - "cinematic"
      - "digital_art"
    
    text_rendering:
      supported: true
      languages: ["en", "zh", "ja", "ko"]
  
  # Workflow dependencies
  dependencies:
    required_nodes:
      - "native"  # Built into ComfyUI 0.3.60+
    optional_nodes:
      - id: "qwen_image_lightning_lora"
        purpose: "4-step acceleration"
        path: "loras/Qwen-Image-Lightning-4steps-V1.0.safetensors"
  
  # Model incompatibilities
  incompatibilities:
    - model: "ip_adapter"
      reason: "Uses different text encoder architecture"
  
  # Cloud availability
  cloud_availability:
    replicate: true
    fal_ai: false
    runpod_template: "qwen-image-edit"
    partner_node: false
  
  # Explanation templates for recommendation
  explanation:
    selected: "Best for instruction-based editing and multi-person consistency"
    rejected_vram: "Requires {required}GB VRAM, you have {available}GB. Consider GGUF Q4 variant."
    rejected_platform: "Not supported on {platform}. Consider OmniGen2 instead."
```

---

## Part 6: Priority Implementation Recommendations

### Critical (Implement Immediately)

1. **CUDA Compute Capability Detection & Resolution**
   - Add `torch.cuda.get_device_capability()` detection
   - Implement precision fallback chain
   - Configure PyTorch backends based on CC

2. **User Feature Specification UI**
   - Add image editing feature checkboxes (inpainting, instruction editing, etc.)
   - Add video generation mode selection (T2V, I2V, FLF2V)
   - Add style preference selector

3. **Cloud Willingness Question**
   - Add to onboarding flow (question 4 or 5)
   - Store preference for cloud fallback logic

### High Priority

4. **Expanded Model Coverage**
   - Add Qwen-Image family (2512, Edit-2511, Layered)
   - Add OmniGen2 with CPU offload flag
   - Add Chroma1-HD/Radiance (Apache 2.0)
   - Add Wan 2.2 FLF2V workflow support

5. **Feature-to-Model Mapping**
   - Implement `IMAGE_EDITING_MODEL_MAP`
   - Implement `VIDEO_FEATURE_MODEL_MAP`
   - Surface "why this model" explanations

### Medium Priority

6. **Cloud Offload Integration**
   - Implement `CloudOffloadStrategy`
   - Add cost estimation display
   - Integrate ComfyUI Partner Nodes information

7. **Quantization Quality Metadata**
   - Add `quality_retention_percent` to all GGUF variants
   - Add `architecture_type` for quantization impact prediction

---

## Appendix: Quick Reference Tables

### Image Editing Model Selection

| Need | Best Model | VRAM | Alternative |
|------|-----------|------|-------------|
| Multi-person editing | Qwen-Edit-2511 | 12-40GB | None equivalent |
| Instruction editing | OmniGen2 | 8-17GB | Qwen-Edit |
| Simple inpainting | SDXL Inpaint | 8GB | SD 1.5 Inpaint |
| Text editing | Qwen-Edit-2511 | 12-40GB | None |
| Layer decomposition | Qwen-Image-Layered | 12-40GB | None |
| Commercial use | Chroma1-HD | 6-10GB | SDXL |

### Video Generation Model Selection

| Need | Best Model | VRAM | Alternative |
|------|-----------|------|-------------|
| First-last frame (FLF2V) | Wan 2.2 FLF2V | 12-24GB | None |
| I2V (single frame) | Wan 2.2 I2V | 8-24GB | HunyuanVideo |
| T2V | Wan 2.2 T2V | 8-24GB | LTX-Video |
| Audio generation | LTX-Video 2B | 8-10GB | None native |
| Lip sync | LatentSync 1.6 | +7GB | None |
| Mac/Apple Silicon | AnimateDiff | 8-16GB | None viable |

### CUDA Compute Capability Quick Reference

| GPU Series | CC | BF16 | FP8 | Flash Attn 2 | MXFP4 |
|-----------|-----|------|-----|--------------|-------|
| RTX 20xx | 7.5 | ❌ | ❌ | ❌ | ❌ |
| RTX 30xx | 8.6 | ✅ | ❌ | ✅ | ❌ |
| RTX 40xx | 8.9 | ✅ | ✅ | ✅ | ❌ |
| RTX 50xx | 12.0 | ✅ | ✅ | ✅ | ✅ |
