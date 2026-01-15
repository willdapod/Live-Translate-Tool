import cv2
import numpy as np
import threading
import json
import re
from rapidocr_onnxruntime import RapidOCR
import argostranslate.translate

class Translator:
    def __init__(self, tesseract_cmd=None):
        # Initializing RapidOCR
        # det_model_path etc are used by default from the package.
        self.ocr_engine = RapidOCR()
        self.translation_cache = {}
        
    def extract_text(self, frame):
        if frame is None:
            return []

        # RapidOCR works natively with BGR images (or internally handles it),
        # but docs often say RGB. Let's convert to be safe, but it's much faster than Tesseract.
        # It also handles resizing internally usually, but we can pass raw frame.
        
        # Run OCR
        # result is a list of [box_points, text, confidence]
        # box_points is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        
        try:
            result, elapse = self.ocr_engine(frame)
        except Exception as e:
            print(f"OCR Exception: {e}")
            return []
            
        if not result:
            return []

        detections = []
        for item in result:
            # item structure: [dt_boxes, rec_res, score]
            # rec_res is text
            # score is confidence
            
            box_points = item[0]
            text = item[1]
            score = item[2]
            
            if score < 0.4: # Filter low confidence
                continue
                
            if not text:
                continue

            # Strict Japanese Check
            if not self.contains_japanese(text):
                continue
            
            # Convert 4 points to x, y, w, h bounding box
            xs = [p[0] for p in box_points]
            ys = [p[1] for p in box_points]
            x_min, x_max = int(min(xs)), int(max(xs))
            y_min, y_max = int(min(ys)), int(max(ys))
            
            w = x_max - x_min
            h = y_max - y_min
            
            detections.append({
                'text': text,
                'x': x_min,
                'y': y_min,
                'w': w,
                'h': h
            })
            
        return detections

    def contains_japanese(self, text):
        # Checks for Hiragana, Katakana, or Kanji
        # Unicode Ranges:
        # Hiragana: 3040-309F
        # Katakana: 30A0-30FF
        # Kanji: 4E00-9FAF
        return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))

    def translate_text(self, text, source='ja', target='en'):
        if not text:
            return ""
        
        if text in self.translation_cache:
            return self.translation_cache[text]

        try:
            # Argos Translate
            translated = argostranslate.translate.translate(text, source, target)
            self.translation_cache[text] = translated
            return translated
        except Exception:
            return text

    def process_frame(self, frame):
        detections = self.extract_text(frame)
        processed_results = []
        
        for det in detections:
            translated = self.translate_text(det['text'])
            det['translated'] = translated
            processed_results.append(det)
            
        return processed_results
