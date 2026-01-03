# AI Generation Model Landscape: Technical Specification for Desktop Configuration Wizard

The AI generation ecosystem in 2025 has matured into a complex but navigable landscape where **hardware constraints—particularly VRAM—determine viable model choices**. A desktop configuration wizard must map user hardware profiles to curated bundles spanning image, video, audio, and 3D generation, with quantization strategies serving as the critical enabler for consumer-grade GPUs. This report provides the capability taxonomy, hardware matrices, and preset recommendations to inform such a system.

## Image generation models define the ecosystem's core

The image generation landscape stratifies into clear capability tiers, each with distinct hardware profiles and use cases. **SD1.5** remains relevant for 4-6GB VRAM environments, generating at 512×512 with the largest fine-tune ecosystem (**10,000+ specialized models**). **SDXL** (3.5B parameters) operates at 1024×1024 with 8-12GB VRAM and offers the most mature LoRA/ControlNet ecosystem. **SD3.5 Medium** (2.5B parameters) represents the breakthrough consumer-friendly option at **9.9GB VRAM**, introducing 94% accuracy text rendering previously impossible in Stable Diffusion.

**Flux dominates quality benchmarks** with its 12B parameter rectified flow transformer. The variant structure matters: Flux.1 [schnell] (Apache 2.0, 1-4 steps) enables rapid iteration; Flux.1 [dev] (non-commercial, 20-50 steps) provides development-quality output; and the tools suite (Fill, Depth, Canny, Redux, Kontext) extends into specialized conditioning. Full FP16 Flux requires 24GB VRAM, but GGUF Q4 drops this to **6-8GB** with approximately 95% quality retention.

| Model Family | Native Resolution | Minimum VRAM | Recommended VRAM | Text Rendering | Ecosystem Maturity |
|-------------|-------------------|--------------|------------------|----------------|-------------------|
| SD1.5 | 512×512 | 4GB | 6-8GB | None | ⭐⭐⭐⭐⭐ Mature |
| SDXL | 1024×1024 | 8GB | 12GB | Poor | ⭐⭐⭐⭐⭐ Mature |
| SD3.5 Medium | 1024×1024 | 9.9GB | 12GB | Good (94%) | ⭐⭐⭐⭐ Growing |
| Flux.1 FP8 | 1024×1024 | 12-13GB | 16GB | Excellent | ⭐⭐⭐⭐ Good |
| Flux.1 GGUF Q4 | 1024×1024 | 6-8GB | 8GB | Very Good | ⭐⭐⭐⭐ Good |
| Flux.1 FP16 | 1024×1024 | 24GB | 24GB+ | Excellent | ⭐⭐⭐⭐ Good |

## Video generation spans three practical tiers

Video generation models divide into **entry (8GB)**, **prosumer (12-16GB)**, and **professional (24GB+)** capability bands. The **Wan 2.x family** from Alibaba offers the most flexible options: Wan2.2-TI2V-5B runs on 8GB VRAM with native ComfyUI offloading, while the 14B models deliver state-of-the-art quality but require 24GB+ unquantized or **4-6GB via GGUF Q3-Q4**.

**LTX-Video** leads on speed—the 2B distilled variant achieves near real-time generation and natively supports **synchronized audio generation**, unique among open-source models. **HunyuanVideo 1.5** (8.3B parameters) offers 16-second clips at 24fps with 1080p super-resolution upscaling; GGUF Q4 with temporal tiling enables **8GB operation**. AnimateDiff remains essential for leveraging existing SD1.5 checkpoints and LoRAs, requiring only 8-13GB for 512×512 output.

Video generation audio-awareness represents a key differentiator: **LTX-2 generates synchronized dialogue and sound effects**, while Wan includes Video-to-Audio as a separate pipeline stage. All other major open-source models (HunyuanVideo, Mochi, CogVideoX) are audio-agnostic.

| Model | Resolution | Max Duration | 8GB VRAM | 12GB VRAM | 24GB VRAM | Audio-Aware |
|-------|-----------|-------------|----------|-----------|-----------|-------------|
| Wan2.2-5B | 720p | 5s | ✅ Native | ✅ | ✅ | V2A pipeline |
| Wan2.2-14B GGUF Q4 | 720p | 5s | ✅ | ✅ | ✅ | V2A pipeline |
| LTX-Video 2B | 4K | 10s | ✅ Quantized | ✅ | ✅ | ✅ Native |
| HunyuanVideo GGUF Q4 | 1080p (SR) | 16s | ⚠️ Tiling | ✅ | ✅ | ❌ |
| AnimateDiff SD1.5 | 512px | 4s | ✅ | ✅ | ✅ | ❌ |
| CogVideoX-5B | 720×480 | 10s | ❌ | ⚠️ Optimized | ✅ | ❌ |

