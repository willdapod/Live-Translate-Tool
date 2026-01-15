import pytesseract
from deep_translator import GoogleTranslator
import cv2
import numpy as np
import threading
import json

from langdetect import detect, LangDetectException
import re

class Translator:
    def __init__(self, tesseract_cmd=None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        self.translation_cache = {}
        
    def extract_text(self, frame):
        if frame is None:
            return []

        # Optimization: Resize for faster OCR if image is huge
        # But keep it large enough for text detection.
        # Max width 1000 seems reasonable for speed/quality balance.
        height, width = frame.shape[:2]
        max_dim = 1000
        scale_ratio = 1.0
        
        proc_frame = frame
        if width > max_dim or height > max_dim:
            if width > height:
                scale_ratio = max_dim / width
            else:
                scale_ratio = max_dim / height
            
            new_w = int(width * scale_ratio)
            new_h = int(height * scale_ratio)
            proc_frame = cv2.resize(frame, (new_w, new_h))

        rgb_frame = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB)
        
        # Using script/Japanese for better Japanese detection
        # psm 6 (assume linear text) or 3 (auto) might be better depending on game UI
        # We will stick to default for now but could tune config.
        data = pytesseract.image_to_data(rgb_frame, lang='script/Japanese', output_type=pytesseract.Output.DICT)
        
        results = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > 40: # Increase confidence threshold
                text = data['text'][i].strip()
                if text:
                    # Strict Japanese Check
                    if not self.contains_japanese(text):
                        continue

                    # Scale coordinates back to original frame size
                    x = int(data['left'][i] / scale_ratio)
                    y = int(data['top'][i] / scale_ratio)
                    w = int(data['width'][i] / scale_ratio)
                    h = int(data['height'][i] / scale_ratio)

                    results.append({
                        'text': text,
                        'x': x,
                        'y': y,
                        'w': w,
                        'h': h
                    })
        return results

    def contains_japanese(self, text):
        # Checks for Hiragana, Katakana, or Kanji
        # Unicode Ranges:
        # Hiragana: 3040-309F
        # Katakana: 30A0-30FF
        # Kanji: 4E00-9FAF
        return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))

    def is_text_english(self, text):
        # We handle this via contains_japanese now, so this is redundant but kept for interface compatibility if needed
        return not self.contains_japanese(text)

    def translate_text(self, text, source='ja', target='en'):
        if not text:
            return ""
        
        if text in self.translation_cache:
            return self.translation_cache[text]

        try:
            translated = GoogleTranslator(source='auto', target=target).translate(text)
            self.translation_cache[text] = translated
            return translated
        except Exception as e:
            return text

    def process_frame(self, frame):
        detections = self.extract_text(frame)
        processed_results = []
        
        for det in detections:
            translated = self.translate_text(det['text'])
            det['translated'] = translated
            processed_results.append(det)
            
        return processed_results
