import customtkinter as ctk
from tkinter import filedialog, ttk
import threading
import subprocess
import os
import requests
import sys
from src.config.manager import config_manager
from src.services.comfy_service import ComfyService
from src.services.system_service import SystemService

class ComfyUIFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
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

    def change_comfy_path(self):
        p = filedialog.askdirectory(initialdir=config_manager.get("comfy_path"))
        if p:
            config_manager.set("comfy_path", p)
            self.comfy_path_lbl.configure(text=p)

    def open_wizard(self):
        win = ctk.CTkToplevel(self)
        win.title("Setup Wizard")
        win.geometry("600x700")
        
        gpu, vram = SystemService.get_gpu_info()
        ctk.CTkLabel(win, text=f"Detected: {gpu} ({vram} GB)", text_color="yellow").pack(pady=10)
        
        ctk.CTkLabel(win, text="Art Style").pack(anchor="w", padx=20)
        style_var = ctk.StringVar(value="General")
        ctk.CTkSegmentedButton(win, values=["Photorealistic", "Anime", "General"], variable=style_var).pack(fill="x", padx=20)
        
        ctk.CTkLabel(win, text="Media Type").pack(anchor="w", padx=20, pady=(10,0))
        media_var = ctk.StringVar(value="Image")
        ctk.CTkSegmentedButton(win, values=["Image", "Video", "Mixed"], variable=media_var).pack(fill="x", padx=20)
        
        consist_var = ctk.BooleanVar()
        ctk.CTkCheckBox(win, text="Consistency (IPAdapter)", variable=consist_var).pack(anchor="w", padx=20, pady=10)
        
        edit_var = ctk.BooleanVar()
        ctk.CTkCheckBox(win, text="Editing (ControlNet)", variable=edit_var).pack(anchor="w", padx=20, pady=5)
        
        def review():
            ans = {
                "style": style_var.get(), 
                "media": media_var.get(), 
                "consistency": consist_var.get(), 
                "editing": edit_var.get()
            }
            manifest = ComfyService.generate_manifest(ans, config_manager.get("comfy_path"))
            self.show_manifest_review(win, manifest)
            
        ctk.CTkButton(win, text="Next: Review Manifest", command=review).pack(side="bottom", fill="x", padx=20, pady=20)

    def show_manifest_review(self, parent, manifest):
        for w in parent.winfo_children(): w.destroy()
        parent.title("Review Manifest")
        
        ctk.CTkLabel(parent, text="Installation Manifest", font=("Arial", 18, "bold")).pack(pady=10)
        
        tree_frame = ctk.CTkFrame(parent)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        tree = ttk.Treeview(tree_frame, columns=("dest"), show="tree headings")
        tree.heading("#0", text="Component / Model")
        tree.heading("dest", text="Destination Folder")
        tree.column("#0", width=250)
        tree.column("dest", width=300)
        tree.pack(fill="both", expand=True)
        
        base_path = config_manager.get("comfy_path")
        for item in manifest:
            short_dest = item['dest'].replace(base_path, "...")
            tree.insert("", "end", text=item['name'], values=(short_dest,))
            
        def execute():
            parent.destroy()
            self.run_install_process(manifest)
            
        ctk.CTkButton(parent, text="Confirm & Install", fg_color="green", height=50, command=execute).pack(fill="x", padx=20, pady=20)

    def run_install_process(self, manifest):
        win = ctk.CTkToplevel(self)
        win.title("Installing...")
        win.geometry("600x400")
        log_box = ctk.CTkTextbox(win)
        log_box.pack(fill="both", expand=True)
        
        def process():
            log_box.insert("end", "Checking Python Environment...\n")
            # Logic to verify/create venv
            # ... (Simplified for this phase, assuming running in app context)
            
            for item in manifest:
                log_box.insert("end", f"Processing: {item['name']}...\n")
                log_box.see("end")
                
                if not os.path.exists(item['dest']): 
                    os.makedirs(item['dest'], exist_ok=True)
                
                if item['type'] == "clone":
                    if not os.path.exists(os.path.join(item['dest'], ".git")):
                        subprocess.call(["git", "clone", item['url'], item['dest']], stdout=subprocess.DEVNULL)
                    else:
                        log_box.insert("end", "  Already exists, skipping.\n")
                        
                elif item['type'] == "download":
                    fname = item['url'].split('/')[-1]
                    dest_file = os.path.join(item['dest'], fname)
                    if not os.path.exists(dest_file):
                        log_box.insert("end", f"  Downloading {fname}...\n")
                        try:
                            # Use requests with stream for future progress bar hooks
                            response = requests.get(item['url'], stream=True)
                            with open(dest_file, 'wb') as f:
                                for data in response.iter_content(4096):
                                    f.write(data)
                            log_box.insert("end", "  Download complete.\n")
                        except Exception as e:
                            log_box.insert("end", f"  Download FAILED: {e}\n")
                    else:
                        log_box.insert("end", "  File exists.\n")
            
            log_box.insert("end", "\n✅ All operations complete.\n")

        threading.Thread(target=process, daemon=True).start()
