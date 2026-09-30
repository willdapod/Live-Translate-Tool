import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Create a mock image simulating game screen with adjacent Japanese text lines
mock_img = np.full((600, 800, 3), (35, 30, 25), dtype=np.uint8) # Dark sepia parchment background
pil_img = Image.fromarray(mock_img)
draw = ImageDraw.Draw(pil_img, "RGBA")

# Adjacent menu items (tight 4px vertical gap)
items = [
    {'x': 300, 'y': 150, 'w': 120, 'h': 26, 'translated': 'Continue Playing'},
    {'x': 300, 'y': 180, 'w': 90, 'h': 26, 'translated': 'Save Progress'},
    {'x': 300, 'y': 210, 'w': 110, 'h': 26, 'translated': 'Load Saved Game'},
    {'x': 300, 'y': 240, 'w': 80, 'h': 26, 'translated': 'Game Options'},
    {'x': 300, 'y': 270, 'w': 70, 'h': 26, 'translated': 'Quit to Desktop'},
]

# Let's test the 2-stage rendering with collision separation
# 1. Resolve bounding patches
patches = []
for it in items:
    text = it['translated']
    ix, iy, iw, ih = it['x'], it['y'], it['w'], it['h']
    
    # Estimate font size
    fsize = max(11, min(18, int(ih * 0.85)))
    char_w = fsize * 0.58
    tw = int(len(text) * char_w)
    th = int(fsize * 1.1)

    pad_x = 6
    pad_y = 2
    bx1 = ix - pad_x
    bx2 = ix + max(iw, tw) + pad_x
    by1 = iy - pad_y
    by2 = iy + ih + pad_y

    patches.append({
        'bx1': bx1, 'by1': by1, 'bx2': bx2, 'by2': by2,
        'text': text, 'fsize': fsize, 'tw': tw, 'th': th
    })

# Resolve vertical overlap between adjacent items
for i in range(len(patches) - 1):
    p1 = patches[i]
    p2 = patches[i + 1]
    if p2['by1'] < p1['by2'] + 2:
        overlap = (p1['by2'] + 2) - p2['by1']
        mid = (p1['by2'] + p2['by1']) // 2
        p1['by2'] = mid - 1
        p2['by1'] = mid + 1

# Check for collisions
for i in range(len(patches) - 1):
    assert patches[i]['by2'] < patches[i+1]['by1'], f"Collision between {patches[i]['text']} and {patches[i+1]['text']}"

print("All seamless patches resolved cleanly with 0 collisions!")
for p in patches:
    print(f"  [{p['text']}]: y1={p['by1']}, y2={p['by2']}, height={p['by2']-p['by1']}")