## Audio generation anchors complete pipelines

Speech synthesis divides into **quality-focused** and **lightweight** categories. **F5-TTS** (Apache 2.0) delivers best-in-class zero-shot voice cloning with 8GB+ VRAM; **XTTS-v2** offers 17-language multilingual capability with 6-second voice cloning samples. For edge deployment, **Piper TTS** runs on Raspberry Pi with 4GB RAM and no GPU—the only production-ready CPU-only option delivering 20-30ms generation times.

Music generation centers on **MusicGen** (Meta, CC-BY-NC) requiring 16GB VRAM for medium/large variants, with melody-guided generation via chromagram conditioning. **ACE-Step** (native ComfyUI) generates full songs with vocals, distinguishing it from instrumental-only alternatives. **AudioLDM 2** handles sound effects generation with CPU/CUDA/MPS support.

Lip sync models form the critical bridge between audio and video. **LatentSync 1.6** (ByteDance) delivers 512×512 lip sync in minutes on RTX 3090, outperforming alternatives for video input. **SadTalker** animates photos with full head motion (8GB+). **LivePortrait** offers finest control but requires hour-long processing for equivalent output. **MuseTalk** achieves real-time 30+ FPS but with 256×256 face region limitation.

| Category | Model | VRAM | CPU-Only | Voice Clone | Best For |
|----------|-------|------|----------|-------------|----------|
| TTS Quality | F5-TTS | 8GB+ | Slow | ✅ | Production cloning |
| TTS Lightweight | Piper | None | ✅ | ❌ | Edge/embedded |
| TTS Multilingual | XTTS-v2 | 4GB+ | Yes (slow) | ✅ | 17 languages |
| Music | MusicGen-medium | 16GB | ❌ | N/A | Text+melody to music |
| SFX | AudioLDM 2 | 8GB+ | ✅ | N/A | Sound effects |
| Lip Sync Video | LatentSync 1.6 | 20GB+ | ❌ | N/A | Video input, fastest |
| Lip Sync Photo | SadTalker | 8GB+ | ❌ | N/A | Full head animation |

## 3D generation remains experimental with exceptions

3D generation exhibits the widest maturity gap. **TripoSR** achieves production status: sub-second inference, 6GB VRAM, native ComfyUI node, and usable mesh output for background game models and AR applications. **InstantMesh** (TencentARC) delivers superior mesh quality in ~10 seconds via Zero123++ multi-view generation feeding LRM-based reconstruction. Both export GLB, FBX, OBJ, and STL.

All other 3D models remain experimental: **Shap-E** (OpenAI) produces rough outputs requiring extensive post-processing; **Point-E** generates low-fidelity point clouds superseded by Shap-E. The common limitation: organic characters and complex scenes produce unreliable results. **3D generation should be positioned as "experimental" in any preset configuration** with clear user expectations.

## ComfyUI nodes form the capability extension layer

Custom nodes transform base model capabilities into production workflows. The **stable, essential tier** includes: ComfyUI Manager (mandatory), IPAdapter Plus (style transfer, face consistency), ControlNet Aux (15+ preprocessors), VideoHelperSuite (video I/O), and IC-Light (relighting). These nodes see active maintenance and minimal breaking changes.

**Efficiency-critical nodes** enable low-VRAM operation: Tiled VAE processes high-resolution in tiles; GGUF Model Loader enables quantized inference; Efficiency Nodes (ltdrdata fork) combine loader/sampler for memory optimization. Critical launch flags include `--medvram --use-xformers --cpu-text-encoder` for 8GB systems.

**Face consistency** requires stacked approaches: IPAdapter Plus provides style/pose transfer; InstantID (SDXL only, **maintenance mode since April 2025**) offers zero-shot identity preservation; PuLID delivers tuning-free ID customization with fidelity/style method selection. All require InsightFace (antelopev2 model specifically—buffalo_l causes issues).

