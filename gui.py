import os
import sys
import time
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont

from video_manager import VideoManager
from audio_manager import AudioManager
from translator import Translator
from tracker import TextTracker

CONFIG_FILE = "config.json"

class LiveTranslateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live Translate Tool - AI Game & Video Translation")
        self.root.geometry("1180x820")
        self.root.minsize(860, 600)
        self.root.configure(bg="#121316")

        # Load persisted configuration
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)
        self.config = self.load_config()

        # Core managers
        self.video_manager = VideoManager()
        self.audio_manager = AudioManager()
        self.translator = Translator(
            default_engine=self.config.get("ocr_engine", "rapidocr"),
            default_provider=self.config.get("trans_provider", "auto")
        )
        self.tracker = TextTracker(
            iou_threshold=0.20,
            max_age_seconds=1.4 # Smooth persistence across brief OCR cycles, prevents flickering
        )
        self.canvas_image_id = None

        # Dynamic Font Cache
        self._font_cache = {}
        self.font_size = self.config.get("font_size", 18)
        self.font = self.get_font(self.font_size)

        # Runtime states
        self.is_running = True
        self.is_frozen = False
        self.frozen_frame = None

        # Thread synchronization
        self.lock = threading.Lock()
        self.last_frame = None
        self.ocr_thread_running = False
        self.last_ocr_end_time = 0.0

        # FPS & Telemetry
        self.frame_counter = 0
        self.fps_timer = time.time()
        self.current_fps = 0.0

        # UI state variables
        self.translation_enabled = tk.BooleanVar(value=self.config.get("translation_enabled", True))
        self.merge_lines_var = tk.BooleanVar(value=self.config.get("merge_lines", True))
        self.tracking_enabled_var = tk.BooleanVar(value=self.config.get("tracking_enabled", True))
        self.lang_filter_var = tk.StringVar(value=self.config.get("lang_filter", "ja"))
        self.ocr_engine_var = tk.StringVar(value=self.config.get("ocr_engine", "rapidocr"))
        self.trans_provider_var = tk.StringVar(value=self.config.get("trans_provider", "auto"))
        self.overlay_mode_var = tk.StringVar(value=self.config.get("overlay_mode", "box"))
        self.conf_threshold_var = tk.DoubleVar(value=self.config.get("confidence", 0.30))
        self.opacity_var = tk.DoubleVar(value=self.config.get("opacity", 1.0)) # Default 100% solid to cover text
        self.audio_passthrough_active = False
        self.audio_volume_var = tk.DoubleVar(value=self.config.get("audio_volume", 1.0))

        # Setup modern dark theme styles
        self.setup_styles()

        # Build UI layout
        self.create_widgets()
        self.populate_video_devices()
        self.populate_audio_devices()

        # Start video loop
        self.update_video()

    def load_config(self):
        defaults = {
            "ocr_engine": "rapidocr",
            "trans_provider": "auto",
            "translation_enabled": True,
            "lang_filter": "ja",
            "merge_lines": True,
            "tracking_enabled": True,
            "overlay_mode": "seamless",
            "confidence": 0.25,
            "font_size": 18,
            "opacity": 1.0,
            "audio_volume": 1.0,
            "resolution": "1080p"
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception as e:
                print(f"[GUI] Error reading config: {e}")
        return defaults

    def save_config(self):
        try:
            self.config.update({
                "ocr_engine": self.ocr_engine_var.get(),
                "trans_provider": self.trans_provider_var.get(),
                "translation_enabled": self.translation_enabled.get(),
                "lang_filter": self.lang_filter_var.get(),
                "merge_lines": self.merge_lines_var.get(),
                "tracking_enabled": self.tracking_enabled_var.get(),
                "overlay_mode": self.overlay_mode_var.get(),
                "confidence": round(self.conf_threshold_var.get(), 2),
                "font_size": self.font_size,
                "opacity": round(self.opacity_var.get(), 2),
                "audio_volume": round(self.audio_volume_var.get(), 2),
                "resolution": self.combo_res.get() if hasattr(self, 'combo_res') else "720p"
            })
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[GUI] Error saving config: {e}")

    def get_font(self, size):
        size = int(size)
        if size in self._font_cache:
            return self._font_cache[size]
        for font_name in ["georgia.ttf", "times.ttf", "segoeui.ttf", "arial.ttf", "meiryo.ttc"]:
            font_path = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", font_name)
            if os.path.exists(font_path):
                try:
                    f = ImageFont.truetype(font_path, size)
                    self._font_cache[size] = f
                    return f
                except Exception:
                    pass
        f = ImageFont.load_default()
        self._font_cache[size] = f
        return f

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        bg_dark = "#121316"
        bg_panel = "#1a1c23"
        bg_control = "#262934"
        fg_white = "#ffffff"
        fg_dim = "#94a3b8"
        accent_blue = "#0ea5e9"

        style.configure("TFrame", background=bg_dark)
        style.configure("Panel.TFrame", background=bg_panel)

        style.configure("TLabel", background=bg_dark, foreground=fg_white, font=("Segoe UI", 9))
        style.configure("Panel.TLabel", background=bg_panel, foreground=fg_white, font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=bg_dark, foreground=fg_white, font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", background="#0d0e11", foreground=fg_dim, font=("Segoe UI", 8))
        style.configure("Dim.TLabel", background=bg_panel, foreground=fg_dim, font=("Segoe UI", 8))

        style.configure("TButton", background=bg_control, foreground=fg_white, borderwidth=0, font=("Segoe UI", 9))
        style.map("TButton", background=[("active", "#374151"), ("pressed", accent_blue)])

        style.configure("Accent.TButton", background=accent_blue, foreground=fg_white, borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Accent.TButton", background=[("active", "#0284c7")])

        style.configure("TCheckbutton", background=bg_panel, foreground=fg_white, font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", bg_panel)])

        style.configure("Top.TCheckbutton", background=bg_dark, foreground=fg_white, font=("Segoe UI", 9, "bold"))
        style.map("Top.TCheckbutton", background=[("active", bg_dark)])

        style.configure("TCombobox", fieldbackground=bg_control, background=bg_control, foreground=fg_white, arrowcolor=fg_white, borderwidth=0)
        style.map("TCombobox", fieldbackground=[("readonly", bg_control)], foreground=[("readonly", fg_white)])

    def create_widgets(self):
        # Top Primary Header
        self.top_bar = tk.Frame(self.root, bg="#121316", height=54)
        self.top_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(8, 4))
        self.top_bar.pack_propagate(False)

        # Brand Title
        lbl_title = tk.Label(self.top_bar, text="LIVE TRANSLATE", bg="#121316", fg="#38bdf8", font=("Segoe UI", 12, "bold"))
        lbl_title.pack(side=tk.LEFT, padx=(4, 16))

        # Video Device
        lbl_vid = ttk.Label(self.top_bar, text="Video:")
        lbl_vid.pack(side=tk.LEFT, padx=(0, 4))
        self.combo_device = ttk.Combobox(self.top_bar, state="readonly", width=22)
        self.combo_device.pack(side=tk.LEFT, padx=(0, 4))
        self.combo_device.bind("<<ComboboxSelected>>", self.on_video_selected)

        btn_refresh = ttk.Button(self.top_bar, text="🔄", width=3, command=self.refresh_all_devices)
        btn_refresh.pack(side=tk.LEFT, padx=(0, 10))

        # Resolution
        lbl_res = ttk.Label(self.top_bar, text="Res:")
        lbl_res.pack(side=tk.LEFT, padx=(0, 4))
        self.combo_res = ttk.Combobox(self.top_bar, state="readonly", width=8, values=["720p", "1080p"])
        self.combo_res.set(self.config.get("resolution", "720p"))
        self.combo_res.pack(side=tk.LEFT, padx=(0, 10))
        self.combo_res.bind("<<ComboboxSelected>>", self.on_res_changed)

        # OCR Engine
        lbl_engine = ttk.Label(self.top_bar, text="Engine:")
        lbl_engine.pack(side=tk.LEFT, padx=(0, 4))
        self.combo_engine = ttk.Combobox(self.top_bar, state="readonly", width=11, values=["RapidOCR", "EasyOCR"])
        self.combo_engine.set("RapidOCR" if self.ocr_engine_var.get() == "rapidocr" else "EasyOCR")
        self.combo_engine.pack(side=tk.LEFT, padx=(0, 10))
        self.combo_engine.bind("<<ComboboxSelected>>", self.on_engine_changed)

        # Translation Provider
        lbl_prov = ttk.Label(self.top_bar, text="Trans:")
        lbl_prov.pack(side=tk.LEFT, padx=(0, 4))
        self.combo_prov = ttk.Combobox(self.top_bar, state="readonly", width=13, values=["Auto (Fallback)", "Offline (Local)", "Google", "MyMemory"])
        prov_map = {"auto": "Auto (Fallback)", "offline": "Offline (Local)", "google": "Google", "mymemory": "MyMemory"}
        self.combo_prov.set(prov_map.get(self.trans_provider_var.get(), "Auto (Fallback)"))
        self.combo_prov.pack(side=tk.LEFT, padx=(0, 12))
        self.combo_prov.bind("<<ComboboxSelected>>", self.on_provider_changed)

        # Enable Translation Toggle
        chk_trans = ttk.Checkbutton(self.top_bar, text="⚡ Translate", variable=self.translation_enabled, style="Top.TCheckbutton", command=self.on_translate_toggled)
        chk_trans.pack(side=tk.LEFT, padx=(0, 12))

        # Right Side Header Actions: Audio, Freeze, Settings Toggle
        self.btn_toggle_settings = ttk.Button(self.top_bar, text="⚙️ Settings", width=10, command=self.toggle_settings_panel)
        self.btn_toggle_settings.pack(side=tk.RIGHT, padx=4)

        self.btn_toggle_audio = ttk.Button(self.top_bar, text="🔊 Audio", width=9, command=self.toggle_audio_panel)
        self.btn_toggle_audio.pack(side=tk.RIGHT, padx=4)

        self.btn_freeze = ttk.Button(self.top_bar, text="⏸ Freeze", width=9, command=self.toggle_freeze)
        self.btn_freeze.pack(side=tk.RIGHT, padx=4)

        # Secondary Collapsible Panels (Audio & Settings)
        self.audio_panel = tk.Frame(self.root, bg="#1a1c23", height=48, highlightthickness=1, highlightbackground="#2d3748")
        self.settings_panel = tk.Frame(self.root, bg="#1a1c23", height=84, highlightthickness=1, highlightbackground="#2d3748")

        self.build_audio_panel()
        self.build_settings_panel()

        # Main Video Canvas Container
        self.canvas_frame = tk.Frame(self.root, bg="#000000")
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bottom Telemetry Status Bar
        self.status_bar = tk.Frame(self.root, bg="#0d0e11", height=26)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        self.lbl_status_fps = ttk.Label(self.status_bar, text="FPS: --", style="Status.TLabel")
        self.lbl_status_fps.pack(side=tk.LEFT, padx=12)

        self.lbl_status_ocr = ttk.Label(self.status_bar, text="OCR: -- ms", style="Status.TLabel")
        self.lbl_status_ocr.pack(side=tk.LEFT, padx=8)

        self.lbl_status_trans = ttk.Label(self.status_bar, text="Trans: -- ms", style="Status.TLabel")
        self.lbl_status_trans.pack(side=tk.LEFT, padx=8)

        self.lbl_status_boxes = ttk.Label(self.status_bar, text="Active: 0 boxes", style="Status.TLabel")
        self.lbl_status_boxes.pack(side=tk.LEFT, padx=8)

        self.lbl_status_audio = ttk.Label(self.status_bar, text="Audio: Inactive", style="Status.TLabel")
        self.lbl_status_audio.pack(side=tk.RIGHT, padx=12)

        self.lbl_status_hardware = ttk.Label(self.status_bar, text=self.translator.cuda_status, style="Status.TLabel")
        self.lbl_status_hardware.pack(side=tk.RIGHT, padx=8)

    def build_audio_panel(self):
        lbl_in = ttk.Label(self.audio_panel, text="Capture Audio In:", style="Panel.TLabel")
        lbl_in.pack(side=tk.LEFT, padx=(12, 4), pady=10)

        self.combo_audio_in = ttk.Combobox(self.audio_panel, state="readonly", width=22)
        self.combo_audio_in.pack(side=tk.LEFT, padx=(0, 10), pady=10)

        lbl_out = ttk.Label(self.audio_panel, text="Play to Output:", style="Panel.TLabel")
        lbl_out.pack(side=tk.LEFT, padx=(4, 4), pady=10)

        self.combo_audio_out = ttk.Combobox(self.audio_panel, state="readonly", width=22)
        self.combo_audio_out.pack(side=tk.LEFT, padx=(0, 12), pady=10)

        lbl_vol = ttk.Label(self.audio_panel, text="Vol:", style="Panel.TLabel")
        lbl_vol.pack(side=tk.LEFT, padx=(0, 4), pady=10)

        self.slider_vol = tk.Scale(
            self.audio_panel, from_=0.0, to=1.5, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.audio_volume_var,
            bg="#1a1c23", fg="#ffffff", highlightthickness=0,
            troughcolor="#262934", length=90, command=self.on_volume_changed
        )
        self.slider_vol.pack(side=tk.LEFT, padx=(0, 14), pady=6)

        self.btn_start_audio = ttk.Button(self.audio_panel, text="▶ Start Passthrough", style="Accent.TButton", command=self.toggle_audio_passthrough)
        self.btn_start_audio.pack(side=tk.LEFT, padx=(0, 10), pady=10)

    def build_settings_panel(self):
        row1 = tk.Frame(self.settings_panel, bg="#1a1c23")
        row1.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(6, 2))

        # Filter
        lbl_filter = ttk.Label(row1, text="Filter:", style="Panel.TLabel")
        lbl_filter.pack(side=tk.LEFT, padx=(0, 4))
        self.combo_filter = ttk.Combobox(row1, state="readonly", width=16, values=["Japanese Only", "All Languages"])
        self.combo_filter.set("Japanese Only" if self.lang_filter_var.get() == "ja" else "All Languages")
        self.combo_filter.pack(side=tk.LEFT, padx=(0, 12))
        self.combo_filter.bind("<<ComboboxSelected>>", self.on_filter_changed)

        # Overlay Mode
        lbl_mode = ttk.Label(row1, text="Overlay Mode:", style="Panel.TLabel")
        lbl_mode.pack(side=tk.LEFT, padx=(0, 4))
        self.combo_overlay_mode = ttk.Combobox(
            row1, state="readonly", width=22,
            values=["Seamless (No Boxes)", "Box Replacement", "Subtitle Banner", "Text Only"]
        )
        mode_val = self.overlay_mode_var.get()
        if mode_val == "seamless":
            self.combo_overlay_mode.set("Seamless (No Boxes)")
        elif mode_val == "box":
            self.combo_overlay_mode.set("Box Replacement")
        elif mode_val == "subtitle":
            self.combo_overlay_mode.set("Subtitle Banner")
        else:
            self.combo_overlay_mode.set("Text Only")
        self.combo_overlay_mode.pack(side=tk.LEFT, padx=(0, 14))
        self.combo_overlay_mode.bind("<<ComboboxSelected>>", self.on_overlay_mode_changed)

        # Merge Lines
        chk_merge = ttk.Checkbutton(row1, text="Merge Lines", variable=self.merge_lines_var)
        chk_merge.pack(side=tk.LEFT, padx=(0, 12))

        # Action: Copy translation
        btn_copy = ttk.Button(row1, text="📋 Copy Text", width=11, command=self.copy_latest_translation)
        btn_copy.pack(side=tk.RIGHT, padx=4)

        # Action: Save Cache
        btn_save_cache = ttk.Button(row1, text="💾 Save Cache", width=11, command=self.save_cache_now)
        btn_save_cache.pack(side=tk.RIGHT, padx=4)

        row2 = tk.Frame(self.settings_panel, bg="#1a1c23")
        row2.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(2, 6))

        # Confidence Slider
        lbl_conf = ttk.Label(row2, text="Min Conf:", style="Panel.TLabel")
        lbl_conf.pack(side=tk.LEFT, padx=(0, 4))
        self.scale_conf = tk.Scale(
            row2, from_=0.15, to=0.80, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.conf_threshold_var,
            bg="#1a1c23", fg="#ffffff", highlightthickness=0,
            troughcolor="#262934", length=90
        )
        self.scale_conf.pack(side=tk.LEFT, padx=(0, 16))

        # Font Size Slider
        lbl_font = ttk.Label(row2, text="Max Font Size:", style="Panel.TLabel")
        lbl_font.pack(side=tk.LEFT, padx=(0, 4))
        self.scale_font = tk.Scale(
            row2, from_=12, to=36, resolution=1,
            orient=tk.HORIZONTAL,
            bg="#1a1c23", fg="#ffffff", highlightthickness=0,
            troughcolor="#262934", length=90, command=self.on_font_size_changed
        )
        self.scale_font.set(self.font_size)
        self.scale_font.pack(side=tk.LEFT, padx=(0, 16))

        # Opacity Slider
        lbl_opacity = ttk.Label(row2, text="Box Opacity:", style="Panel.TLabel")
        lbl_opacity.pack(side=tk.LEFT, padx=(0, 4))
        self.scale_opacity = tk.Scale(
            row2, from_=0.5, to=1.0, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.opacity_var,
            bg="#1a1c23", fg="#ffffff", highlightthickness=0,
            troughcolor="#262934", length=90
        )
        self.scale_opacity.pack(side=tk.LEFT, padx=(0, 16))

    def toggle_settings_panel(self):
        if self.settings_panel.winfo_ismapped():
            self.settings_panel.pack_forget()
        else:
            self.settings_panel.pack(after=self.top_bar, fill=tk.X, padx=12, pady=(0, 6))

    def toggle_audio_panel(self):
        if self.audio_panel.winfo_ismapped():
            self.audio_panel.pack_forget()
        else:
            self.audio_panel.pack(after=self.top_bar, fill=tk.X, padx=12, pady=(0, 6))

    def populate_video_devices(self):
        devices = self.video_manager.get_devices()
        if devices:
            self.combo_device['values'] = [f"{i}: {name}" for i, name in enumerate(devices)]
            self.combo_device.current(0)
            self.on_video_selected(None)
        else:
            self.combo_device['values'] = ["No Camera / Capture Device"]
            self.combo_device.current(0)

    def populate_audio_devices(self):
        inputs, outputs = self.audio_manager.get_devices()
        self.audio_inputs = inputs
        self.audio_outputs = outputs

        if inputs:
            self.combo_audio_in['values'] = [f"{item['index']}: {item['name'][:30]}" for item in inputs]
            self.combo_audio_in.current(0)
        else:
            self.combo_audio_in['values'] = ["No Input Found"]
            self.combo_audio_in.current(0)

        if outputs:
            self.combo_audio_out['values'] = [f"{item['index']}: {item['name'][:30]}" for item in outputs]
            self.combo_audio_out.current(0)
        else:
            self.combo_audio_out['values'] = ["No Output Found"]
            self.combo_audio_out.current(0)

    def refresh_all_devices(self):
        self.populate_video_devices()
        self.populate_audio_devices()

    def on_video_selected(self, event):
        idx = self.combo_device.current()
        if idx >= 0 and self.combo_device.get() != "No Camera / Capture Device":
            res_str = self.combo_res.get()
            if res_str == "1080p":
                self.video_manager.set_target_resolution(1920, 1080)
            else:
                self.video_manager.set_target_resolution(1280, 720)
            self.video_manager.start_capture(idx)
            self.tracker.reset()

    def on_res_changed(self, event):
        res_str = self.combo_res.get()
        if res_str == "1080p":
            self.video_manager.set_target_resolution(1920, 1080)
        else:
            self.video_manager.set_target_resolution(1280, 720)
        if self.video_manager.current_device_index >= 0:
            self.video_manager.start_capture(self.video_manager.current_device_index)

    def on_engine_changed(self, event):
        eng = "rapidocr" if self.combo_engine.get() == "RapidOCR" else "easyocr"
        self.ocr_engine_var.set(eng)
        self.translator.set_engine(eng)
        self.tracker.reset()

    def on_provider_changed(self, event):
        sel = self.combo_prov.get()
        val = "auto"
        if "Offline" in sel:
            val = "offline"
        elif "Google" in sel:
            val = "google"
        elif "MyMemory" in sel:
            val = "mymemory"
        self.trans_provider_var.set(val)
        self.translator.set_provider(val)

    def on_translate_toggled(self):
        if not self.translation_enabled.get():
            self.tracker.reset()

    def on_filter_changed(self, event):
        filt = "ja" if self.combo_filter.get() == "Japanese Only" else "all"
        self.lang_filter_var.set(filt)
        self.tracker.reset()

    def on_overlay_mode_changed(self, event):
        val = self.combo_overlay_mode.get()
        if "Seamless" in val:
            mode = "seamless"
        elif "Box" in val:
            mode = "box"
        elif "Subtitle" in val:
            mode = "subtitle"
        else:
            mode = "text"
        self.overlay_mode_var.set(mode)

    def on_font_size_changed(self, val):
        self.font_size = int(float(val))
        self.font = self.get_font(self.font_size)

    def on_volume_changed(self, val):
        self.audio_manager.set_volume(float(val))

    def toggle_audio_passthrough(self):
        if self.audio_passthrough_active:
            self.audio_manager.stop_passthrough()
            self.audio_passthrough_active = False
            self.btn_start_audio.configure(text="▶ Start Passthrough", style="Accent.TButton")
            self.lbl_status_audio.configure(text="Audio: Inactive")
        else:
            in_sel = self.combo_audio_in.current()
            out_sel = self.combo_audio_out.current()
            if in_sel < 0 or out_sel < 0 or not self.audio_inputs or not self.audio_outputs:
                messagebox.showinfo("Audio", "Please select valid audio input and output devices.")
                return
            in_idx = self.audio_inputs[in_sel]['index']
            out_idx = self.audio_outputs[out_sel]['index']
            ok, msg = self.audio_manager.start_passthrough(in_idx, out_idx)
            if ok:
                self.audio_passthrough_active = True
                self.btn_start_audio.configure(text="⏹ Stop Passthrough", style="TButton")
                self.lbl_status_audio.configure(text=f"Audio: Active ({self.audio_inputs[in_sel]['name'][:12]} ➔ {self.audio_outputs[out_sel]['name'][:12]})")
            else:
                messagebox.showerror("Audio Error", f"Failed to start audio passthrough:\n{msg}")

    def toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        if self.is_frozen:
            self.btn_freeze.configure(text="▶ Resume", style="Accent.TButton")
            if self.last_frame is not None:
                self.frozen_frame = self.last_frame.copy()
        else:
            self.btn_freeze.configure(text="⏸ Freeze", style="TButton")
            self.frozen_frame = None

    def copy_latest_translation(self):
        active_items = self.tracker.get_active()
        texts = [item.get('translated', item.get('text', '')) for item in active_items if item.get('translated')]
        if texts:
            combined = "\n".join(texts)
            self.root.clipboard_clear()
            self.root.clipboard_append(combined)
            messagebox.showinfo("Copied", f"Copied {len(texts)} translated line(s) to clipboard!")
        else:
            messagebox.showinfo("Clipboard", "No translated text available on screen right now.")

    def save_cache_now(self):
        self.translator.save_cache()
        self.save_config()
        messagebox.showinfo("Saved", f"Translations cache ({len(self.translator.translation_cache)} entries) and settings saved locally.")

    def update_video(self):
        if not self.is_running:
            return

        if self.is_frozen and self.frozen_frame is not None:
            ret = True
            frame = self.frozen_frame
        else:
            ret, frame = self.video_manager.get_frame()

        if ret and frame is not None:
            if not self.is_frozen:
                with self.lock:
                    self.last_frame = frame.copy()

            # Measure display FPS
            self.frame_counter += 1
            now = time.time()
            if now - self.fps_timer >= 0.5:
                self.current_fps = self.frame_counter / (now - self.fps_timer)
                self.frame_counter = 0
                self.fps_timer = now
                self.update_telemetry_ui()

            # Render frame on Canvas
            c_width = self.canvas.winfo_width()
            c_height = self.canvas.winfo_height()

            if c_width > 10 and c_height > 10:
                h, w, _ = frame.shape
                scale = min(c_width / w, c_height / h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))

                resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                cv_rgb = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(cv_rgb)

                # Get currently active non-expired translations (clears text no longer on screen in real time)
                if self.translation_enabled.get():
                    active_items = self.tracker.get_active(now)
                    pil_img = self.draw_overlays(resized_frame, scale, active_items)
                else:
                    cv_rgb = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(cv_rgb)

                imgtk = ImageTk.PhotoImage(image=pil_img)
                if self.canvas_image_id is None:
                    self.canvas_image_id = self.canvas.create_image(c_width // 2, c_height // 2, image=imgtk, anchor=tk.CENTER)
                else:
                    self.canvas.coords(self.canvas_image_id, c_width // 2, c_height // 2)
                    self.canvas.itemconfig(self.canvas_image_id, image=imgtk)
                self.canvas.image = imgtk

            # Trigger OCR worker thread if idle
            if self.translation_enabled.get() and not self.ocr_thread_running and not self.is_frozen:
                self.trigger_ocr()

        # Run loop at ~60 FPS
        self.root.after(16, self.update_video)

    def trigger_ocr(self):
        now = time.time()
        # 50ms pacing between OCR passes gives the GPU/CPU breathing room for 60 FPS display
        if now - self.last_ocr_end_time < 0.05:
            return

        with self.lock:
            if self.last_frame is None:
                return
            frame_to_process = self.last_frame.copy()

        self.ocr_thread_running = True
        thread = threading.Thread(target=self.run_ocr_worker, args=(frame_to_process,))
        thread.daemon = True
        thread.start()

    def run_ocr_worker(self, frame):
        try:
            min_c = self.conf_threshold_var.get()
            mode = self.lang_filter_var.get()
            merge = self.merge_lines_var.get()

            detections = self.translator.process_frame(
                frame,
                min_conf=min_c,
                filter_mode=mode,
                merge_lines=merge
            )

            # Update tracker (associates boxes, updates coordinates, drops expired)
            self.tracker.update(detections)

        except Exception as e:
            print(f"[GUI Worker] Exception in OCR task: {e}")
        finally:
            self.last_ocr_end_time = time.time()
            self.ocr_thread_running = False

    def draw_overlays(self, frame_bgr, scale, items):
        if not items:
            cv_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            return Image.fromarray(cv_rgb)

        mode = self.overlay_mode_var.get() # 'seamless', 'box', 'subtitle', 'text'
        img_h, img_w = frame_bgr.shape[:2]

        if mode == "seamless":
            # 1. Seamless in-game mode (NO overlay boxes):
            # Inpaints the detected Japanese text regions to restore the natural underlying background texture
            mask = np.zeros((img_h, img_w), dtype=np.uint8)
            for it in items:
                ix = int(it['x'] * scale)
                iy = int(it['y'] * scale)
                iw = max(8, int(it['w'] * scale))
                ih = max(8, int(it['h'] * scale))
                cv2.rectangle(
                    mask,
                    (max(0, ix - 3), max(0, iy - 2)),
                    (min(img_w, ix + iw + 3), min(img_h, iy + ih + 2)),
                    255, -1
                )
            try:
                inpainted_bgr = cv2.inpaint(frame_bgr, mask, 3, cv2.INPAINT_TELEA)
            except Exception:
                inpainted_bgr = frame_bgr

            cv_rgb = cv2.cvtColor(inpainted_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv_rgb)
            draw = ImageDraw.Draw(pil_img, "RGBA")

            for item in items:
                text = item.get('translated', item.get('text', ''))
                if not text:
                    continue

                ix = int(item['x'] * scale)
                iy = int(item['y'] * scale)
                iw = max(10, int(item['w'] * scale))
                ih = max(10, int(item['h'] * scale))

                # Sample brightness from inpainted background
                roi = inpainted_bgr[max(0, iy):min(img_h, iy + ih), max(0, ix):min(img_w, ix + iw)]
                avg_bgr = np.mean(roi, axis=(0, 1)) if roi.size > 0 else [128, 128, 128]
                brightness = (avg_bgr[2] * 299 + avg_bgr[1] * 587 + avg_bgr[0] * 114) / 1000

                chosen_font_size = max(12, min(self.font_size, int(ih * 0.85)))
                font = self.get_font(chosen_font_size)

                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                # If multi-line paragraph or wide sentence, wrap text within area
                if tw > iw * 1.3 and " " in text:
                    lines = self.wrap_text(text, font, max(iw, 220), draw)
                else:
                    lines = [text]

                line_height = chosen_font_size + 3
                total_th = len(lines) * line_height
                cur_y = iy + (ih - total_th) // 2

                # Contextual RPG typography styling
                if brightness > 120:
                    # Light parchment/paper background (menus, books, scrolls)
                    if text == "Paused":
                        main_color = (65, 85, 120) # Official Oblivion blue-grey
                    else:
                        main_color = (48, 30, 20) # Official Oblivion sepia brown
                    shadow_color = (195, 175, 145, 220) # Warm parchment emboss
                else:
                    # Dark scene background
                    main_color = (255, 255, 255)
                    shadow_color = (0, 0, 0, 230)

                for line in lines:
                    l_bbox = draw.textbbox((0, 0), line, font=font)
                    lw = l_bbox[2] - l_bbox[0]
                    # Left-align multi-line paragraphs, center-align standalone buttons
                    tx = max(0, ix) if len(lines) > 1 else max(0, ix + (iw - lw) // 2)

                    # Draw subtle shadow/emboss + crisp main text
                    draw.text((tx + 1, cur_y + 1), line, font=font, fill=shadow_color)
                    draw.text((tx, cur_y), line, font=font, fill=main_color)
                    cur_y += line_height

            return pil_img

        elif mode == "subtitle":
            # Cinematic Subtitle Banner at bottom
            cv_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv_rgb)
            draw = ImageDraw.Draw(pil_img, "RGBA")
            opacity_val = int(255 * max(0.5, min(1.0, self.opacity_var.get())))

            valid_texts = [it.get('translated', it.get('text', '')) for it in items if it.get('translated')]
            if valid_texts:
                combined_sub = "  •  ".join(valid_texts)
                banner_h = max(54, int(self.font_size * 2.2))
                banner_y = img_h - banner_h - 18
                draw.rectangle(
                    [24, banner_y, img_w - 24, img_h - 18],
                    fill=(12, 14, 20, opacity_val),
                    outline=(255, 255, 255, 70),
                    width=1
                )
                draw.text((36, banner_y + 12), combined_sub, font=self.font, fill=(0, 0, 0, 240))
                draw.text((35, banner_y + 11), combined_sub, font=self.font, fill="#fef08a")
            return pil_img

        elif mode == "text":
            # Text Only mode: direct overlay without background box
            cv_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv_rgb)
            draw = ImageDraw.Draw(pil_img, "RGBA")

            for item in items:
                text = item.get('translated', item.get('text', ''))
                if not text:
                    continue
                ix = int(item['x'] * scale)
                iy = int(item['y'] * scale)
                iw = max(10, int(item['w'] * scale))
                ih = max(10, int(item['h'] * scale))

                chosen_font_size = max(11, min(self.font_size, int(ih * 0.95)))
                font = self.get_font(chosen_font_size)

                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                if tw > iw * 1.5 and " " in text:
                    lines = self.wrap_text(text, font, max(iw, 200), draw)
                else:
                    lines = [text]

                line_height = chosen_font_size + 3
                total_th = len(lines) * line_height
                cur_y = iy + (ih - total_th) // 2

                for line in lines:
                    l_bbox = draw.textbbox((0, 0), line, font=font)
                    lw = l_bbox[2] - l_bbox[0]
                    tx = max(0, ix) if len(lines) > 1 else max(0, ix + (iw - lw) // 2)

                    # 4-way dark outline for readability over any background
                    for ox, oy in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, 2)]:
                        draw.text((tx + ox, cur_y + oy), line, font=font, fill=(0, 0, 0, 240))
                    draw.text((tx, cur_y), line, font=font, fill="#ffffff")
                    cur_y += line_height

            return pil_img

        else: # "box" mode
            # Solid High-Contrast Box mode: clean dark slate background with neutral border
            cv_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv_rgb)
            draw = ImageDraw.Draw(pil_img, "RGBA")
            opacity_val = int(255 * max(0.5, min(1.0, self.opacity_var.get())))

            for item in items:
                text = item.get('translated', item.get('text', ''))
                if not text:
                    continue

                ix = int(item['x'] * scale)
                iy = int(item['y'] * scale)
                iw = max(10, int(item['w'] * scale))
                ih = max(10, int(item['h'] * scale))

                chosen_font_size = max(11, min(self.font_size, int(ih * 0.95)))
                font = self.get_font(chosen_font_size)

                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]

                if tw > iw * 1.5 and " " in text:
                    lines = self.wrap_text(text, font, max(iw + 20, 160), draw)
                else:
                    lines = [text]

                line_height = chosen_font_size + 3
                total_th = len(lines) * line_height
                max_line_w = max(draw.textbbox((0, 0), l, font=font)[2] - draw.textbbox((0, 0), l, font=font)[0] for l in lines)

                box_w = max(iw + 16, max_line_w + 20)
                box_h = max(ih + 8, total_th + 10)

                diff_x = (box_w - iw) // 2
                diff_y = (box_h - ih) // 2
                bx = max(0, min(img_w - box_w, ix - diff_x))
                by = max(0, min(img_h - box_h, iy - diff_y))

                box_fill = (14, 16, 22) if opacity_val >= 235 else (14, 16, 22, opacity_val)
                # Clean neutral dark border (no cyan outline)
                draw.rectangle(
                    [bx, by, bx + box_w, by + box_h],
                    fill=box_fill,
                    outline=(60, 68, 85, 180),
                    width=1
                )

                cur_y = by + (box_h - total_th) // 2
                for line in lines:
                    l_bbox = draw.textbbox((0, 0), line, font=font)
                    lw = l_bbox[2] - l_bbox[0]
                    tx = bx + (box_w - lw) // 2

                    draw.text((tx + 1, cur_y + 1), line, font=font, fill=(0, 0, 0, 240))
                    draw.text((tx, cur_y), line, font=font, fill="#ffffff")
                    cur_y += line_height

            return pil_img

    def wrap_text(self, text, font, max_width, draw):
        words = text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines if lines else [text]

    def update_telemetry_ui(self):
        self.lbl_status_fps.configure(text=f"FPS: {self.current_fps:.1f}")
        self.lbl_status_ocr.configure(text=f"OCR ({self.translator.current_engine_name}): {self.translator.last_ocr_ms:.0f}ms")
        self.lbl_status_trans.configure(text=f"Trans: {self.translator.last_trans_ms:.0f}ms (Hits: {self.translator.cache_hits})")
        active_cnt = len(self.tracker.tracks)
        self.lbl_status_boxes.configure(text=f"Active: {active_cnt} box{'es' if active_cnt != 1 else ''}")

    def on_close(self):
        self.is_running = False
        self.video_manager.stop_capture()
        self.audio_manager.stop_passthrough()
        self.translator.save_cache()
        self.save_config()
        self.root.destroy()
