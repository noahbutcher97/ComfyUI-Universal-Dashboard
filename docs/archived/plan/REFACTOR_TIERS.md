# Refactoring & Fix Plan - Tiered Priority

This document categorizes recommended fixes and refactoring tasks by Impact, Complexity, and Severity.

**Legend:**
*   **Impact**: How much this improves the user experience or system stability.
*   **Complexity**: Estimate of effort and risk (Low = <1 hour, Med = 2-4 hours, High = >4 hours).
*   **Severity**: Criticality of the issue (Critical = broken/dangerous, High = significant UX/logic flaw, Medium = polish/optimization).

## 🚨 Tier 1: CRITICAL & High Impact (Immediate Action)

These issues affect core functionality, safety, or fundamental architecture.

| ID | Issue | Impact | Complexity | Severity | Status |
|----|-------|--------|------------|----------|--------|
| **T1-1** | **Legacy Wizard Removal** | **High** | **Low** | **Critical** | ✅ Fixed |
| **T1-2** | **Unsafe Subprocess Calls** | **High** | **Low** | **Critical** | ✅ Fixed |
| **T1-3** | **Settings Main Thread Blocking** | **High** | **Low** | **High** | ⬜ Pending |
| **T1-4** | **DevTools Error Handling** | **High** | **Low** | **High** | ⬜ Pending |

### T1-3: Settings Main Thread Blocking
*   **Description**: The "Save All Keys" action in `src/ui/views/settings.py` calls `config_manager.set_secure` (keychain access) on the main thread. This blocks the UI.
*   **Fix**: Wrap the save loop in a `threading.Thread`.

### T1-4: DevTools Error Handling
*   **Description**: `subprocess.call` in `src/ui/views/devtools.py` returns an exit code, but the code ignores it and reports "Success" unless a Python exception is raised.
*   **Fix**: Check `if return_code != 0` and show `messagebox.showerror`.

---

## ⚠️ Tier 2: Medium Impact & Usability (Next Priority)

These issues significantly affect the user experience or code maintainability but don't break the system.

| ID | Issue | Impact | Complexity | Severity | Status |
|----|-------|--------|------------|----------|--------|
| **T2-1** | **DevTools Scrollability** | **Medium** | **Low** | **High** | ⬜ Pending |
| **T2-2** | **Key Clearing in Settings** | **Medium** | **Low** | **Medium** | ⬜ Pending |
| **T2-3** | **DevTools State Loss** | **Medium** | **Medium** | **Medium** | ⬜ Pending |
| **T2-4** | **Interaction Consistency** | **Low** | **Medium** | **Medium** | ⬜ Pending |

### T2-1: DevTools Scrollability
*   **Description**: The "AI Tools" list in `src/ui/views/devtools.py` uses a standard frame. Growing lists will clip.
*   **Fix**: Replace with `ctk.CTkScrollableFrame`.

### T2-2: Key Clearing in Settings
*   **Description**: `settings.py` prevents saving empty strings for keys, making it impossible to delete a key.
*   **Fix**: Allow empty strings to trigger `delete_secure` (or handle empty save).

### T2-3: DevTools State Loss
*   **Description**: `refresh_cli_list` rebuilds the entire widget tree, wiping out user checkbox selections during a refresh.
*   **Fix**: Implement a "diff" update or only update the label text/color instead of destroying widgets.

### T2-4: Interaction Consistency
*   **Description**: System tools use "Install" buttons; AI tools use Checkboxes + Bulk Install.
*   **Fix**: Unify to Checkboxes + Bulk Install for both, or row-based buttons for both.

---

## 🔧 Tier 3: Low Impact & Polish (Future Work)

Good-to-have improvements for a polished product.

| ID | Issue | Impact | Complexity | Severity | Status |
|----|-------|--------|------------|----------|--------|
| **T3-1** | **Privilege Escalation** | **Low** | **High** | **Low** | ⬜ Pending |
| **T3-2** | **Clipboard Regex Hardening** | **Low** | **Medium** | **Low** | ⬜ Pending |
| **T3-3** | **Output Streaming** | **Low** | **High** | **Low** | ⬜ Pending |

### T3-1: Privilege Escalation
*   **Description**: Global installs (`npm -g`) fail without Admin rights.
*   **Fix**: Detect failure and prompt user to restart app as Admin (Windows) or use `sudo` wrapper (Linux/Mac).

### T3-2: Clipboard Regex Hardening
*   **Description**: Ensure "Magic Paste" doesn't accidentally capture passwords.
*   **Fix**: Tighten regex patterns for all providers in `src/services/auth_service.py`.

### T3-3: Output Streaming
*   **Description**: Users only see a progress bar during install.
*   **Fix**: Capture `stdout/stderr` from subprocess and stream to a log window.
