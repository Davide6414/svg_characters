"""Funzioni geometriche di base: maschere, scheletro, curve e conversione in percorsi SVG.

Tutte le maschere sono array booleani numpy; i bitmap sono sovracampionati di un fattore K
rispetto al foglio, e `to_xy` riporta le coordinate del bitmap in quelle del foglio.
"""
import math
from collections import deque

import numpy as np
from PIL import Image, ImageFilter
import potrace

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
N4 = [(-1, 0), (0, -1), (0, 1), (1, 0)]


def upsample(arr2d, k, resample=Image.BICUBIC):
    h, w = arr2d.shape
    img = Image.fromarray(np.clip(arr2d, 0, 255).astype(np.uint8), 'L').resize((w * k, h * k), resample)
    return np.array(img).astype(np.float32)


def disk_offsets(r):
    n = int(math.ceil(r))
    return [(dy, dx) for dy in range(-n, n + 1) for dx in range(-n, n + 1) if dy * dy + dx * dx <= r * r + 1e-9]


def erode(mask, r):
    n = int(math.ceil(r)); h, w = mask.shape
    pad = np.pad(mask, n, constant_values=False)
    out = np.ones_like(mask)
    for dy, dx in disk_offsets(r):
        out &= pad[n + dy:n + dy + h, n + dx:n + dx + w]
    return out


def dilate(mask, r):
    n = int(math.ceil(r)); h, w = mask.shape
    pad = np.pad(mask, n, constant_values=False)
    out = np.zeros_like(mask)
    for dy, dx in disk_offsets(r):
        out |= pad[n + dy:n + dy + h, n + dx:n + dx + w]
    return out


def label_components(mask, conn=4):
    """Etichette 1..n delle componenti connesse di `mask` (BFS)."""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    nb = N4 if conn == 4 else N8
    n = 0
    for y, x in zip(*np.nonzero(mask)):
        if lab[y, x]:
            continue
        n += 1
        lab[y, x] = n
        q = deque([(y, x)])
        while q:
            cy, cx = q.popleft()
            for dy, dx in nb:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n
                    q.append((ny, nx))
    return lab, n


def grow_labels(lab, dark, max_iter=200):
    """Voronoi discreto: ogni etichetta si espande dentro i pixel scuri (vicinato 8 e 4 alternati,
    ≈ distanza euclidea), così i confini cadono a metà del tratto del contorno."""
    lab = lab.copy()
    todo = dark & (lab == 0)
    h, w = lab.shape
    for it in range(max_iter):
        if not todo.any():
            break
        p = np.pad(lab, 1)
        best = np.zeros_like(lab)
        for dy, dx in (N8 if it % 2 == 0 else N4):
            best = np.maximum(best, p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w])
        newly = todo & (best > 0)
        if not newly.any():
            break
        lab[newly] = best[newly]
        todo &= ~newly
    return lab


def fill_small_holes(mask, max_area):
    """Riempie i buchi interni di `mask` più piccoli di `max_area` pixel."""
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = mask[y0:y1, x0:x1]
    lab, n = label_components(~sub, conn=4)
    if n == 0:
        return mask
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]).tolist())
    out = sub.copy()
    for i in range(1, n + 1):
        if i not in border and sizes[i] <= max_area:
            out |= (lab == i)
    res = mask.copy()
    res[y0:y1, x0:x1] = out
    return res


def zhang_suen(img):
    """Scheletro (assottigliamento di Zhang-Suen) di una maschera booleana."""
    img = img.copy().astype(np.uint8)
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            p = np.pad(img, 1)
            p2 = p[:-2, 1:-1]; p3 = p[:-2, 2:]; p4 = p[1:-1, 2:]; p5 = p[2:, 2:]
            p6 = p[2:, 1:-1]; p7 = p[2:, :-2]; p8 = p[1:-1, :-2]; p9 = p[:-2, :-2]
            nb = [p2, p3, p4, p5, p6, p7, p8, p9]
            b = sum(x.astype(np.int16) for x in nb)
            seq = nb + [p2]
            a = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.int16) for i in range(8))
            if step == 0:
                c1 = (p2 * p4 * p6) == 0; c2 = (p4 * p6 * p8) == 0
            else:
                c1 = (p2 * p4 * p8) == 0; c2 = (p2 * p6 * p8) == 0
            rm = (img == 1) & (b >= 2) & (b <= 6) & (a == 1) & c1 & c2
            if rm.any():
                img[rm] = 0
                changed = True
    return img.astype(bool)


