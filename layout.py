"""
Layout: place rectangles on a sheet. Knows nothing about houses or panels beyond (name, w, h).

Callers pass the *actual* extent of each item (including protruding tabs and label space), so the
minimum spacing is a real guarantee between cut lines.
"""

from typing import Dict, List, Tuple

from .exceptions import GeometryError

Rect = Tuple[float, float, float, float]   # x, y, w, h


def _overlaps(a: Rect, b: Rect, spacing: float) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + spacing <= bx or bx + bw + spacing <= ax or
                ay + ah + spacing <= by or by + bh + spacing <= ay)


def pack(items: List[Tuple[str, float, float]], sheet_width: float,
         spacing: float) -> Dict[str, Tuple[float, float]]:
    """
    Bottom-left candidate packing. Width is a hard limit, height is unbounded (multiple sheets).

    Deterministic: items are ordered by (height, area) descending, ties broken by input order.
    Returns {name: (x, y)} of each item's top-left corner.
    """
    for name, w, _ in items:
        if w > sheet_width:
            raise GeometryError("layout_constraints",
                                f"Panel {name} width ({w:.1f}mm) exceeds material width ({sheet_width:.1f}mm)")

    order = sorted(range(len(items)), key=lambda i: (-items[i][2], -items[i][1] * items[i][2], i))
    placed: List[Rect] = []
    positions: Dict[str, Tuple[float, float]] = {}
    for i in order:
        name, w, h = items[i]
        # (0, bottom of everything) is always free, so a valid position always exists
        candidates = {(0.0, 0.0), (0.0, max((y + ph for _, y, _, ph in placed), default=0.0) + (spacing if placed else 0.0))}
        for x, y, pw, ph in placed:
            candidates.update([(x + pw + spacing, y), (x, y + ph + spacing),
                               (x + pw + spacing, y + ph + spacing)])
        valid = [(x, y) for x, y in candidates
                 if x + w <= sheet_width and not any(_overlaps((x, y, w, h), r, spacing) for r in placed)]
        x, y = min(valid, key=lambda p: (p[1], p[0]))
        placed.append((x, y, w, h))
        positions[name] = (x, y)
    return positions