| Node Package | Function | Stability | VRAM Overhead | Installation |
|--------------|----------|-----------|---------------|--------------|
| IPAdapter Plus | Style/face transfer | ⭐⭐⭐⭐⭐ | 2-4GB | Medium |
| ControlNet Aux | Structural conditioning | ⭐⭐⭐⭐⭐ | 1-6GB | Medium |
| VideoHelperSuite | Video I/O | ⭐⭐⭐⭐⭐ | Minimal | Easy |
| IC-Light | Relighting | ⭐⭐⭐⭐⭐ | Minimal | Easy |
| InstantID | Identity preservation | ⭐⭐⭐⭐ | 4-6GB | Hard |
| Frame Interpolation | RIFE VFI | ⭐⭐⭐⭐ | 2GB | Medium |
| Efficiency Nodes | Memory optimization | ⭐⭐⭐ | Negative (saves) | Easy |

## Quantization enables consumer hardware viability

**GGUF Q4_K_M represents the practical sweet spot**: ~75% size reduction with <3% quality loss, LoRA compatibility maintained. GGUF uniquely supports Apple Silicon via Metal backend with MLX providing even better performance than llama.cpp on unified memory. Non-K GGUF variants (Q4_0, Q5_0, Q8_0) work on MPS; K variants crash.

**FP8** delivers near-FP16 quality (99%+) with 50% VRAM reduction but requires **Ada Lovelace (RTX 40xx) or newer** for native W8A8 support. Ampere (RTX 30xx, A100) supports only weight-only FP8 via Marlin kernels. FP8 achieves ~3.5 iterations/second at 1024×1024 on RTX 4090 with Flux.

**NF4** (bitsandbytes) optimizes for normally-distributed neural network weights, achieving ~75% VRAM reduction. Critical limitation: **NF4 is incompatible with LoRAs**, making it unsuitable for workflows requiring fine-tuned adaptations. Double quantization saves an additional 0.4 bits/parameter.

```
QUANTIZATION DECISION TREE:

Is LoRA/fine-tuning required?
├── YES → Use GGUF or FP8 (NF4 incompatible)
└── NO → Continue

GPU Architecture:
├── Ada Lovelace+ (RTX 40xx) → FP8 (optimal speed+quality)
├── Ampere (RTX 30xx) → GGUF Q6-Q8 or FP8 Marlin (weight-only)
├── Apple Silicon → GGUF non-K variants (Q4_0, Q8_0)
└── Older NVIDIA/AMD → GGUF Q4_K_M

VRAM Available:
├── 24GB+ → FP16 (no quantization needed)
├── 12-16GB → FP8 or GGUF Q8
├── 8-12GB → GGUF Q4-Q6
├── 6-8GB → GGUF Q3-Q4
└── <6GB → GGUF Q2-Q3 (quality degradation)
```

## Hardware tiers define preset boundaries

The wizard must map hardware to capability presets. **8GB VRAM** (RTX 4060, RTX 3060 8GB) represents the minimum viable tier for modern workflows: SD1.5/SDXL with optimizations, Flux GGUF Q4-Q5, Wan2.2-5B native, AnimateDiff, SadTalker. **12GB VRAM** (RTX 4070, RTX 3060 12GB) unlocks Flux FP8, HunyuanVideo FP8, and LoRA training for SD models. **24GB VRAM** (RTX 4090, RTX 3090) removes most constraints, enabling Flux FP16, full video generation, and complex multi-model workflows.

**Apple Silicon** presents unique considerations: unified memory advantage (larger models than equivalent VRAM GPUs) but **2-4x slower inference** than NVIDIA CUDA. M3 Max with 32GB+ recommended for Flux; M1/M2 limited to SD1.5/SDXL. FP8 is **unsupported on MPS**—use FP16 or GGUF exclusively.

| VRAM Tier | Image Gen | Video Gen | Audio | 3D | Training |
|-----------|-----------|-----------|-------|-----|----------|
| 4GB | SD1.5 limited | ❌ | Piper only | ❌ | ❌ |
| 6GB | SD1.5, SDXL slow | Wan GGUF Q3 | XTTS | TripoSR | ❌ |
| 8GB | SDXL, Flux Q4 | Wan2.2-5B, LTX Q | TTS+Lip sync | TripoSR | SD1.5 LoRA |
| 12GB | Flux FP8 | Wan/Hunyuan FP8 | Full audio | InstantMesh | SDXL LoRA |
| 16GB | Flux FP8 full | All FP8 | Full audio | Full | Most training |
| 24GB | Flux FP16 | All FP16 | Full audio | Full | Full training |

## Preset bundles should target specific outcomes

The configuration wizard should offer **tiered presets** rather than exposing all options. Each preset represents a tested model+node combination for a specific outcome.

