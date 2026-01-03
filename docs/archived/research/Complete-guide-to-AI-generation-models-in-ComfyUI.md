# Complete guide to AI generation models in ComfyUI (Late 2025)

ComfyUI has evolved into the most comprehensive open-source AI generation platform, supporting **100+ models** across image, video, audio, and 3D generation—both local execution and cloud API access. The Wan 2.2 family dominates local video generation with specialized variants for every use case, while Partner Nodes provide seamless access to Veo3, Kling 2.0, and Sora-2 without individual API management. Most critically for hardware-constrained users, GGUF quantization now enables running **14B parameter models on 8GB GPUs**.

---

## Image generation models deliver text rendering breakthrough

The late 2025 landscape features a clear hierarchy: **HiDream-I1** (17B parameters) produces the highest quality images using a hybrid DiT+MoE architecture with four CLIP encoders, while **Z-Image-Turbo** (6B) achieves sub-second inference with excellent bilingual text rendering. Alibaba's **Ovis-Image** specifically targets text accuracy, scoring 0.92 on the CVTG-2K benchmark—outperforming both GPT-4o and Qwen-Image.

| Model | Parameters | FP16 VRAM | FP8 VRAM | GGUF Q4 | Resolution | License |
|-------|-----------|-----------|----------|---------|------------|---------|
| HiDream-I1 Full | 17B | 48GB | 24GB | ~10GB | 1024×1024 | MIT |
| HiDream-I1 Fast | 17B | 27GB | 16GB | ~10GB | 1024×1024 | MIT |
| Z-Image-Turbo | 6B | 16GB | 8GB | N/A | Up to 2048² | Apache 2.0 |
| Ovis-Image | 7B | 16GB | N/A | N/A | 1024×768 | Apache 2.0 |
| Chroma1-HD | 8.9B | 24GB | N/A | ~8GB | 1024×1024 | Apache 2.0 |
| FLUX.1-Dev | 12B | 33GB | 12GB | ~8GB | Up to 2048² | Non-commercial |
| FLUX.1-Schnell | 12B | 24GB | 12GB | ~6GB | Up to 2048² | Apache 2.0 |
| SD3.5 Large | 8B | 20GB | 12GB | N/A | 1024×1024 | Community License |
| SD3.5 Medium | 2.6B | 8GB | N/A | N/A | Up to 1440² | Community License |
| Playground v2.5 | 3.5B | 12GB | N/A | N/A | 1024×1024 | Community License |
| Kolors | 7B | 13GB | 8GB | ~4GB | 1024×1024 | Academic/Commercial |
| PixArt-Σ | 600M+T5 | 20GB | 6GB | N/A | Up to 4K | Non-commercial |

The **SDXL ecosystem** remains the most accessible entry point with variants optimized for speed: Lightning (2-8 steps), Turbo (1-4 steps), LCM, and Hyper-SD all run on **8-12GB VRAM** while maintaining 1024×1024 output quality.

---

## Image editing models now rival commercial solutions

**ChronoEdit 14B** from NVIDIA represents a paradigm shift—it treats image editing as a video generation task, using temporal reasoning to preserve physics, lighting, and geometry. Running at **~34GB FP16** or significantly less with Kijai's FP8 optimized weights, it's already integrated into ComfyUI templates.

| Model | Parameters | FP16 VRAM | FP8 VRAM | GGUF Q4 | Edit Type | License |
|-------|-----------|-----------|----------|---------|-----------|---------|
| ChronoEdit 14B | 14B | 34-38GB | Available | Available | Physics-aware instruction | Apache 2.0 |
| Qwen-Image-Edit 2511 | 20B | 40GB | 16GB | ~12GB | Multi-image, text editing | Apache 2.0 |
| Qwen-Image-Layered | 20B | 40GB | 16GB | Available | RGBA layer decomposition | Apache 2.0 |
| OmniGen2 | 7B | 17GB | N/A | N/A | Instruction, multi-image | Apache 2.0 |
| OmniGen v1 | 3.8B | 15.5GB | Available | N/A | Multi-reference editing | MIT |
| ICEdit | ~200M LoRA | 14GB | N/A | N/A | Mask-based, sequential | FLUX license |
| Step1X-Edit | Large | 46GB | 31GB | N/A | 11 edit categories | Apache 2.0 |
| FLUX.1 Fill | 12B | 24GB | Available | ~8GB | Inpainting/outpainting | Non-commercial |
| InstructPix2Pix | 1B | 6GB | N/A | N/A | Basic instruction | CreativeML |

