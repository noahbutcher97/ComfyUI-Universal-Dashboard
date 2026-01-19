"""
Capability Selector Component for the Setup Wizard.

Per PLAN: Generation Focus MVP - This component replaces the use-case cards
with modality checkboxes that let users select what they want to create.

Use case sub-selection: When a modality is selected, users can choose
specific capabilities (e.g., Image → Generation, Editing, Upscaling).
"""

import customtkinter as ctk
from typing import List, Dict, Callable, Optional, Union, Tuple
from dataclasses import dataclass, field

from src.schemas.hardware import HardwareProfile
from src.schemas.environment import EnvironmentReport


@dataclass
class UseCaseOption:
    """A specific use case within a modality."""
    capability_id: str  # Database capability ID (source of truth)
    display_name: str   # User-friendly name
    description: str    # Short description
    min_vram_gb: float = 0.0  # Override min VRAM if different from modality


# Use case options mapped from database capabilities
# Key: modality_id, Value: list of UseCaseOption
USE_CASE_OPTIONS: Dict[str, List[UseCaseOption]] = {
    "image": [
        UseCaseOption("text_to_image", "Generation", "Create images from text prompts"),
        UseCaseOption("image_editing", "Editing", "Modify existing images"),
        UseCaseOption("inpainting", "Inpainting", "Fill in or replace parts of images"),
        UseCaseOption("image_upscaling", "Upscaling", "Enhance image resolution"),
        UseCaseOption("controlnet", "ControlNet", "Guide generation with poses, edges, depth"),
        UseCaseOption("character_consistency", "Character Consistency", "Maintain character across generations"),
        UseCaseOption("face_swap", "Face Swap", "Replace faces in images"),
        UseCaseOption("background_removal", "Background Removal", "Remove or replace backgrounds"),
        UseCaseOption("relighting", "Relighting", "Change lighting in images"),
    ],
    "video": [
        UseCaseOption("text_to_video", "Text to Video", "Generate video from text prompts", 12.0),
        UseCaseOption("image_to_video", "Image to Video", "Animate a still image", 12.0),
        UseCaseOption("video_editing", "Video Editing", "Modify existing videos"),
        UseCaseOption("video_upscaling", "Video Upscaling", "Enhance video resolution"),
        UseCaseOption("frame_interpolation", "Frame Interpolation", "Create smooth slow-motion"),
        UseCaseOption("lip_sync", "Lip Sync", "Sync lips to audio"),
    ],
    "audio": [
        UseCaseOption("text_to_speech", "Text to Speech", "Convert text to spoken audio"),
        UseCaseOption("voice_cloning", "Voice Cloning", "Clone voices from samples"),
        UseCaseOption("music_generation", "Music Generation", "Create original music"),
        UseCaseOption("audio_generation", "Sound Effects", "Generate sound effects"),
        UseCaseOption("audio_separation", "Audio Separation", "Separate vocals/instruments"),
        UseCaseOption("noise_reduction", "Noise Reduction", "Remove background noise"),
        UseCaseOption("speech_to_text", "Transcription", "Convert speech to text"),
    ],
    "text": [
        UseCaseOption("text_generation", "Writing", "General text generation"),
        UseCaseOption("code_generation", "Coding", "Code generation and assistance"),
        UseCaseOption("chat", "Chat", "Conversational AI"),
        UseCaseOption("analysis", "Analysis", "Document analysis and summarization"),
        UseCaseOption("reasoning", "Reasoning", "Complex reasoning tasks"),
    ],
    "3d": [
        UseCaseOption("image_to_3d", "Image to 3D", "Convert images to 3D models"),
        UseCaseOption("text_to_3d", "Text to 3D", "Generate 3D from text prompts"),
        UseCaseOption("image_to_multiview", "Multi-view", "Generate multiple views from image"),
    ],
}


@dataclass
class ModalityInfo:
    """Information about a capability modality."""
    id: str
    name: str
    icon: str
    description: str
    min_vram_gb: float  # Minimum VRAM for local execution
    cloud_available: bool  # Whether cloud APIs exist for this modality
    use_cases: List[UseCaseOption] = field(default_factory=list)


