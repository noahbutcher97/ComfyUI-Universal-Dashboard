# AI Universal Suite: Hardware & Model Research Addendum v1.0

**Purpose:** Comprehensive research findings on hardware detection factors beyond VRAM/RAM and model landscape gaps not covered in the original specification.

---

## Part 1: Hardware Detection Factors Beyond VRAM/RAM

The original specification correctly identifies VRAM as the primary constraint, but seven additional detectable hardware factors significantly impact AI generation experience.

### 1.1 Thermal Throttling Behavior

**Impact:** AI workloads generate sustained 100% GPU load for extended periods—fundamentally different from gaming's burst patterns. Performance degradation begins when GPU reaches **82-85°C**, with automatic clock speed reduction.

| Environment | Throttling Impact | Time to Onset |
|-------------|-------------------|---------------|
| Data center (regulated cooling) | 34.2% throughput reduction | Rare |
| Consumer GPU (RTX 4090) | Micro-throttling at 82-84°C | 15-30 minutes |
| Edge devices (Raspberry Pi 4B) | 37.5% FPS drop (16→10fps) | ~50 seconds |
| Fanless/passive systems | Continuous degradation via DVFS | Immediate |

**Detection:** 
- GPU: `nvidia-smi -q -d TEMPERATURE` (NVIDIA), ROCm-SMI (AMD)
- CPU: OS APIs universally available (Windows WMI, Linux hwmon, macOS IOKit)

**Specification Impact:**
- Thermal state should trigger workflow recommendations:
  - At >80°C: Suggest reducing batch size
  - At >83°C: Enable tiled processing
  - Persistent high temps: Surface cooling upgrade recommendation
- Apple Silicon: Efficient thermal design allows sustained workloads—no adjustment needed

### 1.2 Memory Bandwidth Type and Impact

**Critical Distinction:** VRAM capacity determines *what can be stored*; memory bandwidth determines *how fast data moves*. LLM inference is **memory bandwidth-bound**, not compute-bound—GPUs spend more time waiting for data than computing.

| Memory Type | Bandwidth | Typical Use | LLM Performance Impact |
|-------------|-----------|-------------|------------------------|
| GDDR6 | 768 GB/s | Consumer GPUs | Adequate for <13B models |
| GDDR6X | ~1 TB/s (PAM4) | RTX 3090, 4090 | Good for 13B-70B models |
| HBM2e | 1.6 TB/s | A100, MI250 | Essential for 70B+ training |
| HBM3 | 3.35 TB/s | H100 | Required for 70B+ inference at scale |
| HBM3e | >8 TB/s | H200, GB200 | Next-gen datacenter |

**Workload-Specific Impact:**
- **Image generation (SD/SDXL/Flux):** GDDR6 sufficient—not bandwidth-limited
- **Video generation:** Benefits from GDDR6X due to temporal frame buffers
- **LLM inference (text encoders):** Bandwidth critical—attention mechanisms are quadratic in memory access

**Detection:** GPU queries return memory type; bandwidth calculable from type + bus width + clock speed.

**Specification Impact:** Memory bandwidth tier should influence model size recommendations in text encoder selection. T5-XXL benefits significantly from GDDR6X over GDDR6 on systems running Flux.

### 1.3 Storage Speed (NVMe vs SATA vs HDD)

**Impact:** Model loading time and swap/spillover behavior dramatically affected.

| Storage Type | Sequential Read | 10GB Model Load Time | Swap Performance |
|--------------|-----------------|---------------------|------------------|
| NVMe Gen 4 | 7,000 MB/s | **1.4 seconds** | Acceptable |
| NVMe Gen 3 | 3,500 MB/s | 2.9 seconds | Acceptable |
| SATA SSD | 600 MB/s | **16.7 seconds** | Tolerable |
| HDD | 120-160 MB/s | **83 seconds** | Catastrophic |

**Critical Interaction:** Low RAM + slow storage = severe compounding bottleneck.

| System Configuration | Effective Performance |
|---------------------|----------------------|
| 16GB RAM + NVMe Gen 4 | **Good** (fast swap mitigates RAM limit) |
| 32GB RAM + SATA SSD | Acceptable (RAM headroom compensates) |
| 16GB RAM + SATA SSD | **Poor** (both constraints hit) |
| Any RAM + HDD | **Unusable** for model-heavy workflows |

**Detection:** OS APIs (Windows DeviceIoControl, Linux /sys/block, macOS diskutil) distinguish interface type.

