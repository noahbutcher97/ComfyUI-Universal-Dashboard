# AI Universal Suite - Technical Specification v2.0

## Executive Summary

AI Universal Suite is a cross-platform desktop application that transforms a user's computer into a fully configured AI workstation through a single, guided setup wizard. The application targets non-technical users who want to leverage AI tools without writing code, using terminals, or navigating complex installations.

**Core Principle:** The user should never need to open a terminal, write code, or understand technical implementation details. Every action should be achievable through GUI interactions.

---

## Table of Contents

1. [Strategic Vision](#1-strategic-vision)
2. [Architecture Overview](#2-architecture-overview)
3. [User Flow](#3-user-flow)
4. [Data Schemas](#4-data-schemas)
5. [Service Layer Specifications](#5-service-layer-specifications)
6. [UI Component Specifications](#6-ui-component-specifications)
7. [File Structure](#7-file-structure)
8. [Implementation Phases](#8-implementation-phases)
9. [Critical Bug Fixes](#9-critical-bug-fixes)
10. [Testing Requirements](#10-testing-requirements)

---

## 1. Strategic Vision

### 1.1 Problem Statement

Experienced professionals (filmmakers, designers, developers, business owners) understand that AI tools could transform their work, but face barriers:

- Consumer AI apps lack control and consistency
- Professional tools require coding knowledge
- Subscription costs accumulate without clear ROI
- No unified system ties tools together

### 1.2 Solution

AI Universal Suite provides:

1. **One-Shot Setup Wizard**: Fully configure an AI workstation in a single guided session
2. **Use-Case Driven Configuration**: Start from "what you want to accomplish" not "what software to install"
3. **Hardware-Aware Recommendations**: Automatically detect capabilities and recommend appropriate tools/models
4. **Zero Terminal Interaction**: All setup, configuration, and launching via GUI and desktop shortcuts
5. **Unified Tool Management**: Manage CLI tools, ComfyUI, API keys, and future modules from one interface

### 1.3 Target Users

| Persona | Description | Primary Use Cases |
|---------|-------------|-------------------|
| Creative Professional | Filmmakers, designers, photographers with domain expertise but limited technical skills | Image/video generation, content pipelines |
| Knowledge Worker | Business professionals, consultants, writers | AI assistants, document processing |
| Technical Veteran | Experienced developers/engineers learning AI tools | Full stack integration, automation |
| Solopreneur | Independent business owners wearing many hats | Productivity, content generation, automation |

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        UI Layer                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Setup Wizard│  │  Dashboard  │  │     Module Views        │  │
│  │  (Modal)    │  │  (Main)     │  │ (DevTools/ComfyUI/etc)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ SetupWizard  │  │ Recommendation│  │    Module Services   │   │
│  │   Service    │  │    Service    │  │ (Comfy/CLI/Shortcut) │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   System     │  │   Download   │  │     Subprocess       │   │
│  │   Service    │  │    Service   │  │      Runner          │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Configuration Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ ConfigManager│  │ resources.json│  │    OS Keyring        │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Module System

The application is organized around **modules** - discrete functional units that can be independently configured, installed, and launched.

**Core Modules:**
| Module ID | Display Name | Description | Status |
|-----------|--------------|-------------|--------|
| `cli_provider` | AI Assistant CLI | Command-line AI with file system access | Implemented |
| `comfyui` | ComfyUI Studio | Visual AI generation (image/video) | Implemented |
| `lm_studio` | LM Studio | Local LLM inference | Planned |
| `mcp_servers` | MCP Configuration | Model Context Protocol servers | Planned |

### 2.3 Use Case System

Use cases sit above modules and define "what the user wants to accomplish." Each use case maps to a set of module configurations.

**Core Use Cases:**
| Use Case ID | Display Name | Modules Required |
|-------------|--------------|------------------|
| `content_generation` | Content Generation | comfyui, cli_provider (optional) |
| `video_generation` | Video Generation | comfyui (with I2V bundle) |
| `productivity` | AI Productivity | cli_provider |
| `automation` | Workflow Automation | cli_provider, mcp_servers |
| `full_stack` | Full AI Workstation | All modules |

---

## 3. User Flow

### 3.1 First Launch Flow

```
Application Start
       │
       ▼
┌──────────────────┐
│ Check first_run  │
│ flag in config   │
└────────┬─────────┘
         │
    ┌────┴────┐
    │ First   │
    │ Launch? │
    └────┬────┘
     Yes │        No
         ▼         ▼
┌─────────────┐  ┌─────────────┐
│ Show Setup  │  │ Show Main   │
│   Wizard    │  │  Dashboard  │
└─────────────┘  └─────────────┘
```

### 3.2 Setup Wizard Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SETUP WIZARD STAGES                           │
└─────────────────────────────────────────────────────────────────┘

Stage 1: Welcome & Use Case Selection
├── Display: Welcome message, value proposition
├── Input: Use case selection (cards with icons)
│   ├── Content Generation (Image/Video)
│   ├── AI Productivity (Writing/Coding Assistant)
│   ├── Full AI Workstation (Everything)
│   └── Custom (Advanced users)
├── Action: [Continue]
└── Skip: Not available (required)

       │
       ▼

Stage 2: Environment Scan (Automatic)
├── Display: Scanning animation with progress
├── Detect:
│   ├── Operating System
│   ├── GPU Type (NVIDIA/Apple Silicon/CPU)
│   ├── VRAM (or unified memory for Apple)
│   ├── Available RAM
│   ├── Available Disk Space
│   ├── Existing installations (Node.js, Git, Python, ComfyUI)
│   └── Network connectivity
├── Output: EnvironmentReport object
├── Action: Automatic progression
└── Skip: Not available

       │
       ▼

Stage 3: Module Configuration Loop
├── For each module relevant to selected use case:
│   │
│   ├── Display:
│   │   ├── Module name and description
│   │   ├── Recommendation with reasoning
│   │   ├── Warnings (if any)
│   │   └── Configuration options (if applicable)
│   │
│   ├── Inputs (varies by module):
│   │   ├── CLI Provider: Provider selection, API key input
│   │   ├── ComfyUI: Model tier (auto-selected), optional features
│   │   └── Common: "Create desktop shortcut" checkbox
│   │
│   ├── Actions: [Skip] [Accept & Next]
│   └── Advanced: [Show Advanced Options] (reveals manual overrides)
│
└── Modules presented in order:
    1. CLI Provider (if applicable)
    2. ComfyUI (if applicable)
    3. LM Studio (if applicable, future)
    4. MCP Servers (if applicable, future)

       │
       ▼

Stage 4: Review & Confirm
├── Display:
│   ├── Summary of all accepted modules
│   ├── Total estimated download size
│   ├── Estimated installation time
│   ├── List of shortcuts to be created
│   └── Warnings summary
├── Actions: [Back] [Begin Installation]
└── Skip: Not available

       │
       ▼

Stage 5: Installation
├── Display:
│   ├── Overall progress bar
│   ├── Current task indicator
│   ├── Per-item progress bars
│   └── Log output (collapsible)
├── Process:
│   ├── Install dependencies (Git, Node.js if missing)
│   ├── Clone repositories
│   ├── Download models
│   ├── Configure environments
│   ├── Validate installations
│   └── Create shortcuts
├── Error Handling:
│   ├── Retry failed downloads (3 attempts, exponential backoff)
│   ├── Show clear error messages
│   └── Allow [Retry] or [Skip This Item]
└── Actions: [Cancel] (with confirmation)

       │
       ▼

Stage 6: Complete
├── Display:
│   ├── Success message
│   ├── List of installed tools with status
│   ├── List of created shortcuts
│   └── Quick start tips
├── Actions: [Open Dashboard] [Launch ComfyUI] [Close]
└── Side Effect: Set first_run = false in config
```

### 3.3 Post-Setup Dashboard Flow

After initial setup, the main dashboard provides:

1. **Overview Tab**: System status, installed modules, quick launch buttons
2. **Dev Tools Tab**: CLI management, API key updates
3. **ComfyUI Tab**: Model management, workflow templates, launch
4. **Settings Tab**: Preferences, re-run wizard, shortcuts management

---

## 4. Data Schemas

### 4.1 Configuration Schema (`config.json`)

```json
{
  "version": "2.0",
  "first_run": true,
  "wizard_completed": false,
  "theme": "Dark",
  "paths": {
    "comfyui": "~/ComfyUI",
    "lm_studio": "~/LMStudio",
    "shortcuts": "~/Desktop"
  },
  "modules": {
    "cli_provider": {
      "enabled": true,
      "provider": "claude",
      "shortcut_created": true
    },
    "comfyui": {
      "enabled": true,
      "use_case": "video_generation",
      "model_tier": "gguf",
      "shortcut_created": true
    }
  },
  "preferences": {
    "cli_scope": "user",
    "auto_update_check": true,
    "create_shortcuts": true
  }
}
```

### 4.2 Resources Schema (`resources.json`)

```json
{
  "version": "2.0",
  
  "use_cases": {
    "content_generation": {
      "display_name": "Content Generation",
      "description": "Generate images and graphics using AI",
      "icon": "🎨",
      "modules": ["comfyui"],
      "optional_modules": ["cli_provider"],
      "comfyui_config": {
        "capabilities": ["t2i", "i2i"],
        "recommended_features": ["controlnet", "ipadapter"]
      }
    },
    "video_generation": {
      "display_name": "Video Generation", 
      "description": "Animate images into video clips",
      "icon": "🎬",
      "modules": ["comfyui"],
      "optional_modules": ["cli_provider"],
      "comfyui_config": {
        "capabilities": ["i2v"],
        "required_nodes": ["ComfyUI-GGUF", "ComfyUI-VideoHelperSuite"],
        "required_models": ["wan_i2v"],
        "recommended_features": []
      }
    },
    "productivity": {
      "display_name": "AI Productivity",
      "description": "AI assistant for writing, coding, and analysis",
      "icon": "⚡",
      "modules": ["cli_provider"],
      "optional_modules": ["lm_studio"],
      "cli_config": {
        "recommended_provider": "claude"
      }
    },
    "full_stack": {
      "display_name": "Full AI Workstation",
      "description": "Complete setup with all AI tools",
      "icon": "🚀",
      "modules": ["cli_provider", "comfyui"],
      "optional_modules": ["lm_studio", "mcp_servers"],
      "comfyui_config": {
        "capabilities": ["t2i", "i2i", "i2v"],
        "recommended_features": ["controlnet", "ipadapter", "animatediff"]
      }
    }
  },

  "modules": {
    "cli_provider": {
      "display_name": "AI Assistant CLI",
      "description": "Command-line AI assistant with direct file system access. Enables AI-powered coding, writing, and file manipulation.",
      "requires_api_key": true,
      "providers": {
        "claude": {
          "display_name": "Claude (Anthropic)",
          "package": "@anthropic-ai/claude-code",
          "package_type": "npm",
          "bin": "claude",
          "api_key_name": "ANTHROPIC_API_KEY",
          "api_key_url": "https://console.anthropic.com/",
          "recommended_for": ["coding", "analysis", "writing"]
        },
        "gemini": {
          "display_name": "Gemini (Google)",
          "package": "@google/gemini-cli",
          "package_type": "npm",
          "bin": "gemini",
          "api_key_name": "GEMINI_API_KEY",
          "api_key_url": "https://aistudio.google.com/apikey",
          "recommended_for": ["research", "multimodal"]
        },
        "codex": {
          "display_name": "Codex (OpenAI)",
          "package": "@openai/codex",
          "package_type": "npm",
          "bin": "codex",
          "api_key_name": "OPENAI_API_KEY",
          "api_key_url": "https://platform.openai.com/api-keys",
          "recommended_for": ["coding"]
        }
      },
      "shortcut_templates": {
        "windows": "@echo off\ncmd /k {bin}",
        "darwin": "#!/bin/bash\n{bin}",
        "linux": "#!/bin/bash\n{bin}"
      }
    },
    
    "comfyui": {
      "display_name": "ComfyUI Studio",
      "description": "Visual node-based AI image and video generation. Create complex pipelines without coding.",
      "requires_api_key": false,
      "core": {
        "repo": "https://github.com/comfyanonymous/ComfyUI.git",
        "manager_repo": "https://github.com/ltdrdata/ComfyUI-Manager.git"
      },
      "shortcut_templates": {
        "windows": "@echo off\ncd /d {path}\ncall venv\\Scripts\\activate\npython main.py --auto-launch\npause",
        "darwin": "#!/bin/bash\ncd \"{path}\"\nsource venv/bin/activate\npython main.py --force-fp16 --auto-launch",
        "linux": "#!/bin/bash\ncd \"{path}\"\nsource venv/bin/activate\npython main.py --auto-launch"
      }
    },
    
    "lm_studio": {
      "display_name": "LM Studio",
      "description": "Run large language models locally on your machine.",
      "requires_api_key": false,
      "status": "planned",
      "download_urls": {
        "windows": "https://releases.lmstudio.ai/windows/latest",
        "darwin": "https://releases.lmstudio.ai/mac/latest",
        "linux": "https://releases.lmstudio.ai/linux/latest"
      }
    }
  },

  "comfyui_components": {
    "custom_nodes": {
      "ComfyUI-GGUF": {
        "display_name": "GGUF Model Loader",
        "description": "Load quantized GGUF models for reduced VRAM usage",
        "repo": "https://github.com/city96/ComfyUI-GGUF.git",
        "required_for": ["gguf_models"],
        "dest_folder": "custom_nodes/ComfyUI-GGUF"
      },
      "ComfyUI-VideoHelperSuite": {
        "display_name": "Video Helper Suite",
        "description": "Video loading, saving, and manipulation tools",
        "repo": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git",
        "required_for": ["i2v", "video"],
        "dest_folder": "custom_nodes/ComfyUI-VideoHelperSuite"
      },
      "ComfyUI-AnimateDiff-Evolved": {
        "display_name": "AnimateDiff",
        "description": "Animation and motion generation",
        "repo": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git",
        "required_for": ["animatediff"],
        "dest_folder": "custom_nodes/ComfyUI-AnimateDiff-Evolved"
      },
      "ComfyUI_IPAdapter_plus": {
        "display_name": "IP-Adapter Plus",
        "description": "Image-based style and character consistency",
        "repo": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
        "required_for": ["ipadapter", "consistency"],
        "dest_folder": "custom_nodes/ComfyUI_IPAdapter_plus"
      },
      "comfyui_controlnet_aux": {
        "display_name": "ControlNet Preprocessors",
        "description": "Pose, depth, and edge detection for controlled generation",
        "repo": "https://github.com/Fannovel16/comfyui_controlnet_aux.git",
        "required_for": ["controlnet", "editing"],
        "dest_folder": "custom_nodes/comfyui_controlnet_aux"
      }
    },
    
    "model_tiers": {
      "flux": {
        "display_name": "Flux (High-End)",
        "min_vram": 12,
        "min_ram": 32,
        "description": "Highest quality, requires powerful GPU"
      },
      "sdxl": {
        "display_name": "SDXL (Standard)",
        "min_vram": 8,
        "min_ram": 16,
        "description": "Great quality, moderate requirements"
      },
      "sd15": {
        "display_name": "SD 1.5 (Lightweight)",
        "min_vram": 4,
        "min_ram": 8,
        "description": "Good quality, runs on most hardware"
      },
      "gguf": {
        "display_name": "GGUF Quantized",
        "min_vram": 0,
        "min_ram": 16,
        "description": "Optimized for Apple Silicon and low VRAM systems",
        "requires_nodes": ["ComfyUI-GGUF"]
      }
    },
    
    "models": {
      "checkpoints": {
        "flux_schnell": {
          "display_name": "Flux.1 Schnell",
          "tier": "flux",
          "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors",
          "size_gb": 23.8,
          "dest": "models/checkpoints",
          "capabilities": ["t2i"]
        },
        "sdxl_juggernaut": {
          "display_name": "Juggernaut XL v9",
          "tier": "sdxl",
          "url": "https://civitai.com/api/download/models/240840",
          "size_gb": 6.5,
          "dest": "models/checkpoints",
          "capabilities": ["t2i", "i2i"]
        },
        "sd15_realistic": {
          "display_name": "Realistic Vision 6",
          "tier": "sd15",
          "url": "https://civitai.com/api/download/models/130072",
          "size_gb": 2.0,
          "dest": "models/checkpoints",
          "capabilities": ["t2i", "i2i"]
        }
      },
      "unet_gguf": {
        "wan_i2v_high_q5": {
          "display_name": "Wan 2.2 I2V High Noise (Q5)",
          "tier": "gguf",
          "url": "https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf",
          "size_gb": 9.8,
          "dest": "models/unet",
          "capabilities": ["i2v"],
          "pair_with": "wan_i2v_low_q5"
        },
        "wan_i2v_low_q5": {
          "display_name": "Wan 2.2 I2V Low Noise (Q5)",
          "tier": "gguf",
          "url": "https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf",
          "size_gb": 9.8,
          "dest": "models/unet",
          "capabilities": ["i2v"],
          "pair_with": "wan_i2v_high_q5"
        }
      }
    },
    
    "workflows": {
      "wan_i2v_basic": {
        "display_name": "Image to Video (Basic)",
        "description": "Animate a still image into a short video clip",
        "file": "workflows/wan_i2v_basic.json",
        "requires_models": ["wan_i2v_high_q5", "wan_i2v_low_q5"],
        "requires_nodes": ["ComfyUI-GGUF", "ComfyUI-VideoHelperSuite"],
        "capabilities": ["i2v"]
      },
      "sdxl_basic": {
        "display_name": "Text to Image (SDXL)",
        "description": "Generate images from text prompts",
        "file": "workflows/sdxl_basic.json",
        "requires_models": ["sdxl_juggernaut"],
        "requires_nodes": [],
        "capabilities": ["t2i"]
      }
    }
  },

  "hardware_profiles": {
    "nvidia_high": {
      "description": "NVIDIA GPU with 12GB+ VRAM",
      "detection": {"gpu_vendor": "nvidia", "vram_min": 12},
      "recommended_tier": "flux",
      "capabilities": ["cuda", "full_precision"]
    },
    "nvidia_mid": {
      "description": "NVIDIA GPU with 8-11GB VRAM",
      "detection": {"gpu_vendor": "nvidia", "vram_min": 8, "vram_max": 11},
      "recommended_tier": "sdxl",
      "capabilities": ["cuda", "full_precision"]
    },
    "nvidia_low": {
      "description": "NVIDIA GPU with 4-7GB VRAM",
      "detection": {"gpu_vendor": "nvidia", "vram_min": 4, "vram_max": 7},
      "recommended_tier": "sd15",
      "capabilities": ["cuda"]
    },
    "apple_silicon": {
      "description": "Apple M-series chip",
      "detection": {"gpu_vendor": "apple"},
      "recommended_tier": "gguf",
      "capabilities": ["mps", "unified_memory"],
      "notes": "Use GGUF models for best performance"
    },
    "cpu_only": {
      "description": "No dedicated GPU detected",
      "detection": {"gpu_vendor": "none"},
      "recommended_tier": "sd15",
      "capabilities": [],
      "warnings": ["Generation will be very slow without GPU acceleration"]
    }
  },

  "system_requirements": {
    "minimum": {
      "ram_gb": 8,
      "disk_gb": 20,
      "python": "3.10"
    },
    "recommended": {
      "ram_gb": 32,
      "disk_gb": 100,
      "python": "3.10"
    }
  }
}
```

### 4.3 Environment Report Schema

```python
@dataclass
class EnvironmentReport:
    """Output of SystemService.scan_full_environment()"""
    
    # Hardware
    os_name: str                    # "Windows", "Darwin", "Linux"
    os_version: str                 # e.g., "10.0.19041", "14.1.2"
    arch: str                       # "x86_64", "arm64"
    gpu_vendor: str                 # "nvidia", "apple", "amd", "none"
    gpu_name: str                   # "NVIDIA GeForce RTX 3080"
    vram_gb: int                    # 10
    ram_gb: int                     # 64
    disk_free_gb: int               # 250
    
    # Software
    python_version: str             # "3.10.12"
    git_installed: bool
    node_installed: bool
    npm_installed: bool
    
    # Existing Installations
    comfyui_path: Optional[str]     # None or path if found
    comfyui_version: Optional[str]
    lm_studio_installed: bool
    
    # Derived
    hardware_profile: str           # Key from hardware_profiles
    recommended_model_tier: str     # "flux", "sdxl", "sd15", "gguf"
    warnings: List[str]             # Any issues detected
```

### 4.4 Module Recommendation Schema

```python
@dataclass
class ModuleRecommendation:
    """Output of RecommendationService for a single module"""
    
    module_id: str                          # "comfyui"
    enabled: bool                           # Whether to install
    
    # Module-specific config
    config: Dict[str, Any]                  # Varies by module
    
    # For display
    display_name: str
    description: str
    reasoning: List[str]                    # Why this recommendation
    warnings: List[str]                     # Potential issues
    
    # Installation details
    components: List[str]                   # What will be installed
    estimated_size_gb: float
    estimated_time_minutes: int
    
    # User overridable
    optional_features: Dict[str, bool]      # Feature toggles
    advanced_options: Dict[str, Any]        # For advanced mode
```

### 4.5 Installation Manifest Schema

```python
@dataclass
class InstallationItem:
    """Single item to install"""
    
    item_id: str                    # Unique identifier
    item_type: str                  # "clone", "download", "pip", "npm", "shortcut"
    name: str                       # Display name
    
    # Type-specific fields
    url: Optional[str]              # For clone/download
    dest: str                       # Destination path
    command: Optional[List[str]]    # For pip/npm
    
    # Validation
    expected_hash: Optional[str]    # SHA256 for downloads
    verify_path: Optional[str]      # Path to check after install
    
    # Progress tracking
    size_bytes: Optional[int]
    
@dataclass  
class InstallationManifest:
    """Complete installation plan"""
    
    manifest_id: str                        # UUID
    created_at: datetime
    
    items: List[InstallationItem]
    
    # Summary
    total_size_gb: float
    estimated_time_minutes: int
    
    # Shortcuts to create after installation
    shortcuts: List[Dict[str, str]]         # {name, command, icon}
```

---

## 5. Service Layer Specifications

### 5.1 SystemService (Enhanced)

**File:** `src/services/system_service.py`

**Changes Required:**
- Fix Apple Silicon RAM detection (currently hardcoded to 16GB)
- Add full environment scanning method
- Add disk space checking

```python
class SystemService:
    
    @staticmethod
    def get_gpu_info() -> Tuple[str, str, int]:
        """
        Returns (gpu_vendor, gpu_name, vram_gb)
        
        MUST FIX: Apple Silicon currently hardcoded to 16GB.
        Should use: subprocess.check_output(["sysctl", "-n", "hw.memsize"])
        """
        pass
    
    @staticmethod
    def get_system_ram_gb() -> int:
        """Returns total system RAM in GB."""
        pass
    
    @staticmethod
    def get_disk_free_gb(path: str = "~") -> int:
        """Returns free disk space at path in GB."""
        pass
    
    @staticmethod
    def scan_full_environment() -> EnvironmentReport:
        """
        Comprehensive environment scan for wizard.
        Returns EnvironmentReport dataclass.
        """
        pass
    
    @staticmethod
    def detect_existing_comfyui() -> Optional[str]:
        """
        Check common locations for existing ComfyUI installation.
        Returns path if found, None otherwise.
        """
        pass
    
    @staticmethod
    def match_hardware_profile(env: EnvironmentReport) -> str:
        """
        Match environment to hardware_profiles in resources.json.
        Returns profile key.
        """
        pass
```

### 5.2 RecommendationService (Enhanced)

**File:** `src/services/recommendation_service.py`

**Changes Required:**
- Integrate with use case system
- Support GGUF model recommendations
- Add workflow template recommendations

```python
class RecommendationService:
    
    def __init__(self, resources: dict):
        self.resources = resources
    
    def generate_recommendations(
        self, 
        use_case: str, 
        env: EnvironmentReport
    ) -> List[ModuleRecommendation]:
        """
        Generate recommendations for all modules relevant to use case.
        
        Args:
            use_case: Key from resources["use_cases"]
            env: EnvironmentReport from SystemService
            
        Returns:
            List of ModuleRecommendation for each relevant module
        """
        pass
    
    def _recommend_cli_provider(
        self, 
        use_case_config: dict, 
        env: EnvironmentReport
    ) -> ModuleRecommendation:
        """Generate CLI provider recommendation."""
        pass
    
    def _recommend_comfyui(
        self, 
        use_case_config: dict, 
        env: EnvironmentReport
    ) -> ModuleRecommendation:
        """
        Generate ComfyUI recommendation including:
        - Model tier selection based on hardware
        - Required custom nodes for capabilities
        - Workflow templates
        - GGUF models for Apple Silicon
        """
        pass
    
    def _select_model_tier(self, env: EnvironmentReport) -> str:
        """
        Select appropriate model tier based on hardware.
        Apple Silicon should default to "gguf".
        """
        pass
    
    def _get_required_components(
        self, 
        capabilities: List[str], 
        model_tier: str
    ) -> Dict[str, List[str]]:
        """
        Given required capabilities and tier, return:
        {
            "custom_nodes": [...],
            "models": [...],
            "workflows": [...]
        }
        """
        pass
```

### 5.3 SetupWizardService (New)

**File:** `src/services/setup_wizard_service.py`

```python
class SetupWizardService:
    """
    Orchestrates the full setup wizard flow.
    Coordinates between SystemService, RecommendationService, 
    and module-specific services.
    """
    
    def __init__(self):
        self.system_service = SystemService()
        self.recommendation_service = RecommendationService(
            config_manager.get_resources()
        )
        self.env_report: Optional[EnvironmentReport] = None
        self.recommendations: List[ModuleRecommendation] = []
        self.accepted_modules: List[ModuleRecommendation] = []
    
    def start_wizard(self) -> None:
        """Initialize wizard state."""
        self.env_report = None
        self.recommendations = []
        self.accepted_modules = []
    
    def scan_environment(self) -> EnvironmentReport:
        """
        Run full environment scan.
        Stores result in self.env_report.
        """
        self.env_report = self.system_service.scan_full_environment()
        return self.env_report
    
    def generate_recommendations(self, use_case: str) -> List[ModuleRecommendation]:
        """
        Generate recommendations for selected use case.
        Requires scan_environment() to have been called first.
        """
        if not self.env_report:
            raise RuntimeError("Must scan environment first")
        
        self.recommendations = self.recommendation_service.generate_recommendations(
            use_case, self.env_report
        )
        return self.recommendations
    
    def accept_module(self, module_id: str, config_overrides: Dict = None) -> None:
        """Mark a module as accepted, optionally with config changes."""
        pass
    
    def skip_module(self, module_id: str) -> None:
        """Mark a module as skipped."""
        pass
    
    def generate_manifest(self) -> InstallationManifest:
        """
        Generate unified installation manifest from accepted modules.
        """
        pass
    
    def execute_installation(
        self, 
        manifest: InstallationManifest,
        progress_callback: Callable[[str, float], None],
        error_callback: Callable[[str, Exception], None]
    ) -> bool:
        """
        Execute the installation manifest.
        
        Args:
            manifest: What to install
            progress_callback: Called with (item_id, progress 0-1)
            error_callback: Called with (item_id, exception)
            
        Returns:
            True if all items succeeded, False if any failed
        """
        pass
    
    def create_shortcuts(self) -> List[Path]:
        """Create desktop shortcuts for installed tools."""
        pass
    
    def finalize(self) -> None:
        """
        Mark wizard as complete.
        Updates config with wizard_completed=True and first_run=False.
        """
        pass
```

### 5.4 ShortcutService (New)

**File:** `src/services/shortcut_service.py`

```python
class ShortcutService:
    """
    Creates OS-appropriate desktop shortcuts/launchers.
    """
    
    @staticmethod
    def get_desktop_path() -> Path:
        """Returns path to user's Desktop folder."""
        pass
    
    @staticmethod
    def create_shortcut(
        name: str,
        command: str,
        working_dir: Optional[str] = None,
        icon_path: Optional[str] = None,
        destination: Optional[Path] = None
    ) -> Path:
        """
        Create a desktop shortcut.
        
        Windows: Creates .bat file
        macOS: Creates .command file, removes quarantine attribute
        Linux: Creates .desktop file or .sh script
        
        Args:
            name: Display name (also used for filename)
            command: Command to execute
            working_dir: Working directory for command
            icon_path: Path to icon file (optional)
            destination: Where to create (default: Desktop)
            
        Returns:
            Path to created shortcut
        """
        pass
    
    @staticmethod
    def create_comfyui_shortcut(comfy_path: str) -> Path:
        """Create ComfyUI launcher shortcut."""
        pass
    
    @staticmethod
    def create_cli_shortcut(cli_name: str, bin_name: str) -> Path:
        """Create CLI tool launcher shortcut."""
        pass
    
    @staticmethod
    def remove_macos_quarantine(path: Path) -> None:
        """Remove macOS quarantine attribute to prevent security warnings."""
        pass
```

### 5.5 DownloadService (New)

**File:** `src/services/download_service.py`

```python
class DownloadService:
    """
    Handles file downloads with progress tracking, retry logic, and validation.
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # Exponential backoff base
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    
    @staticmethod
    def download_file(
        url: str,
        dest_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        expected_hash: Optional[str] = None
    ) -> bool:
        """
        Download a file with retry logic.
        
        Args:
            url: Source URL
            dest_path: Destination file path
            progress_callback: Called with (bytes_downloaded, total_bytes)
            expected_hash: SHA256 hash to verify (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            DownloadError: If all retries fail
            HashMismatchError: If hash doesn't match
        """
        pass
    
    @staticmethod
    def verify_hash(file_path: Path, expected_hash: str) -> bool:
        """Verify file SHA256 hash."""
        pass
    
    @staticmethod
    def get_file_size(url: str) -> Optional[int]:
        """Get file size from URL headers without downloading."""
        pass
```

### 5.6 ComfyService (Enhanced)

**File:** `src/services/comfy_service.py`

**Changes Required:**
- Accept ModuleRecommendation as input instead of raw answers
- Support GGUF model installation
- Support workflow template deployment
- Add update and validation methods

```python
class ComfyService:
    
    @staticmethod
    def generate_manifest(
        recommendation: ModuleRecommendation,
        install_path: str
    ) -> List[InstallationItem]:
        """
        Generate installation items from recommendation.
        
        Now supports:
        - GGUF custom node and models
        - Workflow template copying
        - All model tiers
        """
        pass
    
    @staticmethod
    def install_custom_node(node_url: str, dest_path: str) -> bool:
        """Clone a custom node repository."""
        pass
    
    @staticmethod
    def deploy_workflow(
        workflow_key: str, 
        comfy_path: str,
        resources: dict
    ) -> bool:
        """
        Copy workflow template to ComfyUI workflows directory.
        
        Source: bundled workflows/ directory in app
        Dest: {comfy_path}/user/default/workflows/
        """
        pass
    
    @staticmethod
    def validate_installation(comfy_path: str) -> Dict[str, bool]:
        """
        Validate ComfyUI installation.
        
        Returns dict of checks:
        {
            "core_exists": bool,
            "venv_exists": bool,
            "manager_exists": bool,
            "can_launch": bool
        }
        """
        pass
    
    @staticmethod
    def get_installed_models(comfy_path: str) -> Dict[str, List[str]]:
        """
        List installed models by category.
        
        Returns:
        {
            "checkpoints": ["model1.safetensors", ...],
            "unet": ["wan_i2v_high.gguf", ...],
            "loras": [...]
        }
        """
        pass
```

### 5.7 DevService (Enhanced)

**File:** `src/services/dev_service.py`

**Changes Required:**
- Add uninstall method
- Add method to check API key validity
- Integrate with shortcut creation

```python
class DevService:
    
    @staticmethod
    def get_install_cmd(tool_name: str, scope: str = "user") -> List[str]:
        """Get installation command for a CLI tool."""
        pass
    
    @staticmethod
    def get_uninstall_cmd(tool_name: str, scope: str = "user") -> List[str]:
        """
        Get uninstall command for a CLI tool.
        
        npm: ["npm", "uninstall", "-g", package]
        pip: [sys.executable, "-m", "pip", "uninstall", "-y", package]
        """
        pass
    
    @staticmethod
    def validate_api_key(provider: str, api_key: str) -> bool:
        """
        Validate an API key by making a minimal API call.
        
        Returns True if key is valid, False otherwise.
        """
        pass
    
    @staticmethod
    def get_binary_path(tool_name: str) -> Optional[str]:
        """Get full path to installed CLI binary."""
        pass
```

---

## 6. UI Component Specifications

### 6.1 Setup Wizard Window

**File:** `src/ui/wizard/setup_wizard.py`

```python
class SetupWizard(ctk.CTkToplevel):
    """
    Modal wizard window for initial setup.
    Manages multi-stage flow with back/next navigation.
    """
    
    def __init__(self, master, on_complete: Callable):
        """
        Args:
            master: Parent window
            on_complete: Callback when wizard finishes
        """
        pass
    
    # Stage management
    def show_stage(self, stage_name: str) -> None:
        """Switch to a wizard stage."""
        pass
    
    def next_stage(self) -> None:
        """Advance to next stage."""
        pass
    
    def prev_stage(self) -> None:
        """Go back to previous stage."""
        pass
    
    # Stages (each implemented as a method that builds the UI)
    def build_welcome_stage(self) -> ctk.CTkFrame:
        """Use case selection cards."""
        pass
    
    def build_scanning_stage(self) -> ctk.CTkFrame:
        """Environment scan with progress."""
        pass
    
    def build_module_stage(self, module: ModuleRecommendation) -> ctk.CTkFrame:
        """
        Module configuration stage.
        Shows recommendation, reasoning, config options.
        """
        pass
    
    def build_review_stage(self) -> ctk.CTkFrame:
        """Final review before installation."""
        pass
    
    def build_installation_stage(self) -> ctk.CTkFrame:
        """Installation progress display."""
        pass
    
    def build_complete_stage(self) -> ctk.CTkFrame:
        """Success screen with next steps."""
        pass
```

### 6.2 Wizard Stage Components

**File:** `src/ui/wizard/components/`

```
components/
├── use_case_card.py      # Clickable card for use case selection
├── module_config.py      # Module configuration panel
├── api_key_input.py      # API key entry with validation
├── progress_panel.py     # Installation progress display
├── reasoning_display.py  # Shows recommendation reasoning
└── warning_banner.py     # Warning/error display
```

### 6.3 App Modifications

**File:** `src/ui/app.py`

**Changes Required:**
- Check `wizard_completed` flag on startup
- Show wizard modal if needed
- Add method to re-run wizard from settings

```python
class App(ctk.CTk):
    def __init__(self):
        # ... existing init ...
        
        # Check if wizard needed
        if not config_manager.get("wizard_completed", False):
            self.after(100, self.show_setup_wizard)
    
    def show_setup_wizard(self):
        """Launch the setup wizard."""
        wizard = SetupWizard(self, on_complete=self.on_wizard_complete)
        wizard.grab_set()  # Make modal
    
    def on_wizard_complete(self):
        """Called when wizard finishes."""
        # Refresh all views to reflect new installations
        self.refresh_all_views()
```

---

## 7. File Structure

### 7.1 New Files to Create

```
src/
├── services/
│   ├── setup_wizard_service.py    # NEW: Wizard orchestration
│   ├── shortcut_service.py        # NEW: Desktop shortcut creation
│   ├── download_service.py        # NEW: Download with retry/progress
│   └── recommendation_service.py  # EXISTS: Enhance
│
├── ui/
│   ├── wizard/
│   │   ├── __init__.py
│   │   ├── setup_wizard.py        # NEW: Main wizard window
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── use_case_card.py   # NEW
│   │       ├── module_config.py   # NEW
│   │       ├── api_key_input.py   # NEW
│   │       ├── progress_panel.py  # NEW
│   │       ├── reasoning_display.py # NEW
│   │       └── warning_banner.py  # NEW
│   │
│   └── views/
│       └── comfyui.py             # EXISTS: Update to use recommendations
│
├── config/
│   └── resources.json             # EXISTS: Major update per schema
│
└── workflows/                      # NEW: Bundled workflow templates
    ├── wan_i2v_basic.json
    ├── sdxl_basic.json
    └── README.md
```

### 7.2 Files to Modify

| File | Changes |
|------|---------|
| `src/services/system_service.py` | Fix Apple Silicon RAM, add full scan |
| `src/services/comfy_service.py` | Support GGUF, workflows, recommendations |
| `src/services/dev_service.py` | Add uninstall, API validation |
| `src/config/manager.py` | Add wizard_completed flag handling |
| `src/config/resources.json` | Complete rewrite per schema |
| `src/ui/app.py` | Add wizard launch logic |
| `src/ui/views/comfyui.py` | Fix messagebox import, use recommendations |
| `src/ui/views/settings.py` | Add "Re-run Setup Wizard" button |

---

## 8. Implementation Phases

### Phase 1: Critical Fixes (Do First)

**Priority: BLOCKER - App crashes without these**

1. Fix messagebox import in `src/ui/views/comfyui.py`
   ```python
   from tkinter import filedialog, ttk, messagebox
   ```

2. Fix Apple Silicon RAM detection in `src/services/system_service.py`
   ```python
   elif platform.system() == "Darwin" and platform.machine() == "arm64":
       gpu_name = "Apple Silicon (MPS)"
       try:
           result = subprocess.check_output(["sysctl", "-n", "hw.memsize"])
           ram_bytes = int(result.strip())
           vram_gb = ram_bytes // (1024**3)  # Unified memory = RAM
       except:
           vram_gb = 16  # Fallback
   ```

### Phase 2: GGUF & Video Support

**Priority: HIGH - Enables Andy use case**

1. Add to `resources.json`:
   - ComfyUI-GGUF custom node definition
   - Wan 2.2 I2V GGUF model definitions
   - Video generation use case

2. Update `ComfyService.generate_manifest()` to handle GGUF models

3. Create `workflows/wan_i2v_basic.json` template

4. Add workflow deployment logic

### Phase 3: Core Services

**Priority: HIGH - Foundation for wizard**

1. Create `ShortcutService`
2. Create `DownloadService` 
3. Enhance `SystemService` with full environment scan
4. Create `SetupWizardService`

### Phase 4: Wizard UI

**Priority: HIGH - User-facing feature**

1. Create wizard window skeleton
2. Implement use case selection stage
3. Implement environment scan stage
4. Implement module configuration stages
5. Implement review stage
6. Implement installation stage
7. Implement completion stage

### Phase 5: Integration & Polish

**Priority: MEDIUM**

1. Connect wizard to app startup
2. Add "Re-run Wizard" to settings
3. Update existing views to reflect wizard choices
4. Add API key validation
5. Comprehensive error handling
6. User testing and refinement

### Phase 6: Future Modules

**Priority: LOW - After core is stable**

1. LM Studio module
2. MCP configuration module
3. Advanced mode features

---

## 9. Critical Bug Fixes

### 9.1 Messagebox Import (BLOCKER)

**File:** `src/ui/views/comfyui.py`

**Current (Broken):**
```python
from tkinter import filedialog, ttk
```

**Fixed:**
```python
from tkinter import filedialog, ttk, messagebox
```

### 9.2 Apple Silicon RAM Detection (HIGH)

**File:** `src/services/system_service.py`

**Current (Broken):**
```python
elif platform.system() == "Darwin" and platform.machine() == "arm64":
    gpu_name = "Apple Silicon (MPS)"
    vram_gb = 16  # Hardcoded - WRONG
```

**Fixed:**
```python
elif platform.system() == "Darwin" and platform.machine() == "arm64":
    gpu_name = "Apple Silicon (MPS)"
    try:
        # Get actual unified memory
        result = subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"],
            creationflags=0  # No Windows flags on Mac
        )
        ram_bytes = int(result.strip())
        vram_gb = ram_bytes // (1024**3)
    except Exception as e:
        log.warning(f"Could not detect Mac RAM: {e}")
        vram_gb = 16  # Conservative fallback
```

---

## 10. Testing Requirements

### 10.1 Unit Tests

| Service | Test Cases |
|---------|------------|
| SystemService | GPU detection (NVIDIA, Apple, none), RAM detection, disk space |
| RecommendationService | Each use case + hardware combination |
| ShortcutService | Shortcut creation on each OS |
| DownloadService | Success, retry on failure, hash validation |
| SetupWizardService | Full flow, skip handling, error recovery |

### 10.2 Integration Tests

1. Full wizard flow on Windows with NVIDIA GPU
2. Full wizard flow on macOS with Apple Silicon
3. Full wizard flow on Linux
4. ComfyUI installation and launch
5. CLI tool installation and shortcut creation
6. API key storage and retrieval

### 10.3 Manual Testing Checklist

- [ ] First launch shows wizard
- [ ] Environment scan completes without errors
- [ ] Recommendations make sense for hardware
- [ ] Skip button works on each module
- [ ] API key input and validation works
- [ ] Installation progress displays correctly
- [ ] Shortcuts are created and work
- [ ] ComfyUI launches successfully
- [ ] CLI tools launch from shortcuts
- [ ] Re-run wizard from settings works
- [ ] App remembers wizard_completed state

---

## Appendix A: Consulting Proposal Alignment

This specification directly supports the AI Infrastructure Consulting proposal:

| Proposal Deliverable | App Feature |
|---------------------|-------------|
| **Quick Win Session** | Setup wizard completes full stack in one session |
| **Full Stack Audit** | Environment scan + reasoning display |
| **ComfyUI Pipelines** | Workflow template deployment |
| **CLI/API Setup** | CLI provider module with API key management |
| **Cost Optimization** | CLI tools use pay-per-use API, not subscriptions |
| **Desktop Shortcuts** | ShortcutService creates launchers |
| **No Coding Required** | Entire flow is GUI-based |

---

## Appendix B: Video Generation Use Case (Andy)

Specific requirements for the documentary filmmaker use case:

**Input:** Historical photograph + audio track
**Output:** 5-10 second animated video clip

**Required Components:**
1. ComfyUI-GGUF node (for Apple Silicon compatibility)
2. Wan 2.2 I2V High Noise GGUF model
3. Wan 2.2 I2V Low Noise GGUF model
4. Video Helper Suite node
5. wan_i2v_basic.json workflow template

**Hardware Profile:** Apple Silicon with 64GB unified memory
**Recommended Tier:** GGUF (not full precision)

**Workflow Template Contents:**
- Two Unet Loader (GGUF) nodes configured for High/Low noise models
- Load Image node
- WanImageToVideo node
- Video output node
- Preset resolution: 320x320 (for testing), 640x640 (for production)

---

## 11. Model Management System

### 11.1 Overview

Post-installation model management allowing users to browse, download, organize, and remove models without touching the file system directly.

**Core Capabilities:**
- Browse installed models by category (checkpoints, loras, unet, vae, controlnet, etc.)
- Download new models from curated repositories (HuggingFace, CivitAI)
- Hash verification for security and integrity
- Move/copy models between directories
- Batch operations (select multiple, delete, move)
- Model metadata display (size, hash, source, capabilities)

### 11.2 Model Directory Structure

ComfyUI uses this standard structure under `{comfy_path}/models/`:

```
models/
├── checkpoints/        # Main generation models (.safetensors, .ckpt)
├── clip/               # Text encoders
├── clip_vision/        # Vision encoders
├── controlnet/         # ControlNet models
├── embeddings/         # Textual inversions
├── loras/              # LoRA fine-tunes
├── style_models/       # Style transfer models
├── unet/               # GGUF and standalone UNet models
├── upscale_models/     # Upscaling models
└── vae/                # VAE models
```

### 11.3 Data Schemas

#### Model Registry Entry

```python
@dataclass
class LocalModel:
    """Represents an installed model file."""
    
    filename: str                       # "juggernaut_xl_v9.safetensors"
    filepath: Path                      # Full path
    category: str                       # "checkpoints", "loras", etc.
    size_bytes: int
    hash_sha256: Optional[str]          # Computed on demand, cached
    
    # Metadata (if known)
    display_name: Optional[str]         # "Juggernaut XL v9"
    source_url: Optional[str]           # Where it was downloaded from
    source_repo: Optional[str]          # "civitai", "huggingface"
    model_type: Optional[str]           # "sdxl", "sd15", "flux", "gguf"
    capabilities: List[str]             # ["t2i", "i2i"]
    
    # Status
    verified: bool                      # Hash matches known good value
    created_at: datetime
    last_used: Optional[datetime]
```

#### Repository Model Entry

```python
@dataclass
class RepoModel:
    """Represents a model available for download from a repository."""
    
    repo_id: str                        # Unique ID in the repo
    repo_source: str                    # "huggingface", "civitai"
    
    display_name: str
    description: str
    author: str
    
    # Files available
    files: List[RepoModelFile]
    
    # Metadata
    model_type: str                     # "sdxl", "sd15", "flux", "gguf"
    base_model: Optional[str]           # What it's based on
    capabilities: List[str]
    tags: List[str]
    
    # Stats
    downloads: int
    rating: Optional[float]
    
    # Safety
    nsfw: bool
    verified_safe: bool                 # Has been scanned/reviewed
    
@dataclass
class RepoModelFile:
    """Single downloadable file within a repo model."""
    
    filename: str
    url: str
    size_bytes: int
    hash_sha256: Optional[str]
    quantization: Optional[str]         # "Q5_K_M", "Q8", "fp16", "fp32"
    format: str                         # "safetensors", "gguf", "ckpt"
```

### 11.4 ModelManagerService

**File:** `src/services/model_manager_service.py`

```python
class ModelManagerService:
    """
    Manages local model files in ComfyUI installation.
    """
    
    SUPPORTED_EXTENSIONS = [".safetensors", ".ckpt", ".pt", ".pth", ".gguf", ".bin"]
    
    def __init__(self, comfy_path: str):
        self.comfy_path = Path(comfy_path)
        self.models_path = self.comfy_path / "models"
        self._hash_cache: Dict[str, str] = {}  # filepath -> hash
    
    # === Browsing ===
    
    def get_categories(self) -> List[str]:
        """
        List all model subdirectories.
        Returns: ["checkpoints", "loras", "unet", ...]
        """
        pass
    
    def list_models(self, category: str) -> List[LocalModel]:
        """
        List all models in a category.
        
        Args:
            category: Subdirectory name (e.g., "checkpoints")
            
        Returns:
            List of LocalModel objects
        """
        pass
    
    def list_all_models(self) -> Dict[str, List[LocalModel]]:
        """
        List all models across all categories.
        
        Returns:
            Dict mapping category -> list of models
        """
        pass
    
    def get_model_info(self, filepath: Path) -> LocalModel:
        """Get detailed info for a specific model file."""
        pass
    
    def search_models(self, query: str) -> List[LocalModel]:
        """Search models by filename or display name."""
        pass
    
    # === Hash Verification ===
    
    def compute_hash(self, filepath: Path) -> str:
        """
        Compute SHA256 hash of a model file.
        Uses chunked reading for large files.
        Caches result.
        """
        pass
    
    def verify_model(self, filepath: Path, expected_hash: str) -> bool:
        """Verify model file matches expected hash."""
        pass
    
    def verify_all_models(
        self, 
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, bool]:
        """
        Verify all known models against stored hashes.
        
        Args:
            progress_callback: Called with (filename, current, total)
            
        Returns:
            Dict mapping filepath -> verification result
        """
        pass
    
    # === File Operations ===
    
    def delete_model(self, filepath: Path) -> bool:
        """
        Delete a model file.
        
        Returns:
            True if deleted, False if failed
        """
        pass
    
    def delete_models_batch(self, filepaths: List[Path]) -> Dict[str, bool]:
        """
        Delete multiple models.
        
        Returns:
            Dict mapping filepath -> success
        """
        pass
    
    def move_model(self, filepath: Path, dest_category: str) -> Path:
        """
        Move a model to a different category.
        
        Args:
            filepath: Current path
            dest_category: Target category (e.g., "loras")
            
        Returns:
            New filepath
        """
        pass
    
    def move_models_batch(
        self, 
        filepaths: List[Path], 
        dest_category: str
    ) -> Dict[str, Path]:
        """
        Move multiple models to a category.
        
        Returns:
            Dict mapping old path -> new path
        """
        pass
    
    def copy_model(self, filepath: Path, dest_category: str) -> Path:
        """Copy a model to a different category."""
        pass
    
    def rename_model(self, filepath: Path, new_name: str) -> Path:
        """
        Rename a model file.
        
        Args:
            filepath: Current path
            new_name: New filename (with extension)
            
        Returns:
            New filepath
        """
        pass
    
    # === Metadata ===
    
    def save_model_metadata(self, filepath: Path, metadata: dict) -> None:
        """
        Save metadata for a model to sidecar JSON file.
        Creates {filename}.meta.json alongside the model.
        """
        pass
    
    def load_model_metadata(self, filepath: Path) -> Optional[dict]:
        """Load metadata from sidecar file if exists."""
        pass
    
    # === Statistics ===
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            {
                "total_size_gb": float,
                "by_category": {"checkpoints": float, ...},
                "model_count": int,
                "largest_models": List[Tuple[str, float]]
            }
        """
        pass
```

### 11.5 ModelRepositoryService

**File:** `src/services/model_repository_service.py`

```python
class ModelRepositoryService:
    """
    Interface with external model repositories (HuggingFace, CivitAI).
    Provides browsing, search, and download capabilities.
    """
    
    def __init__(self):
        self.sources = {
            "huggingface": HuggingFaceAdapter(),
            "civitai": CivitAIAdapter()
        }
        self._curated_models: Optional[dict] = None  # Loaded from resources.json
    
    # === Curated Models ===
    
    def get_curated_models(
        self, 
        category: Optional[str] = None,
        model_type: Optional[str] = None,
        capabilities: Optional[List[str]] = None
    ) -> List[RepoModel]:
        """
        Get pre-vetted models from our curated list in resources.json.
        These are safe, tested, and have verified hashes.
        
        Args:
            category: Filter by category (checkpoints, loras, etc.)
            model_type: Filter by type (sdxl, sd15, flux, gguf)
            capabilities: Filter by capabilities (t2i, i2i, i2v)
            
        Returns:
            List of curated RepoModel entries
        """
        pass
    
    def get_recommended_models(
        self, 
        use_case: str, 
        hardware_profile: str
    ) -> List[RepoModel]:
        """
        Get models recommended for a specific use case and hardware.
        
        Args:
            use_case: From use_cases in resources.json
            hardware_profile: From hardware_profiles
            
        Returns:
            Sorted list of recommended models
        """
        pass
    
    # === Repository Search ===
    
    def search_huggingface(
        self,
        query: str,
        model_type: Optional[str] = None,
        limit: int = 20
    ) -> List[RepoModel]:
        """
        Search HuggingFace for models.
        
        Filters to ComfyUI-compatible formats.
        """
        pass
    
    def search_civitai(
        self,
        query: str,
        model_type: Optional[str] = None,
        nsfw: bool = False,
        limit: int = 20
    ) -> List[RepoModel]:
        """
        Search CivitAI for models.
        
        Args:
            query: Search query
            model_type: Filter by type
            nsfw: Include NSFW models
            limit: Max results
        """
        pass
    
    def search_all(
        self,
        query: str,
        **filters
    ) -> Dict[str, List[RepoModel]]:
        """
        Search all repositories.
        
        Returns:
            Dict mapping source -> results
        """
        pass
    
    # === Model Details ===
    
    def get_model_details(self, repo_source: str, repo_id: str) -> RepoModel:
        """Get full details for a specific model."""
        pass
    
    def get_available_files(self, repo_source: str, repo_id: str) -> List[RepoModelFile]:
        """
        Get all downloadable files for a model.
        
        Includes different quantizations, formats, etc.
        """
        pass
    
    # === Download ===
    
    def download_model(
        self,
        file: RepoModelFile,
        dest_category: str,
        comfy_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> LocalModel:
        """
        Download a model file to the appropriate directory.
        
        Args:
            file: RepoModelFile to download
            dest_category: Target category (checkpoints, loras, etc.)
            comfy_path: ComfyUI installation path
            progress_callback: Called with (bytes_downloaded, total_bytes)
            
        Returns:
            LocalModel representing the downloaded file
            
        Raises:
            HashMismatchError: If hash verification fails
            DownloadError: If download fails
        """
        pass
    
    def download_model_batch(
        self,
        files: List[Tuple[RepoModelFile, str]],  # (file, dest_category)
        comfy_path: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[LocalModel]:
        """
        Download multiple models.
        
        Args:
            files: List of (file, destination_category) tuples
            comfy_path: ComfyUI installation path
            progress_callback: Called with (filename, bytes_downloaded, total_bytes)
        """
        pass


class HuggingFaceAdapter:
    """Adapter for HuggingFace Hub API."""
    
    BASE_URL = "https://huggingface.co"
    API_URL = "https://huggingface.co/api"
    
    def search(self, query: str, **filters) -> List[dict]:
        """Search HuggingFace models."""
        pass
    
    def get_model_info(self, model_id: str) -> dict:
        """Get model metadata."""
        pass
    
    def get_file_url(self, model_id: str, filename: str) -> str:
        """Get direct download URL for a file."""
        pass


class CivitAIAdapter:
    """Adapter for CivitAI API."""
    
    BASE_URL = "https://civitai.com"
    API_URL = "https://civitai.com/api/v1"
    
    def search(self, query: str, **filters) -> List[dict]:
        """Search CivitAI models."""
        pass
    
    def get_model_info(self, model_id: str) -> dict:
        """Get model metadata."""
        pass
    
    def get_model_version(self, version_id: str) -> dict:
        """Get specific version details."""
        pass
    
    def get_download_url(self, version_id: str) -> str:
        """Get download URL (may require API key for some models)."""
        pass
```

### 11.6 Curated Models Schema (Addition to resources.json)

```json
{
  "model_repository": {
    "curated_models": {
      "checkpoints": [
        {
          "id": "juggernaut_xl_v9",
          "display_name": "Juggernaut XL v9",
          "description": "Photorealistic SDXL model, excellent for portraits and scenes",
          "source": "civitai",
          "source_id": "133005",
          "files": [
            {
              "filename": "juggernautXL_v9Rdphoto2Lightning.safetensors",
              "url": "https://civitai.com/api/download/models/240840",
              "size_bytes": 6938078792,
              "hash_sha256": "aeb7c9a6a0...",
              "format": "safetensors",
              "quantization": null
            }
          ],
          "model_type": "sdxl",
          "capabilities": ["t2i", "i2i"],
          "tags": ["photorealistic", "portrait", "landscape"],
          "min_vram": 8,
          "recommended_for": ["content_generation", "full_stack"]
        }
      ],
      "unet_gguf": [
        {
          "id": "wan_i2v_q5",
          "display_name": "Wan 2.2 Image-to-Video (Q5)",
          "description": "Quantized I2V model optimized for Apple Silicon and low VRAM",
          "source": "huggingface",
          "source_id": "QuantStack/Wan2.2-I2V-A14B-GGUF",
          "files": [
            {
              "filename": "Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf",
              "url": "https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf",
              "size_bytes": 10523648000,
              "hash_sha256": "abc123...",
              "format": "gguf",
              "quantization": "Q5_K_M"
            },
            {
              "filename": "Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf",
              "url": "https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf",
              "size_bytes": 10523648000,
              "hash_sha256": "def456...",
              "format": "gguf",
              "quantization": "Q5_K_M"
            }
          ],
          "model_type": "gguf",
          "capabilities": ["i2v"],
          "tags": ["video", "animation", "apple-silicon"],
          "min_vram": 0,
          "min_ram": 32,
          "recommended_for": ["video_generation"],
          "requires_nodes": ["ComfyUI-GGUF"]
        }
      ],
      "loras": [],
      "controlnet": [],
      "vae": []
    },
    
    "trusted_sources": {
      "huggingface": {
        "display_name": "Hugging Face",
        "base_url": "https://huggingface.co",
        "api_url": "https://huggingface.co/api",
        "requires_auth": false,
        "safety_rating": "high"
      },
      "civitai": {
        "display_name": "CivitAI",
        "base_url": "https://civitai.com",
        "api_url": "https://civitai.com/api/v1",
        "requires_auth": false,
        "safety_rating": "medium",
        "notes": "User-uploaded content, verify hashes"
      }
    },
    
    "blocked_hashes": [
      "known_malicious_hash_1",
      "known_malicious_hash_2"
    ]
  }
}
```

### 11.7 Model Manager UI

**File:** `src/ui/views/model_manager.py`

```python
class ModelManagerFrame(ctk.CTkFrame):
    """
    Model management interface.
    
    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │ [Installed] [Browse & Download]                    [Search] │
    ├─────────────────────────────────────────────────────────────┤
    │ Categories │  Model List                          │ Details │
    │ ─────────  │  ──────────                          │ ─────── │
    │ checkpoints│  □ juggernaut_xl_v9.safetensors 6.5GB│ Name    │
    │ loras      │  □ realistic_vision.safetensors 2.0GB│ Size    │
    │ unet       │  ☑ wan_i2v_high.gguf          9.8GB  │ Hash    │
    │ vae        │                                      │ Source  │
    │ controlnet │                                      │         │
    │            │                                      │ [Verify]│
    ├────────────┴──────────────────────────────────────┴─────────┤
    │ Selected: 1 | [Move To...] [Copy To...] [Delete] | 16.3 GB  │
    └─────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self, master, app):
        pass
    
    # === View Modes ===
    
    def show_installed_models(self):
        """Show locally installed models."""
        pass
    
    def show_download_browser(self):
        """Show model download/browse interface."""
        pass
    
    # === Installed Models Tab ===
    
    def build_category_list(self):
        """Build category sidebar."""
        pass
    
    def build_model_list(self, category: str):
        """Build scrollable model list for category."""
        pass
    
    def build_details_panel(self):
        """Build model details sidebar."""
        pass
    
    def on_model_selected(self, model: LocalModel):
        """Handle model selection, update details panel."""
        pass
    
    def on_category_selected(self, category: str):
        """Handle category change, refresh model list."""
        pass
    
    # === Batch Operations ===
    
    def get_selected_models(self) -> List[LocalModel]:
        """Get all checked models."""
        pass
    
    def on_delete_selected(self):
        """Delete selected models with confirmation."""
        pass
    
    def on_move_selected(self):
        """Show move dialog, move selected models."""
        pass
    
    def on_copy_selected(self):
        """Show copy dialog, copy selected models."""
        pass
    
    # === Download Browser Tab ===
    
    def build_curated_section(self):
        """Show curated/recommended models."""
        pass
    
    def build_search_section(self):
        """Search bar and results."""
        pass
    
    def on_search(self, query: str):
        """Execute search across repositories."""
        pass
    
    def on_download_model(self, model: RepoModel, file: RepoModelFile):
        """Start model download."""
        pass
    
    # === Verification ===
    
    def on_verify_model(self, model: LocalModel):
        """Verify single model hash."""
        pass
    
    def on_verify_all(self):
        """Verify all models (background task)."""
        pass
```

---

## 12. Workflow Management System

### 12.1 Overview

Workflow management focused on **importing and recommending existing workflows** rather than creating new ones from scratch. This avoids the complexity of ComfyUI's node API.

**Core Capabilities:**
- Browse and import community workflows from curated sources
- Recommend workflows based on use case and installed models
- Organize workflows into user collections
- Validate workflows against installed models/nodes
- One-click workflow loading into ComfyUI

### 12.2 Workflow Sources

**Curated Sources:**
1. **Bundled Workflows** - Ship with the app, tested and validated
2. **ComfyUI Examples** - Official example workflows from ComfyUI repo
3. **OpenArt Workflows** - Community workflows from openart.ai
4. **Civitai Workflows** - Workflows attached to models on CivitAI

### 12.3 Data Schemas

```python
@dataclass
class Workflow:
    """Represents a ComfyUI workflow."""
    
    workflow_id: str                    # Unique identifier
    filename: str                       # "wan_i2v_basic.json"
    filepath: Optional[Path]            # Local path if installed
    
    # Metadata
    display_name: str
    description: str
    author: str
    source: str                         # "bundled", "openart", "civitai", "user"
    source_url: Optional[str]
    
    # Requirements
    required_models: List[str]          # Model IDs that must be installed
    required_nodes: List[str]           # Custom node IDs required
    capabilities: List[str]             # What this workflow does
    
    # Compatibility
    min_comfy_version: Optional[str]
    model_type: str                     # "sdxl", "sd15", "flux", "gguf"
    
    # Preview
    preview_image_url: Optional[str]
    example_outputs: List[str]          # URLs to example outputs
    
    # Status
    installed: bool
    validated: bool                     # All requirements met
    missing_requirements: List[str]     # What's missing if not validated
    
    # Categorization
    tags: List[str]
    category: str                       # "image", "video", "upscale", etc.


@dataclass
class WorkflowCollection:
    """User-created workflow collection/folder."""
    
    collection_id: str
    name: str
    description: str
    workflows: List[str]                # Workflow IDs
    created_at: datetime
```

### 12.4 WorkflowService

**File:** `src/services/workflow_service.py`

```python
class WorkflowService:
    """
    Manages workflow discovery, import, and organization.
    """
    
    COMFY_WORKFLOWS_PATH = "user/default/workflows"
    
    def __init__(self, comfy_path: str):
        self.comfy_path = Path(comfy_path)
        self.workflows_path = self.comfy_path / self.COMFY_WORKFLOWS_PATH
    
    # === Browsing ===
    
    def get_installed_workflows(self) -> List[Workflow]:
        """List all workflows installed in ComfyUI."""
        pass
    
    def get_bundled_workflows(self) -> List[Workflow]:
        """List workflows bundled with the app."""
        pass
    
    def get_curated_workflows(
        self,
        category: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        model_type: Optional[str] = None
    ) -> List[Workflow]:
        """
        Get curated workflows from resources.json.
        
        Args:
            category: Filter by category (image, video, etc.)
            capabilities: Filter by capabilities (t2i, i2v, etc.)
            model_type: Filter by compatible model type
        """
        pass
    
    def search_openart_workflows(
        self,
        query: str,
        limit: int = 20
    ) -> List[Workflow]:
        """Search OpenArt for community workflows."""
        pass
    
    # === Recommendations ===
    
    def get_recommended_workflows(
        self,
        use_case: str,
        installed_models: List[str],
        installed_nodes: List[str]
    ) -> List[Workflow]:
        """
        Get workflows recommended for use case that work with installed components.
        
        Prioritizes:
        1. Workflows where all requirements are already met
        2. Workflows that match the use case capabilities
        3. Higher-rated/more popular workflows
        """
        pass
    
    def get_workflows_for_model(self, model_id: str) -> List[Workflow]:
        """Get workflows that use a specific model."""
        pass
    
    # === Validation ===
    
    def validate_workflow(
        self,
        workflow: Workflow,
        installed_models: List[str],
        installed_nodes: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Check if a workflow can run with current installation.
        
        Returns:
            (is_valid, list_of_missing_requirements)
        """
        pass
    
    def parse_workflow_requirements(self, workflow_json: dict) -> dict:
        """
        Parse a workflow JSON to extract requirements.
        
        Returns:
            {
                "nodes": ["ComfyUI-GGUF", ...],
                "models": ["wan_i2v_high.gguf", ...],
                "model_type": "gguf"
            }
        """
        pass
    
    # === Import/Install ===
    
    def import_workflow(
        self,
        source_path_or_url: str,
        display_name: Optional[str] = None
    ) -> Workflow:
        """
        Import a workflow from file or URL.
        
        - Downloads if URL
        - Copies to workflows directory
        - Parses and validates
        - Creates metadata entry
        """
        pass
    
    def import_bundled_workflow(self, workflow_id: str) -> Workflow:
        """Copy a bundled workflow to user's ComfyUI."""
        pass
    
    def download_workflow(
        self,
        url: str,
        display_name: str
    ) -> Workflow:
        """Download workflow from URL."""
        pass
    
    # === Organization ===
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete an installed workflow."""
        pass
    
    def rename_workflow(self, workflow_id: str, new_name: str) -> Workflow:
        """Rename a workflow."""
        pass
    
    def create_collection(self, name: str, description: str = "") -> WorkflowCollection:
        """Create a new workflow collection."""
        pass
    
    def add_to_collection(self, workflow_id: str, collection_id: str) -> None:
        """Add workflow to a collection."""
        pass
    
    # === Launch ===
    
    def get_workflow_launch_url(self, workflow: Workflow) -> str:
        """
        Get URL to open ComfyUI with this workflow loaded.
        
        Returns URL like: http://localhost:8188/?workflow=path/to/workflow.json
        """
        pass


class OpenArtAdapter:
    """Adapter for OpenArt workflow API."""
    
    BASE_URL = "https://openart.ai"
    API_URL = "https://openart.ai/api"
    
    def search_workflows(self, query: str, **filters) -> List[dict]:
        """Search OpenArt workflows."""
        pass
    
    def get_workflow_details(self, workflow_id: str) -> dict:
        """Get workflow metadata."""
        pass
    
    def get_workflow_json(self, workflow_id: str) -> dict:
        """Download the actual workflow JSON."""
        pass
```

### 12.5 Curated Workflows Schema (Addition to resources.json)

```json
{
  "workflow_repository": {
    "bundled_workflows": [
      {
        "id": "wan_i2v_basic",
        "filename": "wan_i2v_basic.json",
        "display_name": "Image to Video (Basic)",
        "description": "Animate a still image into a short video clip using Wan 2.2",
        "author": "AI Universal Suite",
        "category": "video",
        "capabilities": ["i2v"],
        "model_type": "gguf",
        "required_models": ["wan_i2v_high_q5", "wan_i2v_low_q5"],
        "required_nodes": ["ComfyUI-GGUF", "ComfyUI-VideoHelperSuite"],
        "tags": ["video", "animation", "beginner-friendly"],
        "preview_image": "previews/wan_i2v_basic.png"
      },
      {
        "id": "sdxl_basic_t2i",
        "filename": "sdxl_basic_t2i.json",
        "display_name": "Text to Image (SDXL)",
        "description": "Generate images from text prompts using SDXL",
        "author": "AI Universal Suite",
        "category": "image",
        "capabilities": ["t2i"],
        "model_type": "sdxl",
        "required_models": [],
        "required_nodes": [],
        "tags": ["image", "text-to-image", "beginner-friendly"],
        "preview_image": "previews/sdxl_basic_t2i.png"
      },
      {
        "id": "flux_schnell_t2i",
        "filename": "flux_schnell_t2i.json",
        "display_name": "Text to Image (Flux Schnell)",
        "description": "Fast, high-quality image generation with Flux",
        "author": "AI Universal Suite",
        "category": "image",
        "capabilities": ["t2i"],
        "model_type": "flux",
        "required_models": ["flux_schnell"],
        "required_nodes": [],
        "tags": ["image", "text-to-image", "fast"],
        "preview_image": "previews/flux_schnell_t2i.png"
      }
    ],
    
    "curated_external": [
      {
        "id": "openart_wan_lipsync",
        "source": "openart",
        "source_id": "abc123",
        "display_name": "Wan 2.2 with Lip Sync",
        "description": "Full pipeline for animated talking heads",
        "category": "video",
        "capabilities": ["i2v", "lipsync"],
        "model_type": "gguf",
        "required_nodes": ["ComfyUI-GGUF", "ComfyUI-LatentSyncWrapper"],
        "tags": ["video", "lipsync", "advanced"],
        "url": "https://openart.ai/workflows/..."
      }
    ],
    
    "workflow_sources": {
      "openart": {
        "display_name": "OpenArt",
        "base_url": "https://openart.ai",
        "api_available": true,
        "quality": "community"
      },
      "comfyui_examples": {
        "display_name": "ComfyUI Official",
        "base_url": "https://github.com/comfyanonymous/ComfyUI_examples",
        "api_available": false,
        "quality": "official"
      }
    }
  }
}
```

### 12.6 Workflow Browser UI

**File:** `src/ui/views/workflow_browser.py`

```python
class WorkflowBrowserFrame(ctk.CTkFrame):
    """
    Workflow browsing and management interface.
    
    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │ [Installed] [Recommended] [Browse]              [Search]    │
    ├─────────────────────────────────────────────────────────────┤
    │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
    │ │  [Preview]      │ │  [Preview]      │ │  [Preview]      │ │
    │ │                 │ │                 │ │                 │ │
    │ │ Wan I2V Basic   │ │ SDXL Text2Img   │ │ Flux Fast       │ │
    │ │ ✓ Ready         │ │ ⚠ Missing model │ │ ✓ Ready         │ │
    │ │ [Load] [Info]   │ │ [Install Reqs]  │ │ [Load] [Info]   │ │
    │ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
    ├─────────────────────────────────────────────────────────────┤
    │ Showing 12 workflows | Filter: [All ▼] [Video ▼] [Ready ▼] │
    └─────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self, master, app):
        pass
    
    # === View Modes ===
    
    def show_installed(self):
        """Show locally installed workflows."""
        pass
    
    def show_recommended(self):
        """Show workflows recommended for user's setup."""
        pass
    
    def show_browse(self):
        """Show browsable curated workflows."""
        pass
    
    # === Workflow Cards ===
    
    def build_workflow_card(self, workflow: Workflow) -> ctk.CTkFrame:
        """
        Build a workflow card widget.
        
        Shows:
        - Preview image (if available)
        - Name and description
        - Status (ready, missing requirements)
        - Action buttons
        """
        pass
    
    def on_workflow_load(self, workflow: Workflow):
        """Load workflow into ComfyUI."""
        pass
    
    def on_workflow_info(self, workflow: Workflow):
        """Show detailed workflow info dialog."""
        pass
    
    def on_install_requirements(self, workflow: Workflow):
        """Install missing models/nodes for workflow."""
        pass
    
    # === Search & Filter ===
    
    def on_search(self, query: str):
        """Search workflows."""
        pass
    
    def apply_filters(self, category: str, capability: str, status: str):
        """Apply display filters."""
        pass
    
    # === Import ===
    
    def on_import_file(self):
        """Import workflow from local file."""
        pass
    
    def on_import_url(self):
        """Import workflow from URL."""
        pass
```

---

## 13. Recommendation Resolution Algorithm

### 13.1 Overview

The recommendation engine uses a **weighted scoring system** that combines:
1. **User Profile Scores** - Self-reported experience and preferences from onboarding survey
2. **Use Case Parameters** - Specific requirements for content type, style, and quality
3. **Hardware Constraint Scores** - System capabilities normalized to compatibility scores

These combine into a **composite fitness score** for each candidate configuration, allowing dynamic manifest resolution that balances user needs against system reality.

### 13.2 User Profile Schema

Collected during onboarding survey:

```python
@dataclass
class UserProfile:
    """User's self-reported experience and preferences."""
    
    # === Experience Scores (1-10 self-report) ===
    ai_experience: int              # 1 = "Never used AI tools" → 10 = "Daily power user"
    technical_experience: int       # 1 = "Avoid terminals" → 10 = "Comfortable with code"
    
    # === Proficiency Level (derived from scores) ===
    # Beginner: ai_exp < 4 AND tech_exp < 4
    # Intermediate: ai_exp >= 4 OR tech_exp >= 4
    # Advanced: ai_exp >= 7 OR tech_exp >= 7
    # Expert: ai_exp >= 8 AND tech_exp >= 8
    proficiency: Literal["Beginner", "Intermediate", "Advanced", "Expert"]
    
    # === Use Case Intent (multi-select) ===
    primary_use_cases: List[str]    # ["image_generation", "video_generation", "productivity"]
    
    # === Content Parameters (per use case) ===
    content_preferences: Dict[str, ContentPreferences]


@dataclass
class ContentPreferences:
    """Detailed parameters about desired output characteristics."""
    
    # === Content Type (1-10 importance) ===
    photorealism: int               # How important is photorealistic output?
    artistic_style: int             # How important is stylized/artistic output?
    speed: int                      # How important is generation speed?
    quality: int                    # How important is maximum quality?
    consistency: int                # How important is consistent results?
    
    # === Style Tags (selected from predefined list) ===
    style_tags: List[str]           # ["portrait", "landscape", "product", "anime", etc.]
    
    # === Output Parameters ===
    typical_resolution: str         # "512x512", "1024x1024", "2048x2048", "video_480p", "video_1080p"
    batch_size: int                 # Typical number of outputs per session
    
    # === Advanced (shown only if proficiency >= Advanced) ===
    preferred_model_family: Optional[str]   # "flux", "sdxl", "sd15", None = auto
    quantization_acceptable: bool           # Accept GGUF/quantized for performance?
```

### 13.3 Hardware Constraint Schema

```python
@dataclass
class HardwareConstraints:
    """Normalized hardware capabilities as constraint scores."""
    
    # === Raw Values (from SystemService) ===
    vram_gb: float
    ram_gb: float
    disk_free_gb: float
    gpu_vendor: str                 # "nvidia", "amd", "apple", "none"
    gpu_name: str
    os: str
    cpu_cores: int
    
    # === Normalized Scores (0.0 - 1.0) ===
    vram_score: float               # 0 = no VRAM, 1 = 24GB+
    ram_score: float                # 0 = 8GB, 1 = 64GB+
    storage_score: float            # 0 = <50GB free, 1 = 500GB+ free
    compute_score: float            # Combined GPU capability score
    
    # === Hard Limits (binary) ===
    can_run_flux: bool              # VRAM >= 12GB OR (Apple Silicon AND RAM >= 32GB)
    can_run_sdxl: bool              # VRAM >= 8GB OR (Apple Silicon AND RAM >= 16GB)
    can_run_video: bool             # VRAM >= 8GB OR (Apple Silicon AND RAM >= 32GB)
    requires_quantization: bool     # Apple Silicon OR VRAM < 8GB
    
    @classmethod
    def from_environment(cls, env: EnvironmentReport) -> "HardwareConstraints":
        """Compute constraint scores from raw environment data."""
        
        # VRAM scoring (0-1 normalized)
        if env.gpu_vendor == "apple":
            # Apple Silicon uses unified memory
            effective_vram = env.ram_gb * 0.75  # ~75% available for GPU
            vram_score = min(1.0, effective_vram / 24)
        else:
            vram_score = min(1.0, env.vram_gb / 24)
        
        # RAM scoring
        ram_score = min(1.0, (env.ram_gb - 8) / 56)  # 8GB = 0, 64GB = 1
        
        # Storage scoring
        storage_score = min(1.0, env.disk_free_gb / 500)
        
        # Compute score (GPU capability)
        if env.gpu_vendor == "nvidia":
            compute_score = vram_score * 1.0  # Full CUDA support
        elif env.gpu_vendor == "apple":
            compute_score = vram_score * 0.7  # MPS has overhead
        elif env.gpu_vendor == "amd":
            compute_score = vram_score * 0.5  # ROCm limited support
        else:
            compute_score = 0.1  # CPU only
        
        # Hard limits
        can_run_flux = (env.vram_gb >= 12) or (env.gpu_vendor == "apple" and env.ram_gb >= 32)
        can_run_sdxl = (env.vram_gb >= 8) or (env.gpu_vendor == "apple" and env.ram_gb >= 16)
        can_run_video = (env.vram_gb >= 8) or (env.gpu_vendor == "apple" and env.ram_gb >= 32)
        requires_quantization = env.gpu_vendor == "apple" or env.vram_gb < 8
        
        return cls(
            vram_gb=env.vram_gb,
            ram_gb=env.ram_gb,
            disk_free_gb=env.disk_free_gb,
            gpu_vendor=env.gpu_vendor,
            gpu_name=env.gpu_name,
            os=env.os,
            cpu_cores=env.cpu_cores,
            vram_score=vram_score,
            ram_score=ram_score,
            storage_score=storage_score,
            compute_score=compute_score,
            can_run_flux=can_run_flux,
            can_run_sdxl=can_run_sdxl,
            can_run_video=can_run_video,
            requires_quantization=requires_quantization
        )
```

### 13.4 Model Candidate Scoring

Each model in the repository has attributes that are scored against user preferences:

```python
@dataclass
class ModelCandidate:
    """A model being evaluated for recommendation."""
    
    model_id: str
    model_info: dict                # From resources.json
    
    # === Capability Scores (from model metadata) ===
    photorealism_score: float       # 0-1, how photorealistic
    artistic_score: float           # 0-1, how stylized
    speed_score: float              # 0-1, how fast (inverse of quality often)
    quality_score: float            # 0-1, maximum output quality
    consistency_score: float        # 0-1, how consistent outputs are
    
    # === Requirements ===
    min_vram_gb: float
    min_ram_gb: float
    size_gb: float
    capabilities: List[str]         # ["t2i", "i2i", "i2v", etc.]
    
    # === Computed Scores ===
    user_fit_score: float = 0.0     # How well it matches user preferences
    hardware_fit_score: float = 0.0 # How well it fits hardware constraints
    composite_score: float = 0.0    # Final weighted score


def score_model_candidate(
    candidate: ModelCandidate,
    user_profile: UserProfile,
    hardware: HardwareConstraints,
    content_prefs: ContentPreferences
) -> ModelCandidate:
    """
    Compute fitness scores for a model candidate.
    
    User Fit Score = weighted dot product of user preferences vs model capabilities
    Hardware Fit Score = penalty-based score for constraint violations
    Composite Score = weighted combination
    """
    
    # === User Fit Score ===
    # Normalize user preferences to weights (sum to 1)
    pref_sum = (content_prefs.photorealism + content_prefs.artistic_style + 
                content_prefs.speed + content_prefs.quality + content_prefs.consistency)
    
    if pref_sum > 0:
        weights = {
            "photorealism": content_prefs.photorealism / pref_sum,
            "artistic": content_prefs.artistic_style / pref_sum,
            "speed": content_prefs.speed / pref_sum,
            "quality": content_prefs.quality / pref_sum,
            "consistency": content_prefs.consistency / pref_sum
        }
    else:
        # Default equal weights
        weights = {k: 0.2 for k in ["photorealism", "artistic", "speed", "quality", "consistency"]}
    
    user_fit = (
        weights["photorealism"] * candidate.photorealism_score +
        weights["artistic"] * candidate.artistic_score +
        weights["speed"] * candidate.speed_score +
        weights["quality"] * candidate.quality_score +
        weights["consistency"] * candidate.consistency_score
    )
    
    # Style tag bonus: +0.1 for each matching style tag
    model_tags = candidate.model_info.get("style_tags", [])
    matching_tags = len(set(content_prefs.style_tags) & set(model_tags))
    user_fit += min(0.3, matching_tags * 0.1)
    
    candidate.user_fit_score = min(1.0, user_fit)
    
    # === Hardware Fit Score ===
    # Start at 1.0, apply penalties for constraint violations
    hw_fit = 1.0
    
    # VRAM penalty (hard fail if exceeds)
    if candidate.min_vram_gb > hardware.vram_gb:
        if hardware.requires_quantization:
            # Check if quantized version exists
            if not candidate.model_info.get("has_gguf", False):
                hw_fit = 0.0  # Cannot run at all
            else:
                hw_fit -= 0.2  # Penalty for needing quantization
        else:
            hw_fit = 0.0  # Cannot run
    
    # RAM penalty
    if candidate.min_ram_gb > hardware.ram_gb:
        hw_fit = 0.0  # Cannot run
    
    # Storage penalty (soft)
    if candidate.size_gb > hardware.disk_free_gb * 0.5:
        hw_fit -= 0.3  # Takes more than half available space
    elif candidate.size_gb > hardware.disk_free_gb * 0.8:
        hw_fit = 0.0  # Not enough space
    
    # Speed penalty for low-end hardware
    if hardware.compute_score < 0.5 and candidate.speed_score < 0.5:
        hw_fit -= 0.2  # Slow model on slow hardware
    
    candidate.hardware_fit_score = max(0.0, hw_fit)
    
    # === Composite Score ===
    # Weight hardware more heavily - no point recommending something that won't run
    # But user preferences still matter for choosing between viable options
    
    if candidate.hardware_fit_score == 0.0:
        candidate.composite_score = 0.0
    else:
        # 60% hardware fit, 40% user fit
        candidate.composite_score = (
            0.6 * candidate.hardware_fit_score +
            0.4 * candidate.user_fit_score
        )
    
    return candidate
```

### 13.5 Resolution Process

```
┌─────────────────────────────────────────────────────────────────┐
│              WEIGHTED RECOMMENDATION RESOLUTION                  │
└─────────────────────────────────────────────────────────────────┘

INPUT:
├── user_profile: UserProfile       # From onboarding survey
├── env: EnvironmentReport          # From hardware scan
└── advanced_mode: bool             # Expert override enabled?

PHASE 1: Normalize Inputs
├── Compute HardwareConstraints from env
├── Determine proficiency level from experience scores
├── Extract content preferences for each selected use case
└── Output: HardwareConstraints, proficiency, Dict[use_case, ContentPreferences]

PHASE 2: Generate Candidate Pool
├── For each selected use_case:
│   ├── Load all models with matching capabilities
│   ├── Load all workflows with matching capabilities
│   └── Load all custom nodes required by candidates
└── Output: List[ModelCandidate], List[WorkflowCandidate], List[str] nodes

PHASE 3: Score All Candidates
├── For each ModelCandidate:
│   ├── Compute user_fit_score against content preferences
│   ├── Compute hardware_fit_score against constraints
│   ├── Compute composite_score
│   └── Record reasoning for score components
├── For each WorkflowCandidate:
│   ├── Check required models exist in passing candidates
│   ├── Check required nodes are available
│   └── Compute workflow_fit_score
└── Output: Scored candidates with reasoning

PHASE 4: Apply Hard Constraints (Guardrails)
├── REJECT models where:
│   ├── hardware_fit_score == 0.0 (cannot run)
│   ├── min_vram > available AND no GGUF variant
│   └── size_gb > disk_free_gb
├── REJECT workflows where:
│   ├── Any required model was rejected
│   └── Any required node is incompatible with OS
├── WARN but allow if:
│   ├── Model requires quantization (suggest GGUF)
│   └── Storage is tight but sufficient
└── Output: Filtered candidates, warnings

PHASE 5: Rank and Select
├── Sort ModelCandidates by composite_score DESC
├── Select top model per capability needed:
│   ├── Best t2i model
│   ├── Best i2i model (if capability requested)
│   ├── Best i2v model (if capability requested)
│   └── etc.
├── Select workflows compatible with selected models
├── Collect all required custom nodes
└── Output: Selected models, workflows, nodes

PHASE 6: Expert Override (if advanced_mode)
├── Present full candidate list with scores
├── Allow manual selection/deselection
├── Re-validate against hard constraints
└── Output: User-modified selection

PHASE 7: Generate Manifest
├── For each selected model:
│   ├── Resolve download URL (prefer GGUF if requires_quantization)
│   ├── Compute expected hash
│   └── Determine destination directory
├── For each selected workflow:
│   └── Resolve file path
├── For each required node:
│   └── Resolve git repo URL
├── Calculate total size and time estimate
└── Output: InstallationManifest

PHASE 8: Generate Output
├── Compile reasoning from all scoring decisions
├── Compile warnings from constraint checks
├── Calculate overall confidence score
└── Output: RecommendationResult
```

### 13.6 Scoring Weights Configuration

Stored in `resources.json` to allow tuning without code changes:

```json
{
  "recommendation_config": {
    "scoring_weights": {
      "composite": {
        "hardware_fit": 0.6,
        "user_fit": 0.4
      },
      "user_fit_components": {
        "photorealism": 1.0,
        "artistic_style": 1.0,
        "speed": 1.0,
        "quality": 1.0,
        "consistency": 1.0,
        "style_tag_match_bonus": 0.1,
        "style_tag_max_bonus": 0.3
      },
      "hardware_penalties": {
        "quantization_required": -0.2,
        "storage_over_50pct": -0.3,
        "slow_model_slow_hw": -0.2
      }
    },
    
    "proficiency_thresholds": {
      "beginner": {"ai_max": 3, "tech_max": 3},
      "intermediate": {"ai_min": 4, "tech_min": 4},
      "advanced": {"ai_min": 7, "tech_min": 7},
      "expert": {"ai_min": 8, "tech_min": 8}
    },
    
    "hardware_normalization": {
      "vram_max_gb": 24,
      "ram_min_gb": 8,
      "ram_max_gb": 64,
      "storage_max_gb": 500,
      "apple_silicon_vram_factor": 0.75,
      "apple_silicon_compute_factor": 0.7,
      "amd_compute_factor": 0.5,
      "cpu_compute_factor": 0.1
    },
    
    "hard_limits": {
      "flux_min_vram": 12,
      "flux_apple_min_ram": 32,
      "sdxl_min_vram": 8,
      "sdxl_apple_min_ram": 16,
      "video_min_vram": 8,
      "video_apple_min_ram": 32,
      "storage_max_usage_pct": 0.8
    }
  }
}
```

### 13.7 Model Metadata Schema (Addition to resources.json)

Each model entry needs scoring attributes:

```json
{
  "comfyui_components": {
    "models": {
      "checkpoints": {
        "juggernaut_xl_v9": {
          "display_name": "Juggernaut XL v9",
          "url": "https://...",
          "size_gb": 6.5,
          "hash_sha256": "abc123...",
          
          "capabilities": ["t2i", "i2i"],
          "model_family": "sdxl",
          "has_gguf": false,
          
          "requirements": {
            "min_vram_gb": 8,
            "min_ram_gb": 16
          },
          
          "scoring": {
            "photorealism": 0.95,
            "artistic_style": 0.3,
            "speed": 0.6,
            "quality": 0.9,
            "consistency": 0.85
          },
          
          "style_tags": ["photorealistic", "portrait", "landscape", "product"],
          
          "recommended_for_profiles": {
            "high_photorealism": true,
            "high_quality": true
          }
        },
        
        "dreamshaper_xl": {
          "display_name": "DreamShaper XL",
          "url": "https://...",
          "size_gb": 6.5,
          "hash_sha256": "def456...",
          
          "capabilities": ["t2i", "i2i"],
          "model_family": "sdxl",
          "has_gguf": false,
          
          "requirements": {
            "min_vram_gb": 8,
            "min_ram_gb": 16
          },
          
          "scoring": {
            "photorealism": 0.5,
            "artistic_style": 0.9,
            "speed": 0.6,
            "quality": 0.85,
            "consistency": 0.7
          },
          
          "style_tags": ["artistic", "fantasy", "anime", "stylized"],
          
          "recommended_for_profiles": {
            "high_artistic": true,
            "creative_freedom": true
          }
        }
      },
      
      "unet_gguf": {
        "wan_i2v_q5": {
          "display_name": "Wan 2.2 I2V (Q5 Quantized)",
          "files": {
            "high_noise": {
              "url": "https://huggingface.co/...",
              "size_gb": 9.8,
              "hash_sha256": "..."
            },
            "low_noise": {
              "url": "https://huggingface.co/...",
              "size_gb": 9.8,
              "hash_sha256": "..."
            }
          },
          
          "capabilities": ["i2v"],
          "model_family": "gguf",
          "is_quantized": true,
          "quantization": "Q5_K_M",
          
          "requirements": {
            "min_vram_gb": 0,
            "min_ram_gb": 32
          },
          
          "scoring": {
            "photorealism": 0.7,
            "artistic_style": 0.6,
            "speed": 0.3,
            "quality": 0.75,
            "consistency": 0.8
          },
          
          "style_tags": ["video", "animation", "motion"],
          
          "required_nodes": ["ComfyUI-GGUF", "ComfyUI-VideoHelperSuite"],
          
          "notes": "Optimized for Apple Silicon and low-VRAM systems"
        }
      }
    }
  }
}
```

### 13.8 Onboarding Survey UI Flow

The survey collects data to populate `UserProfile`:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ONBOARDING SURVEY                             │
└─────────────────────────────────────────────────────────────────┘

SCREEN 1: Experience Assessment
─────────────────────────────────────────────────────────────────
"How would you rate your experience with AI tools?"

Never used ○──○──○──○──○──○──○──○──○──● Daily power user
          1  2  3  4  5  6  7  8  9  10

"How comfortable are you with technical tasks?"
(Installing software, using command line, editing config files)

Avoid if possible ○──○──○──○──○──○──○──○──○──● Very comfortable
                  1  2  3  4  5  6  7  8  9  10

─────────────────────────────────────────────────────────────────

SCREEN 2: Use Case Selection
─────────────────────────────────────────────────────────────────
"What do you want to create?" (Select all that apply)

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  🖼️ Images      │  │  🎬 Videos      │  │  ✍️ Writing     │
│                 │  │                 │  │                 │
│ Generate images │  │ Animate photos  │  │ AI assistant    │
│ from text or    │  │ Create video    │  │ for writing,    │
│ edit existing   │  │ content         │  │ coding, tasks   │
│                 │  │                 │  │                 │
│     [  ✓  ]     │  │     [  ✓  ]     │  │     [    ]      │
└─────────────────┘  └─────────────────┘  └─────────────────┘

─────────────────────────────────────────────────────────────────

SCREEN 3: Content Preferences (per selected use case)
─────────────────────────────────────────────────────────────────
"For IMAGE GENERATION, rate importance of each:" (1 = not important, 10 = critical)

Photorealistic results     ○──○──●──○──○──○──○──○──○──○  [3]
Artistic/stylized results  ○──○──○──○──○──○──○──●──○──○  [8]
Fast generation speed      ○──○──○──○──●──○──○──○──○──○  [5]
Maximum quality            ○──○──○──○──○──○──●──○──○──○  [7]
Consistent outputs         ○──○──○──○──○──●──○──○──○──○  [6]

"What styles interest you?" (Select all that apply)

[ ] Photorealistic    [✓] Fantasy/Sci-fi    [ ] Product shots
[✓] Anime/Manga       [ ] Portraits         [✓] Concept art
[ ] Landscapes        [✓] Characters        [ ] Architecture

─────────────────────────────────────────────────────────────────

SCREEN 4: Technical Preferences (shown if tech_experience >= 5)
─────────────────────────────────────────────────────────────────
"Advanced options:"

Preferred model family:  [Auto-select ▼]
                        ├─ Auto-select (recommended)
                        ├─ Flux (highest quality)
                        ├─ SDXL (balanced)
                        └─ SD 1.5 (fastest)

Accept quantized models for better performance?
[✓] Yes, prioritize compatibility

Typical output resolution: [1024x1024 ▼]

─────────────────────────────────────────────────────────────────

SCREEN 5: Review Profile
─────────────────────────────────────────────────────────────────
"Here's your profile:"

Experience Level: Intermediate
  • AI Experience: 6/10
  • Technical: 4/10

Selected Use Cases:
  • Image Generation (artistic focus)
  • Video Generation

Content Style:
  • Artistic > Quality > Consistency > Speed > Photorealism
  • Tags: Fantasy, Anime, Concept Art, Characters

                    [ Edit ]  [ Continue → ]
```

### 13.9 RecommendationService Implementation

```python
class RecommendationService:
    """
    Weighted scoring-based recommendation engine.
    """
    
    def __init__(self, resources_path: str):
        with open(resources_path) as f:
            self.resources = json.load(f)
        
        self.config = self.resources.get("recommendation_config", {})
        self.weights = self.config.get("scoring_weights", {})
        self.thresholds = self.config.get("proficiency_thresholds", {})
        self.limits = self.config.get("hard_limits", {})
    
    def generate_recommendations(
        self,
        user_profile: UserProfile,
        environment: EnvironmentReport
    ) -> RecommendationResult:
        """
        Main entry point for recommendation generation.
        """
        reasoning = []
        warnings = []
        
        # Phase 1: Normalize inputs
        hardware = HardwareConstraints.from_environment(environment)
        proficiency = self._determine_proficiency(user_profile)
        
        reasoning.append(f"Detected proficiency level: {proficiency}")
        reasoning.append(f"Hardware profile: {hardware.gpu_vendor}, "
                        f"VRAM score: {hardware.vram_score:.2f}, "
                        f"Compute score: {hardware.compute_score:.2f}")
        
        # Phase 2-3: Score candidates for each use case
        all_selections = {}
        
        for use_case in user_profile.primary_use_cases:
            content_prefs = user_profile.content_preferences.get(use_case)
            if not content_prefs:
                continue
            
            selection = self._resolve_use_case(
                use_case=use_case,
                content_prefs=content_prefs,
                hardware=hardware,
                proficiency=proficiency,
                reasoning=reasoning,
                warnings=warnings
            )
            
            all_selections[use_case] = selection
        
        # Phase 7: Generate manifest
        manifest = self._compile_manifest(all_selections, hardware, reasoning)
        
        # Phase 8: Generate output
        confidence = self._calculate_confidence(all_selections)
        
        return RecommendationResult(
            recommendation_id=str(uuid.uuid4()),
            confidence_score=confidence,
            user_profile=user_profile,
            hardware_constraints=hardware,
            selections=all_selections,
            manifest=manifest,
            reasoning=reasoning,
            warnings=warnings
        )
    
    def _determine_proficiency(self, profile: UserProfile) -> str:
        """Derive proficiency level from experience scores."""
        ai = profile.ai_experience
        tech = profile.technical_experience
        
        if ai >= 8 and tech >= 8:
            return "Expert"
        elif ai >= 7 or tech >= 7:
            return "Advanced"
        elif ai >= 4 or tech >= 4:
            return "Intermediate"
        else:
            return "Beginner"
    
    def _resolve_use_case(
        self,
        use_case: str,
        content_prefs: ContentPreferences,
        hardware: HardwareConstraints,
        proficiency: str,
        reasoning: List[str],
        warnings: List[str]
    ) -> UseCaseSelection:
        """Resolve optimal configuration for a single use case."""
        
        # Get required capabilities for this use case
        use_case_config = self.resources["use_cases"].get(use_case, {})
        required_capabilities = use_case_config.get("capabilities", [])
        
        reasoning.append(f"Resolving {use_case}: needs {required_capabilities}")
        
        # Load and score all model candidates
        candidates = self._load_model_candidates(required_capabilities)
        scored = []
        
        for candidate in candidates:
            scored_candidate = self._score_candidate(
                candidate, content_prefs, hardware
            )
            
            if scored_candidate.composite_score > 0:
                scored.append(scored_candidate)
                reasoning.append(
                    f"  {candidate.model_id}: "
                    f"user_fit={scored_candidate.user_fit_score:.2f}, "
                    f"hw_fit={scored_candidate.hardware_fit_score:.2f}, "
                    f"composite={scored_candidate.composite_score:.2f}"
                )
            else:
                reasoning.append(
                    f"  {candidate.model_id}: REJECTED (hardware incompatible)"
                )
        
        if not scored:
            warnings.append(f"No compatible models found for {use_case}")
            return UseCaseSelection(use_case=use_case, models=[], workflows=[], nodes=[])
        
        # Sort by composite score
        scored.sort(key=lambda c: c.composite_score, reverse=True)
        
        # Select best model per capability
        selected_models = self._select_best_per_capability(
            scored, required_capabilities, reasoning
        )
        
        # Find compatible workflows
        selected_workflows = self._select_workflows(
            use_case, selected_models, hardware, reasoning
        )
        
        # Collect required nodes
        required_nodes = self._collect_required_nodes(
            selected_models, selected_workflows
        )
        
        return UseCaseSelection(
            use_case=use_case,
            models=selected_models,
            workflows=selected_workflows,
            nodes=required_nodes,
            top_candidate_score=scored[0].composite_score if scored else 0
        )
    
    def _score_candidate(
        self,
        candidate: ModelCandidate,
        content_prefs: ContentPreferences,
        hardware: HardwareConstraints
    ) -> ModelCandidate:
        """Apply the scoring algorithm to a candidate."""
        
        # User fit score
        pref_values = [
            content_prefs.photorealism,
            content_prefs.artistic_style,
            content_prefs.speed,
            content_prefs.quality,
            content_prefs.consistency
        ]
        pref_sum = sum(pref_values)
        
        if pref_sum > 0:
            weights = [p / pref_sum for p in pref_values]
        else:
            weights = [0.2] * 5
        
        model_scores = [
            candidate.photorealism_score,
            candidate.artistic_score,
            candidate.speed_score,
            candidate.quality_score,
            candidate.consistency_score
        ]
        
        user_fit = sum(w * s for w, s in zip(weights, model_scores))
        
        # Style tag bonus
        model_tags = set(candidate.model_info.get("style_tags", []))
        user_tags = set(content_prefs.style_tags)
        tag_matches = len(model_tags & user_tags)
        tag_bonus = min(
            self.weights["user_fit_components"]["style_tag_max_bonus"],
            tag_matches * self.weights["user_fit_components"]["style_tag_match_bonus"]
        )
        
        candidate.user_fit_score = min(1.0, user_fit + tag_bonus)
        
        # Hardware fit score
        hw_fit = 1.0
        
        # Check hard limits
        if candidate.min_vram_gb > hardware.vram_gb:
            if hardware.requires_quantization and candidate.model_info.get("has_gguf"):
                hw_fit += self.weights["hardware_penalties"]["quantization_required"]
            else:
                hw_fit = 0.0
        
        if candidate.min_ram_gb > hardware.ram_gb:
            hw_fit = 0.0
        
        # Storage check
        max_storage_pct = self.limits.get("storage_max_usage_pct", 0.8)
        if candidate.size_gb > hardware.disk_free_gb * max_storage_pct:
            hw_fit = 0.0
        elif candidate.size_gb > hardware.disk_free_gb * 0.5:
            hw_fit += self.weights["hardware_penalties"]["storage_over_50pct"]
        
        # Speed penalty
        if hardware.compute_score < 0.5 and candidate.speed_score < 0.5:
            hw_fit += self.weights["hardware_penalties"]["slow_model_slow_hw"]
        
        candidate.hardware_fit_score = max(0.0, hw_fit)
        
        # Composite score
        if candidate.hardware_fit_score == 0.0:
            candidate.composite_score = 0.0
        else:
            hw_weight = self.weights["composite"]["hardware_fit"]
            user_weight = self.weights["composite"]["user_fit"]
            candidate.composite_score = (
                hw_weight * candidate.hardware_fit_score +
                user_weight * candidate.user_fit_score
            )
        
        return candidate
    
    def _select_best_per_capability(
        self,
        candidates: List[ModelCandidate],
        required_capabilities: List[str],
        reasoning: List[str]
    ) -> List[str]:
        """Select the best model for each required capability."""
        selected = []
        
        for capability in required_capabilities:
            best = None
            best_score = 0
            
            for candidate in candidates:
                if capability in candidate.capabilities:
                    if candidate.composite_score > best_score:
                        best = candidate
                        best_score = candidate.composite_score
            
            if best and best.model_id not in selected:
                selected.append(best.model_id)
                reasoning.append(
                    f"Selected {best.model_id} for {capability} "
                    f"(score: {best.composite_score:.2f})"
                )
        
        return selected
    
    def _calculate_confidence(self, selections: Dict[str, UseCaseSelection]) -> float:
        """Calculate overall confidence in the recommendation."""
        if not selections:
            return 0.0
        
        scores = [s.top_candidate_score for s in selections.values() if s.top_candidate_score > 0]
        
        if not scores:
            return 0.0
        
        return sum(scores) / len(scores)
```

### 13.10 Output Schema

```python
@dataclass
class RecommendationResult:
    """Complete output of the recommendation engine."""
    
    recommendation_id: str
    confidence_score: float             # 0-1, overall confidence
    
    # Inputs (for reference/debugging)
    user_profile: UserProfile
    hardware_constraints: HardwareConstraints
    
    # Selections per use case
    selections: Dict[str, UseCaseSelection]
    
    # Installation manifest
    manifest: InstallationManifest
    
    # Explanations
    reasoning: List[str]                # Why each decision was made
    warnings: List[str]                 # Potential issues


@dataclass
class UseCaseSelection:
    """Selection for a single use case."""
    
    use_case: str
    models: List[str]                   # Model IDs to install
    workflows: List[str]                # Workflow IDs to install
    nodes: List[str]                    # Custom node IDs required
    top_candidate_score: float          # Score of best candidate


@dataclass  
class InstallationManifest:
    """Complete installation specification."""
    
    # Models to download
    models: List[ModelDownload]
    
    # Custom nodes to clone
    nodes: List[NodeInstall]
    
    # Workflows to copy
    workflows: List[WorkflowInstall]
    
    # Totals
    total_size_gb: float
    estimated_time_minutes: int


@dataclass
class ModelDownload:
    """Single model download specification."""
    
    model_id: str
    url: str
    dest_path: str                      # Relative to ComfyUI/models/
    size_gb: float
    hash_sha256: str
    is_quantized: bool
```
```

---

## 14. Updated File Structure

### 14.1 Complete New File List

```
src/
├── services/
│   ├── setup_wizard_service.py        # NEW: Wizard orchestration
│   ├── shortcut_service.py            # NEW: Desktop shortcut creation
│   ├── download_service.py            # NEW: Download with retry/progress
│   ├── model_manager_service.py       # NEW: Local model management
│   ├── model_repository_service.py    # NEW: External repo integration
│   ├── workflow_service.py            # NEW: Workflow management
│   ├── recommendation_service.py      # EXISTS: Enhance with resolver
│   ├── comfy_service.py               # EXISTS: Enhance
│   ├── dev_service.py                 # EXISTS: Enhance
│   └── system_service.py              # EXISTS: Fix + enhance
│
├── ui/
│   ├── wizard/
│   │   ├── __init__.py
│   │   ├── setup_wizard.py            # NEW: Main wizard window
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── use_case_card.py       # NEW
│   │       ├── module_config.py       # NEW
│   │       ├── api_key_input.py       # NEW
│   │       ├── progress_panel.py      # NEW
│   │       ├── reasoning_display.py   # NEW
│   │       └── warning_banner.py      # NEW
│   │
│   └── views/
│       ├── model_manager.py           # NEW: Model management view
│       ├── workflow_browser.py        # NEW: Workflow browser view
│       ├── overview.py                # EXISTS: Update
│       ├── comfyui.py                 # EXISTS: Fix + update
│       ├── devtools.py                # EXISTS: Update
│       └── settings.py                # EXISTS: Update
│
├── config/
│   └── resources.json                 # EXISTS: Major update
│
└── workflows/                          # NEW: Bundled workflow templates
    ├── wan_i2v_basic.json
    ├── sdxl_basic_t2i.json
    ├── flux_schnell_t2i.json
    └── previews/
        ├── wan_i2v_basic.png
        ├── sdxl_basic_t2i.png
        └── flux_schnell_t2i.png
```

### 14.2 Updated Implementation Phases

| Phase | Focus | Files | Priority |
|-------|-------|-------|----------|
| 1 | Critical Fixes | system_service.py, comfyui.py | BLOCKER |
| 2 | GGUF + Video | resources.json, comfy_service.py, workflows/ | HIGH |
| 3 | Core Services | shortcut_service.py, download_service.py, setup_wizard_service.py | HIGH |
| 4 | Wizard UI | wizard/*.py | HIGH |
| 5 | Model Manager | model_manager_service.py, model_repository_service.py, model_manager.py | MEDIUM |
| 6 | Workflow Browser | workflow_service.py, workflow_browser.py | MEDIUM |
| 7 | Polish | All views, error handling, testing | MEDIUM |
| 8 | Future Modules | LM Studio, MCP | LOW |

---

*End of Specification*
