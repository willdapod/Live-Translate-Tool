import cv2
import sys
import os

# Add current directory to path so we can import translator
from translator import Translator

def debug_image(image_path):
    print(f"Testing image: {image_path}")
    frame = cv2.imread(image_path)
    if frame is None:
        print("Failed to load image")
        return

    translator = Translator()
    
    print("\n--- Processed Detections (EasyOCR via Translator) ---")
    detections = translator.extract_text(frame)
    for det in detections:
        print(det)

    print("\n--- Merged Detections ---")
    merged = translator.merge_detections(detections)
    for det in merged:
        print(det)


if __name__ == "__main__":
    # Use the path provided in metadata
    img_path = r"C:/Users/willd/.gemini/antigravity/brain/df4de95c-ecb8-4ad7-99a4-af6d731b53be/uploaded_image_1768518333308.png" 
    debug_image(img_path)