**Specification Impact:**
- Systems with <32GB RAM should display strong NVMe recommendation
- HDD detection should surface clear warning: "AI model loading will be extremely slow"
- Factor into "estimated workflow time" calculations

### 1.4 PCIe Lane Configuration

**Impact:** Affects model loading speed and CPU offload performance, but **not inference speed** once model is loaded.

| PCIe Config | Bandwidth | Impact |
|-------------|-----------|--------|
| PCIe 5.0 x16 | 128 GB/s | Optimal (future-proof) |
| PCIe 4.0 x16 | 64 GB/s | Standard, no bottleneck |
| PCIe 4.0 x8 | 32 GB/s | ~40% slower model loading |
| PCIe 4.0 x4 | 8 GB/s | Chipset slots, significant slowdown |

**When It Matters:**
- **Single-GPU inference:** PCIe NOT a bottleneck after model loads
- **Multi-GPU training:** x8 lanes minimum per GPU; x4 causes 5-10% performance loss
- **CPU offloading workflows:** PCIe bandwidth critical when shuttling between VRAM and RAM

**Detection:** `nvidia-smi -q` or `lspci -vv` returns PCIe generation and lane count.

**Specification Impact:**
- Multi-GPU recommendations should verify x8+ lanes per GPU
- CPU offload workflows should note x16 lanes preferred
- Low lane count (x4) should trigger warning about slow model loading

### 1.5 Power Supply Stability (Inferred)

**Impact:** Insufficient PSU wattage causes voltage drops → GPU throttling. Transient power spikes during GPU boost can trigger protection circuits.

**Detection Challenge:** Direct PSU wattage not queryable via software. However:
- GPU model TDP is known
- System builder often leaves headroom clues (laptop vs desktop)
- Can infer from GPU boost behavior patterns (frequent clock drops without thermal cause)

**Specification Impact:**
- Display estimated power budget: GPU TDP + CPU TDP + 100W headroom
- For RTX 4090 (450W TDP) + high-end CPU: Recommend 850W+ PSU
- For RTX 4060 (115W TDP): 500W sufficient

### 1.6 CPU Single-Thread Performance

**Impact:** Often overlooked, but ComfyUI workflow execution is **single-threaded** (node graph traversal). Slow CPU causes delays between GPU operations.

| CPU Class | Example | Single-Thread Impact |
|-----------|---------|---------------------|
| Modern desktop | Ryzen 7 7800X3D, i7-14700K | Minimal overhead |
| Modern laptop | Ryzen 7 7840U, i7-1365U | Acceptable |
| Older desktop | i5-6600K, Ryzen 5 1600 | Noticeable delays |
| Budget/embedded | Celeron, old Xeon | Significant bottleneck |

**Specific Impacts:**
- Text encoder preprocessing (CLIP, T5) runs on CPU even with GPU available
- Workflow orchestration, image loading/saving, format conversions
- ControlNet preprocessors (OpenPose, depth estimation) often CPU-bound

**Detection:** CPU model queryable via OS APIs; benchmark lookup against known performance database.

**Specification Impact:**
- Weak CPU should trigger "workflow overhead warning"
- Recommend CPU-light preprocessors when CPU bottleneck detected
- Factor into "estimated workflow time" calculations

### 1.7 System RAM Speed

**Impact:** Affects CPU offload performance and any operations running in system memory.

| RAM Type | Speed | CPU Offload Impact |
|----------|-------|-------------------|
| DDR5-5600 | 89.6 GB/s | Near-optimal |
| DDR5-4800 | 76.8 GB/s | Good |
| DDR4-3200 | 51.2 GB/s | Acceptable |
| DDR4-2133 | 34.1 GB/s | Noticeable slowdown |

**Specification Impact:** 
- Low RAM speed + CPU offload = compounded slowdown
- Display RAM speed in system info panel
- Factor into recommendations when --lowvram or --cpu flags active

---

## Part 2: Missing Model Families and Quantization Coverage

### 2.1 Vision-Language Models for Image Understanding/Editing

The original specification omits **Qwen-VL family** and **OmniGen**, which represent a paradigm shift from "SDXL + ControlNet + IPAdapter" pipelines to **unified multimodal understanding and generation**.

#### Qwen2.5-VL / Qwen3-VL

**Architecture:** Vision-language models with native image understanding, operating as both text encoder and visual analyzer.

