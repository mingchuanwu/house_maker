import random

from house_maker.layout import pack


def test_pack_never_overlaps_and_respects_sheet_width():
    rng = random.Random(3)
    for _ in range(200):
        items = [(f'p{i}', rng.uniform(3, 90), rng.uniform(3, 120)) for i in range(rng.randint(1, 25))]
        pos = pack(items, 200, 2.0)
        assert set(pos) == {n for n, _, _ in items}
        rects = [(pos[n][0], pos[n][1], w, h) for n, w, h in items]
        for i, (x, y, w, h) in enumerate(rects):
            assert x >= 0 and y >= 0 and x + w <= 200 + 1e-9
            for x2, y2, w2, h2 in rects[i + 1:]:
                assert x + w + 2 <= x2 + 1e-9 or x2 + w2 + 2 <= x + 1e-9 or \
                       y + h + 2 <= y2 + 1e-9 or y2 + h2 + 2 <= y + 1e-9