# Modality definitions with hardware requirements
MODALITIES = [
    ModalityInfo(
        id="image",
        name="Images",
        icon="🎨",
        description="Generate and edit images from text prompts",
        min_vram_gb=4.0,  # SD 1.5 can run on 4GB
        cloud_available=True,
        use_cases=USE_CASE_OPTIONS.get("image", [])
    ),
    ModalityInfo(
        id="video",
        name="Video",
        icon="🎬",
        description="Generate video clips from images or text",
        min_vram_gb=12.0,  # Video models need significant VRAM
        cloud_available=True,
        use_cases=USE_CASE_OPTIONS.get("video", [])
    ),
    ModalityInfo(
        id="audio",
        name="Audio",
        icon="🎵",
        description="Generate music, speech, and sound effects",
        min_vram_gb=8.0,
        cloud_available=True,
        use_cases=USE_CASE_OPTIONS.get("audio", [])
    ),
    ModalityInfo(
        id="text",
        name="Text/LLM",
        icon="📝",
        description="Local language models for writing and coding",
        min_vram_gb=8.0,  # Quantized LLMs
        cloud_available=True,
        use_cases=USE_CASE_OPTIONS.get("text", [])
    ),
    ModalityInfo(
        id="3d",
        name="3D",
        icon="🎲",
        description="Generate 3D models and assets",
        min_vram_gb=12.0,
        cloud_available=True,
        use_cases=USE_CASE_OPTIONS.get("3d", [])
    ),
]


