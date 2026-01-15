import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import threading
import time
import numpy as np
from video_manager import VideoManager
from translator import Translator

class LiveTranslateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live Translate Tool")
        self.root.geometry("1000x800")
        self.root.configure(bg="#1e1e1e")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 10))
        style.configure("TButton", background="#3e3e3e", foreground="#ffffff", borderwidth=0, font=("Segoe UI", 10))
        style.map("TButton", background=[("active", "#505050")])
        style.configure("TCombobox", fieldbackground="#3e3e3e", background="#3e3e3e", foreground="#ffffff", arrowcolor="#ffffff")

        self.video_manager = VideoManager()
        self.translator = Translator()
        
        self.is_running = True
        self.frame_count = 0
        self.last_ocr_time = 0
        self.current_translations = []
        self.ocr_interval = 0.5 # Increased frequency
        self.last_frame = None
        self.ocr_thread_running = False

        self.create_widgets()
        self.populate_devices()
        self.update_video()

    def create_widgets(self):
        top_bar = tk.Frame(self.root, bg="#252526", height=50)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        top_bar.pack_propagate(False)

        lbl_device = ttk.Label(top_bar, text="Video Source:")
        lbl_device.pack(side=tk.LEFT, padx=(10, 5), pady=10)

        self.combo_device = ttk.Combobox(top_bar, state="readonly", width=40)
        self.combo_device.pack(side=tk.LEFT, padx=5, pady=10)
        self.combo_device.bind("<<ComboboxSelected>>", self.on_device_selected)
        
        self.canvas_frame = tk.Frame(self.root, bg="#000000")
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def populate_devices(self):
        devices = self.video_manager.get_devices()
        if devices:
            self.combo_device['values'] = devices
            self.combo_device.current(0)
            self.on_device_selected(None)
        else:
            self.combo_device['values'] = [f"Camera {i}" for i in range(5)]
            self.combo_device.current(0)

    def on_device_selected(self, event):
        selection_index = self.combo_device.current()
        if selection_index >= 0:
            if not self.video_manager.start_capture(selection_index):
                messagebox.showerror("Error", f"Could not open device {selection_index}")

    def update_video(self):
        if not self.is_running:
            return

        ret, frame = self.video_manager.get_frame()
        if ret:
            self.last_frame = frame.copy()
            
            # --- Rendering ---
            # Convert BGR to RGB
            cv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Prepare image for Canvas
            # We might want to resize if the window is smaller/larger, but for now exact fit or simple resize
            # Getting canvas dimensions
            c_width = self.canvas.winfo_width()
            c_height = self.canvas.winfo_height()
            
            if c_width > 1 and c_height > 1:
                # Resize maintain aspect ratio
                h, w, _ = cv_image.shape
                scale = min(c_width/w, c_height/h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                cv_image = cv2.resize(cv_image, (new_w, new_h))
            
            # Draw Translations
            # To draw text with OpenCV for better performance before converting to PIL
            # Or draw on Canvas. Drawing on Canvas is slower for many items but allows better text styling.
            # Let's draw on the OpenCV image for simplicity and performance sync.
            
            self.draw_overlays(cv_image, scale if 'scale' in locals() else 1.0, frame)

            # Convert to PIL
            pil_image = Image.fromarray(cv_image)
            imgtk = ImageTk.PhotoImage(image=pil_image)
            
            self.canvas.create_image(c_width//2, c_height//2, image=imgtk, anchor=tk.CENTER)
            self.canvas.image = imgtk # Keep reference

            # --- OCR Trigger ---
            current_time = time.time()
            if current_time - self.last_ocr_time > self.ocr_interval and not self.ocr_thread_running:
                self.trigger_ocr()
        
        self.root.after(10, self.update_video) # Loop ~100fps max attempt

    def trigger_ocr(self):
        if self.last_frame is None:
            return

        self.ocr_thread_running = True
        self.last_ocr_time = time.time()
        
        # Run in thread
        thread = threading.Thread(target=self.run_ocr_task, args=(self.last_frame.copy(),))
        thread.daemon = True
        thread.start()

    def run_ocr_task(self, frame):
        try:
            results = self.translator.process_frame(frame)
            self.current_translations = results
        except Exception:
            pass
        finally:
            self.ocr_thread_running = False

    def draw_overlays(self, img, scale, original_frame):
        # Draw detected text overlays
        # Note: 'current_translations' contains coords from original frame resolution
        
        for item in self.current_translations:
            if not item.get('translated'):
                continue
                
            x = int(item['x'] * scale)
            y = int(item['y'] * scale)
            w = int(item['w'] * scale)
            h = int(item['h'] * scale)
            
            text = item['translated']
            
            # Smart Background Color Extraction
            # Get the ROI from the original frame (not the resized one if possible, but img is resized rgb)
            # It's cleaner to sample from the resized/displayed img if we want to match visualization
            # But 'x' here is scaled.
            
            # Ensure coords are safely within bounds
            H, W, _ = img.shape
            x = max(0, min(x, W-1))
            y = max(0, min(y, H-1))
            w = max(1, min(w, W-x))
            h = max(1, min(h, H-y))

            roi = img[y:y+h, x:x+w]
            if roi.size > 0:
                # Calculate average color of the ROI
                avg_color_per_row = np.average(roi, axis=0)
                avg_color = np.average(avg_color_per_row, axis=0)
                # avg_color is RGB float
                
                # To make it readable, we might need to adjust slightly or just use it as bg
                bg_color = (int(avg_color[0]), int(avg_color[1]), int(avg_color[2]))
            else:
                bg_color = (20, 20, 20)            

            # Draw solid background with sampled color
            cv2.rectangle(img, (x, y), (x + w, y + h), bg_color, -1)
            
            # Determine text color (black or white) based on background brightness
            brightness = (bg_color[0] * 299 + bg_color[1] * 587 + bg_color[2] * 114) / 1000
            text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
            
            # Add text
            # Calculate font scale based on height
            font_scale = h / 30.0 
            if font_scale < 0.4: font_scale = 0.4
            
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)[0]
            text_x = x + (w - text_size[0]) // 2
            text_y = y + (h + text_size[1]) // 2
            
            # Ensure text stays within box (simple check)
            if text_x < x: text_x = x
            
            cv2.putText(img, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1, cv2.LINE_AA)

    def on_close(self):
        self.is_running = False
        self.video_manager.stop_capture()
        self.root.destroy()