**Qwen-Image-Edit 2511** (December 2025) brought major improvements in character consistency and multi-person handling, while **Qwen-Image-Layered** enables decomposing images into independent RGBA layers for surgical edits. For low-VRAM systems, **ICEdit** achieves competitive results using just a 200M LoRA with optional Nunchaku acceleration down to **4GB VRAM**.

---

## Wan 2.2 family delivers complete video production toolkit

The Wan model family from Alibaba represents the most comprehensive open-source video generation system, with **specialized variants for every production need**. The MoE (Mixture of Experts) architecture in Wan 2.2 splits models into high-noise and low-noise components, requiring both loaded for optimal quality.

### Wan 2.2 core variants and VRAM requirements

| Variant | Purpose | Parameters | FP16 VRAM | FP8 VRAM | Q8 GGUF | Q4 GGUF | Resolution |
|---------|---------|-----------|-----------|----------|---------|---------|------------|
| T2V 14B | Text-to-video | 14B×2 | ~60GB total | ~28GB | 15.4GB | 9.6GB | 720P |
| I2V 14B | Image-to-video | 14B×2 | ~57GB total | ~28GB | 15.4GB | 9.6GB | 720P |
| TI2V 5B | Hybrid T2V+I2V | 5B | 10GB | 5-6GB | 5.4GB | 3.4GB | 720P |
| FLF2V 14B | First-last-frame | 14B | Uses I2V | Uses I2V | Uses I2V | Uses I2V | 720P |
| Fun Camera 14B | Camera control | 14B | ~32GB | 14-15GB | N/A | N/A | 720P |
| Fun Control 14B | Pose/depth/canny | 14B | ~32GB | 14-16GB | N/A | N/A | 720P |
| Fun Inpaint 14B | Video inpainting | 14B | ~32GB | 14-16GB | N/A | N/A | Up to 1024² |
| Animate 14B | Character animation | 14B | ~32GB | 16-18GB | 18.7GB | 11.5GB | 720P |
| S2V 14B | Speech-to-video | 14B | 32.6GB | 16.4GB | 19.6GB | 13.9GB | 720P |

### Wan 2.1 variants for lightweight deployment

| Variant | Parameters | FP16 VRAM | FP8 VRAM | Best For |
|---------|-----------|-----------|----------|----------|
| T2V 14B | 14B | 28GB | 14GB | High quality |
| T2V 1.3B | 1.3B | 8.2GB | 4-5GB | Consumer GPUs |
| I2V 14B-720P | 14B | 28GB | 14-16GB | HD output |
| VACE 14B | 14B | 28-32GB | N/A | Composable editing |
| VACE 1.3B | 1.3B | 6-8GB | N/A | Low VRAM editing |

**Critical insight**: The **TI2V 5B** model is the breakthrough for consumer hardware—combining both T2V and I2V capabilities in a single **10GB FP16** or **5GB FP8** footprint, with GGUF Q4 dropping to just **3.4GB**. This runs comfortably on an RTX 3060.

**LightX2V LoRA** enables 4-step generation (vs default 50 steps), delivering **20x speedup**—reducing RTX 4090 generation time from ~12 minutes to ~3.5 minutes for 81-frame videos.

### Apple Silicon compatibility

