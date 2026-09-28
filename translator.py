import os
import json
import time
import re
import cv2
import threading
from deep_translator import GoogleTranslator, MyMemoryTranslator
from deep_translator.exceptions import TooManyRequests
import onnxruntime as ort
from rapidocr_onnxruntime import RapidOCR

# Japanese Unicode Ranges:
# Hiragana: 3040-309F
# Katakana: 30A0-30FF
# Kanji: 4E00-9FAF
JAPANESE_REGEX = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')

def detect_gpu_capabilities():
    """
    Detects GPU capabilities across DirectML and PyTorch CUDA.
    """
    providers = ort.get_available_providers()
    has_dml = "DmlExecutionProvider" in providers
    
    cuda_status = "DirectML GPU (NVIDIA RTX 5070 Ti)" if has_dml else "CPU Execution"

    # Test PyTorch CUDA
    torch_cuda = False
    try:
        import torch
        if torch.cuda.is_available():
            x = torch.zeros(1, device='cuda')
            _ = x + 1
            dev_name = torch.cuda.get_device_name(0)
            cuda_status = f"CUDA GPU ({dev_name})"
            torch_cuda = True
    except Exception:
        pass

    return has_dml, torch_cuda, cuda_status

class ArgosWrapper:
    """
    100% Local Neural Translation using Argos Translate.
    Requires no internet connection, has 0ms network latency, and cannot be rate-limited.
    """
    def __init__(self):
        self.translation = None
        self.is_ready = False
        try:
            import argostranslate.translate
            installed = argostranslate.translate.get_installed_languages()
            ja = next((l for l in installed if l.code == 'ja'), None)
            en = next((l for l in installed if l.code == 'en'), None)
            if ja and en:
                self.translation = ja.get_translation(en)
                self.is_ready = True
                print("[Translator] Local Argos Translate (ja -> en) ready.")
            else:
                print("[Translator] Argos Translate: Japanese language package not found.")
        except Exception as e:
            print(f"[Translator] Local Argos Translate initialization error: {e}")

    def translate(self, text):
        if not self.is_ready or not self.translation or not text:
            return None
        try:
            return self.translation.translate(text)
        except Exception as e:
            print(f"[Translator] Argos error: {e}")
            return None