**Photorealism Preset (12GB+):**
- Base: Flux.1 [dev] FP8 + photorealistic LoRAs
- Nodes: IPAdapter Plus, ControlNet (Depth, Canny), FaceDetailer, Real-ESRGAN 4x
- Quality tags: "RAW photo, 4k, highres, photorealistic"

**Illustration/Anime Preset (8GB+):**
- Base: SD1.5 DreamShaper or SDXL Hassaku
- Nodes: ControlNet (Lineart, NormalBae), 4x-AnimeSharp upscaler
- VAE: kl-f8-anime2
- Embeddings: easynegative, bad-hands-5

**Video Generation Preset (12GB+):**
- Base: Wan2.2-14B GGUF Q5 or LTX-Video 2B
- Nodes: VideoHelperSuite, Frame Interpolation (RIFE), AnimateDiff-Evolved
- Audio: F5-TTS, LatentSync for lip sync

**Lightweight/Edge Preset (6-8GB):**
- Base: SD1.5 with optimizations or SDXL GGUF
- Nodes: Efficiency Nodes, Tiled VAE
- Audio: Piper TTS (CPU)
- Flags: --medvram --use-xformers

**Character Consistency Preset (16GB+):**
- Base: SDXL or Flux FP8
- Nodes: IPAdapter FaceID Plus V2, InstantID (SDXL), PuLID (Flux)
- Face models: InsightFace antelopev2, CodeFormer

## Gap analysis reveals maturity spectrum

**Mature/Production-Ready:**
- SD1.5, SDXL: Fully stable, massive ecosystem
- Flux.1 [schnell/dev]: Quality leader, broad quantization support
- IPAdapter, ControlNet: Essential, well-maintained
- VideoHelperSuite: Required for all video workflows
- Piper TTS: Only reliable CPU-only TTS
- TripoSR: Only production-grade 3D option

**Maturing/Recommended:**
- SD3.5 Medium: Text rendering breakthrough, growing ecosystem
- Wan 2.x: Best open-source video, native ComfyUI
- HunyuanVideo: Excellent motion, consumer GPU viable
- LTX-Video: Speed leader, unique audio capability
- F5-TTS: Best voice cloning, Apache licensed

**Experimental/Use With Caution:**
- Mochi: 60GB baseline, research preview
- InstantID: **Maintenance mode** since April 2025
- 3D generation (except TripoSR): Unreliable organic output
- Audio-reactive video: Variable stability

**Missing/Gap:**
- Real-time video generation at quality (LTX-2 approaches this)
- Unified audio+video generation (only LTX-2)
- Reliable organic 3D character generation
- MPS-optimized Flux inference (significant Apple Silicon gap)
- Cross-model LoRA compatibility (each family isolated)

## Technical specification recommendations

**Add to specification:**

1. **Hardware Detection Module:** Query VRAM, RAM, GPU architecture (Ampere/Ada/Apple), and recommend appropriate quantization strategy automatically.

2. **Preset System:** Implement outcome-based presets (Photorealism, Anime, Video, Lightweight, Character Consistency) with locked model+node combinations rather than exposing individual choices.

3. **Quantization Selector:** For advanced users, expose GGUF tier selection (Q4/Q5/Q6/Q8) and FP8 toggle based on detected GPU architecture.

4. **Node Dependency Resolver:** Map node packages to Python dependencies; flag conflicts (opencv-python variants, numpy 2.0, PyTorch/CUDA mismatches) before installation.

5. **Apple Silicon Path:** Separate configuration track using MLX framework and GGUF non-K variants; disable FP8 options entirely on MPS.

6. **Maturity Indicators:** Tag experimental features (3D beyond TripoSR, Mochi video) with clear warnings; hide behind "Show Experimental" toggle.

7. **Storage Calculator:** Sum selected model sizes (Flux FP8: 12GB, T5-XXL FP8: 5GB, VAE: 300MB, ControlNets: 1-2GB each) and display total with SSD recommendation.

8. **VRAM Budget Monitor:** Calculate combined VRAM for selected models+nodes; warn when exceeding detected capacity with quantization suggestions.

**Exclude from default presets:**
- FLUX.2 (90GB VRAM requirement, not consumer-viable)
- Mochi (research preview, impractical generation times)
- All 3D except TripoSR (experimental status)
- NF4 quantization (LoRA incompatibility)
- K-quant GGUF on Apple Silicon (crash risk)

This specification enables a wizard that maps user hardware to proven, stable configurations while exposing advanced options for power users. The key insight: **quantization strategy selection is the primary lever** for enabling consumer hardware access to state-of-the-art capabilities.