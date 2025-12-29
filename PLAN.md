# 🗺️ Project Roadmap: Advanced AI Workstation Manager

**Current Status**: Phase 3 Complete (Visual Polish).
**Next Phase**: Phase 4 (Intelligent Recommendation Engine & Workflow Management).

---

## 🎯 Strategic Vision

Transform the application from a simple installer into a comprehensive **AI Workstation Manager** capable of intelligently matching user intent with technical reality. The system must act as a bridge, ensuring users are never overwhelmed by unassisted systems navigation or scripting.

---

## 1. Guardrail Specification & Constraints
The system must enforce strict operational boundaries to prevent system instability.

*   **Hardware Constraints**:
    *   **VRAM Hard Limits**: Prevent installation of models exceeding physical VRAM (e.g., Block Flux on < 8GB VRAM unless GGUF is selected).
    *   **RAM Buffers**: Ensure system RAM allows for model loading overhead (+2GB buffer).
    *   **Storage Check**: Pre-flight check for disk space before starting multi-GB downloads.
*   **Forbidden Actions**:
    *   No overriding of system-critical Python environments (Must use `venv`).
    *   No execution of unverified custom nodes without explicit user "High Risk" confirmation.

## 2. Advanced Mode Triggers & Workflow
**Advanced Mode** is a distinct operational state enabled by:
*   **User Selection**: Selecting "Expert" proficiency in Stage 2.
*   **Manual Toggle**: A persistent "Enable Advanced Configuration" toggle in the review screen.

**Capabilities Unlocked**:
*   Manual selection/deselection of individual model files.
*   Access to raw `.json` workflow template editing.
*   Ability to install arbitrary custom nodes via URL.
*   GGUF Custom Node manual configuration.

## 3. Input Validation & Data Integrity
*   **User Profile Input**:
    *   Must validate "Proficiency" against allowed enum: `['Beginner', 'Intermediate', 'Advanced', 'Expert']`.
    *   Styles must map to defined tags in `resources.json`.
*   **Resource Validation**:
    *   **Checksums**: All downloads *must* pass SHA256 verification (Strict Mode for production assets).
    *   **JSON Schema**: `resources.json` must be validated against a strict schema on load.

## 4. Output Schema Definition (Recommendation Engine)
The `RecommendationService` must return a structured object:

```json
{
  "recommendation_id": "uuid",
  "score": 0.95,
  "setup_profile": {
    "base_model": "sdxl_juggernaut",
    "quantization": "none",
    "custom_nodes": ["controlnet_aux", "ipadapter_plus"],
    "workflow_template": "photorealism_v2.json"
  },
  "reasoning": [
    "Selected SDXL over Flux due to 8GB VRAM constraint.",
    "Added ControlNet because 'Editing' was prioritized."
  ],
  "warnings": []
}
```

## 5. Tool Usage & Technical Constraints
*   **Subprocess Management**: All external commands (git, pip) must be executed via a centralized, thread-safe runner with timeout safeguards.
*   **MCP/Agent Constraints**:
    *   File operations restricted to `ComfyUI` and `.dashboard_env` directories.
    *   No modification of system-wide PATH or Registry outside of the initial setup script.

## 6. Error Handling Protocols
*   **Download Failures**:
    *   **Retry Logic**: Exponential backoff (3 attempts).
    *   **Fallback**: If primary source fails, attempt configured mirror.
    *   **User Action**: "Resume" button in Activity Center (no full restart).
*   **Installation Failures**: Rollback changes to the specific component (delete partial directory) and notify user with a clear "Try Again" option.

## 7. Performance Targets
*   **Recommendation Latency**: Engine must generate specific recommendations in < 200ms.
*   **UI Responsiveness**: The main thread must *never* block. All file I/O and hashing must occur in background threads.
*   **Resource Usage**: The Dashboard itself must consume < 150MB RAM to leave room for AI models.

## 8. Security Directives
*   **Data Handling**: User profile data (skill level, hardware specs) is processed locally in-memory only. No telemetry upload.
*   **Access Control**: API Keys continue to use the OS Keyring.
*   **Content Safety**: Community workflows must be scanned for malicious nodes (e.g., `ComfyUI-Manager` "BAD_ID" list check) before suggestion.
