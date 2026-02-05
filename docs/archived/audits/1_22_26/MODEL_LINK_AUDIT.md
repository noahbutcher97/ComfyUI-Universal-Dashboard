# Model Link & Schema Validation Report
**Date:** 2026-01-22 12:09

## Summary
- **Total Variants Checked:** 466
- **Valid:** 294
- **Invalid:** 172
- **Warnings:** 133

## Failures & Warnings
| Model | Variant | Status | Message |
|-------|---------|--------|---------|
| comfyui_fal | repository | 🔴 fail | HTTP 404 |
| comfyui_runpod | repository | 🔴 fail | HTTP 404 |
| hidream_i1_full | fp16 | ⚠️ warning | Size mismatch: DB=34.00GB, Real=0.00GB |
| hidream_i1_full | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| hidream_i1_full | gguf_q4 | 🔴 fail | Unreachable: HTTP 401 |
| hidream_i1_fast | fp16 | 🔴 fail | Missing download_url |
| hidream_i1_fast | fp8 | 🔴 fail | Missing download_url |
| flux_dev | fp16 | ⚠️ warning | Size mismatch: DB=23.80GB, Real=0.00GB |
| flux_dev | fp8 | ⚠️ warning | Size mismatch: DB=12.00GB, Real=0.00GB |
| flux_dev | gguf_q8 | ⚠️ warning | Size mismatch: DB=12.00GB, Real=0.00GB |
| flux_dev | gguf_q5 | 🔴 fail | Missing download_url |
| flux_dev | gguf_q4 | 🔴 fail | Missing download_url |
| flux_schnell | fp16 | ⚠️ warning | Size mismatch: DB=23.80GB, Real=0.00GB |
| flux_schnell | fp8 | 🔴 fail | Missing download_url |
| flux_schnell | gguf_q4 | 🔴 fail | Missing download_url |
| sd35_large | fp16 | 🔴 fail | Missing download_url |
| sd35_large | fp8 | 🔴 fail | Missing download_url |
| sd35_medium | fp16 | 🔴 fail | Missing download_url |
| sdxl_base | fp16 | 🔴 fail | Missing download_url |
| sdxl_base | gguf_q4 | 🔴 fail | Missing download_url |
| sd15 | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| sd15 | fp32 | 🔴 fail | Missing download_url |
| sd15_inpainting | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| pony_v6 | gguf_q4 | 🔴 fail | Missing download_url |
| illustrious_xl | fp16 | ⚠️ warning | Size mismatch: DB=6.50GB, Real=0.00GB |
| illustrious_xl | gguf_q4 | 🔴 fail | Missing download_url |
| noobai_xl | gguf_q4 | 🔴 fail | Missing download_url |
| realvis_xl | gguf_q4 | 🔴 fail | Missing download_url |
| juggernaut_xl_v9 | gguf_q4 | 🔴 fail | Missing download_url |
| dreamshaper_xl | gguf_q4 | 🔴 fail | Missing download_url |
| animagine_xl_v3 | fp16 | ⚠️ warning | Size mismatch: DB=6.50GB, Real=0.00GB |
| animagine_xl_v3 | gguf_q4 | 🔴 fail | Missing download_url |
| playground_v25 | fp16 | ⚠️ warning | Size mismatch: DB=6.50GB, Real=0.00GB |
| pixart_sigma | fp16 | ⚠️ warning | Size mismatch: DB=2.50GB, Real=0.00GB |
| stable_cascade | bf16 | ⚠️ warning | Size mismatch: DB=10.20GB, Real=0.00GB |
| kandinsky_3 | fp16 | ⚠️ warning | Size mismatch: DB=11.80GB, Real=0.00GB |
| proteus_xl | fp16 | 🔴 fail | Unreachable: HTTP 404 |
| qwen_image | bf16 | ⚠️ warning | Size mismatch: DB=40.00GB, Real=0.00GB |
| qwen_image | fp8 | ⚠️ warning | Size mismatch: DB=20.00GB, Real=0.00GB |
| qwen_image | dfloat11_offload | ⚠️ warning | Size mismatch: DB=22.00GB, Real=0.00GB |
| z_image_turbo | bf16 | ⚠️ warning | Size mismatch: DB=12.00GB, Real=0.00GB |
| z_image_turbo | fp8 | ⚠️ warning | Size mismatch: DB=6.00GB, Real=0.00GB |
| z_image_turbo | gguf_q4 | ⚠️ warning | Size mismatch: DB=4.00GB, Real=0.00GB |
| z_image_turbo | gguf_q8 | ⚠️ warning | Size mismatch: DB=6.50GB, Real=0.00GB |
| z_image_base | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| glm_image | bf16 | ⚠️ warning | Size mismatch: DB=32.00GB, Real=0.00GB |
| glm_image | fp8 | ⚠️ warning | Size mismatch: DB=16.00GB, Real=0.00GB |
| glm_image | sdnq_4bit | ⚠️ warning | Size mismatch: DB=10.00GB, Real=0.00GB |
| wan_22_t2i | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_22_t2i | gguf_q4 | 🔴 fail | Unreachable: HTTP 401 |
| qwen_image_2512 | bf16 | ⚠️ warning | Size mismatch: DB=40.00GB, Real=0.00GB |
| qwen_image_2512 | fp8 | ⚠️ warning | Size mismatch: DB=20.00GB, Real=0.00GB |
| qwen_image_2512 | gguf_q4 | ⚠️ warning | Size mismatch: DB=13.00GB, Real=0.00GB |
| qwen_image_lightning | bf16_lora | ⚠️ warning | Size mismatch: DB=1.50GB, Real=0.00GB |
| qwen_image_2512_lightning | bf16_lora | ⚠️ warning | Size mismatch: DB=1.50GB, Real=0.00GB |
| qwen_image_layered | bf16 | ⚠️ warning | Size mismatch: DB=40.00GB, Real=0.00GB |
| qwen_image_layered | gguf_q4 | ⚠️ warning | Size mismatch: DB=13.00GB, Real=0.00GB |
| hunyuan_image_3 | bf16 | ⚠️ warning | Size mismatch: DB=170.00GB, Real=0.00GB |
| hunyuan_image_3 | nf4 | ⚠️ warning | Size mismatch: DB=45.00GB, Real=0.00GB |
| flux2_klein_9b | bf16 | ⚠️ warning | Size mismatch: DB=18.00GB, Real=0.00GB |
| flux2_klein_9b | fp8 | ⚠️ warning | Size mismatch: DB=9.00GB, Real=0.00GB |
| flux2_klein_4b | bf16 | ⚠️ warning | Size mismatch: DB=8.00GB, Real=0.00GB |
| flux2_klein_4b | fp8 | ⚠️ warning | Size mismatch: DB=4.00GB, Real=0.00GB |
| flux2_klein_4b | nvfp4 | ⚠️ warning | Size mismatch: DB=2.50GB, Real=0.00GB |
| flux2_klein_base_9b | bf16 | ⚠️ warning | Size mismatch: DB=18.00GB, Real=0.00GB |
| flux2_klein_base_9b | fp8 | ⚠️ warning | Size mismatch: DB=9.00GB, Real=0.00GB |
| flux2_klein_base_4b | bf16 | ⚠️ warning | Size mismatch: DB=8.00GB, Real=0.00GB |
| flux1_kontext_dev | bf16 | ⚠️ warning | Size mismatch: DB=24.00GB, Real=0.00GB |
| flux1_kontext_dev | fp8 | 🔴 fail | Missing download_url |
| sana_1600m | bf16 | ⚠️ warning | Size mismatch: DB=3.20GB, Real=0.00GB |
| sana_1600m | int4 | 🔴 fail | Missing download_url |
| sana_4800m | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| sana_4800m | int4 | 🔴 fail | Missing download_url |
| vibe_image_edit | bf16 | ⚠️ warning | Size mismatch: DB=7.20GB, Real=0.00GB |
| chroma_unlocked | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| chroma_unlocked | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| chroma_unlocked | gguf_q4 | 🔴 fail | Unreachable: HTTP 401 |
| chroma_unlocked_v11 | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| chroma_unlocked_v11 | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| chroma_hd | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| chroma_hd | fp8_scaled | 🔴 fail | Unreachable: HTTP 401 |
| chroma_radiance | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| chroma_radiance | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| cosmos_predict2_t2i | bf16 | ⚠️ warning | Size mismatch: DB=4.00GB, Real=0.00GB |
| cosmos_predict2_t2i | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| flux_fill_dev | bf16 | ⚠️ warning | Size mismatch: DB=23.80GB, Real=0.00GB |
| flux_fill_dev | fp8 | ⚠️ warning | Size mismatch: DB=11.90GB, Real=0.00GB |
| flux_fill_dev | gguf_q4 | 🔴 fail | Unreachable: HTTP 401 |
| flux_canny_dev | bf16 | ⚠️ warning | Size mismatch: DB=23.80GB, Real=0.00GB |
| flux_canny_dev | fp8 | ⚠️ warning | Size mismatch: DB=11.90GB, Real=0.00GB |
| flux_depth_dev | bf16 | ⚠️ warning | Size mismatch: DB=23.80GB, Real=0.00GB |
| flux_depth_dev | fp8 | ⚠️ warning | Size mismatch: DB=11.90GB, Real=0.00GB |
| flux_redux_dev | bf16 | ⚠️ warning | Size mismatch: DB=23.80GB, Real=0.00GB |
| kandinsky_5_lite | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| kandinsky_5_lite | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| lotus_depth_d | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| lotus_depth_g | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| lotus_normal_g | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| humo_17b | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| humo_17b | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| humo_17b | gguf_q4 | 🔴 fail | Unreachable: HTTP 401 |
| ovis_image | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| omnigen | fp16 | ⚠️ warning | Size mismatch: DB=7.60GB, Real=0.00GB |
| omnigen | gguf_q4 | 🔴 fail | Missing download_url |
| instructpix2pix | fp16 | ⚠️ warning | Size mismatch: DB=4.00GB, Real=0.00GB |
| sdxl_inpainting | fp16 | ⚠️ warning | Size mismatch: DB=6.50GB, Real=0.00GB |
| qwen_image_edit | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| qwen_image_edit | fp8 | 🔴 fail | Missing download_url |
| qwen_image_edit | gguf_q4 | 🔴 fail | Missing download_url |
| qwen_image_edit_2511 | bf16 | ⚠️ warning | Size mismatch: DB=40.00GB, Real=0.00GB |
| qwen_image_edit_2511 | fp8 | ⚠️ warning | Size mismatch: DB=20.00GB, Real=0.00GB |
| qwen_image_edit_2511 | dfloat11_offload | ⚠️ warning | Size mismatch: DB=22.00GB, Real=0.00GB |
| qwen_image_edit_2511_lightning | bf16_lora | ⚠️ warning | Size mismatch: DB=1.50GB, Real=0.00GB |
| qwen_image_edit_2511_lightning | fp8_lora | ⚠️ warning | Size mismatch: DB=1.50GB, Real=0.00GB |
| z_image_edit | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| z_image_edit | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| hidream_edit | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| hidream_edit | gguf_q8 | 🔴 fail | Missing download_url |
| hidream_edit | gguf_q4 | 🔴 fail | Missing download_url |
| flux_kontext | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| flux_kontext | gguf_q8 | 🔴 fail | Missing download_url |
| flux_kontext | gguf_q4 | 🔴 fail | Missing download_url |
| chromaedit | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| ic_light | fp16 | ⚠️ warning | Size mismatch: DB=2.80GB, Real=0.00GB |
| instantid | fp16 | ⚠️ warning | Size mismatch: DB=1.70GB, Real=0.00GB |
| pulid | fp16 | ⚠️ warning | Size mismatch: DB=1.20GB, Real=0.00GB |
| sam2_large | fp16 | ⚠️ warning | Size mismatch: DB=1.30GB, Real=0.00GB |
| depth_anything_v2_large | fp16 | ⚠️ warning | Size mismatch: DB=0.66GB, Real=0.00GB |
| wan_22_t2v_14b | fp16 | 🔴 fail | Missing download_url |
| wan_22_t2v_14b | fp8 | 🔴 fail | Missing download_url |
| wan_22_t2v_14b | gguf_q8 | 🔴 fail | Missing download_url |
| wan_22_t2v_14b | gguf_q4 | 🔴 fail | Missing download_url |
| wan_22_i2v_14b | fp16 | 🔴 fail | Missing download_url |
| wan_22_i2v_14b | fp8 | 🔴 fail | Missing download_url |
| wan_22_i2v_14b | gguf_q5 | 🔴 fail | Missing download_url |
| wan_22_i2v_14b | gguf_q4 | 🔴 fail | Missing download_url |
| wan_22_ti2v_5b | fp16 | 🔴 fail | Missing download_url |
| wan_22_ti2v_5b | fp8 | 🔴 fail | Missing download_url |
| wan_22_ti2v_5b | gguf_q8 | 🔴 fail | Missing download_url |
| wan_22_ti2v_5b | gguf_q4 | 🔴 fail | Missing download_url |
| ltx_video_2b | fp16 | 🔴 fail | Missing download_url |
| ltx_video_2b | fp8 | 🔴 fail | Missing download_url |
| ltx_video_13b | fp16 | 🔴 fail | Missing download_url |
| ltx_video_13b | fp8 | 🔴 fail | Missing download_url |
| ltx_video_2_19b | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| ltx_video_2_19b | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| ltx_video_2_19b_distilled | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| ltx_video_2_19b_distilled | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| animatediff_sd15 | fp16 | 🔴 fail | Missing download_url |
| cogvideox_5b | fp16 | ⚠️ warning | Size mismatch: DB=10.00GB, Real=0.00GB |
| cogvideox_5b | int8 | 🔴 fail | Missing download_url |
| cogvideox_2b | fp16 | ⚠️ warning | Size mismatch: DB=4.00GB, Real=0.00GB |
| mochi_1_preview | bf16 | ⚠️ warning | Size mismatch: DB=20.00GB, Real=0.00GB |
| svd_xt | fp16 | ⚠️ warning | Size mismatch: DB=3.10GB, Real=0.00GB |
| svd | fp16 | ⚠️ warning | Size mismatch: DB=3.00GB, Real=0.00GB |
| hunyuan_video | bf16 | ⚠️ warning | Size mismatch: DB=26.00GB, Real=0.00GB |
| opensora_12 | fp16 | ⚠️ warning | Size mismatch: DB=4.50GB, Real=0.00GB |
| dynamicrafter | fp16 | ⚠️ warning | Size mismatch: DB=5.80GB, Real=0.00GB |
| tooncrafter | fp16 | ⚠️ warning | Size mismatch: DB=5.80GB, Real=0.00GB |
| pyramid_flow | bf16 | ⚠️ warning | Size mismatch: DB=8.50GB, Real=0.00GB |
| hunyuanvideo_15_t2v | bf16_480p | ⚠️ warning | Size mismatch: DB=16.60GB, Real=0.00GB |
| hunyuanvideo_15_t2v | bf16_720p | ⚠️ warning | Size mismatch: DB=16.60GB, Real=0.00GB |
| hunyuanvideo_15_t2v | bf16_1080p | ⚠️ warning | Size mismatch: DB=16.60GB, Real=0.00GB |
| hunyuanvideo_15_t2v | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| hunyuanvideo_15_t2v | gguf_q8 | 🔴 fail | Unreachable: HTTP 401 |
| hunyuanvideo_15_i2v | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| hunyuanvideo_15_i2v | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| hunyuanvideo_15_cfg_distilled | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| hunyuanvideo_15_cfg_distilled | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| hunyuanvideo_15_step_distilled | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| hunyuanvideo_15_step_distilled | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| cosmos_predict2_v2w | fp16 | ⚠️ warning | Size mismatch: DB=4.00GB, Real=0.00GB |
| cosmos_predict2_v2w | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| wan_fun_control | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_fun_control | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| wan_fun_camera | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_fun_camera | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| wan_fun_inpaint | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_fun_inpaint | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| wan_vace_14b | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_vace_14b | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| wan_vace_1_3b | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_vace_1_3b | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| wan_phantom | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_phantom | gguf_q4 | 🔴 fail | Unreachable: HTTP 401 |
| wan_skyreels | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_skyreels | gguf_q4 | 🔴 fail | Unreachable: HTTP 401 |
| wan_anisora | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_anisora | gguf_q4 | 🔴 fail | Unreachable: HTTP 401 |
| wan_fast | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan_fast | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| clip_vit_large | fp16 | ⚠️ warning | Size mismatch: DB=0.80GB, Real=0.00GB |
| blip2_opt_2_7b | fp16 | ⚠️ warning | Size mismatch: DB=5.40GB, Real=0.00GB |
| blip2_opt_2_7b | int8 | 🔴 fail | Missing download_url |
| florence2_large | fp16 | ⚠️ warning | Size mismatch: DB=1.50GB, Real=0.00GB |
| joycaption_alpha_two | fp16 | ⚠️ warning | Size mismatch: DB=16.00GB, Real=0.00GB |
| joycaption_alpha_two | gguf_q4 | 🔴 fail | Missing download_url |
| cogvlm2_llama3_chat | bf16 | ⚠️ warning | Size mismatch: DB=38.00GB, Real=0.00GB |
| cogvlm2_llama3_chat | gguf_q4 | 🔴 fail | Missing download_url |
| llava_v1_6_34b | fp16 | ⚠️ warning | Size mismatch: DB=68.00GB, Real=0.00GB |
| llava_v1_6_34b | gguf_q4 | 🔴 fail | Missing download_url |
| llava_v1_6_7b | fp16 | ⚠️ warning | Size mismatch: DB=14.00GB, Real=0.00GB |
| llava_v1_6_7b | gguf_q4 | 🔴 fail | Missing download_url |
| internvl2_8b | bf16 | ⚠️ warning | Size mismatch: DB=16.00GB, Real=0.00GB |
| internvl2_8b | gguf_q4 | 🔴 fail | Missing download_url |
| realesrgan_x4plus | fp32 | 🔴 fail | Unreachable: HTTP 404 |
| nmkd_superscale_8x | fp32 | 🔴 fail | Unreachable: HTTP 404 |
| supir | fp16 | ⚠️ warning | Size mismatch: DB=5.20GB, Real=0.00GB |
| hat_large | fp32 | 🔴 fail | Unreachable: HTTP 401 |
| df2k_jpeg | fp32 | 🔴 fail | Unreachable: HTTP 404 |
| hunyuanvideo15_latent_upsampler_720p | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| hunyuanvideo15_latent_upsampler_1080p | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| ltx2_spatial_upscaler | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| ltx2_temporal_upscaler | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| controlnet_canny_sdxl | fp16 | ⚠️ warning | Size mismatch: DB=2.50GB, Real=0.00GB |
| controlnet_depth_sdxl | fp16 | ⚠️ warning | Size mismatch: DB=2.50GB, Real=0.00GB |
| controlnet_openpose_sd15 | fp16 | ⚠️ warning | Size mismatch: DB=1.40GB, Real=0.00GB |
| controlnet_canny_sd15 | fp16 | ⚠️ warning | Size mismatch: DB=1.40GB, Real=0.00GB |
| controlnet_depth_sd15 | fp16 | ⚠️ warning | Size mismatch: DB=1.40GB, Real=0.00GB |
| controlnet_lineart_sd15 | fp16 | ⚠️ warning | Size mismatch: DB=1.40GB, Real=0.00GB |
| controlnet_union_flux | fp16 | ⚠️ warning | Size mismatch: DB=6.40GB, Real=0.00GB |
| qwen_image_controlnet_inpainting | bf16 | ⚠️ warning | Size mismatch: DB=3.00GB, Real=0.00GB |
| controlnet_blur_sd35_large | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| controlnet_canny_sd35_large | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| controlnet_depth_sd35_large | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan21_controlnet_canny_14b | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan21_controlnet_depth_14b | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan21_controlnet_hed_14b | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan21_controlnet_canny_1_3b | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| wan21_uni3c | fp16 | 🔴 fail | Unreachable: HTTP 401 |
| qwen_image_controlnet_union | bf16 | ⚠️ warning | Size mismatch: DB=3.50GB, Real=0.00GB |
| z_image_turbo_controlnet_union | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| z_image_turbo_controlnet_tile | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| clip_vit_g_14 | fp16 | ⚠️ warning | Size mismatch: DB=1.40GB, Real=0.00GB |
| t5_xxl | fp16 | ⚠️ warning | Size mismatch: DB=22.00GB, Real=0.00GB |
| t5_xxl | fp8 | 🔴 fail | Missing download_url |
| t5_xxl | gguf_q4 | 🔴 fail | Missing download_url |
| mistral_3_small_flux2 | bf16 | 🔴 fail | Unreachable: HTTP 404 |
| mistral_3_small_flux2 | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| qwen_3_8b_flux2 | bf16 | 🔴 fail | Unreachable: HTTP 404 |
| qwen_3_8b_flux2 | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| gemma_3_4b_flux2 | bf16 | 🔴 fail | Unreachable: HTTP 404 |
| gemma_3_4b_flux2 | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| ovis_encoder | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| llama_3_2_3b | fp16 | ⚠️ warning | Size mismatch: DB=6.40GB, Real=0.00GB |
| llama_3_2_3b | gguf_q4 | ⚠️ warning | Size mismatch: DB=2.00GB, Real=0.00GB |
| llama_3_2_3b | gguf_q8 | 🔴 fail | Missing download_url |
| llama_3_1_8b | fp16 | ⚠️ warning | Size mismatch: DB=16.00GB, Real=0.00GB |
| llama_3_1_8b | gguf_q4 | ⚠️ warning | Size mismatch: DB=4.90GB, Real=0.00GB |
| llama_3_1_8b | gguf_q8 | 🔴 fail | Missing download_url |
| qwen2_5_7b | fp16 | ⚠️ warning | Size mismatch: DB=15.20GB, Real=0.00GB |
| qwen2_5_7b | gguf_q4 | ⚠️ warning | Size mismatch: DB=4.40GB, Real=0.00GB |
| qwen2_5_7b | gguf_q8 | 🔴 fail | Missing download_url |
| qwen2_5_3b | fp16 | ⚠️ warning | Size mismatch: DB=6.20GB, Real=0.00GB |
| qwen2_5_3b | gguf_q4 | ⚠️ warning | Size mismatch: DB=1.90GB, Real=0.00GB |
| mistral_7b_v03 | fp16 | ⚠️ warning | Size mismatch: DB=14.50GB, Real=0.00GB |
| mistral_7b_v03 | gguf_q4 | ⚠️ warning | Size mismatch: DB=4.40GB, Real=0.00GB |
| mistral_7b_v03 | gguf_q8 | 🔴 fail | Missing download_url |
| phi3_mini | fp16 | ⚠️ warning | Size mismatch: DB=7.60GB, Real=0.00GB |
| phi3_mini | gguf_q4 | ⚠️ warning | Size mismatch: DB=2.30GB, Real=0.00GB |
| gemma2_9b | fp16 | ⚠️ warning | Size mismatch: DB=18.50GB, Real=0.00GB |
| gemma2_9b | gguf_q4 | ⚠️ warning | Size mismatch: DB=5.50GB, Real=0.00GB |
| gemma2_9b | gguf_q8 | 🔴 fail | Missing download_url |
| gemma2_2b | fp16 | ⚠️ warning | Size mismatch: DB=5.20GB, Real=0.00GB |
| gemma2_2b | gguf_q4 | ⚠️ warning | Size mismatch: DB=1.60GB, Real=0.00GB |
| deepseek_r1_7b | bf16 | ⚠️ warning | Size mismatch: DB=14.00GB, Real=0.00GB |
| deepseek_r1_7b | gguf_q4 | ⚠️ warning | Size mismatch: DB=4.30GB, Real=0.00GB |
| deepseek_r1_7b | gguf_q8 | 🔴 fail | Missing download_url |
| deepseek_r1_32b | bf16 | ⚠️ warning | Size mismatch: DB=64.00GB, Real=0.00GB |
| deepseek_r1_32b | gguf_q4 | ⚠️ warning | Size mismatch: DB=19.00GB, Real=0.00GB |
| deepseek_r1_32b | gguf_q8 | 🔴 fail | Missing download_url |
| smollm2_1_7b | fp16 | ⚠️ warning | Size mismatch: DB=3.40GB, Real=0.00GB |
| smollm2_1_7b | gguf_q4 | ⚠️ warning | Size mismatch: DB=1.10GB, Real=0.00GB |
| smollm2_360m | fp16 | ⚠️ warning | Size mismatch: DB=0.72GB, Real=0.00GB |
| tinyllama_1_1b | fp16 | ⚠️ warning | Size mismatch: DB=2.20GB, Real=0.00GB |
| tinyllama_1_1b | gguf_q4 | ⚠️ warning | Size mismatch: DB=0.67GB, Real=0.00GB |
| qwen2_5_72b | bf16 | ⚠️ warning | Size mismatch: DB=144.00GB, Real=0.00GB |
| qwen2_5_72b | gguf_q4 | ⚠️ warning | Size mismatch: DB=42.00GB, Real=0.00GB |
| qwen2_5_72b | gguf_q3 | 🔴 fail | Missing download_url |
| f5_tts | fp16 | 🔴 fail | Missing download_url |
| kokoro_tts | fp16 | 🔴 fail | Missing download_url |
| xtts_v2 | fp16 | 🔴 fail | Missing download_url |
| musicgen_medium | fp16 | 🔴 fail | Missing download_url |
| ace_step | fp16 | 🔴 fail | Missing download_url |
| styletts2 | fp32 | ⚠️ warning | Size mismatch: DB=0.80GB, Real=0.00GB |
| parler_tts_mini | fp16 | ⚠️ warning | Size mismatch: DB=1.80GB, Real=0.00GB |
| parler_tts_large | fp16 | ⚠️ warning | Size mismatch: DB=4.70GB, Real=0.00GB |
| stable_audio_open | fp16 | ⚠️ warning | Size mismatch: DB=2.20GB, Real=0.00GB |
| bark | fp16 | ⚠️ warning | Size mismatch: DB=2.50GB, Real=0.00GB |
| bark | fp16_small | ⚠️ warning | Size mismatch: DB=0.80GB, Real=0.00GB |
| mmaudio | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| mmaudio | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| mmaudio_large | bf16 | 🔴 fail | Unreachable: HTTP 401 |
| mmaudio_large | fp8 | 🔴 fail | Unreachable: HTTP 401 |
| hunyuan3d_2_mini | fp16 | 🔴 fail | Missing download_url |
| hunyuan3d_21 | fp16 | 🔴 fail | Missing download_url |
| triposr | fp16 | 🔴 fail | Missing download_url |
| trellis_2 | fp16 | 🔴 fail | Missing download_url |
| instantmesh | fp16 | ⚠️ warning | Size mismatch: DB=2.50GB, Real=0.00GB |
| zero123plus_v12 | fp16 | ⚠️ warning | Size mismatch: DB=3.80GB, Real=0.00GB |
| shap_e | fp16 | ⚠️ warning | Size mismatch: DB=1.00GB, Real=0.00GB |
| sv3d | fp16 | ⚠️ warning | Size mismatch: DB=9.60GB, Real=0.00GB |
| wav2lip | fp16 | 🔴 fail | Missing download_url |
| latentsync_16 | fp16 | 🔴 fail | Missing download_url |
| sadtalker | fp16 | 🔴 fail | Missing download_url |
