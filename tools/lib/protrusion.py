"""Protuberanze (corna, palchi, pinne, creste): le parti che spuntano dalla testa di un alieno.

Come i capelli degli umani sono disegnate una volta sola, sulla testa di una figura del foglio, e la build le adatta alla testa
di ogni sagoma. Le coordinate stanno in un riquadro di riferimento, la testa di una sagoma (`frame`: centro e mezza larghezza del
cranio, cima); la build le sposta e le scala (in modo uniforme, così non si deformano) sulla testa di ognuna con le stesse tre
misure: la cima e il centro del cranio restano gli ancoraggi.

Nel foglio la protuberanza è fusa con la testa (stesso colore, spesso nessuna linea fra le due), quindi si isola con un
**taglio**: un poligono, in px del foglio, che racchiude la protuberanza e lascia fuori il cranio. Due tipi di parte:

- `cut` (dietro la testa): la parte della silhouette dentro il poligono. Continua per EXT px dentro il cranio, dove la testa di ogni
  sagoma la copre, così resta attaccata qualunque sia la testa; il tratto sta solo sul bordo esterno (il contorno della testa è
  quello della sagoma). Le linee interne (nervature, spirali) restano sopra il riempimento.
- `region` (davanti alla testa): una regione chiusa dal tratto del foglio (un corno che passa davanti al cranio), scelta con un punto
  dentro (`seed`); riempimento e contorno interi, sopra la testa. `bridge` chiude le interruzioni del tratto.
"""
import re

import numpy as np
from PIL import Image, ImageDraw

from .geom import catmull_d, dilate, erode, fill_small_holes, fmt, grow_labels, rdp, skeleton_lines, trace_paths
from .parts import find_seams
from .alien import SKULL_DEPTH
from .segment import K, segment

EXT = 8           # px: la parte dietro la testa continua tanto dentro il cranio
PAIR = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')


def poly_mask(poly, shape, box):
    """Maschera (bitmap della figura) di un poligono in px del foglio."""
    x0, y0 = box[:2]
    img = Image.new('L', (shape[1], shape[0]), 0)
    ImageDraw.Draw(img).polygon([((x - x0) * K, (y - y0) * K) for x, y in poly], fill=255)
    return np.asarray(img) > 127


def edge_mask(poly, shape, box, width):
    """Maschera del contorno di un poligono (il taglio), largo `width` px del foglio."""
    x0, y0 = box[:2]
    img = Image.new('L', (shape[1], shape[0]), 0)
    pts = [((x - x0) * K, (y - y0) * K) for x, y in poly]
    ImageDraw.Draw(img).line(pts + [pts[0]], fill=255, width=int(width * K))
    return np.asarray(img) > 127


def circle_mask(cx, cy, r, shape, box):
    x0, y0 = box[:2]
    img = Image.new('L', (shape[1], shape[0]), 0)
    ImageDraw.Draw(img).ellipse([((cx - r) - x0) * K, ((cy - r) - y0) * K, ((cx + r) - x0) * K, ((cy + r) - y0) * K], fill=255)
    return np.asarray(img) > 127


def close_bottom(sheet, box):
    """Un busto non ha il contorno in basso: un segmento scuro fra i due estremi del contorno lo chiude."""
    x0, y0, x1, y1 = box
    dk = sheet.lum[y0:y1, x0:x1] < 60
    ys, xs = np.nonzero(dk)
    band = ys > ys.max() - 22
    i0, i1 = np.argmin(np.where(band, xs, 10 ** 6)), np.argmax(np.where(band, xs, -1))
    return [((x0 + xs[i0], y0 + ys[i0]), (x0 + xs[i1], y0 + ys[i1]))]