| Model | Parameters | VRAM (FP16) | VRAM (AWQ 4-bit) | GGUF Support |
|-------|------------|-------------|------------------|--------------|
| Qwen2.5-VL-3B | 3B | 6GB | 3GB | ✅ Q4_K_M |
| Qwen2.5-VL-7B | 7B | 14GB | 5GB | ✅ Full range |
| Qwen2.5-VL-32B | 32B | 64GB | 18GB | ✅ Q4-Q8 |
| Qwen2.5-VL-72B | 72B | 144GB | 40GB | ✅ Q4-Q8 |
| Qwen3-VL-8B | 8B | 16GB | 5GB | ✅ Full range |

**ComfyUI Integration:**
- **ComfyUI-QwenVL** (1038lab): GGUF support added Dec 2025, smart quantization
- **ComfyUI-Qwen2_5-VL** (MakkiShizu): Native video input support
- Auto-download from HuggingFace, 4-bit/8-bit/FP16 on-the-fly quantization

**Use Cases:**
- Image description/captioning for automatic prompt generation
- Visual agent capabilities (computer use, phone use)
- Long video comprehension (1+ hour)
- Event pinpointing in video timelines
- **Qwen-Image-2512**: Uses Qwen2.5-VL as text encoder for superior text rendering

**Specification Impact:**
- Add Qwen2.5-VL-7B to standard text encoder options alongside T5-XXL
- Qwen-Image-2512 should be offered as alternative to Flux for users prioritizing text rendering
- GGUF Q4_K_M enables 7B model on 8GB systems

#### Qwen-Image / Qwen-Image-Edit

**Architecture:** 20B parameter Multimodal Diffusion Transformer (MMDiT) using Qwen2.5-VL as encoder.

| Model | Parameters | VRAM (FP8) | VRAM (Q4_K_M) | Key Feature |
|-------|------------|------------|---------------|-------------|
| Qwen-Image-2512 | 20B | 16GB | 8GB | Best open-source text rendering |
| Qwen-Image-Edit-2511 | 20B | 16GB | 8GB | 1-3 image input, instruction editing |
| Qwen-Image-Layered | 20B | 16GB | 8GB | Layer-aware generation |

**ComfyUI Integration:**
- ComfyUI-GGUF (city96) supports direct loading
- Unsloth provides Q4_K_M through Q8_0 quantizations
- Lightning LoRA available for 4-step generation

**Specification Impact:**
- Position as competitor to Flux for text-heavy use cases
- 8GB VRAM viable via GGUF Q4_K_M
- Include in "Photorealism Preset" as text rendering alternative

#### OmniGen / OmniGen2

**Architecture:** Unified image generation/editing model using natural language instructions instead of separate ControlNets.

| Model | Parameters | VRAM (Native) | VRAM (Q4_K_M) | Architecture |
|-------|------------|---------------|---------------|--------------|
| OmniGen v1 | 15.5B | 24GB | 6GB | Single decoder |
| OmniGen2 | 7B (3B text + 4B image) | 17GB | 5GB | Dual-path transformer |

**Key Innovation:**
- **No separate ControlNet installation required**
- Natural language editing: "Make the sky sunset colors" instead of depth map + mask + inpainting
- Multi-image composition: "Put the cat from image_1 in the scene from image_2"
- In-context learning without fine-tuning

**ComfyUI Integration:**
- **ComfyUI-OmniGen** (1038lab): Auto-download, placeholder syntax for image references
- **Native ComfyUI support** (July 2025): Official OmniGen2 workflows
- GGUF available via calcuis/omnigen2-gguf

**Specification Impact:**
- Recommend for users who find ControlNet intimidating
- "Simplified Editing Preset" using OmniGen2 instead of SDXL + node stack
- T2I ~3-5x faster than I2I/editing due to architecture
- 8GB viable with CPU offload + Q4 GGUF

### 2.2 Distilled/Accelerated Model Variants

The original specification mentions Flux variants but omits comprehensive coverage of distilled SDXL models.

#### SDXL-Lightning (ByteDance)

**Architecture:** Progressive adversarial diffusion distillation from SDXL.

| Variant | Steps | Format | Quality vs Full SDXL |
|---------|-------|--------|---------------------|
| 1-step UNet | 1 | Checkpoint | ~85% |
| 2-step LoRA | 2 | LoRA | ~90% |
| 4-step LoRA | 4 | LoRA | ~95% |
| 8-step LoRA | 8 | LoRA | ~98% |

**Practical Considerations:**
- **Negative prompts ineffective** due to CFG ~1
- LoRA variants combinable with other SDXL LoRAs
- 1-step checkpoint: experimental, useful for realtime preview
- 4-step recommended for quality/speed balance

**ComfyUI Integration:** Standard SDXL loader + LoRA application