MPS support remains experimental with these workarounds:
- Use GGUF Q5/Q6 quantized models via ComfyUI-GGUF
- Set `PYTORCH_ENABLE_MPS_FALLBACK=1`
- Use Euler sampler with normal scheduler
- Expect ~5 minutes for 2-second low-res clips on M4 Pro

---

## Other local video models fill specialized niches

Beyond Wan, several models offer distinct advantages for specific workflows:

| Model | Parameters | Min VRAM | Recommended | T2V | I2V | FLF2V | Best For |
|-------|-----------|----------|-------------|-----|-----|-------|----------|
| HunyuanVideo 1.5 | 8.3B | 8GB (GGUF) | 24GB | ✅ | ❌ | ❌ | Cinematic camera |
| HunyuanVideo-I2V | 13B | 12GB (GGUF) | 60GB | ❌ | ✅ | ❌ | Image animation |
| LTX-Video 2B | 2B | 6GB | 10GB | ✅ | ✅ | ✅ | Real-time generation |
| LTX-Video 13B | 13B | 10GB | 24GB | ✅ | ✅ | ✅ | Quality + speed |
| CogVideoX-2B | 2B | 6GB | 8GB | ✅ | ❌ | ❌ | Entry point |
| CogVideoX-5B | 5B | 12GB | 16GB | ✅ | ✅ | ❌ | Budget mid-range |
| Mochi 1 | 10B | 12GB | 24GB | ✅ | Via encoder | ❌ | Motion quality |
| AnimateDiff SD1.5 | Module | 6GB | 10GB | ✅ | Via ControlNet | ❌ | Infinite animation |
| Pyramid Flow | SD3-based | 8GB | 12GB | ✅ | ✅ | ❌ | 10-second videos |
| Kandinsky 5 Lite | 2B | 16GB | 24GB | ✅ | ✅ | ❌ | Bilingual prompts |
| Open-Sora 2.0 | 11B | 16GB | 24GB | ✅ | ✅ | ❌ | Research |

**LTX-Video** stands out for real-time generation—the 2B model produces video in **5-10 seconds** on RTX 4090, while the 13B distilled version achieves high quality in 4-8 steps. The Apache 2.0/OpenRail-M licensing makes these commercially viable.

---

## Partner Nodes unlock commercial video APIs

ComfyUI's Partner Node system provides one-click access to commercial APIs using unified credits—no individual API key management required.

### Video API capabilities matrix

| Service | Versions | T2V | I2V | FLF2V | Camera Control | Character Consistency | Max Duration | Audio |
|---------|----------|-----|-----|-------|----------------|----------------------|--------------|-------|
| **Google Veo** | 2, 3, 3.1, fast | ✅ | ✅ | ✅ (3.1) | ✅ | Via prompts | 8 sec | ✅ (3+) |
| **Kling** | 2.0, 1.6, 1.5, O1 | ✅ | ✅ | ✅ | ✅ Full suite | Dual character refs | 10 sec | Lip sync |
| **Luma Ray** | 3, 2, flash-2 | ✅ | ✅ | ✅ Keyframes | ✅ | Reference images | 10 sec | ✅ (Ray2+) |
| **Runway** | Gen3a, Gen4 Turbo | ✅ | ✅ | ✅ | Via prompts | Image references | 10 sec | ❌ |
| **OpenAI Sora** | 2, 2 Pro | ✅ | ✅ | ❌ | ❌ | Via prompts | 12 sec | ✅ Native |
| **MiniMax/Hailuo** | Hailuo-02, S2V-01 | ✅ | ✅ | ✅ | Via prompts | S2V-01 subject ref | 10 sec | ❌ |
| **Vidu** | Multiple | ✅ | ✅ | ✅ | ❌ | Ref2V mode | 10 sec | ❌ |
| **PixVerse** | V4 | ✅ | ✅ | ❌ | ❌ | Via prompts | Variable | ❌ |