class CapabilityCard(ctk.CTkFrame):
    """
    A single capability card with checkbox, icon, and expandable use case options.

    Supports three states:
    - enabled: User can toggle on/off
    - disabled: Hardware can't run locally, but cloud available
    - unavailable: Not supported at all (greyed out)

    When selected, shows use case sub-options as checkboxes.
    """

    def __init__(
        self,
        master,
        modality: ModalityInfo,
        can_run_locally: bool,
        cloud_enabled: bool,
        on_change: Callable[[str, bool], None] = None,
        on_use_case_change: Callable[[str, List[str]], None] = None
    ):
        super().__init__(master, corner_radius=10)

        self.modality = modality
        self.can_run_locally = can_run_locally
        self.cloud_enabled = cloud_enabled
        self.on_change = on_change
        self.on_use_case_change = on_use_case_change

        # Track use case selections
        self.use_case_vars: Dict[str, ctk.BooleanVar] = {}
        self.use_case_frame: Optional[ctk.CTkFrame] = None

        # Determine state
        self.is_available = can_run_locally or (cloud_enabled and modality.cloud_available)

        # Layout - main content area
        self.grid_columnconfigure(1, weight=1)

        # Checkbox
        self.var_selected = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.var_selected,
            command=self._on_toggle,
            width=24,
            state="normal" if self.is_available else "disabled"
        )
        self.checkbox.grid(row=0, column=0, rowspan=2, padx=(15, 10), pady=15, sticky="n")

        # Icon + Name
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=1, sticky="w", padx=5, pady=(15, 0))

        icon_text = modality.icon if self.is_available else "⊘"
        self.icon_lbl = ctk.CTkLabel(header, text=icon_text, font=("Arial", 20))
        self.icon_lbl.pack(side="left", padx=(0, 10))

        name_color = "white" if self.is_available else "gray50"
        self.name_lbl = ctk.CTkLabel(
            header,
            text=modality.name,
            font=("Arial", 14, "bold"),
            text_color=name_color
        )
        self.name_lbl.pack(side="left")

        # Availability badge
        if not can_run_locally and cloud_enabled and modality.cloud_available:
            badge = ctk.CTkLabel(
                header,
                text="Cloud Only",
                font=("Arial", 10),
                text_color="gray80",
                fg_color="#2d4a6d",
                corner_radius=4,
                padx=6,
                pady=2
            )
            badge.pack(side="left", padx=(10, 0))
        elif not self.is_available:
            badge = ctk.CTkLabel(
                header,
                text="Unavailable",
                font=("Arial", 10),
                text_color="gray60",
                fg_color="#3d3d3d",
                corner_radius=4,
                padx=6,
                pady=2
            )
            badge.pack(side="left", padx=(10, 0))

        # Description
        desc_color = "gray70" if self.is_available else "gray50"
        self.desc_lbl = ctk.CTkLabel(
            self,
            text=modality.description,
            font=("Arial", 11),
            text_color=desc_color,
            anchor="w"
        )
        self.desc_lbl.grid(row=1, column=1, sticky="w", padx=5, pady=(0, 10))

        # Info button for unavailable items
        if not self.is_available:
            self.info_btn = ctk.CTkButton(
                self,
                text="?",
                width=24,
                height=24,
                corner_radius=12,
                fg_color="gray30",
                hover_color="gray40",
                command=self._show_unavailable_reason
            )
            self.info_btn.grid(row=0, column=2, rowspan=2, padx=15, sticky="n")

    def _on_toggle(self):
        """Handle checkbox toggle - show/hide use case options."""
        selected = self.var_selected.get()

        if selected and self.modality.use_cases and self.is_available:
            self._show_use_case_options()
        else:
            self._hide_use_case_options()

        if self.on_change:
            self.on_change(self.modality.id, selected)

    def _show_use_case_options(self):
        """Display use case checkboxes below the description."""
        if self.use_case_frame:
            return  # Already showing

        self.use_case_frame = ctk.CTkFrame(self, fg_color="gray20", corner_radius=8)
        self.use_case_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))

        # Label
        ctk.CTkLabel(
            self.use_case_frame,
            text="What do you want to do?",
            font=("Arial", 11),
            text_color="gray60"
        ).pack(anchor="w", padx=10, pady=(8, 4))

        # Checkboxes in a flow layout
        checkbox_container = ctk.CTkFrame(self.use_case_frame, fg_color="transparent")
        checkbox_container.pack(fill="x", padx=10, pady=(0, 8))

        # Create checkboxes for each use case
        for i, use_case in enumerate(self.modality.use_cases):
            var = ctk.BooleanVar(value=True)  # Default to selected
            self.use_case_vars[use_case.capability_id] = var

            cb = ctk.CTkCheckBox(
                checkbox_container,
                text=use_case.display_name,
                variable=var,
                command=self._on_use_case_toggle,
                font=("Arial", 10),
                width=24,
                height=20
            )
            # Flow layout: 2-3 items per row
            row = i // 3
            col = i % 3
            cb.grid(row=row, column=col, padx=(0, 15), pady=2, sticky="w")

            # Add tooltip on hover (description)
            cb.bind("<Enter>", lambda e, uc=use_case: self._show_tooltip(e, uc.description))
            cb.bind("<Leave>", self._hide_tooltip)

    def _hide_use_case_options(self):
        """Remove use case checkboxes."""
        if self.use_case_frame:
            self.use_case_frame.destroy()
            self.use_case_frame = None
            self.use_case_vars.clear()

    def _on_use_case_toggle(self):
        """Handle use case checkbox change."""
        if self.on_use_case_change:
            selected_use_cases = self.get_selected_use_cases()
            self.on_use_case_change(self.modality.id, selected_use_cases)

    def _show_tooltip(self, event, text: str):
        """Show tooltip near cursor."""
        # Simple tooltip implementation using label
        self._tooltip = ctk.CTkLabel(
            self,
            text=text,
            font=("Arial", 9),
            fg_color="gray30",
            corner_radius=4,
            padx=6,
            pady=2
        )
        self._tooltip.place(x=event.x + 10, y=event.y + 10)

    def _hide_tooltip(self, event=None):
        """Hide tooltip."""
        if hasattr(self, '_tooltip') and self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    def _show_unavailable_reason(self):
        """Show tooltip explaining why this modality is unavailable."""
        if not self.can_run_locally:
            reason = f"Requires {self.modality.min_vram_gb}GB+ VRAM for local execution."
            if not self.cloud_enabled:
                reason += "\nCloud APIs are disabled in your preferences."
            dialog = ctk.CTkToplevel(self)
            dialog.title("Why Unavailable?")
            dialog.geometry("300x100")
            dialog.resizable(False, False)
            ctk.CTkLabel(dialog, text=reason, wraplength=280).pack(padx=20, pady=20)
            dialog.after(100, dialog.lift)
            dialog.after(200, dialog.focus_force)

    def set_selected(self, selected: bool):
        """Programmatically set selection state."""
        if self.is_available:
            self.var_selected.set(selected)
            # Trigger show/hide of use case options
            if selected and self.modality.use_cases:
                self._show_use_case_options()
            else:
                self._hide_use_case_options()

    def is_selected(self) -> bool:
        """Check if this capability is selected."""
        return self.var_selected.get()

    def get_selected_use_cases(self) -> List[str]:
        """Get list of selected use case capability IDs."""
        return [
            cap_id
            for cap_id, var in self.use_case_vars.items()
            if var.get()
        ]

    def set_selected_use_cases(self, capability_ids: List[str]):
        """Set which use cases are selected."""
        for cap_id, var in self.use_case_vars.items():
            var.set(cap_id in capability_ids)


