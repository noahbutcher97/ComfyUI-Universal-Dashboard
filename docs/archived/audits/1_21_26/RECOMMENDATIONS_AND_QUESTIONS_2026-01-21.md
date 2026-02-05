# Audit Recommendations & Key Decisions
**Date:** January 21, 2026
**Reference:** Based on `docs/audits/MASTER_AUDIT_2026-01-21.md`

---

## 1. Prioritized Action Plan

### 🔴 Phase 1: Critical Security & Stability (Immediate)
*   **[Security] Pin Dependencies:** Immediately run `pip freeze > requirements.txt` (or equivalent) to pin all package versions to stable releases. Remove the open-ended versions.
*   **[Security] Sanitize Inputs:** Refactor `src/services/dev_service.py` and `src/ui/views/devtools.py` to remove `shell=True`. Use the `subprocess_utils.py` safe wrappers or list-based arguments for `subprocess.run`.
*   **[UI] Fix Blocking Init:** Move `OverviewFrame` system checks to a background thread. Show a "Loading System Info..." spinner on the dashboard until the thread returns.

### 🟠 Phase 2: Architectural Alignment (Short Term)
*   **[Arch] Eliminate Hybrid Data:**
    1.  Fully port any remaining logic from `resources.json` to `models_database.yaml`.
    2.  Update `RecommendationService` to read *only* from the YAML database.
    3.  Archive/Delete `resources.json` to prevent regression.
*   **[Arch] Enforce Platform Constraints:** Connect the `HardwareDetector` outputs to the recommendation filters. Specifically, ensure the "Apple Silicon -> Block K-quants" rule is active in the code, not just the spec.

### 🟡 Phase 3: Technical Debt Paydown (Medium Term)
*   **[Arch] Retire ScoringService:** Complete the implementation of `ConstraintSatisfactionLayer` and `ContentBasedLayer`. Once functional, swap them into `RecommendationService` and delete `scoring_service.py`.
*   **[UI] Error Feedback System:** Create a centralized `NotificationService` or `MessageBus` in `app.py`. All background threads should post errors to this bus, which then displays a UI Toast/Snackbar to the user.

---

## 2. Key Decisions Required
*The following items require architectural decisions from the Lead Developer before implementation:*

### Q1: The "3-Layer" Migration Strategy
*   **Context:** The spec calls for a complex 3-layer engine (CSP -> Content -> TOPSIS). The current app uses a simple weighted sum.
*   **Question:** Should we stop feature development to build the full 3-layer engine now (blocking release), or refactor the current weighted sum into a cleaner "Layer 1.5" intermediate state?
*   **Recommendation:** **Layer 1.5**. Implement the `ConstraintLayer` (hard filters) immediately to fix platform bugs (Apple Silicon issues), but keep the weighted scoring for ranking until post-MVP.

### Q2: User-Defined CLI Installations
*   **Context:** The security audit flagged `npm`/`winget` calls as potential injection vectors if user input is allowed.
*   **Question:** Do we intend to allow users to type arbitrary package names to install, or will it always be a strict allowlist from our database?
*   **Recommendation:** **Strict Allowlist**. Do not allow free-form text input for package managers. If custom packages are needed, they must go through a rigid validation regex.

### Q3: UI Toolkit Standardization
*   **Context:** `tkinter.ttk` widgets look out of place next to `customtkinter`.
*   **Question:** Should we build custom wrappers for complex widgets (Tables/Trees) in `customtkinter` or accept the visual discrepancy for MVP?
*   **Recommendation:** **Accept for MVP**. Styling `ttk.Treeview` is time-consuming. Focus on functionality first, unless the visual clash triggers user rejection.

---

## 3. Success Metrics for Next Audit
*   **Architecture:** `scoring_service.py` is deleted.
*   **Data:** `resources.json` is deleted.
*   **Security:** `shell=True` usage count is 0.
*   **Performance:** App startup time < 2 seconds (visual load).
