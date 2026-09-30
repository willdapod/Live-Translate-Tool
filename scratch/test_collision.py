import sys
sys.stdout.reconfigure(encoding='utf-8')

def deduplicate_and_resolve_overlaps(items, min_gap=3):
    """
    1. Removes duplicate or subsumed detections (e.g. partial OCR bounding boxes).
    2. Prevents vertical box collisions between adjacent list rows/menu items.
    """
    if not items or len(items) <= 1:
        return items

    # Step 1: Remove overlapping duplicate detections (NMS)
    survivors = []
    # Sort by area descending so larger/more complete boxes take precedence
    sorted_by_area = sorted(items, key=lambda it: it['w'] * it['h'], reverse=True)
    
    for it in sorted_by_area:
        ix1, iy1 = it['x'], it['y']
        ix2, iy2 = ix1 + it['w'], iy1 + it['h']
        area = it['w'] * it['h']
        duplicate = False
        for s in survivors:
            sx1, sy1 = s['x'], s['y']
            sx2, sy2 = sx1 + s['w'], sy1 + s['h']
            s_area = s['w'] * s['h']

            # Compute intersection
            ox1 = max(ix1, sx1)
            oy1 = max(iy1, sy1)
            ox2 = min(ix2, sx2)
            oy2 = min(iy2, sy2)
            if ox2 > ox1 and oy2 > oy1:
                inter = (ox2 - ox1) * (oy2 - oy1)
                # If overlap is > 45% of the smaller box, it's a redundant duplicate detection
                if inter / float(min(area, s_area)) > 0.45:
                    duplicate = True
                    break
        if not duplicate:
            survivors.append(it)

    # Step 2: Sort survivors vertically by Y coordinate
    survivors.sort(key=lambda it: it['y'])

    # Step 3: Non-overlapping vertical alignment (prevent box collisions)
    for i in range(len(survivors) - 1):
        cur = survivors[i]
        nxt = survivors[i + 1]

        # Check horizontal overlap
        cur_x1, cur_x2 = cur['x'], cur['x'] + cur['w']
        nxt_x1, nxt_x2 = nxt['x'], nxt['x'] + nxt['w']
        x_overlap = min(cur_x2, nxt_x2) - max(cur_x1, nxt_x1)

        # If they overlap horizontally and collide vertically:
        if x_overlap > 10:
            cur_bottom = cur['y'] + cur['h']
            nxt_top = nxt['y']
            if cur_bottom + min_gap > nxt_top:
                overlap_amt = (cur_bottom + min_gap) - nxt_top
                # Split the difference or nudge apart
                half = overlap_amt // 2 + 1
                cur['h'] = max(10, cur['h'] - half)
                nxt['y'] = cur['y'] + cur['h'] + min_gap

    return survivors

# Test cases: 2 tightly stacked items
test_items = [
    {'x': 100, 'y': 50, 'w': 120, 'h': 40, 'translated': 'Item 1'},
    {'x': 105, 'y': 80, 'w': 115, 'h': 40, 'translated': 'Item 2'}, # Overlaps Item 1 by 10px!
    {'x': 102, 'y': 52, 'w': 116, 'h': 36, 'translated': 'Item 1 duplicate'}, # Redundant duplicate
]

cleaned = deduplicate_and_resolve_overlaps(test_items)
print(f"Original items: {len(test_items)} -> Cleaned: {len(cleaned)}")
for idx, it in enumerate(cleaned):
    print(f"Item {idx}: y={it['y']}, h={it['h']}, bottom={it['y']+it['h']}, text={it['translated']}")

# Verify no overlap
for i in range(len(cleaned) - 1):
    assert cleaned[i]['y'] + cleaned[i]['h'] < cleaned[i+1]['y'], "Collision still exists!"
print("Overlap resolution test PASSED successfully!")