#### SDXL-Turbo (Stability AI)

| Feature | Specification |
|---------|---------------|
| Steps | 1-4 (1 recommended) |
| Resolution | 512×512 only (SD1.5 resolution despite SDXL architecture) |
| CFG | Must be 1-2 (higher causes artifacts) |
| Negative prompts | Ineffective |

**Use Case:** Rapid iteration/preview only; final renders should use full SDXL or Lightning.

#### LCM (Latent Consistency Models)

**Key Advantage:** Single LoRA works across step counts (no separate 1-step, 2-step, 4-step files).

| Compatibility | Steps | CFG |
|---------------|-------|-----|
| SDXL | 4-8 | 1-2 |
| SD1.5 | 4-8 | 1-2 |

**ComfyUI Integration:** LCM-specific sampler node required; standard LoRA loader.

#### Hyper-SD (ByteDance)

**Key Innovation:** Trajectory Segmented Consistency Model—can use single LoRA for variable step counts (1-8).

| Model | Steps Supported | CFG | Negative Prompts |
|-------|-----------------|-----|------------------|
| Hyper-SDXL-1step-lora | 1-8 (TCD scheduler) | ~1 | No |
| Hyper-SDXL-8steps-CFG-LoRA | 6-12 | 5-8 | Yes |
| Hyper-SD15-8steps-CFG-LoRA | 6-12 | 5-8 | Yes |
| Hyper-Flux | 8-16 | Variable | Yes |

**CFG-Preserved Variants:** Support guidance_scale 5-8, restoring negative prompt functionality.

**ComfyUI Integration:**
- Requires ComfyUI-TCD custom node for TCD scheduler
- ControlNet compatible
- Available for FLUX, SDXL, and SD1.5

**Specification Impact:**
- **Hyper-SD 8-step CFG-LoRA should be default for SDXL/SD1.5** when speed matters
- Enables negative prompts unlike Lightning/Turbo
- RX 6600 achieves ~1.5 second generations

### 2.3 Additional Image Models

#### Playground v2.5

**Architecture:** SDXL-architecture fine-tune with EDM training framework and human preference alignment.

| Specification | Value |
|---------------|-------|
| Parameters | ~2.6B |
| Native resolution | 1024×1024 |
| VRAM | Same as SDXL (8-12GB) |
| License | Open weights (HuggingFace) |

**Benchmark Performance:**
- Outperforms SDXL by 4.8x on aesthetic preference
- Outperforms DALL-E 3 and Midjourney 5.2 in user studies
- Superior human/portrait rendering

**ComfyUI Integration:**
- Standard SDXL checkpoint loader
- EDMDPMSolverMultistepScheduler default (use DPM++ 2M Karras equivalent)
- guidance_scale=3.0 recommended (lower than typical SDXL)

#### Kolors (Kwai/Kuaishou)

**Architecture:** Large-scale latent diffusion with ChatGLM3 text encoder.

| Specification | Value |
|---------------|-------|
| Model size | 16.5GB (FP16) |
| VRAM | 12-16GB (FP16), 6-8GB (quant8/quant4) |
| Text encoder | ChatGLM3 (quantizable separately) |
| Language support | Bilingual (Chinese/English) |

**Key Features:**
- Superior photorealism with simple prompts
- Complex prompt understanding
- IP-Adapter-Plus and ControlNet support available

**ComfyUI Integration:**
- ComfyUI-KwaiKolorsWrapper (Kijai)
- ChatGLM3 quantization significantly reduces VRAM
- Auto-download from HuggingFace

#### PixArt-Sigma (PixArt-Σ)

**Architecture:** Diffusion Transformer (DiT) with T5 text encoder.

| Specification | Value |
|---------------|-------|
| Parameters | ~900M |
| Native resolution | Up to **4K direct generation** |
| VRAM | 6GB minimum (T5 on CPU) |
| Unique feature | Direct 4K without upscaling |

**Key Advantage:** Only open-source model supporting native 4K generation without post-processing upscale.

**ComfyUI Integration:**
- ComfyUI_ExtraModels (city96)
- T5 can run on CPU with only 6GB VRAM for DiT
- Checkpoints: 256px, 512px, 1024px, 2K available

**Specification Impact:**
- Include in "High Resolution Preset" for users needing 4K output
- Significantly faster than generate-then-upscale workflows
- 6GB VRAM entry point makes it accessible

### 2.4 GGUF Quantization Matrix Update