def trace_protrusion(sheet, spec, frame):
    """Traccia la protuberanza descritta da `spec` (vedi tools/trace_protrusions.py). Restituisce le parti (dietro e davanti,
    in coordinate del riquadro di riferimento) e le misure della testa della figura."""
    box = spec['box']
    x0, y0, x1, y1 = box
    bridge = list(spec.get('bridge', ()))
    if spec.get('bust'):
        bridge += close_bottom(sheet, box)
    seg = segment(sheet, box, bridge=bridge, dots=(6, 60), eye_aspect=1.15, eye_zone=1.0 if spec.get('bust') else 0.35)
    if len(seg.eyes) != 2:
        raise ValueError(f'{spec["id"]}: servono due occhi, trovati {len(seg.eyes)}')
    g = grow_labels(seg.lab, seg.dark)
    background = [i for i in range(1, seg.n_lab + 1) if i in seg.border]
    S = (g > 0) & ~np.isin(g, background)                        # la silhouette: testa, protuberanze, collo, corpo
    shape = S.shape

    # le parti 'cut': la silhouette dentro il poligono
    def cut_mask(p):
        m = poly_mask(p['poly'], shape, box) & S
        if 'not_circle' in p:                                    # fuori da un cerchio (cx, cy, r): il cranio rotondo
            m &= ~circle_mask(*p['not_circle'], shape, box)
        return m
    cuts = [cut_mask(p) for p in spec['parts'] if p['kind'] == 'cut']
    taken = np.zeros_like(S)
    for m in cuts:
        taken |= m
    regions = [int(g[int((p['seed'][1] - y0) * K), int((p['seed'][0] - x0) * K)]) for p in spec['parts'] if p['kind'] == 'region']
    for rid in regions:
        taken |= (g == rid)

    # misure del cranio della figura (senza le protuberanze): cima, centro e mezza larghezza della calotta
    ex = sorted(e['cx'] for e in seg.eyes)
    eye_y = float(np.mean([e['cy'] for e in seg.eyes]))
    head = S & ~taken
    rows = np.nonzero(head[:int((eye_y - y0) * K)].any(1))[0]
    top = rows.min() / K + y0
    skull = head[rows.min():rows.min() + int(SKULL_DEPTH * (int((eye_y - y0) * K) - rows.min()))]       # la calotta, come per le sagome
    cols = np.nonzero(skull.any(0))[0]
    skull_x, skull_half = (cols.min() + cols.max()) / 2 / K + x0, (cols.max() - cols.min()) / 2 / K
    # dalla figura al riquadro di riferimento: scala uniforme (larghezza del cranio), cima e centro del cranio sovrapposti
    fit = spec.get('fit', {})
    k = frame['skullHalf'] / skull_half
    kx, ky = k * fit.get('sx', 1.0), k * fit.get('sy', 1.0)
    to_xy = lambda u, v: (frame['skullX'] + (x0 + u / K - skull_x) * kx + fit.get('dx', 0.0), frame['T'] + (y0 + v / K - top) * ky + fit.get('dy', 0.0))
    raw = lambda u, v: (u, v)

    def d_frame(d):                                              # un percorso in coordinate del bitmap → riquadro
        return PAIR.sub(lambda m: ','.join(fmt(c) for c in to_xy(float(m.group(1)), float(m.group(2)))), d)

    # le linee interne (nervature, spirali, ticchettii alla base): pixel scuri con una sola regione intorno
    seams = find_seams(seg, g, set(np.unique(g[S])) - {0}, raw, minlen=7.0)
    seam_pts = [[(float(a), float(b)) for a, b in PAIR.findall(s['d'])][::3] for s in seams]      # solo i punti sulla curva (non i punti di controllo)

    def inside(mask, pts, share=0.8):
        ok = [bool(mask[int(min(max(v, 0), mask.shape[0] - 1)), int(min(max(u, 0), mask.shape[1] - 1))]) for u, v in pts]
        return sum(ok) >= share * len(ok)

    boundary = S & ~erode(S, 1.5)                                # il bordo della silhouette (a mezzo tratto, verso lo sfondo)
    back, front, used = [], [], set()
    for part, m in zip([p for p in spec['parts'] if p['kind'] == 'cut'], cuts):
        ext = m | (dilate(m, EXT * K) & erode(S, 7 * K))          # dentro il cranio, ma non fino al suo bordo (sporgerebbe da una testa più stretta)
        fill = trace_paths(fill_small_holes(ext, 30 * K * K), to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0)
        outline = [catmull_d(rdp(line, 1.1 * K), to_xy) for line in skeleton_lines(boundary & dilate(m, 2 * K), 9 * K)]
        inner = poly_mask(part['poly'], shape, box) & S
        if 'not_circle' in part:
            inner &= ~circle_mask(*part['not_circle'], shape, box)
        along_cut = edge_mask(part['poly'], shape, box, 8)
        if 'not_circle' in part:
            along_cut |= dilate(circle_mask(*part['not_circle'], shape, box), 4 * K) & ~erode(circle_mask(*part['not_circle'], shape, box), 4 * K)
        lines = []
        for i, (s, pts) in enumerate(zip(seams, seam_pts)):
            if i not in used and inside(inner, pts, 0.5) and not inside(along_cut, pts, 0.5):       # le linee lungo il taglio (il contorno del cranio) non servono
                used.add(i)
                lines.append(d_frame(s['d']))
        back.append(dict(fill=fill, outline=outline, lines=lines))
    for part, rid in zip([p for p in spec['parts'] if p['kind'] == 'region'], regions):
        cell = fill_small_holes(g == rid, 30 * K * K)
        fill = trace_paths(cell, to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0)
        lines = []
        for i, (s, pts) in enumerate(zip(seams, seam_pts)):
            if s['label'] == rid and i not in used:
                used.add(i)
                lines.append(d_frame(s['d']))
        front.append(dict(fill=fill, lines=lines))
    return dict(back=back, front=front, top=top, scale=(kx, ky))