**Kling 2.0** offers the most complete feature set with full camera control, dual character consistency, virtual try-on, and lip sync—all accessible through Partner Nodes. **Veo3** uniquely generates synchronized audio natively, while **Luma Ray3** pushes quality to 4K HDR with "Hi-Fi Diffusion mastering."

### Image API pricing (approximate ComfyUI credits)

| Service | Models | Cost/Image |
|---------|--------|------------|
| FLUX Pro | Standard | ~$0.04 |
| FLUX Pro Ultra | 4MP output | ~$0.06 |
| GPT-Image-1 | Standard | $0.02-0.08 |
| DALL·E 3 | HD | ~$0.04-0.12 |
| Stability Ultra | Premium | ~$0.08 |
| Ideogram V3 | Typography | ~$0.08 |
| Recraft V3 | Design | ~$0.04 |

**Note**: Midjourney has **no official API integration**—only third-party proxy services (ComfyUI-MidjourneyNode) provide unofficial access.

---

## Audio generation spans voice cloning to full songs

| Model | Type | Parameters | VRAM | Voice Cloning | Languages | License |
|-------|------|-----------|------|---------------|-----------|---------|
| F5-TTS | TTS/Clone | ~1.2GB | 6GB | ✅ High (5-15s sample) | 9+ | Apache 2.0 |
| Kokoro TTS | TTS | 82M | Low/CPU | ❌ Presets only | 9 | Apache 2.0 |
| XTTS v2 | TTS/Clone | N/A | 4-8GB | ✅ Excellent (6s) | 17 | CPML |
| Bark | TTS/SFX | ~1B | 8-12GB | ⚠️ Limited | 13+ | MIT |
| MusicGen | Music | 300M-3.3B | 8-16GB | N/A | EN prompts | CC-BY-NC |
| ACE-Step | Music/Vocals | 3.5B | 8-16GB | ✅ Vocals | Multi | Apache 2.0 |
| Stable Audio Open | Music/SFX | ~4.7GB | 8-12GB | N/A | EN prompts | Commercial-safe |
| WhisperSpeech | TTS/Clone | Varies | 4-8GB | ✅ On-the-fly | 3+ | Apache 2.0 |

**TTS Audio Suite** consolidates 8+ engines (F5-TTS, ChatterBox, Higgs Audio 2, VibeVoice, IndexTTS-2 with emotion control) into a single comprehensive node pack supporting **23+ languages**, SRT subtitle timing, and multi-character switching.

**ACE-Step** (3.5B) generates full-length songs with lyrics and voice cloning—producing 4 minutes of music in 20 seconds on A100.

---

## 3D generation achieves production-ready quality

| Model | Parameters | Min VRAM | Full Pipeline | Input | Output | License |
|-------|-----------|----------|---------------|-------|--------|---------|
| Hunyuan3D 2-mini | 0.6B shape | 5GB | 8GB | Image/text | GLB with PBR | Open |
| Hunyuan3D 2.1 | 3.3B shape + 1.3B texture | 6GB shape | 24GB full | Image/text | GLB with PBR | Open |
| TRELLIS.2 | 4B | 8GB | 24GB | Image/text | Mesh/Gaussians/PBR | MIT |
| TripoSR | ~300M | 7GB | 8GB | Single image | UV-unwrapped mesh | MIT |
| InstantMesh | ~1B | 10GB | 12GB | Single image | Textured mesh | Apache 2.0 |
| StableFast3D | N/A | 7GB | 8GB | Single image | RGB textured mesh | Stability |
| Zero123++ | ~1B | 6-8GB | 8GB | Single image | Multi-view images | Various |
| SV3D | SVD-based | 10-12GB | 12GB | Single image | Orbital video | Community |

**Hunyuan3D 2.1** uses a two-stage pipeline (shape generation → texture painting) producing production-ready GLB files with PBR materials. The **2-mini** variant runs full pipeline in just **5GB VRAM**.