class CapabilitySelector(ctk.CTkFrame):
    """
    Main capability selector component.

    Shows a grid of modalities that users can select based on what they
    want to create. Respects hardware constraints and cloud preferences.

    When modalities are selected, shows use case sub-options for fine-grained
    selection (e.g., Image → Generation, Editing, Upscaling).
    """

    def __init__(
        self,
        master,
        hardware_profile: Optional[Union[HardwareProfile, EnvironmentReport]] = None,
        cloud_willingness: str = "cloud_fallback",
        on_selection_change: Callable[[List[str]], None] = None,
        on_use_case_change: Callable[[Dict[str, List[str]]], None] = None
    ):
        super().__init__(master, fg_color="transparent")

        self.hardware_profile = hardware_profile
        self.cloud_willingness = cloud_willingness
        self.on_selection_change = on_selection_change
        self.on_use_case_change = on_use_case_change
        self.cards: Dict[str, CapabilityCard] = {}

        # Determine cloud availability from user preference
        self.cloud_enabled = cloud_willingness in ["cloud_fallback", "cloud_preferred", "cloud_only"]

        # Get VRAM for local capability checks
        self.vram_gb = hardware_profile.vram_gb if hardware_profile else 0.0

        # Header
        ctk.CTkLabel(
            self,
            text="What do you want to create?",
            font=("Arial", 20, "bold")
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            self,
            text="Select the types of content you're interested in generating.",
            font=("Arial", 12),
            text_color="gray70"
        ).pack(pady=(0, 20))

        # Hardware summary (if available)
        if hardware_profile:
            hw_text = f"Your hardware: {hardware_profile.gpu_name} ({hardware_profile.vram_gb:.0f}GB VRAM)"
            ctk.CTkLabel(
                self,
                text=hw_text,
                font=("Arial", 11),
                text_color="gray60"
            ).pack(pady=(0, 15))

        # Cards container with scrolling support
        self.cards_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cards_container.pack(fill="both", expand=True)
        self.cards_container.grid_columnconfigure(0, weight=1)

        # Create cards in a single column (allows for expansion)
        for i, modality in enumerate(MODALITIES):
            can_run_locally = self._can_run_locally(modality)

            card = CapabilityCard(
                self.cards_container,
                modality=modality,
                can_run_locally=can_run_locally,
                cloud_enabled=self.cloud_enabled,
                on_change=self._on_card_change,
                on_use_case_change=self._on_use_case_change
            )
            card.grid(row=i, column=0, padx=10, pady=5, sticky="ew")
            self.cards[modality.id] = card

        # Select defaults based on user profile
        self._set_defaults()

    def _can_run_locally(self, modality: ModalityInfo) -> bool:
        """Check if modality can run locally based on hardware."""
        if self.cloud_willingness == "cloud_only":
            # Cloud-only users don't need local capability
            return False

        if not self.hardware_profile:
            # No hardware info, assume capable
            return True

        # Check VRAM requirement
        return self.vram_gb >= modality.min_vram_gb

    def _on_card_change(self, modality_id: str, selected: bool):
        """Handle card selection change."""
        if self.on_selection_change:
            self.on_selection_change(self.get_selected_modalities())
        # Also notify about use case changes
        self._notify_use_case_change()

    def _on_use_case_change(self, modality_id: str, use_cases: List[str]):
        """Handle use case selection change within a modality."""
        self._notify_use_case_change()

    def _notify_use_case_change(self):
        """Notify about the current use case selection state."""
        if self.on_use_case_change:
            self.on_use_case_change(self.get_all_selected_use_cases())

    def _set_defaults(self):
        """Set default selections based on common use cases."""
        # Default: select Images (most common use case)
        if "image" in self.cards and self.cards["image"].is_available:
            self.cards["image"].set_selected(True)

    def get_selected_modalities(self) -> List[str]:
        """Get list of selected modality IDs."""
        return [
            modality_id
            for modality_id, card in self.cards.items()
            if card.is_selected()
        ]

    def get_all_selected_use_cases(self) -> Dict[str, List[str]]:
        """
        Get all selected use cases grouped by modality.

        Returns:
            Dict mapping modality_id to list of selected capability_ids.
            Only includes modalities that are selected.
        """
        result = {}
        for modality_id, card in self.cards.items():
            if card.is_selected():
                use_cases = card.get_selected_use_cases()
                if use_cases:  # Only include if there are selected use cases
                    result[modality_id] = use_cases
        return result

    def get_flat_selected_capabilities(self) -> List[str]:
        """
        Get a flat list of all selected capability IDs across all modalities.

        Returns:
            List of capability_ids (e.g., ["text_to_image", "inpainting", "text_to_video"])
        """
        capabilities = []
        for modality_id, card in self.cards.items():
            if card.is_selected():
                capabilities.extend(card.get_selected_use_cases())
        return capabilities

    def set_selected_modalities(self, modality_ids: List[str]):
        """Set which modalities are selected."""
        for modality_id, card in self.cards.items():
            card.set_selected(modality_id in modality_ids)

    def set_selected_use_cases(self, modality_id: str, capability_ids: List[str]):
        """Set which use cases are selected for a specific modality."""
        if modality_id in self.cards:
            self.cards[modality_id].set_selected_use_cases(capability_ids)
