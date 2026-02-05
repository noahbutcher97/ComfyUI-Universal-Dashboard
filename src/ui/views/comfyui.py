import customtkinter as ctk
from tkinter import filedialog, ttk, messagebox
import threading
import subprocess
import os
from src.config.manager import config_manager
from src.services.comfy_service import ComfyService
from src.services.system_service import SystemService
from src.ui.components.tooltip import ToolTip

class ComfyUIFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(self, text="ComfyUI Studio", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        # Path config
        path_frame = ctk.CTkFrame(self)
        path_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(path_frame, text="Install Location:").pack(side="left", padx=10)
        self.comfy_path_lbl = ctk.CTkLabel(path_frame, text=config_manager.get("comfy_path"), text_color="cyan")
        self.comfy_path_lbl.pack(side="left", padx=10)
        ctk.CTkButton(path_frame, text="Change", width=80, command=self.change_comfy_path).pack(side="right", padx=10)
        
        # Wizard
        wiz = ctk.CTkFrame(self)
        wiz.pack(fill="x", pady=20)
        ctk.CTkLabel(wiz, text="Installation Wizard", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkButton(wiz, text="✨ Build Installation Manifest", height=50, fg_color="#6A0dad", command=self.open_wizard).pack(pady=20, fill="x", padx=40)

        # #TODO: Add ComfyUI lifecycle management features.
        # The current UI only supports the initial installation. Key features
        # for a robust tool would include updating and uninstalling.
        #
        # Suggested implementation:
        # 1. Add "Update ComfyUI" and "Uninstall ComfyUI" buttons.
        # 2. Update: Should run `git pull` in the core and manager directories,
        #    and potentially update other custom nodes. This should be a
        #    service-layer function.
        # 3. Uninstall: Should provide a confirmation dialog and then remove
        #    the entire ComfyUI directory. This should also be a service-layer
        #    function.

    def change_comfy_path(self):
        p = filedialog.askdirectory(initialdir=config_manager.get("comfy_path"))
        if p:
            config_manager.set("comfy_path", p)
            self.comfy_path_lbl.configure(text=p)

    def open_wizard(self):
        """Launch the main Setup Wizard."""
        if hasattr(self.app, "show_setup_wizard"):
            self.app.show_setup_wizard()
        else:
            messagebox.showerror("Error", "Setup Wizard not available.")