**TRELLIS.2** (December 2025) from Microsoft handles complex topologies with transparency support, generating meshes in **3-60 seconds** at resolutions up to 1536³.

---

## Lip sync models enable talking head generation

| Model | Parameters | Min VRAM | Recommended | Input | Quality |
|-------|-----------|----------|-------------|-------|---------|
| Wav2Lip | ~100M | 4GB | 6GB | Video + 16kHz audio | Good lip sync |
| LatentSync 1.6 | ~5GB models | 6.5GB | 20GB | Video + audio | High (512×512) |
| SadTalker | Multiple | 6GB | 8GB | Image + audio | Realistic head motion |
| LivePortrait | Multiple | 8GB | 12GB | Image + driving video | Facial reenactment |
| AniPortrait | SD1.5-based | 8GB | 10GB | Image + audio | Audio-driven |
| HuMo 1.7B | 1.7B | 10GB | 16GB | Text/image/audio | Multimodal |
| HuMo 14B/17B | 14-17B | 24GB | 48GB | Text/image/audio | Highest quality |

**LatentSync 1.6** from ByteDance delivers the best lip clarity using audio-conditioned latent diffusion, while **LivePortrait** (Kuaishou) excels at facial reenactment from driving videos. **HuMo** combines all modalities—text, image, and audio conditioning—for complete human-centric video generation.

---

## Platform support and hardware recommendations

### NVIDIA CUDA (full support)
All models work on NVIDIA GPUs with CUDA. **RTX 4090 (24GB)** handles most workflows; **RTX 3060 (12GB)** runs quantized models effectively.

### AMD ROCm (limited support)
Basic functionality for SD/SDXL, Flux, AnimateDiff. Video models have experimental support. Set `HSA_OVERRIDE_GFX_VERSION` for compatibility.

### Apple Silicon MPS (experimental)

| Category | Status | Workaround |
|----------|--------|------------|
| Image (SD/SDXL/Flux) | ✅ Working | Native |
| Wan video | ⚠️ Limited | GGUF + Euler sampler |
| HunyuanVideo | ❌ BF16 issues | Not recommended |
| 3D (native nodes) | ✅ Working | Use Hunyuan3D native |
| Audio | ✅ Most work | F5-TTS, Kokoro tested |

### VRAM tiers and recommended models

| VRAM | Image | Video | 3D | Audio |
|------|-------|-------|-----|-------|
| **6-8GB** | SD3.5 Medium, Z-Image FP8 | Wan TI2V 5B Q4, LTX 2B | Hunyuan3D mini | F5-TTS, Kokoro |
| **12GB** | FLUX Dev FP8, HiDream Q4 | Wan 2.1 14B Q4, CogVideoX | TripoSR | All TTS |
| **24GB** | All FP8 | Wan 2.2 FP8, HunyuanVideo | Hunyuan3D 2.1 full | All including ACE-Step |
| **48GB+** | All FP16 | Wan 2.2 FP16, HuMo 14B | TRELLIS.2 max | Production workflows |

---

## Conclusion

ComfyUI's model ecosystem has reached a critical inflection point where **open-source alternatives match or exceed commercial offerings** in most categories. The Wan 2.2 family's specialized variants cover virtually every video production need, GGUF quantization democratizes access to massive models on consumer hardware, and Partner Nodes eliminate API management friction for commercial services.

Three trends define the late 2025 landscape: **text rendering quality** (Ovis-Image, Z-Image-Turbo), **physics-aware editing** (ChronoEdit), and **multimodal conditioning** (HuMo, ACE-Step). For practitioners building production workflows, the winning strategy combines local Wan models for iteration with API access to Veo3/Kling 2.0 for final renders—all orchestrated through ComfyUI's unified interface.

The most significant accessibility breakthrough is the **Wan TI2V 5B** model: full T2V and I2V capabilities in 3.4GB GGUF Q4, running on any modern GPU. This single model eliminates the traditional hardware barrier to video generation.