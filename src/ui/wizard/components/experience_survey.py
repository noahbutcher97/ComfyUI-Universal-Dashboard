import customtkinter as ctk
from typing import Optional

# Cloud willingness options (PLAN: Cloud API Integration)
CLOUD_WILLINGNESS_OPTIONS = [
    ("Local Only", "local_only"),
    ("Open to Both", "cloud_fallback"),
    ("Prefer Cloud", "cloud_preferred"),
    ("Cloud Only", "cloud_only"),
]


class ExperienceSurvey(ctk.CTkFrame):
    """
    Survey component for gathering user experience and preferences.

    Per PLAN: Cloud API Integration - Now includes cloud API preference questions
    that shape whether recommendations come from local or cloud model databases.
    """

    def __init__(self, master, on_next, storage_free_gb: Optional[float] = None):
        """
        Initialize the experience survey.

        Args:
            master: Parent widget
            on_next: Callback with signature:
                on_next(ai_exp, tech_exp, cloud_willingness, cost_sensitivity)
            storage_free_gb: Free storage in GB (for contextual warning). If < 50GB,
                highlights "Cloud Only" option.
        """
        super().__init__(master, fg_color="transparent")
        self.on_next = on_next
        self.storage_free_gb = storage_free_gb

        # Create scrollable frame for content
        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            self.content, text="Customize Your Experience", font=("Arial", 20, "bold")
        ).pack(pady=(20, 30))

        # AI Experience
        self.ai_var = ctk.IntVar(value=3)
        self._build_slider_group(
            "How familiar are you with AI tools?",
            self.ai_var,
            ["Newcomer", "Dabbler", "User", "Advanced", "Pro"],
        )

        # Tech Experience
        self.tech_var = ctk.IntVar(value=3)
        self._build_slider_group(
            "Technical Proficiency",
            self.tech_var,
            ["Non-Tech", "Basic", "Comfortable", "Dev", "Expert"],
        )

        # Cloud API Willingness (PLAN: Cloud API Integration)
        self._build_cloud_willingness_section()

        # Cost Sensitivity (PLAN: Cloud API Integration)
        self.cost_var = ctk.IntVar(value=3)
        self._build_slider_group(
            "How important is keeping costs low?",
            self.cost_var,
            ["Not at all", "Quality first", "Balance", "Prefer cheaper", "Minimize cost"],
        )

        ctk.CTkButton(
            self.content, text="Next", height=40, command=self.on_continue
        ).pack(pady=40, ipadx=20)

    def _build_slider_group(self, title, variable, labels):
        """Build a labeled slider group."""
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        f.pack(fill="x", padx=50, pady=20)

        ctk.CTkLabel(f, text=title, font=("Arial", 14, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        slider = ctk.CTkSlider(f, from_=1, to=5, number_of_steps=4, variable=variable)
        slider.pack(fill="x", pady=5)

        # Labels row
        lbls = ctk.CTkFrame(f, fg_color="transparent")
        lbls.pack(fill="x")
        lbls.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        for i, txt in enumerate(labels):
            ctk.CTkLabel(lbls, text=txt, font=("Arial", 10)).grid(row=0, column=i)

    def _build_cloud_willingness_section(self):
        """
        Build the cloud API willingness section with 4-option segmented control.

        Per PLAN: Cloud API Integration - This question shapes which recommendation
        pathway (local vs cloud) is primary.
        """
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        f.pack(fill="x", padx=50, pady=20)

        ctk.CTkLabel(
            f, text="How would you like to run AI models?", font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))

        # Storage constraint warning (PLAN: Cloud API Integration)
        if self.storage_free_gb is not None and self.storage_free_gb < 50:
            warning_frame = ctk.CTkFrame(f, fg_color="#3D3D00", corner_radius=8)
            warning_frame.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                warning_frame,
                text=f"⚠️ Limited storage ({self.storage_free_gb:.0f}GB free) - Cloud Only might be a good fit",
                font=("Arial", 11),
                text_color="#FFCC00",
            ).pack(padx=10, pady=8)

        # Variable to track selection (default: cloud_fallback)
        self.cloud_willingness_var = ctk.StringVar(value="cloud_fallback")

        # Create segmented button frame
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)

        # Use radio buttons styled as segmented control
        for i, (label, value) in enumerate(CLOUD_WILLINGNESS_OPTIONS):
            # Highlight "Cloud Only" if storage is constrained
            highlight = (
                value == "cloud_only"
                and self.storage_free_gb is not None
                and self.storage_free_gb < 50
            )

            btn = ctk.CTkRadioButton(
                btn_frame,
                text=label,
                variable=self.cloud_willingness_var,
                value=value,
                font=("Arial", 12, "bold") if highlight else ("Arial", 12),
                fg_color="#FFCC00" if highlight else None,
            )
            btn.pack(side="left", padx=(0 if i == 0 else 15, 0), pady=5)

        # Description labels
        desc_frame = ctk.CTkFrame(f, fg_color="transparent")
        desc_frame.pack(fill="x", pady=(10, 0))

        descriptions = {
            "local_only": "Download and run everything on your hardware",
            "cloud_fallback": "Prefer local, but show cloud options if hardware can't handle it",
            "cloud_preferred": "Prefer cloud APIs, but show local options if you want to tinker",
            "cloud_only": "No downloads - use cloud APIs exclusively",
        }

        self.desc_label = ctk.CTkLabel(
            desc_frame,
            text=descriptions["cloud_fallback"],
            font=("Arial", 11),
            text_color="gray",
        )
        self.desc_label.pack(anchor="w")

        # Update description when selection changes
        def update_description(*args):
            selected = self.cloud_willingness_var.get()
            self.desc_label.configure(text=descriptions.get(selected, ""))

        self.cloud_willingness_var.trace_add("write", update_description)

    def on_continue(self):
        """
        Continue to next step with all survey values.

        Callback signature: on_next(ai_exp, tech_exp, cloud_willingness, cost_sensitivity)
        """
        self.on_next(
            self.ai_var.get(),
            self.tech_var.get(),
            self.cloud_willingness_var.get(),
            self.cost_var.get(),
        )