| Model | Q2_K | Q3_K_M | Q4_K_M | Q5_K_M | Q6_K | Q8_0 | Notes |
|-------|------|--------|--------|--------|------|------|-------|
| Flux.1 Dev | 4GB | 5GB | 6GB | 8GB | 10GB | 12GB | city96, Unsloth |
| Flux.1 Schnell | 4GB | 5GB | 6GB | 8GB | 10GB | 12GB | city96 |
| Qwen-Image-2512 | - | 9GB | 13GB | 15GB | 18GB | 22GB | Unsloth, city96 |
| Qwen2.5-VL-7B | - | 3GB | 4GB | 5GB | 6GB | 8GB | Unsloth, Mungert |
| OmniGen2 | - | 5.8GB | 6GB | 6.15GB | 6.33GB | 6.66GB | calcuis |
| Wan2.2-14B | - | 5GB | 6GB | 7GB | 9GB | 11GB | Community |
| LTX-Video | - | 4GB | 5GB | 6GB | 7GB | 9GB | city96 |

**Quality Retention by Quantization:**
- Q8_0: 98-99% (near-lossless)
- Q6_K: 95% 
- Q5_K_M: 90%
- Q4_K_M: 75-85% (sweet spot for consumer hardware)
- Q3_K_M: 70% (noticeable degradation)
- Q2_K: 60% (concept testing only)

---

## Part 3: Updated Hardware Tier Matrix

Incorporating all factors (VRAM + RAM + bandwidth + storage + thermal + PCIe + CPU):

| VRAM | RAM | Storage | Optimal Models | Key Constraints |
|------|-----|---------|----------------|-----------------|
| 4GB | 16GB | NVMe | SD1.5 only | CPU offload mandatory |
| 6GB | 16GB | NVMe | SD1.5, SDXL Q4, PixArt-Σ | T5 on CPU |
| 8GB | 32GB | NVMe | SDXL, Flux Q4-Q5, Wan2.2-5B | Full capability |
| 8GB | 16GB | SATA | SDXL only | Storage bottleneck |
| 12GB | 32GB | NVMe | Flux FP8, Wan2.2 FP8, Qwen-Image Q6 | Full video |
| 16GB | 64GB | NVMe | Most models FP8, OmniGen2 native | Training viable |
| 24GB | 64GB+ | NVMe | All FP16, multi-model | No constraints |

**Apple Silicon Special Considerations:**
- M3 Max (32GB unified): Flux GGUF Q6-Q8, 2-4x slower than CUDA
- M1/M2 (16GB unified): SD1.5, SDXL GGUF Q4 only
- FP8 unsupported on MPS—use FP16 or GGUF exclusively
- Non-K GGUF variants required (Q4_0, Q5_0, Q8_0)

---

## Part 4: Specification Recommendations

### New Detection Requirements

1. **Thermal Monitor:** Query GPU/CPU temps; surface warnings at >80°C
2. **Memory Bandwidth Tier:** Classify as GDDR6/GDDR6X/HBM; influence text encoder recommendations
3. **Storage Speed Check:** Detect NVMe/SATA/HDD; warn on HDD, recommend NVMe for <32GB RAM
4. **PCIe Lane Query:** Detect generation and lane count; warn on x4 slots
5. **CPU Single-Thread Score:** Benchmark lookup or simple test; factor into time estimates

### New Model Presets

**Text-Rendering Preset (8GB+):**
- Base: Qwen-Image-2512 GGUF Q4_K_M
- Text encoder: Qwen2.5-VL-7B GGUF Q4
- Use case: Posters, signage, text-heavy compositions

**Simplified Editing Preset (8GB+):**
- Base: OmniGen2 with CPU offload
- Replaces: SDXL + ControlNet + IPAdapter stack
- Use case: Users finding node workflows intimidating

**Fast Iteration Preset (8GB+):**
- Base: SDXL + Hyper-SD 8-step CFG-LoRA
- Enables: Negative prompts, 1.5s generations
- Use case: Rapid concepting before final render

**Ultra-Resolution Preset (6GB+):**
- Base: PixArt-Σ 2K/4K
- T5 on CPU mode
- Use case: Direct 4K without upscaling workflow

### Exclusion List Update

Add to "Exclude from default presets":
- Qwen2.5-VL-72B (impractical VRAM)
- OmniGen v1 (superseded by OmniGen2)
- SDXL-Turbo for final output (512×512 limit)
- Non-CFG Lightning/LCM for workflows requiring negative prompts

---

*Research completed: January 2, 2026*
*Sources: HuggingFace, GitHub, ComfyUI documentation, academic papers, community benchmarks*