def components_pts(mask):
    """Componenti 8-connesse come liste di punti (y, x)."""
    h, w = mask.shape
    seen = np.zeros_like(mask, bool); comps = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        q = deque([(y, x)]); seen[y, x] = True; pts = []
        while q:
            cy, cx = q.popleft(); pts.append((cy, cx))
            for dy, dx in N8:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; q.append((ny, nx))
        comps.append(pts)
    return comps


def longest_path(pts):
    """Cammino più lungo (doppia BFS) fra i punti di una componente dello scheletro."""
    s = set(pts)

    def bfs(src):
        dist = {src: 0}; prev = {src: None}; q = deque([src]); last = src
        while q:
            c = q.popleft(); last = c
            for dy, dx in N8:
                n = (c[0] + dy, c[1] + dx)
                if n in s and n not in dist:
                    dist[n] = dist[c] + 1; prev[n] = c; q.append(n)
        return last, prev

    a, _ = bfs(pts[0]); b, prev = bfs(a)
    path = []; c = b
    while c is not None:
        path.append(c); c = prev[c]
    return path[::-1]


def skeleton_lines(mask, minlen, max_lines=60):
    """Linee (liste di (x, y)) ricavate dallo scheletro di `mask`, dalla più lunga, scartando quelle < minlen."""
    work = zhang_suen(mask)
    lines = []
    for _ in range(max_lines):
        comps = [c for c in components_pts(work) if len(c) >= minlen]
        if not comps:
            break
        c = max(comps, key=len)
        path = longest_path(c)
        for y, x in c:
            work[y, x] = False
        if len(path) >= minlen:
            lines.append([(float(x), float(y)) for y, x in path])
    return lines


def rdp(pts, eps):
    """Semplificazione di Ramer-Douglas-Peucker."""
    pts = np.array(pts, float)

    def rec(i, j):
        if j <= i + 1:
            return [i]
        a, b = pts[i], pts[j]
        ab = b - a; length = np.hypot(*ab)
        seg = pts[i + 1:j] - a
        d = np.abs(seg[:, 0] * ab[1] - seg[:, 1] * ab[0]) / length if length > 0 else np.hypot(seg[:, 0], seg[:, 1])
        k = int(np.argmax(d))
        if d[k] > eps:
            return rec(i, i + 1 + k) + rec(i + 1 + k, j)
        return [i]

    idx = rec(0, len(pts) - 1) + [len(pts) - 1]
    return pts[idx]


def fmt(v):
    """Numero con al più un decimale, senza zeri inutili."""
    s = f'{v:.1f}'
    if s.endswith('.0'):
        s = s[:-2]
    return '0' if s == '-0' else s


def trace_paths(mask, to_xy, opttol=2.0, alphamax=1.0, turd=30, smooth=0.0):
    """Maschera booleana (True = interno) → lista di attributi `d` SVG (curve di Bézier da potrace)."""
    if smooth > 0:
        img = Image.fromarray((mask * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(smooth))
        mask = np.array(img) > 127
    plist = potrace.Bitmap(~mask).trace(turdsize=turd, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                                        alphamax=alphamax, opticurve=True, opttolerance=opttol)

    def pt(p):
        x, y = to_xy(p.x, p.y)
        return f'{fmt(x)},{fmt(y)}'

    out = []
    for p in plist:
        c = p.curve if hasattr(p, 'curve') else p
        d = [f'M{pt(c.start_point)}']
        for seg in c.segments:
            if seg.is_corner:
                d.append(f'L{pt(seg.c)}L{pt(seg.end_point)}')
            else:
                d.append(f'C{pt(seg.c1)} {pt(seg.c2)} {pt(seg.end_point)}')
        d.append('Z')
        out.append(''.join(d))
    return out


def catmull_d(points, to_xy, tension=1.0):
    """Polilinea → curva di Bézier (Catmull-Rom) come attributo `d`."""
    pts = [np.array(p, float) for p in points]

    def f(p):
        return to_xy(p[0], p[1])

    a = f(pts[0]); out = [f'M{fmt(a[0])},{fmt(a[1])}']
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]; p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else pts[i + 1]
        c1 = p1 + (p2 - p0) / 6 * tension; c2 = p2 - (p3 - p1) / 6 * tension
        a, b, c = f(c1), f(c2), f(p2)
        out.append(f'C{fmt(a[0])},{fmt(a[1])} {fmt(b[0])},{fmt(b[1])} {fmt(c[0])},{fmt(c[1])}')
    return ''.join(out)
