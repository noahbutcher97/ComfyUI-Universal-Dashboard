import os
import hashlib
from src.services.system_service import SystemService
from src.utils.logger import log

class ComfyService:
    # Known hashes for popular base models (partial for verification)
    MODEL_HASHES = {
        "flux1-schnell.safetensors": "a9e1e277b9b1", # Partial example
        "v1-5-pruned-emaonly.safetensors": "cc6cb2710341"
    }

    @staticmethod
    def verify_file(filepath, expected_hash=None):
        """
        Verifies file existence and optional hash.
        """
        if not os.path.exists(filepath):
            return False
            
        if expected_hash:
            # Calculate hash (chunked)
            sha256_hash = hashlib.sha256()
            try:
                with open(filepath, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                file_hash = sha256_hash.hexdigest()
                return file_hash.startswith(expected_hash)
            except Exception as e:
                log.error(f"Hash check failed for {filepath}: {e}")
                return False
        
        return True

    @staticmethod
    def generate_manifest(answers, install_root):
        """
        Generates the installation manifest based on user answers and hardware.
        """
        gpu_name, vram = SystemService.get_gpu_info()
        manifest = []
        
        # 1. Base Installation
        manifest.append({
            "type": "clone", 
            "url": "https://github.com/comfyanonymous/ComfyUI.git", 
            "dest": install_root, 
            "name": "ComfyUI Core"
        })
        manifest.append({
            "type": "clone", 
            "url": "https://github.com/ltdrdata/ComfyUI-Manager.git", 
            "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-Manager"), 
            "name": "ComfyUI Manager"
        })

        # 2. Model Tier Selection logic
        # Improved logic: Consider 12GB cards as high tier for SDXL/Flux usage if optimized
        model_tier = "sd15"
        if vram >= 12: 
            model_tier = "flux" # High end
        elif vram >= 8: 
            model_tier = "sdxl" # Mid range
        
        ckpt_dir = os.path.join(install_root, "models", "checkpoints")
        
        # Style Mappings
        # In a future phase, these URLs should come from an external JSON
        if answers.get("style") == "Photorealistic":
            if model_tier == "flux": 
                manifest.append({"type": "download", "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors", "dest": ckpt_dir, "name": "Flux1-Schnell"})
            elif model_tier == "sdxl": 
                manifest.append({"type": "download", "url": "https://civitai.com/api/download/models/240840", "dest": ckpt_dir, "name": "Juggernaut XL v9"})
            else: 
                manifest.append({"type": "download", "url": "https://civitai.com/api/download/models/130072", "dest": ckpt_dir, "name": "Realistic Vision 6"})
                
        elif answers.get("style") == "Anime":
            if model_tier in ["sdxl", "flux"]:
                manifest.append({"type": "download", "url": "https://civitai.com/api/download/models/290640", "dest": ckpt_dir, "name": "Pony Diffusion V6 XL"})
            else:
                manifest.append({"type": "download", "url": "https://civitai.com/api/download/models/100675", "dest": ckpt_dir, "name": "Anything V5"})
        
        else: # General / Default
            if model_tier == "flux": 
                manifest.append({"type": "download", "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors", "dest": ckpt_dir, "name": "Flux1-Schnell"})
            elif model_tier == "sdxl": 
                manifest.append({"type": "download", "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors", "dest": ckpt_dir, "name": "SDXL Base 1.0"})
            else: 
                manifest.append({"type": "download", "url": "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors", "dest": ckpt_dir, "name": "SD 1.5 Pruned"})

        # 3. Feature Selection
        if answers.get("media") in ["Video", "Mixed"]:
            manifest.append({
                "type": "clone", 
                "url": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git", 
                "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-AnimateDiff-Evolved"), 
                "name": "AnimateDiff Node"
            })
            manifest.append({
                "type": "download", 
                "url": "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt", 
                "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-AnimateDiff-Evolved", "models"), 
                "name": "AnimateDiff V2 Motion Model"
            })

        if answers.get("consistency"):
            manifest.append({
                "type": "clone", 
                "url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git", 
                "dest": os.path.join(install_root, "custom_nodes", "ComfyUI_IPAdapter_plus"), 
                "name": "IPAdapter Plus"
            })
            
        if answers.get("editing"):
            manifest.append({
                "type": "clone", 
                "url": "https://github.com/Fannovel16/comfyui_controlnet_aux.git", 
                "dest": os.path.join(install_root, "custom_nodes", "comfyui_controlnet_aux"), 
                "name": "ControlNet Preprocessors"
            })
            manifest.append({
                "type": "download", 
                "url": "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_canny.pth", 
                "dest": os.path.join(install_root, "models", "controlnet"), 
                "name": "ControlNet Canny (SD1.5)"
            })

        return manifest
