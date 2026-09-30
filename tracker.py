import time

class TextTracker:
    """
    Spatial & Temporal tracker for detected text boxes.
    Eliminates bounding box jitter, prevents overlay flickering across frame drops,
    and promptly clears text that is no longer on screen.
    """
    def __init__(self, iou_threshold=0.20, max_age_seconds=1.4):
        self.tracks = []
        self.iou_threshold = iou_threshold
        self.max_age_seconds = max_age_seconds
        self.next_id = 0

    def reset(self):
        self.tracks.clear()

    def update(self, detections):
        """
        detections: list of dicts with {'x', 'y', 'w', 'h', 'text', 'translated', 'conf'}
        Returns: list of active tracked objects to display
        """
        now = time.time()
        unmatched_detections = list(range(len(detections)))

        for t in self.tracks:
            t['updated_this_tick'] = False

        # Match existing tracks with new detections via IoU and Spatial/Text Proximity
        for t in self.tracks:
            best_score = 0.0
            best_idx = -1
            t_box = t['box']
            t_cx = t_box[0] + t_box[2] / 2.0
            t_cy = t_box[1] + t_box[3] / 2.0

            for i in unmatched_detections:
                det = detections[i]
                d_box = [det['x'], det['y'], det['w'], det['h']]
                iou = self.calculate_iou(t_box, d_box)

                d_cx = det['x'] + det['w'] / 2.0
                d_cy = det['y'] + det['h'] / 2.0
                dist = ((t_cx - d_cx)**2 + (t_cy - d_cy)**2) ** 0.5

                det_text_clean = det.get('text', '').replace(' ', '')
                t_text_clean = t.get('text', '').replace(' ', '')
                same_text = (det_text_clean == t_text_clean and len(det_text_clean) > 0)

                # Matching logic:
                # 1. If text is identical and center within bounding region -> strong match
                max_dim = max(det['w'], det['h'])
                if same_text and dist <= (max_dim * 1.5 + 45):
                    score = 0.85 + 0.15 * max(0.0, 1.0 - (dist / 100.0))
                # 2. Geometric IoU overlap
                elif iou >= self.iou_threshold:
                    score = iou
                # 3. Very close spatial center even if OCR text slightly differs
                elif dist < 30 and (iou > 0.05 or abs(t_box[1] - det['y']) < 15):
                    score = 0.35 + (0.3 if same_text else 0.0)
                else:
                    score = 0.0

                if score > best_score and score >= 0.20:
                    best_score = score
                    best_idx = i

            if best_idx >= 0:
                det = detections[best_idx]
                det_text_clean = det.get('text', '').replace(' ', '')
                t_text_clean = t.get('text', '').replace(' ', '')
                is_same = (det_text_clean == t_text_clean and len(det_text_clean) > 0)

                if is_same:
                    # Deadband coordinate stabilization:
                    # If bounding box moved <= 4 pixels, keep the smoothed coordinates.
                    # This eliminates micro-jitter completely and keeps rendering caches 100% warm.
                    dx = abs(t['box'][0] - det['x'])
                    dy = abs(t['box'][1] - det['y'])
                    dw = abs(t['box'][2] - det['w'])
                    dh = abs(t['box'][3] - det['h'])
                    if dx > 4 or dy > 4 or dw > 6 or dh > 6:
                        alpha = 0.70
                        t['box'][0] = int(alpha * t['box'][0] + (1 - alpha) * det['x'])
                        t['box'][1] = int(alpha * t['box'][1] + (1 - alpha) * det['y'])
                        t['box'][2] = int(alpha * t['box'][2] + (1 - alpha) * det['w'])
                        t['box'][3] = int(alpha * t['box'][3] + (1 - alpha) * det['h'])
                else:
                    # Text changed (dialogue moved to next line): snap coordinates immediately
                    t['box'] = [det['x'], det['y'], det['w'], det['h']]
                    t['text'] = det.get('text', '')

                if det.get('translated') and det['translated'].strip():
                    t['translated'] = det['translated']

                t['conf'] = det.get('conf', 1.0)
                t['hits'] = t.get('hits', 1) + 1
                t['last_seen'] = now
                t['updated_this_tick'] = True
                unmatched_detections.remove(best_idx)

        # Create new tracks for unmatched detections
        for i in unmatched_detections:
            det = detections[i]
            self.tracks.append({
                'id': self.next_id,
                'box': [det['x'], det['y'], det['w'], det['h']],
                'text': det.get('text', ''),
                'translated': det.get('translated', ''),
                'conf': det.get('conf', 1.0),
                'hits': 1,
                'last_seen': now,
                'updated_this_tick': True
            })
            self.next_id += 1

        # Prune expired tracks
        self.prune(now)
        return self.get_active(now)

    def prune(self, current_time=None):
        if current_time is None:
            current_time = time.time()
        # Discard any track not refreshed within max_age_seconds
        active = [
            t for t in self.tracks
            if (current_time - t['last_seen']) <= self.max_age_seconds
        ]
        # Deduplicate overlapping tracks (NMS)
        if len(active) > 1:
            active.sort(key=lambda t: (t.get('hits', 1), t['box'][2] * t['box'][3]), reverse=True)
            survivors = []
            for t in active:
                tb = t['box']
                area_t = tb[2] * tb[3]
                dup = False
                for s in survivors:
                    sb = s['box']
                    area_s = sb[2] * sb[3]
                    iou = self.calculate_iou(tb, sb)
                    if iou > 0.35:
                        dup = True
                        break
                    # Containment check
                    ox1 = max(tb[0], sb[0])
                    oy1 = max(tb[1], sb[1])
                    ox2 = min(tb[0] + tb[2], sb[0] + sb[2])
                    oy2 = min(tb[1] + tb[3], sb[1] + sb[3])
                    if ox2 > ox1 and oy2 > oy1:
                        inter = (ox2 - ox1) * (oy2 - oy1)
                        if area_t > 0 and area_s > 0 and (inter / float(min(area_t, area_s)) > 0.40):
                            dup = True
                            break
                if not dup:
                    survivors.append(t)
            self.tracks = survivors
        else:
            self.tracks = active

    def get_active(self, current_time=None):
        if current_time is None:
            current_time = time.time()
        self.prune(current_time)
        results = []
        for t in self.tracks:
            results.append({
                'id': t['id'],
                'x': t['box'][0],
                'y': t['box'][1],
                'w': t['box'][2],
                'h': t['box'][3],
                'text': t['text'],
                'translated': t['translated'],
                'conf': t.get('conf', 1.0),
                'hits': t.get('hits', 1),
                'last_seen': t['last_seen']
            })
        return results

    def calculate_iou(self, boxA, boxB):
        # box: [x, y, w, h]
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
        yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

        interW = max(0, xB - xA)
        interH = max(0, yB - yA)
        interArea = interW * interH

        boxAArea = boxA[2] * boxA[3]
        boxBArea = boxB[2] * boxB[3]

        unionArea = float(boxAArea + boxBArea - interArea)
        if unionArea <= 0:
            return 0.0

        return interArea / unionArea
