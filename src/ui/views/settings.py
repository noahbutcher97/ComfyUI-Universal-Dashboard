import customtkinter as ctk
import webbrowser
import re
from tkinter import messagebox
from src.config.manager import config_manager
from src.services.auth_service import AuthService
from src.ui.components.tooltip import ToolTip

class SettingsFrame(ctk.CTkFrame):
    
    KEY_CATEGORIES = {
        "Thinking & Chat": [
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", 
            "GROK_API_KEY", "DEEPSEEK_API_KEY"
        ],
        "Files & Downloads": [
            "HF_TOKEN", "CIVITAI_API_KEY"
        ],
        "App Features": [
            "COMFYUI_MANAGER_TOKEN"
        ]
    }

    KEY_DESCRIPTIONS = {
        "OPENAI_API_KEY": "Required for GPT-4 and DALL-E 3 generation.",
        "ANTHROPIC_API_KEY": "Required for Claude 3.5 Sonnet/Opus models.",
        "GEMINI_API_KEY": "Required for Google's Gemini Pro/Flash models.",
        "GROK_API_KEY": "Required for xAI's Grok models.",
        "DEEPSEEK_API_KEY": "Required for DeepSeek Coder models.",
        "HF_TOKEN": "Required to download models from Hugging Face (Gated/Private).",
        "CIVITAI_API_KEY": "Required for downloading NSFW or restricted models from CivitAI.",
        "COMFYUI_MANAGER_TOKEN": "Used for premium ComfyUI Manager features."
    }

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.auth_service = AuthService()
        
        ctk.CTkLabel(self, text="Settings & Keys", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        self.key_entries = {}
        self.key_visibility = {}
        self.key_buttons = {} 
        self.clipboard_monitor_job = None
        
        # --- API Keys Tabs ---
        self.tab_view = ctk.CTkTabview(self, height=400)
        self.tab_view.pack(fill="x", pady=10)

        for category, keys in self.KEY_CATEGORIES.items():
            self.tab_view.add(category)
            self._build_key_rows(self.tab_view.tab(category), keys)

        # Action Buttons
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(actions_frame, text="Save All Keys", command=self.save_keys, width=200).pack(side="left", padx=10)
        
        help_btn = ctk.CTkButton(actions_frame, text="❓ What is an API Key?", 
                               fg_color="transparent", border_width=1, text_color="gray80",
                               command=self.show_api_help)
        help_btn.pack(side="right", padx=10)
        
        # System Section
        sys_frame = ctk.CTkFrame(self)
        sys_frame.pack(fill="x", pady=20)
        ctk.CTkLabel(sys_frame, text="System & Maintenance", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkButton(sys_frame, text="Re-run Setup Wizard", fg_color="#555555", command=self.rerun_wizard).pack(anchor="w", padx=20, pady=20)

    def _build_key_rows(self, parent, keys):
        """Build key entry rows for a specific tab."""
        for provider in keys:
            if provider not in config_manager.SECURE_KEYS:
                continue

            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            
            # Info
            info = self.auth_service.get_provider_info(provider)
            label = ctk.CTkLabel(row, text=info["label"], width=150, anchor="w")
            label.pack(side="left", padx=10)
            
            # Tooltip
            desc = self.KEY_DESCRIPTIONS.get(provider, "API Key for this provider.")
            ToolTip(label, desc)
            
            # Entry
            ent = ctk.CTkEntry(row, show="*")
            ent.pack(side="left", fill="x", expand=True, padx=10)
            
            # Show/Hide
            toggle_btn = ctk.CTkButton(
                row, text="👁", width=30, fg_color="transparent", 
                text_color="gray", hover_color="gray30",
                command=lambda p=provider: self.toggle_key_visibility(p)
            )
            toggle_btn.pack(side="left", padx=(0, 5))
            
            # Auth Button
            btn_text = "Sign In" if (info["oauth"] and config_manager.get("auth.hf_client_id")) else "Get Key"
            auth_btn = ctk.CTkButton(
                row, text=btn_text, width=80,
                fg_color="#2d4a6d" if btn_text == "Sign In" else "gray",
                command=lambda p=provider: self.initiate_provider_auth(p)
            )
            auth_btn.pack(side="right", padx=5)
            
            # State tracking
            self.key_buttons[provider] = auth_btn
            
            # Load existing
            val = config_manager.get_secure(provider)
            if val:
                ent.insert(0, val)
                
            self.key_entries[provider] = ent
            self.key_visibility[provider] = {"btn": toggle_btn, "visible": False}

    def show_api_help(self):
        """Open generic help page."""
        webbrowser.open("https://platform.openai.com/docs/quickstart") # Good generic intro, or use internal help text
        messagebox.showinfo("API Keys 101", 
                          "API Keys are secret passwords that allow this app to talk to AI services.\n\n"
                          "1. Click 'Get Key' to open the provider's website.\n"
                          "2. Create a new key (it starts with sk- or similar).\n"
                          "3. Copy it.\n"
                          "4. The app will auto-paste it for you!\n\n"
                          "Keys are stored securely on your computer.")

    # ... keep existing methods (toggle_key_visibility, initiate_provider_auth, etc) ...

    def toggle_key_visibility(self, provider):
        """Toggle visibility of the API key entry."""
        state = self.key_visibility[provider]
        entry = self.key_entries[provider]
        
        if state["visible"]:
            entry.configure(show="*")
            state["btn"].configure(text="👁")
            state["visible"] = False
        else:
            entry.configure(show="")
            state["btn"].configure(text="🔒")
            state["visible"] = True

    def initiate_provider_auth(self, key_name):
        """Handle auth flow for any provider."""
        # Stop any existing listeners first
        self.cleanup()
        
        info = self.auth_service.get_provider_info(key_name)
        
        # UX: Copy token name to clipboard for easier pasting on the web form
        token_name = "AI-Universal-Suite"
        self.clipboard_clear()
        self.clipboard_append(token_name)
        
        status = self.auth_service.initiate_auth(
            key_name,
            on_success=lambda token: self._on_auth_success(key_name, token),
            on_error=self._on_auth_error
        )
        
        # Start "Magic Paste" Listener if regex is defined and NOT using OAuth
        if "pattern" in info and not (info["oauth"] and config_manager.get("auth.hf_client_id")):
            self.monitor_clipboard(key_name, info["pattern"])
            
        if status:
            # If magic paste active, show tailored message
            if "pattern" in info:
                messagebox.showinfo("Authentication", f"{status}\n\n✨ MAGIC PASTE ACTIVE: Just copy the key on the website, and we'll catch it!")
            else:
                messagebox.showinfo("Authentication", status)

    def monitor_clipboard(self, key_name, pattern, attempt=0):
        """Watch clipboard for API key pattern (60s timeout)."""
        # Stop if max attempts (60s)
        if attempt > 60:
            self.key_buttons[key_name].configure(text="Get Key")
            self.clipboard_monitor_job = None
            return

        # Update button text to show activity
        self.key_buttons[key_name].configure(text=f"Listening {60-attempt}s...")

        try:
            text = self.clipboard_get()
            if text and re.match(pattern, text.strip()):
                # Found it!
                self._update_entry(key_name, text.strip())
                self.key_buttons[key_name].configure(text="Get Key") # Reset
                self.clipboard_monitor_job = None
                return
        except Exception:
            pass # Clipboard might be empty or locked

        # Schedule next check
        self.clipboard_monitor_job = self.after(1000, lambda: self.monitor_clipboard(key_name, pattern, attempt+1))

    def cleanup(self):
        """Cancel any active background tasks."""
        if self.clipboard_monitor_job:
            self.after_cancel(self.clipboard_monitor_job)
            self.clipboard_monitor_job = None
            # Reset buttons if needed
            for btn in self.key_buttons.values():
                if "Listening" in btn.cget("text"):
                    btn.configure(text="Get Key")

    def _on_auth_success(self, key_name, token):
        """Callback for successful OAuth."""
        # Update entry and save
        if key_name in self.key_entries:
            # Must run on main thread if callback comes from background thread
            self.after(0, lambda: self._update_entry(key_name, token))

    def _update_entry(self, key_name, token):
        """Update UI entry safely."""
        ent = self.key_entries[key_name]
        ent.delete(0, "end")
        ent.insert(0, token)
        config_manager.set_secure(key_name, token)
        messagebox.showinfo("Success", f"Successfully authenticated with {key_name}!")

    def _on_auth_error(self, error_msg):
        """Callback for OAuth failure."""
        self.after(0, lambda: messagebox.showerror("Auth Failed", error_msg))

    def save_keys(self):
        for k, ent in self.key_entries.items():
            val = ent.get().strip()
            if val:
                config_manager.set_secure(k, val)
            
        messagebox.showinfo("Saved", "API Keys saved securely to OS Keychain.")

    def rerun_wizard(self):
        if messagebox.askyesno("Confirm", "This will re-scan your system and may overwrite existing configurations. Continue?"):
            self.app.show_setup_wizard()