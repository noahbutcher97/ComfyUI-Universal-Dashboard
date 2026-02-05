# AI Universal Suite

A cross-platform desktop application that transforms your computer into a fully configured AI workstation through a guided setup wizard.

## Overview

AI Universal Suite solves the "AI tool sprawl" problem - helping professionals move from scattered subscriptions and copy-paste workflows to an integrated, hardware-optimized AI infrastructure. The application detects your hardware, asks about your needs, and recommends the optimal configuration of models, tools, and workflows.

### Key Features

- **Zero Terminal Interaction** - Every action achievable through GUI
- **Hardware-Aware Recommendations** - Automatic detection and optimization for your specific GPU, RAM, and storage
- **100+ AI Models** - Image, video, audio, and 3D generation with intelligent selection
- **Dual Onboarding Paths** - Quick Setup (~2 min) or Comprehensive Setup (~5-8 min)
- **Cloud/Local Hybrid** - Seamless fallback to cloud APIs when local hardware is insufficient
- **Cross-Platform** - Windows/NVIDIA, macOS/Apple Silicon, Linux/AMD ROCm

### Target Users

- Creative professionals (filmmakers, designers, photographers)
- Knowledge workers adopting AI tools
- Technical users transitioning to local AI infrastructure
- Solopreneurs building AI-enhanced workflows

## Project Structure

```
AI-Universal-Suite/
├── data/                    # Runtime data
│   └── models_database.yaml # Model definitions with variants and capabilities
├── docs/
│   ├── context/             # Business context
│   ├── plans/               # Implementation tracking + Claude Code plans
│   │   └── PLAN_v3.md
│   ├── spec/                # Technical specification
│   │   └── AI_UNIVERSAL_SUITE_SPEC_v3.md
│   └── archived/            # Historical documents
├── src/                     # Application source code
└── (launcher scripts)
```

## Documentation

| Document | Description |
|----------|-------------|
| [SPEC_v3](docs/spec/AI_UNIVERSAL_SUITE_SPEC_v3.md) | Complete technical specification - architecture, algorithms, schemas |
| [HARDWARE_DETECTION](docs/spec/HARDWARE_DETECTION.md) | GPU, CPU, Storage, RAM detection and classification |
| [CUDA_PYTORCH_INSTALLATION](docs/spec/CUDA_PYTORCH_INSTALLATION.md) | Dynamic PyTorch/CUDA installation logic |
| [PLAN_v3](docs/plans/PLAN_v3.md) | Implementation roadmap, decision log, task tracking |
| [MIGRATION_PROTOCOL](docs/spec/MIGRATION_PROTOCOL.md) | How to migrate legacy code to SPEC_v3 architecture |
| [models_database.yaml](data/models_database.yaml) | Model database with 100+ entries, variants, and hardware requirements |
| [CLAUDE.md](CLAUDE.md) | Claude Code context (auto-loaded) |
| [GEMINI.md](GEMINI.md) | Gemini CLI context (auto-loaded) |
| [AGENTS.md](AGENTS.md) | General AI agent context (Cursor, Aider, etc.) |

## Current Status

**Phase**: Planning Complete → Implementation Phase 1

The specification consolidates all research into a single source of truth covering:
- Three-layer recommendation engine (CSP → Content-Based → TOPSIS)
- Dual-path onboarding system
- Platform-specific hardware detection
- Cloud API integration via ComfyUI Partner Nodes
- Complete model database schema

See [PLAN_v3.md](docs/plans/PLAN_v3.md) for current progress and next steps.

## Quick Start

*Coming soon - currently in development*

```bash
# Windows
Run_Windows.bat

# macOS
./Run_Mac.command

# Linux
./Run_Unix.sh
```

## Requirements

- Python 3.10+
- Git
- 8GB+ RAM (32GB recommended)
- GPU with 4GB+ VRAM (for local generation)

## Platform Support

| Platform | GPU | Status |
|----------|-----|--------|
| Windows 10/11 | NVIDIA (RTX 20/30/40/50 series) | Primary target (40%) |
| macOS 12+ | Apple Silicon (M1/M2/M3/M4) | Primary target (40%) |
| Linux | AMD ROCm (RX 6000/7000) | Supported (20%) |

## License

*TBD*

## Contributing

*TBD - currently in early development*

---

*Part of the AI Infrastructure Consulting service - helping professionals transition from scattered AI subscriptions to integrated, cost-effective infrastructure solutions.*
