import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Import our modified LiveTranslateApp components
from gui import HardwareMonitor

print("--- 1. Testing HardwareMonitor ---")
hw = HardwareMonitor()
import time
time.sleep(1.2)
stats = hw.get_stats_formatted()
print("Formatted HW stats:", stats)
assert "CPU:" in stats, "CPU stat missing"
hw.stop()
print("HardwareMonitor test PASSED!")

print("\n--- 2. Testing Box & Seamless Rendering with Overlapping Detections ---")
# Create mock game frame with a menu
frame_bgr = np.full((720, 1280, 3), (40, 35, 30), dtype=np.uint8)
# Add some parchment texture/content
cv2.rectangle(frame_bgr, (400, 150), (880, 550), (60, 52, 45), -1)
cv2.rectangle(frame_bgr, (410, 160), (870, 540), (210, 195, 170), -1) # Parchment paper

# Mock detections with overlapping items, partial duplicates, and tight adjacent menu items
test_items = [
    # Top title
    {'x': 520, 'y': 180, 'w': 240, 'h': 40, 'translated': 'PAUSE MENU', 'text': 'ポーズメニュー'},
    # Duplicate detection on title
    {'x': 525, 'y': 182, 'w': 230, 'h': 38, 'translated': 'PAUSE MENU', 'text': 'ポーズメニュー'},
    # Tightly spaced vertical menu list (6px gaps)
    {'x': 560, 'y': 240, 'w': 160, 'h': 32, 'translated': 'Continue Playing', 'text': 'ゲームを再開'},
    {'x': 560, 'y': 278, 'w': 160, 'h': 32, 'translated': 'Save Game', 'text': 'セーブ'},
    {'x': 560, 'y': 316, 'w': 160, 'h': 32, 'translated': 'Load Game', 'text': 'ロード'},
    {'x': 560, 'y': 354, 'w': 160, 'h': 32, 'translated': 'Audio & Video Options', 'text': '設定'},
    {'x': 560, 'y': 392, 'w': 160, 'h': 32, 'translated': 'Quit to Desktop', 'text': 'ゲームを終了'},
]

# Mock a mini GUI app instance to test draw_overlays
class MockApp:
    def __init__(self):
        self.font_size = 18
        self._font_cache = {}
        self.hw_stats_enabled = type('obj', (), {'get': lambda: True})
        self.overlay_mode_var = type('obj', (), {'get': lambda: "box"})
        self.opacity_var = type('obj', (), {'get': lambda: 1.0})
        self.translator = type('obj', (), {'is_japanese': lambda self, t: False})()

    # Bind methods from gui.LiveTranslateApp
    from gui import LiveTranslateApp
    deduplicate_items = LiveTranslateApp.deduplicate_items
    resolve_box_collisions = LiveTranslateApp.resolve_box_collisions
    resolve_seamless_collisions = LiveTranslateApp.resolve_seamless_collisions
    draw_overlays = LiveTranslateApp.draw_overlays
    wrap_text = LiveTranslateApp.wrap_text
    get_font = LiveTranslateApp.get_font
    sample_background_smart = LiveTranslateApp.sample_background_smart

mock = MockApp()

# Test Box mode
mock.overlay_mode_var.get = lambda: "box"
box_img = mock.draw_overlays(frame_bgr, 1.0, test_items)
box_out_path = "scratch/test_box_result.png"
box_img.save(box_out_path)
print(f"Box mode rendered and saved to {box_out_path}")

# Test Seamless mode
mock.overlay_mode_var.get = lambda: "seamless"
seamless_img = mock.draw_overlays(frame_bgr, 1.0, test_items)
seamless_out_path = "scratch/test_seamless_result.png"
seamless_img.save(seamless_out_path)
print(f"Seamless mode rendered and saved to {seamless_out_path}")

print("All tests completed successfully!")
