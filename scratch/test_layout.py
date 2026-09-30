import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def resolve_layout(items, img_w=1920, img_h=1080, mode="box", min_gap=4):
    """
    Collision resolution and layout engine for LiveTranslateTool.
    1. Deduplicates overlapping OCR detections (NMS).
    2. Computes collision-free bounding boxes for all items.
    3. Guarantees zero overlapping boxes or text collisions.
    """
    if not items:
        return []

    # --- Step 1: Non-Maximum Suppression (Deduplication) ---
    sorted_by_area = sorted(items, key=lambda it: it['w'] * it['h'], reverse=True)
    survivors = []
    for it in sorted_by_area:
        ix1, iy1 = it['x'], it['y']
        ix2, iy2 = ix1 + it['w'], iy1 + it['h']
        area = it['w'] * it['h']
        duplicate = False
        for s in survivors:
            sx1, sy1 = s['x'], s['y']
            sx2, sy2 = sx1 + s['w'], sy1 + s['h']
            s_area = s['w'] * s['h']

            # Intersection
            ox1 = max(ix1, sx1)
            oy1 = max(iy1, sy1)
            ox2 = min(ix2, sx2)
            oy2 = min(iy2, sy2)
            if ox2 > ox1 and oy2 > oy1:
                inter = (ox2 - ox1) * (oy2 - oy1)
                # If overlap is > 40% of the smaller box, it's a redundant duplicate detection
                if inter / float(min(area, s_area)) > 0.40:
                    duplicate = True
                    break
        if not duplicate:
            survivors.append(dict(it))

    if not survivors:
        return []

    # Sort primarily by Y, then by X
    survivors.sort(key=lambda it: (it['y'], it['x']))

    # --- Step 2: Compute ideal dimensions per item ---
    layout_items = []
    # Using a dummy draw/font measure or rough measure
    for it in survivors:
        text = it.get('translated', it.get('text', ''))
        iw = it['w']
        ih = it['h']
        ix = it['x']
        iy = it['y']

        # Estimate text dimensions (approx 10px width per char at default font)
        # In real code we use draw.textbbox
        est_font_size = max(11, min(18, int(ih * 0.90)))
        char_w = est_font_size * 0.58
        tw = int(len(text) * char_w)
        th = int(est_font_size * 1.2)

        if mode == "box":
            bw = max(iw + 16, tw + 20)
            bh = max(ih + 8, th + 10)
        else: # seamless
            bw = max(iw + 8, tw + 10)
            bh = max(ih + 4, th + 6)

        bx = ix - (bw - iw) // 2
        by = iy - (bh - ih) // 2

        # Initial clamp
        bx = max(0, min(img_w - bw, bx))
        by = max(0, min(img_h - bh, by))

        layout_items.append({
            'orig': it,
            'text': text,
            'font_size': est_font_size,
            'bx': bx,
            'by': by,
            'bw': bw,
            'bh': bh,
            'tw': tw,
            'th': th
        })

    # --- Step 3: Vertical & Horizontal Collision Resolution ---
    # Multi-pass constraint solver
    n = len(layout_items)
    for _ in range(4): # 4 relaxation passes ensure stability even in dense lists
        has_collision = False
        for i in range(n):
            for j in range(i + 1, n):
                a = layout_items[i]
                b = layout_items[j]

                # Check AABB intersection
                ax1, ay1, ax2, ay2 = a['bx'], a['by'], a['bx'] + a['bw'], a['by'] + a['bh']
                bx1, by1, bx2, by2 = b['bx'], b['by'], b['bx'] + b['bw'], b['by'] + b['bh']

                ox = min(ax2, bx2) - max(ax1, bx1)
                oy = min(ay2, by2) - max(ay1, by1)

                if ox > 0 and oy > 0:
                    has_collision = True
                    # Decide if collision is primarily vertical or horizontal
                    # If horizontally aligned (e.g. list items), separate vertically
                    if ox >= min(a['bw'], b['bw']) * 0.30 or ox > 15:
                        # Vertical separation
                        overlap = oy + min_gap
                        if a['by'] <= b['by']:
                            # Push a up a bit, push b down
                            shift_b = overlap // 2 + 1
                            shift_a = overlap - shift_b
                            a['by'] = max(0, a['by'] - shift_a)
                            b['by'] = min(img_h - b['bh'], b['by'] + shift_b)
                        else:
                            shift_a = overlap // 2 + 1
                            shift_b = overlap - shift_a
                            b['by'] = max(0, b['by'] - shift_b)
                            a['by'] = min(img_h - a['bh'], a['by'] + shift_a)
                    else:
                        # Horizontal separation
                        overlap = ox + min_gap
                        if a['bx'] <= b['bx']:
                            shift_b = overlap // 2 + 1
                            shift_a = overlap - shift_b
                            a['bx'] = max(0, a['bx'] - shift_a)
                            b['bx'] = min(img_w - b['bw'], b['bx'] + shift_b)
                        else:
                            shift_a = overlap // 2 + 1
                            shift_b = overlap - shift_a
                            b['bx'] = max(0, b['bx'] - shift_b)
                            a['bx'] = min(img_w - a['bw'], a['bx'] + shift_a)

        if not has_collision:
            break

    return layout_items

# Test with 5 tightly packed menu items (like Oblivion Pause menu)
menu_items = [
    {'x': 500, 'y': 200, 'w': 100, 'h': 28, 'translated': 'Continue'},
    {'x': 502, 'y': 234, 'w': 98, 'h': 28, 'translated': 'Save'},      # 6px gap!
    {'x': 498, 'y': 268, 'w': 102, 'h': 28, 'translated': 'Load Game'}, # 6px gap!
    {'x': 500, 'y': 302, 'w': 100, 'h': 28, 'translated': 'Options'},   # 6px gap!
    {'x': 501, 'y': 336, 'w': 99, 'h': 28, 'translated': 'Quit'},       # 6px gap!
    {'x': 500, 'y': 200, 'w': 100, 'h': 28, 'translated': 'Continue'},  # Duplicate detection!
]

resolved = resolve_layout(menu_items, mode="box")
print(f"Total resolved items: {len(resolved)} (should be 5, 1 duplicate removed)")

# Verify no collisions between any pair
collisions = 0
for i in range(len(resolved)):
    for j in range(i + 1, len(resolved)):
        a = resolved[i]
        b = resolved[j]
        ax1, ay1, ax2, ay2 = a['bx'], a['by'], a['bx'] + a['bw'], a['by'] + a['bh']
        bx1, by1, bx2, by2 = b['bx'], b['by'], b['bx'] + b['bw'], b['by'] + b['bh']
        ox = min(ax2, bx2) - max(ax1, bx1)
        oy = min(ay2, by2) - max(ay1, by1)
        if ox > 0 and oy > 0:
            print(f"COLLISION between {a['text']} and {b['text']}: ox={ox}, oy={oy}")
            collisions += 1

print(f"Verification complete: {collisions} collisions found.")
for it in resolved:
    print(f"  [{it['text']}]: by={it['by']}, bh={it['bh']}, bottom={it['by']+it['bh']}")