class Translator:
    def __init__(self, default_engine='rapidocr', default_provider='auto', cache_file="translations.json"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(base_dir, cache_file) if not os.path.isabs(cache_file) else cache_file
        self.cache_lock = threading.Lock()
        self.translation_cache = {}
        self.normalized_cache = {}
        self.load_cache()

        # Engine states
        self.current_engine_name = default_engine
        self.rapid_engine = None
        self.easy_engine = None
        
        # Translation provider states
        self.current_provider = default_provider # 'auto', 'offline', 'google', 'mymemory'
        self.argos = ArgosWrapper()

        # Check GPU capabilities
        self.has_dml, self.torch_cuda, self.cuda_status = detect_gpu_capabilities()
        print(f"[Translator] Hardware Status: {self.cuda_status}")

        # Performance & telemetry
        self.last_ocr_ms = 0.0
        self.last_trans_ms = 0.0
        self.cache_hits = 0
        self.api_calls = 0

        # Rate limiting & cooldown state
        self.google_rate_limited = False
        self.last_rate_limit_time = 0.0
        self._logged_rate_limit = False
        self._last_google_request_time = 0.0
        self._last_disk_save = 0.0
        self._pending_failed_cooldown = {}

        # Downsample scale for high-speed OCR (e.g., 960px max width for 3x speedup)
        # Full 1080p resolution support: preserves fine text in books, journals, and dialogue
        self.max_ocr_width = 1920

        # Initialize default OCR engine
        self.init_engine(default_engine)

    def init_engine(self, engine_name):
        engine_name = engine_name.lower()
        if engine_name == 'rapidocr':
            if self.rapid_engine is None:
                use_dml = self.has_dml
                base_dir = os.path.dirname(os.path.abspath(__file__))
                jp_model = os.path.join(base_dir, "japan_rec.onnx")
                jp_dict = os.path.join(base_dir, "japan_dict.txt")
                if os.path.exists(jp_model) and os.path.exists(jp_dict):
                    print(f"[Translator] Initializing RapidOCR with dedicated Japanese PP-OCR model (DirectML GPU={use_dml})...")
                    try:
                        self.rapid_engine = RapidOCR(rec_model_path=jp_model, rec_keys_path=jp_dict, use_dml=use_dml)
                    except Exception as e:
                        print(f"[Translator] DirectML GPU init failed: {e}. Falling back to CPU...")
                        self.rapid_engine = RapidOCR(rec_model_path=jp_model, rec_keys_path=jp_dict, use_dml=False)
                else:
                    print(f"[Translator] Initializing RapidOCR (DirectML GPU={use_dml})...")
                    try:
                        self.rapid_engine = RapidOCR(use_dml=use_dml)
                    except Exception as e:
                        print(f"[Translator] DirectML init failed: {e}. Falling back to standard RapidOCR...")
                        self.rapid_engine = RapidOCR(use_dml=False)
                print("[Translator] RapidOCR ready.")
            self.current_engine_name = 'rapidocr'
        elif engine_name == 'easyocr':
            if self.easy_engine is None:
                import easyocr
                use_gpu = self.torch_cuda
                print(f"[Translator] Initializing EasyOCR (GPU={use_gpu})...")
                try:
                    self.easy_engine = easyocr.Reader(['ja', 'en'], gpu=use_gpu)
                except Exception as e:
                    print(f"[Translator] EasyOCR GPU init failed: {e}. Falling back to CPU...")
                    self.easy_engine = easyocr.Reader(['ja', 'en'], gpu=False)
                print("[Translator] EasyOCR ready.")
            self.current_engine_name = 'easyocr'

    def set_engine(self, engine_name):
        self.init_engine(engine_name)

    def set_provider(self, provider_name):
        self.current_provider = provider_name.lower()

    def _normalize_key(self, text):
        if not text:
            return ""
        # Strip all punctuation, quotes, dashes, and game-specific decorative flourishes
        t = re.sub(r'[・。\.、\s\-_:：【】「」『』\[\]\(\)（）ー―=＝%#f§*~]', '', text)
        small_to_large = str.maketrans('ァィゥェォッャュョヮ', 'アイウエオツヤユヨワ')
        return t.translate(small_to_large)

    def _rebuild_normalized_cache(self):
        with self.cache_lock:
            self.normalized_cache = {self._normalize_key(k): v for k, v in self.translation_cache.items()}

    def load_cache(self):
        # 1. First, load user/disk translations
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    disk_cache = json.load(f)
                    with self.cache_lock:
                        self.translation_cache = disk_cache
            except Exception as e:
                print(f"[Translator] Error loading cache file: {e}")

        # Purge known bad machine-translation artifacts from previous sessions
        bad_keys = ["豪", "尊", "女士長"]
        with self.cache_lock:
            for bk in bad_keys:
                if bk in self.translation_cache and self.translation_cache[bk] in ("Australia", "Zun", "Female"):
                    del self.translation_cache[bk]

        # 2. Authoritative Elder Scrolls IV: Oblivion canonical terms ALWAYS take highest precedence
        try:
            from oblivion_dict import get_oblivion_dictionary
            ob_dict = get_oblivion_dictionary()
            with self.cache_lock:
                self.translation_cache.update(ob_dict)
            print(f"[Translator] Loaded {len(ob_dict)} canonical Elder Scrolls IV: Oblivion translations (authoritative).")
        except Exception as e:
            print(f"[Translator] Oblivion dictionary load notice: {e}")

        print(f"[Translator] Cache populated: total {len(self.translation_cache)} entries ready.")
        self._rebuild_normalized_cache()

    def save_cache(self):
        try:
            from oblivion_dict import get_oblivion_dictionary
            ob_dict = get_oblivion_dictionary()
            with self.cache_lock:
                # Guarantee canonical terms are never overwritten by machine translation
                self.translation_cache.update(ob_dict)
                data = dict(self.translation_cache)

            # Purge bad artifacts before persisting
            if "豪" in data and data["豪"] == "Australia":
                data["豪"] = "Champion"
            if "尊" in data and data["尊"] == "Zun":
                data["尊"] = "Rumors"
            if "女士長" in data and data["女士長"] == "Female":
                data["女士長"] = "Blademistress"

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._rebuild_normalized_cache()
            # Also mirror to root translations.json if applicable
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(self.cache_file)))
            root_cache = os.path.join(parent_dir, "translations.json")
            if os.path.normpath(root_cache) != os.path.normpath(self.cache_file) and os.path.exists(parent_dir):
                with open(root_cache, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Translator] Error saving cache: {e}")

    def schedule_auto_save(self):
        now = time.time()
        if now - self._last_disk_save > 2.0:
            self._last_disk_save = now
            threading.Thread(target=self.save_cache, daemon=True).start()

    def is_japanese(self, text):
        return bool(JAPANESE_REGEX.search(text))

    def is_ignorable_noise(self, text):
        t = text.strip()
        if len(t) <= 1 and not self.is_japanese(t):
            return True
        if re.match(r'^(RS|LS|LT|RT|LB|RB)[\}\]>\)]?$', t, re.IGNORECASE):
            return True
        if re.match(r'^[0-9\s\.,:\-_=+*#~/\\]+$', t):
            return True
        return False

    def extract_text(self, frame, min_conf=0.3):
        """
        Runs the selected OCR engine with GPU acceleration and resolution scaling.
        Scales coordinates back up to original frame resolution seamlessly.
        """
        if frame is None:
            return []

        start_time = time.perf_counter()
        detections = []

        # Downsample large video frames for 3x OCR speedup
        h, w = frame.shape[:2]
        if w > self.max_ocr_width:
            ocr_scale = self.max_ocr_width / float(w)
            target_h = int(h * ocr_scale)
            ocr_frame = cv2.resize(frame, (self.max_ocr_width, target_h), interpolation=cv2.INTER_AREA)
        else:
            ocr_scale = 1.0
            ocr_frame = frame

        try:
            if self.current_engine_name == 'rapidocr':
                if self.rapid_engine is None:
                    self.init_engine('rapidocr')
                res, _ = self.rapid_engine(ocr_frame)
                if res:
                    for item in res:
                        box, text, score = item[0], item[1], float(item[2])
                        if score < min_conf:
                            continue
                        text = text.strip()
                        if not text:
                            continue
                        xs = [p[0] for p in box]
                        ys = [p[1] for p in box]
                        # Scale coordinates back to original video resolution
                        x_min = int(min(xs) / ocr_scale)
                        x_max = int(max(xs) / ocr_scale)
                        y_min = int(min(ys) / ocr_scale)
                        y_max = int(max(ys) / ocr_scale)
                        w_box = max(1, x_max - x_min)
                        h_box = max(1, y_max - y_min)
                        detections.append({
                            'text': text,
                            'x': x_min,
                            'y': y_min,
                            'w': w_box,
                            'h': h_box,
                            'conf': score
                        })
            else:
                if self.easy_engine is None:
                    self.init_engine('easyocr')
                results = self.easy_engine.readtext(ocr_frame, paragraph=False)
                for (bbox, text, prob) in results:
                    prob = float(prob)
                    if prob < min_conf:
                        continue
                    text = text.strip()
                    if not text:
                        continue
                    (tl, tr, br, bl) = bbox
                    x = int(tl[0] / ocr_scale)
                    y = int(tl[1] / ocr_scale)
                    w_box = max(1, int((br[0] - tl[0]) / ocr_scale))
                    h_box = max(1, int((br[1] - tl[1]) / ocr_scale))
                    detections.append({
                        'text': text,
                        'x': x,
                        'y': y,
                        'w': w_box,
                        'h': h_box,
                        'conf': prob
                    })
        except Exception as e:
            print(f"[Translator] OCR Exception ({self.current_engine_name}): {e}")

        self.last_ocr_ms = (time.perf_counter() - start_time) * 1000.0
        return detections

    def merge_detections(self, detections, max_x_gap=65, y_overlap_ratio=0.55):
        if not detections or len(detections) <= 1:
            return detections

        # Pass 1: Horizontal line merging (combine adjacent characters/words on the same line)
        dets = sorted(detections, key=lambda d: (d['y'], d['x']))
        merged = []
        used = [False] * len(dets)

        for i in range(len(dets)):
            if used[i]:
                continue
            cur = dict(dets[i])
            used[i] = True
            changed = True
            while changed:
                changed = False
                for j in range(len(dets)):
                    if used[j]:
                        continue
                    cand = dets[j]
                    h_min = min(cur['h'], cand['h'])
                    y_diff = abs(cur['y'] - cand['y'])
                    if y_diff < h_min * y_overlap_ratio:
                        cur_right = cur['x'] + cur['w']
                        cand_right = cand['x'] + cand['w']
                        gap = max(0, max(cand['x'] - cur_right, cur['x'] - cand_right))
                        if gap <= max_x_gap:
                            nx = min(cur['x'], cand['x'])
                            ny = min(cur['y'], cand['y'])
                            nw = max(cur_right, cand_right) - nx
                            nh = max(cur['y'] + cur['h'], cand['y'] + cand['h']) - ny
                            is_ja = self.is_japanese(cur['text'] + cand['text'])
                            sep = '' if is_ja else ' '
                            if cur['x'] <= cand['x']:
                                cur['text'] = cur['text'] + sep + cand['text']
                            else:
                                cur['text'] = cand['text'] + sep + cur['text']
                            cur['x'], cur['y'], cur['w'], cur['h'] = nx, ny, nw, nh
                            cur['conf'] = (cur['conf'] + cand['conf']) / 2.0
                            used[j] = True
                            changed = True
            merged.append(cur)

        # Pass 2: Vertical paragraph merging for multi-line text (books, quest journals, dialogue subtitles)
        # Stitches wrapped lines into a single complete sentence/paragraph for natural translation.
        # Leaves individual short menu buttons (<= 5 chars) untouched so buttons remain separate.
        if len(merged) > 1:
            para_merged = []
            lines = sorted(merged, key=lambda d: (d['y'], d['x']))
            used_p = [False] * len(lines)
            for i in range(len(lines)):
                if used_p[i]:
                    continue
                cur_p = dict(lines[i])
                used_p[i] = True
                while True:
                    best_next = None
                    best_gap = 999999
                    cur_bottom = cur_p['y'] + cur_p['h']
                    cur_right = cur_p['x'] + cur_p['w']

                    for j in range(len(lines)):
                        if used_p[j]:
                            continue
                        cand = lines[j]
                        cand_right = cand['x'] + cand['w']

                        vert_gap = cand['y'] - cur_bottom
                        line_ref_h = cur_p.get('line_h', min(cur_p['h'], cand['h']))
                        # Paragraph line spacing in books and dialogue subtitles is tight (2-14px)
                        # Standalone menu buttons are separated by large gaps (>25px) and must never merge
                        max_allowed_gap = max(14, int(line_ref_h * 0.50))
                        if 0 <= vert_gap <= max_allowed_gap:
                            # Never merge canonical game terms or menu buttons
                            if self.resolve_game_term(cur_p['text']) is not None or self.resolve_game_term(cand['text']) is not None:
                                continue
                            # Standalone short items with gap are separate buttons
                            if (len(cur_p['text']) <= 8 and vert_gap > 8) or (len(cand['text']) <= 8 and vert_gap > 8):
                                continue

                            x_overlap = min(cur_right, cand_right) - max(cur_p['x'], cand['x'])
                            min_w = min(cur_p['w'], cand['w'])
                            is_aligned = (x_overlap > min_w * 0.30) or (abs(cur_p['x'] - cand['x']) < 65)
                            if is_aligned:
                                if vert_gap < best_gap:
                                    best_gap = vert_gap
                                    best_next = (j, cand)

                    if best_next is not None:
                        j_idx, cand = best_next
                        nx = min(cur_p['x'], cand['x'])
                        ny = cur_p['y']
                        nw = max(cur_right, cand['x'] + cand['w']) - nx
                        nh = (cand['y'] + cand['h']) - ny
                        is_ja = self.is_japanese(cur_p['text'] + cand['text'])
                        sep = '' if is_ja else ' '
                        cur_p['text'] = cur_p['text'] + sep + cand['text']
                        cur_p['x'], cur_p['y'], cur_p['w'], cur_p['h'] = nx, ny, nw, nh
                        cur_p['line_h'] = min(cur_p.get('line_h', cur_p['h']), cand['h'])
                        cur_p['conf'] = (cur_p['conf'] + cand['conf']) / 2.0
                        used_p[j_idx] = True
                    else:
                        break
                para_merged.append(cur_p)
            return para_merged

        return merged

    def filter_detections(self, detections, mode='ja'):
        filtered = []
        for det in detections:
            text = det['text'].strip()
            if self.is_ignorable_noise(text):
                continue
            if mode == 'ja' and not self.is_japanese(text):
                continue
            filtered.append(det)
        return filtered

    def resolve_game_term(self, text):
        """
        Specialized local resolver for The Elder Scrolls IV: Oblivion & RPG gaming terms.
        Resolves:
        1. Exact cache matches (0ms)
        2. Fast normalized kana & dot-stripped lookup (O(1))
        3. Fuzzy matching against Oblivion dictionary
        4. Stripped brackets, quotes, dashes, and menu flourishes (e.g. 'ーポーズ中ー' -> 'Paused')
        5. Key-Value pairs with colons/spaces
        6. Quantities / Hotkeys
        """
        if not text:
            return None

        # 1. Exact match in cache
        with self.cache_lock:
            if text in self.translation_cache:
                return self.translation_cache[text]

        # 2. Fast normalized kana & dot-stripped lookup (O(1))
        nq = self._normalize_key(text)
        if nq and nq in self.normalized_cache:
            return self.normalized_cache[nq]

        # 3. Fuzzy matching against Oblivion dictionary (handles minor OCR kana/dakuten misreads)
        if len(nq) >= 3:
            import difflib
            for k_norm, trans in self.normalized_cache.items():
                if abs(len(nq) - len(k_norm)) <= 2:
                    if difflib.SequenceMatcher(None, nq, k_norm).ratio() >= 0.72:
                        return trans

        # 4. Stripped brackets / bullets / dashes / decorative menu flourishes
        trimmed = text.strip("【】「」『』[]()（）{}・■◆★▲- :：ー―=＝%#f§*~")
        trimmed_nospaces = re.sub(r'(?<=[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff])\s+(?=[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff])', '', trimmed)
        with self.cache_lock:
            if trimmed in self.translation_cache:
                trans = self.translation_cache[trimmed]
                if (text.startswith("【") and text.endswith("】")) or (text.startswith("[") and text.endswith("]")):
                    return f"[{trans}]"
                return trans
            if trimmed_nospaces in self.translation_cache:
                trans = self.translation_cache[trimmed_nospaces]
                if (text.startswith("【") and text.endswith("】")) or (text.startswith("[") and text.endswith("]")):
                    return f"[{trans}]"
                return trans

        # 5. Key-Value stat patterns: e.g. "腕力: 60" or "ゴールド 250" or "防御力: 18"
        m_stat = re.match(r'^([^:：\s]+)\s*[:：]\s*(.+)$', text)
        if m_stat:
            key_part = m_stat.group(1).strip()
            val_part = m_stat.group(2).strip()
            key_clean = re.sub(r'(?<=[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff])\s+(?=[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff])', '', key_part)
            with self.cache_lock:
                if key_part in self.translation_cache:
                    return f"{self.translation_cache[key_part]}: {val_part}"
                if key_clean in self.translation_cache:
                    return f"{self.translation_cache[key_clean]}: {val_part}"

        # 6. Quantity / Hotkey / Count suffix: e.g. "鉄のロングソード (1)" or "ロックピック x3" or "開錠 [E]"
        m_qty = re.match(r'^(.+?)\s*([\(（\[].+?[\)）\]]|\s*x\s*\d+|\s*\d+)$', text)
        if m_qty:
            item_part = m_qty.group(1).strip()
            suffix_part = m_qty.group(2).strip()
            item_clean = re.sub(r'(?<=[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff])\s+(?=[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff])', '', item_part)
            with self.cache_lock:
                if item_part in self.translation_cache:
                    return f"{self.translation_cache[item_part]} {suffix_part}"
                if item_clean in self.translation_cache:
                    return f"{self.translation_cache[item_clean]} {suffix_part}"

        # 7. Compound Material + Equipment resolver: e.g. "鉄のロングソード", "デイドラのクレイモア"
        materials = [
            ("錆びた", "Rusted"), ("鉄", "Iron"), ("鋼鉄", "Steel"), ("銀", "Silver"),
            ("ドワーフ", "Dwarven"), ("オーク", "Orcish"), ("エルフ", "Elven"),
            ("グラス", "Glass"), ("黒檀", "Ebony"), ("デイドラ", "Daedric"),
            ("毛皮", "Fur"), ("革", "Leather"), ("鎖帷子", "Chainmail"),
            ("スケール", "Scale"), ("ミスリル", "Mithril"), ("琥珀", "Amber"), ("狂気", "Madness")
        ]
        equipment = [
            ("ロングソード", "Longsword"), ("ショートソード", "Shortsword"), ("ダガー", "Dagger"),
            ("クレイモア", "Claymore"), ("片手斧", "War Axe"), ("バトルアックス", "Battleaxe"),
            ("両手斧", "Battleaxe"), ("メイス", "Mace"), ("ウォーハンマー", "Warhammer"),
            ("戦槌", "Warhammer"), ("弓", "Bow"), ("矢", "Arrow"),
            ("キュイラス", "Cuirass"), ("鎧", "Cuirass"), ("兜", "Helmet"),
            ("ヘルメット", "Helmet"), ("グリーヴ", "Greaves"), ("具足", "Greaves"),
            ("脛当て", "Greaves"), ("篭手", "Gauntlets"), ("ガントレット", "Gauntlets"),
            ("ブーツ", "Boots"), ("靴", "Boots"), ("盾", "Shield"), ("シールド", "Shield")
        ]
        for m_ja, m_en in materials:
            for eq_ja, eq_en in equipment:
                if text == f"{m_ja}の{eq_ja}" or text == f"{m_ja}{eq_ja}":
                    return f"{m_en} {eq_en}"

        # 8. Strip trailing sentence punctuation: e.g. "敵が近くにいるため待機できません。"
        if text.endswith(("。", "！", "!", "？", "?")):
            stem = text[:-1]
            with self.cache_lock:
                if stem in self.translation_cache:
                    return self.translation_cache[stem]

        return None

    def translate_text(self, text, provider=None, source='auto', target='en'):
        text = text.strip()
        if not text:
            return ""

        # Normalize whitespace
        cache_key = re.sub(r'\s+', ' ', text)

        # Tier 1: Check Oblivion Game Term & Canonical Dictionary FIRST (0ms, 0 network, no rate-limits)
        resolved = self.resolve_game_term(text)
        if resolved:
            self.cache_hits += 1
            with self.cache_lock:
                self.translation_cache[cache_key] = resolved
            return resolved

        now = time.time()

        # Cooldown check: prevent hammering remote APIs for text that just failed
        if cache_key in self._pending_failed_cooldown:
            if now - self._pending_failed_cooldown[cache_key] < 8.0:
                if self.argos.is_ready:
                    argos_res = self.argos.translate(text)
                    if argos_res:
                        with self.cache_lock:
                            self.translation_cache[cache_key] = argos_res
                        self.schedule_auto_save()
                        return argos_res
                return text

        self.api_calls += 1
        active_provider = provider if provider else self.current_provider
        translated = None

        # Reset Google rate-limit cooldown after 300 seconds (5 minutes)
        if self.google_rate_limited and (now - self.last_rate_limit_time > 300):
            self.google_rate_limited = False

        # Tier 2: If Offline/Argos requested or Google is rate-limited, prioritize local Argos
        if active_provider in ('offline', 'argos') or (self.google_rate_limited and active_provider == 'auto'):
            if self.argos.is_ready:
                res = self.argos.translate(text)
                if res and res.strip():
                    translated = res.strip()

        # Tier 3: Attempt Google Translate if allowed, not rate-limited, and not offline-only
        if not translated and not self.google_rate_limited and active_provider in ('auto', 'google'):
            # Enforce 250ms spacing between Google requests to avoid bursting over limits
            if now - self._last_google_request_time < 0.25:
                time.sleep(0.25 - (now - self._last_google_request_time))
            self._last_google_request_time = time.time()
            try:
                res = GoogleTranslator(source=source, target=target).translate(text)
                if res and res.strip():
                    translated = res.strip()
            except Exception as e:
                err_msg = str(e).lower()
                is_rate_limit = (
                    isinstance(e, TooManyRequests)
                    or "too many requests" in err_msg
                    or "429" in err_msg
                    or type(e).__name__ == "TooManyRequests"
                )
                if is_rate_limit:
                    if not self._logged_rate_limit:
                        print("[Translator] Google rate limit reached. Switched seamlessly to local offline Argos Translate & Oblivion dictionary.")
                        self._logged_rate_limit = True
                    self.google_rate_limited = True
                    self.last_rate_limit_time = time.time()
                else:
                    print(f"[Translator] Google translation error: {e}")

        # Tier 4: Fallback to local offline Argos Translate if Google failed or was rate-limited
        if not translated and self.argos.is_ready:
            try:
                res = self.argos.translate(text)
                if res and res.strip():
                    translated = res.strip()
            except Exception as e:
                print(f"[Translator] Argos fallback error: {e}")

        # Tier 5: Fallback to MyMemory if still unresolved
        if not translated and not self.google_rate_limited:
            try:
                src_lang = 'japanese' if (source == 'ja' or self.is_japanese(text)) else 'auto'
                tgt_lang = 'english' if target == 'en' else target
                res = MyMemoryTranslator(source=src_lang, target=tgt_lang).translate(text)
                if res and res.strip():
                    translated = res.strip()
            except Exception:
                pass

        if translated:
            with self.cache_lock:
                self.translation_cache[cache_key] = translated
            self.schedule_auto_save()
            return translated
        else:
            self._pending_failed_cooldown[cache_key] = now
            return text

    def process_frame(self, frame, min_conf=0.3, filter_mode='ja', merge_lines=True):
        if frame is None:
            return []

        raw_detections = self.extract_text(frame, min_conf=min_conf)

        if merge_lines:
            detections = self.merge_detections(raw_detections)
        else:
            detections = raw_detections

        filtered_detections = self.filter_detections(detections, mode=filter_mode)

        start_trans = time.perf_counter()
        results = []
        for det in filtered_detections:
            translated = self.translate_text(det['text'])
            det_copy = dict(det)
            det_copy['translated'] = translated
            results.append(det_copy)

        self.last_trans_ms = (time.perf_counter() - start_trans) * 1000.0
        return results
