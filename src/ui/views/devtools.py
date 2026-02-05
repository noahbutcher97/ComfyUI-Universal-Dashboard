import customtkinter as ctk
import threading
import subprocess
import platform
import os
import shutil
import webbrowser
from tkinter import messagebox, simpledialog
from src.services.system_service import SystemService
from src.services.dev_service import DevService
from src.services.auth_service import AuthService
from src.config.manager import config_manager

class DevToolsFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.auth_service = AuthService()
        self.install_event = threading.Event()
        
        ctk.CTkLabel(self, text="Developer Environment", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        # Tabs
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True)
        
        # Dynamic Tabs from Config
        sys_conf = DevService.get_system_tools_config()
        categories = sys_conf.get("categories", {})
        
        for cat_key, tools in categories.items():
            tab_name = cat_key.replace("_", " ").title()
            self.tabs.add(tab_name)
            self._build_category_tab(self.tabs.tab(tab_name), tools)
            
        # Custom AI Tools Tab
        self.tabs.add("AI Tools")
        self._build_ai_tools(self.tabs.tab("AI Tools"))

        # Initial Status Check
        self.refresh_status()

    def _build_category_tab(self, parent, tool_ids):
        # Add scrollable frame if list is long
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        for tid in tool_ids:
            # Filter: Only show tools installable on this OS
            if not DevService.get_system_install_cmd(tid):
                continue

            tool = DevService.get_system_tool_def(tid)
            if tool:
                self._add_tool_row(
                    scroll, 
                    tool["name"], 
                    tool["desc"], 
                    tid, 
                    lambda t=tid: self._install_system_tool(t)
                )

    def _confirm_process_kill(self, processes):
        """Standard callback for terminating locking processes."""
        msg = "The following processes are currently running and may lock the installation:\n\n"
        msg += "\n".join([f"- {p['name']} (PID: {p['pid']})" for p in processes])
        msg += "\n\nDo you want to terminate them and continue?"
        return messagebox.askyesno("Process Conflict", msg)

    def _install_system_tool(self, tool_id):
        cmd = DevService.get_system_install_cmd(tool_id)
        
        # Intercept Winget Install on Windows to use internal logic
        if tool_id == "winget" and platform.system() == "Windows":
             def run_winget():
                 self.app.add_activity("install_winget", "Installing Winget...")
                 if SystemService.install_winget(confirmation_callback=self._confirm_process_kill):
                     self.app.after(0, self.refresh_status)
                     self.app.after(0, lambda: messagebox.showinfo("Success", "Winget is ready!"))
                 else:
                     self.app.after(0, lambda: messagebox.showerror("Error", "Failed to configure Winget."))
                 self.app.complete_activity("install_winget")
             threading.Thread(target=run_winget, daemon=True).start()
             return

        if not cmd:
            messagebox.showinfo("Manual Install", f"No automated installer available for {tool_id} on this OS.\nPlease install manually.")
            return

        def run():
            self.app.add_activity(f"install_{tool_id}", f"Installing {tool_id}...")
            try:
                # Handle special Winget missing case on Windows
                if platform.system() == "Windows" and cmd and "winget" in str(cmd) and not shutil.which("winget"):
                     if messagebox.askyesno("Winget Missing", "Windows Package Manager (Winget) is required. Install it now?"):
                         if SystemService.install_winget(confirmation_callback=self._confirm_process_kill):
                             messagebox.showinfo("Success", "Winget installed. Please try again.")
                         else:
                             messagebox.showerror("Error", "Failed to install Winget.")
                         self.app.complete_activity(f"install_{tool_id}")
                         return

                # Generic Lock Check
                if not SystemService.ensure_no_locks(tool_id, self._confirm_process_kill):
                    self.app.complete_activity(f"install_{tool_id}")
                    return

                if isinstance(cmd, str):
                    subprocess.call(cmd, shell=True)
                else:
                    subprocess.call(cmd, shell=(platform.system()=="Windows"))
                
                self.app.after(0, self.refresh_status)
                self.app.after(0, lambda: messagebox.showinfo("Success", f"{tool_id} installation command finished."))
            except Exception as e:
                self.app.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.app.complete_activity(f"install_{tool_id}")

        threading.Thread(target=run, daemon=True).start()

    def _build_ai_tools(self, parent):
        # Reuse existing cli_widgets_frame logic but reparented
        self.cli_widgets_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.cli_widgets_frame.pack(fill="x", pady=10)
        
        # Options
        opt = ctk.CTkFrame(parent, fg_color="transparent")
        opt.pack(fill="x", pady=10)
        
        self.path_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt, text="Add to System PATH (Make available in Terminal)", variable=self.path_var).pack(side="left", padx=10)
        
        ctk.CTkButton(parent, text="Install Selected", fg_color="green", command=self.install_clis).pack(pady=10)
        self.cli_vars = {}

    def _add_tool_row(self, parent, name, desc, tool_id_check, install_cmd):
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=5, padx=5)
        
        ctk.CTkLabel(row, text=name, font=("Arial", 14, "bold"), width=150, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(row, text=desc, text_color="gray", width=200, anchor="w").pack(side="left", padx=10)
        
        status_lbl = ctk.CTkLabel(row, text="Checking...", width=100)
        status_lbl.pack(side="left", padx=10)
        
        # Store for update using ID as key
        if not hasattr(self, 'tool_status_labels'): self.tool_status_labels = {}
        self.tool_status_labels[tool_id_check] = status_lbl
        
        if install_cmd:
            ctk.CTkButton(row, text="Install", width=80, command=install_cmd).pack(side="right", padx=10, pady=5)

    def refresh_status(self):
        # Update System Tools
        for tool_id, lbl in getattr(self, 'tool_status_labels', {}).items():
            # Check if it's a system tool ID first
            if DevService.get_system_tool_def(tool_id):
                installed = DevService.check_system_tool(tool_id)
                lbl.configure(text="✅ Installed" if installed else "❌ Missing", 
                              text_color="green" if installed else "red")
            
        # Update AI Tools (if frame exists)
        if hasattr(self, 'cli_widgets_frame'):
            self.refresh_cli_list()

    def _update_cli_list_ui(self, statuses):
        # Check Prerequisites
        env = SystemService.verify_environment()
        has_npm = env["npm"]
        
        # Clear existing
        for w in self.cli_widgets_frame.winfo_children():
            w.destroy()
        
        for tool_name, is_installed in statuses.items():
            # Filter: Only show tools installable on this OS
            # Note: is_installed check allows showing manually installed tools even if we don't have an installer
            if not is_installed and not DevService.get_install_cmd(tool_name):
                continue

            row = ctk.CTkFrame(self.cli_widgets_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            # Get Config
            tool_conf = DevService.get_provider_config(tool_name)
            pkg_type = tool_conf.get("package_type") if tool_conf else "unknown"
            
            # Prerequisite Check
            is_disabled = False
            status_text = ""
            status_color = "gray"
            
            if is_installed:
                status_text = "✅ Installed"
                status_color = "green"
                is_disabled = True
            elif pkg_type == "npm" and not has_npm:
                status_text = "⚠ Needs Node.js"
                status_color = "#eab308" # Amber
                is_disabled = True
            else:
                status_text = "Not Installed"

            var = ctk.BooleanVar(value=is_installed)
            chk = ctk.CTkCheckBox(row, text=tool_name, variable=var)
            chk.pack(side="left")
            self.cli_vars[tool_name] = var

            if is_disabled:
                chk.configure(state="disabled")
                
            ctk.CTkLabel(row, text=status_text, text_color=status_color, width=120).pack(side="left", padx=10)

    def refresh_cli_list(self):
        # Clear and show loading
        for w in self.cli_widgets_frame.winfo_children(): w.destroy()
        
        def do_check():
            # In a thread, check all statuses
            DevService.clear_cache()
            providers = DevService.get_all_providers()
            statuses = {
                tool_name: DevService.is_installed(tool_name)
                for tool_name in providers
            }
            # Schedule UI update on main thread
            self.app.after(0, lambda: self._update_cli_list_ui(statuses))

        threading.Thread(target=do_check, daemon=True).start()

    def install_clis(self):
        add_to_path = self.path_var.get()
        targets = [t for t, v in self.cli_vars.items() if v.get() and not DevService.is_installed(t)]
        if not targets: 
            messagebox.showinfo("Info", "No new tools selected.")
            return

        threading.Thread(target=self._install_worker, args=(targets, add_to_path), daemon=True).start()
        messagebox.showinfo("Started", "Installation sequence initiated.")

    def _install_worker(self, targets, add_to_path):
        for t in targets:
            task_id = f"cli_{t.replace(' ', '_')}"
            self.app.add_activity(task_id, f"Installing {t}")
            
            # 1. API Key Check
            tool_conf = DevService.get_provider_config(t)
            api_key_name = tool_conf.get("api_key_name")
            
            key = None
            if api_key_name:
                key = config_manager.get_secure(api_key_name)
                if not key:
                    # Pause and ask user
                    self.install_event.clear()
                    self.app.after(0, lambda: self._prompt_api_key(t, api_key_name))
                    self.install_event.wait() # Block thread until dialog closes
                    
                    # Refresh key
                    key = config_manager.get_secure(api_key_name)
            
            # 2. Install
            self.app.update_activity(task_id, 0.3)
            
            # Generic Lock Check
            if not SystemService.ensure_no_locks(t, self._confirm_process_kill):
                self.app.complete_activity(task_id)
                continue # Skip this tool

            # Hardcode 'system' scope:
            # - NPM: Forces -g (Global)
            # - Pip: Ignored in Venv (Install to Venv)
            cmd = DevService.get_install_cmd(t, scope="system")
            
            if cmd:
                try:
                    # Detect shell script (String) vs Command List
                    is_script = isinstance(cmd, list) and len(cmd) == 1 and " " in cmd[0]
                    
                    if is_script:
                        subprocess.call(cmd[0], shell=True)
                    else:
                        subprocess.call(cmd, shell=(platform.system()=="Windows"))
                        
                    self.app.update_activity(task_id, 0.8)
                    
                    # 3. Post-Install Config (PATH/Env)
                    if platform.system() == "Windows":
                        # A. API Keys
                        if api_key_name and key:
                            # Check if already set in environment
                            current_env = os.getenv(api_key_name)
                            if current_env != key:
                                # Ask to persist
                                if messagebox.askyesno("Configure Environment", f"Add {api_key_name} to System Environment?\n(Required for CLI usage outside this app)"):
                                    subprocess.call(["setx", api_key_name, key], shell=True)
                                    os.environ[api_key_name] = key
                        
                        # B. Binaries to PATH (if requested)
                        if add_to_path:
                            self._add_tool_to_path(t, tool_conf)
                            
                except Exception as e:
                    print(f"Install error: {e}")

            self.app.complete_activity(task_id)
        
        # Refresh UI
        self.app.after(100, self.refresh_cli_list)

    def _add_tool_to_path(self, tool_name, conf):
        """Helper to add tool binary path to System PATH."""
        try:
            # Determine path based on package type
            pkg_type = conf.get("package_type")
            target_path = None
            
            if pkg_type == "npm":
                target_path = os.path.join(os.getenv('APPDATA'), 'npm')
            elif pkg_type == "pip":
                # If running in venv, adding venv/Scripts to PATH is what makes it "global"
                if os.environ.get("VIRTUAL_ENV"):
                    target_path = os.path.join(os.environ["VIRTUAL_ENV"], "Scripts")
                else:
                    # User Install location
                    target_path = os.path.join(os.getenv('APPDATA'), 'Python', 'Python311', 'Scripts') # Heuristic, might need improvement
            
            if target_path and os.path.exists(target_path):
                # Verify not already in PATH
                if target_path.lower() not in os.environ["PATH"].lower():
                    if messagebox.askyesno("Update PATH", f"Add {target_path} to System PATH?\n\nThis makes '{tool_name}' accessible from any terminal."):
                        # Append to User Path via PowerShell
                        ps_cmd = f'[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";{target_path}", "User")'
                        subprocess.check_call(["powershell", "-NoProfile", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        # Update local env
                        os.environ["PATH"] += f";{target_path}"
        except Exception as e:
            print(f"Failed to update PATH: {e}")

    def _prompt_api_key(self, tool_name, key_name):
        """Show a modal dialog for API Key generation."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Configure {tool_name}")
        dialog.geometry("500x250")
        dialog.grab_set() # Modal
        
        ctk.CTkLabel(dialog, text=f"{tool_name} requires an API Key", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkLabel(dialog, text=f"We need {key_name} to configure this tool.", text_color="gray").pack()
        
        def on_auth_click():
            status = self.auth_service.initiate_auth(key_name, 
                on_success=lambda t: on_save(t), 
                on_error=lambda e: messagebox.showerror("Error", e)
            )
            if status:
                messagebox.showinfo("Instructions", status)

        ctk.CTkButton(dialog, text="Get / Sign In", command=on_auth_click).pack(pady=10)
        
        entry = ctk.CTkEntry(dialog, width=300, placeholder_text="Paste Key Here")
        entry.pack(pady=5)
        
        def on_save(token=None):
            val = token or entry.get().strip()
            if val:
                config_manager.set_secure(key_name, val)
                dialog.destroy()
                self.install_event.set() # Resume thread
            else:
                messagebox.showerror("Error", "Key cannot be empty")

        ctk.CTkButton(dialog, text="Save & Continue", fg_color="green", command=on_save).pack(pady=10)
        
        # Handle close (Skip)
        def on_close():
            dialog.destroy()
            self.install_event.set() # Resume (will skip config)
            
        dialog.protocol("WM_DELETE_WINDOW", on_close)
