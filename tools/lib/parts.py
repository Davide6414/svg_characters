"""Dalla segmentazione alle parti del corpo: classificazione, celle tracciate, cuciture e pieghe.

Ogni parte è la cella di Voronoi della sua regione: il confine cade a metà del tratto scuro del contorno, così
parti vicine si toccano senza buchi e il contorno si può disegnare come tratto centrato (var --line-w).
"""
import math

import numpy as np
from PIL import Image, ImageFilter

from .geom import (N8, catmull_d, components_pts, dilate, erode, fill_small_holes, grow_labels,
                   longest_path, rdp, skeleton_lines, trace_paths, zhang_suen)
from .segment import K, segment

GROUND = 900.0     # y della linea del suolo (le suole poggiano qui in tutte le sagome)
PAD = 14           # px: i pantaloni scendono sotto le scarpe, così l'orlo non si vede
SEAM_RADIUS = 4.2  # px: una fessura interna ha una sola regione entro questo raggio
SHOE_CLASSES = ('sole', 'tongue', 'upper-l', 'upper-r', 'toe', 'lace')


# ---------------------------------------------------------------- classificazione
def region_info(seg):
    x0, y0, x1, y1 = seg.box
    info = {}
    for i in range(1, seg.n_lab + 1):
        area = seg.sizes[i] / (K * K)
        if area < 30:
            continue
        ys, xs = np.nonzero(seg.lab == i)
        c = seg.rgb[seg.lab == i].mean(0)
        info[i] = dict(area=area, cx=xs.mean() / K + x0, cy=ys.mean() / K + y0, rgb=c, bg=i in seg.border,
                       lum=0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])
    return info


def classify(seg):
    """Assegna a ogni regione un ruolo: head, torso, arm-left, arm-right, pants, pants-detail, pocket, sole,
    tongue, upper-l, upper-r, toe, lace. Restituisce (info, classi)."""
    x0, y0, x1, y1 = seg.box
    info = region_info(seg)
    e = seg.eyes[0]
    head = int(seg.lab[int((e['cy'] - y0) * K), int((e['cx'] - x0) * K)])
    skin = [i for i, r in info.items() if not r['bg'] and i != head and r['rgb'][0] > 215
            and 150 < r['rgb'][1] < 215 and 110 < r['rgb'][2] < 190 and r['rgb'][0] - r['rgb'][2] > 45]
    skin.sort(key=lambda i: info[i]['cx'])
    arm_left, arm_right = skin[0], skin[-1]
    h = y1 - y0
    whites = [i for i, r in info.items() if not r['bg'] and r['rgb'].min() > 215
              and r['rgb'].max() - r['rgb'].min() < 25 and r['cy'] < y0 + 0.62 * h]
    shirt = max(whites, key=lambda i: info[i]['area'])
    cls = {head: 'head', arm_left: 'arm-left', arm_right: 'arm-right', shirt: 'torso'}
    rest = [i for i, r in info.items() if not r['bg'] and i not in cls]
    pants = max(rest, key=lambda i: info[i]['area'])
    cls[pants] = 'pants'
    cand = [i for i in rest if i != pants]

    # suole: le due regioni più in basso (area ≥ 350)
    soles = sorted([i for i in cand if info[i]['area'] >= 350], key=lambda i: -info[i]['cy'])[:2]
    soles.sort(key=lambda i: info[i]['cx'])
    sole_l, sole_r = soles
    for i in soles:
        cls[i] = 'sole'
    sole_top = min(info[i]['cy'] for i in soles)

    def xrange(i):
        xs = np.nonzero(seg.lab == i)[1]
        return xs.min() / K + x0, xs.max() / K + x0

    l_hi = xrange(sole_l)[1]; r_lo = xrange(sole_r)[0]
    shoes_l, shoes_r = [], []
    for i in cand:
        if i in soles:
            continue
        r = info[i]
        if r['cy'] < sole_top - 70:
            # dettaglio dei pantaloni (tasca) se ha la stessa tinta, altrimenti un'asola di sfondo
            cls[i] = 'pants-detail' if abs(r['lum'] - info[pants]['lum']) < 45 else 'pocket'
        elif l_hi < r['cx'] < r_lo:
            cls[i] = 'pocket'                          # asola di sfondo fra le gambe
        elif r['cx'] < (l_hi + r_lo) / 2:
            shoes_l.append(i)
        else:
            shoes_r.append(i)

    # piede sinistro: la regione più in alto è la linguetta, le altre sono tomaia
    top = min(shoes_l, key=lambda i: info[i]['cy'])
    for i in shoes_l:
        cls[i] = 'tongue' if i == top else 'upper-l'
    # piede destro: tomaia = la regione grande più a sinistra; punta = la più a destra fra le grandi;
    # le piccole chiare sono lacci, le piccole scure restano tomaia
    big = [i for i in shoes_r if info[i]['area'] >= 250]
    upper = min(big, key=lambda i: info[i]['cx'])
    toes = [i for i in big if i != upper and info[i]['cx'] > info[upper]['cx'] + 8]
    toe = max(toes, key=lambda i: info[i]['cx']) if toes else None
    for i in shoes_r:
        if i == upper:
            cls[i] = 'upper-r'
        elif i == toe:
            cls[i] = 'toe'
        elif info[i]['lum'] > 150:
            cls[i] = 'lace'
        else:
            cls[i] = 'upper-r'
    return info, cls


# ---------------------------------------------------------------- cuciture e pieghe
def _minmax_in_disk(g, r):
    n = int(math.ceil(r)); h, w = g.shape
    big = np.int32(10 ** 6)
    pmin = np.pad(g, n, constant_values=big); pmax = np.pad(g, n, constant_values=-1)
    mn = np.full(g.shape, big, np.int32); mx = np.full(g.shape, -1, np.int32)
    from .geom import disk_offsets
    for dy, dx in disk_offsets(r):
        mn = np.minimum(mn, pmin[n + dy:n + dy + h, n + dx:n + dx + w])
        mx = np.maximum(mx, pmax[n + dy:n + dy + h, n + dx:n + dx + w])
    return mn, mx


def find_seams(seg, g, allowed, to_xy, minlen=9.0):
    """Fessure scure dentro una stessa regione (orecchio, cuciture delle maniche, cucitura dei pantaloni…):
    pixel scuri che hanno una sola regione intorno. `allowed` = etichette delle regioni da considerare.
    Restituisce le linee (con l'etichetta della regione), già estese fino al contorno."""
    dark = seg.dark
    h, w = dark.shape
    mn, mx = _minmax_in_disk(g, SEAM_RADIUS * K)
    cand = dark & (mn == mx)
    bnd = np.zeros_like(dark)
    p = np.pad(g, 1)
    for dy, dx in N8:
        bnd |= (p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w] != g)
    out = []
    for pts in skeleton_lines(cand, minlen * K):
        label = int(np.bincount([int(g[int(y), int(x)]) for x, y in pts]).argmax())
        if label not in allowed:
            continue
        pm = np.zeros_like(dark)                  # spessore del tratto: area scura intorno alla linea / lunghezza
        for x, y in pts:
            pm[int(y), int(x)] = True
        thick = float((dilate(pm, 3 * K) & cand).sum() / len(pts) / K)
        pts = list(pts)
        for end in (0, -1):                      # estende le estremità vicine al contorno
            a = np.array(pts[end])
            ref = np.array(pts[end + 8] if end == 0 else pts[end - 9]) if len(pts) > 12 else np.array(pts[-1 if end == 0 else 0])
            v = a - ref; nv = np.hypot(*v)
            if nv == 0:
                continue
            v /= nv; cur = a.copy(); hit = None
            for _ in range(int(11 * K)):
                cur = cur + v
                x, y = int(round(cur[0])), int(round(cur[1]))
                if not (0 <= x < w and 0 <= y < h) or not dark[y, x]:
                    break
                if bnd[y, x]:
                    hit = cur - v * (1.4 * K)
                    break
            if hit is not None:
                pts.insert(0, tuple(hit)) if end == 0 else pts.append(tuple(hit))
        out.append(dict(d=catmull_d(rdp(pts, 1.1 * K), to_xy), label=label, kind='seam', length=len(pts) / K, thick=thick))
    return out


def find_folds(seg, g, pid, to_xy, contrast=20, minlen=9.0, sigma=6.0):
    """Pieghe sottili all'orlo dei pantaloni (regione `pid`): troppo chiare per la soglia del contorno, ma più
    scure dell'intorno."""
    interior = erode((g == pid) & ~seg.dark, 3.5 * K)
    blur = np.array(Image.fromarray(np.clip(seg.lum, 0, 255).astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(sigma * K))).astype(np.float32)
    thin = interior & ((blur - seg.lum) > contrast)
    mask = np.zeros_like(thin)
    for c in components_pts(thin):
        if len(c) >= 14 * K:
            for y, x in c:
                mask[y, x] = True
    return [dict(d=catmull_d(rdp(l, 1.1 * K), to_xy), label=pid, kind='fold', length=len(l) / K)
            for l in skeleton_lines(mask, minlen * K)]


# ---------------------------------------------------------------- misure
def _hex(c):
    return '#%02x%02x%02x' % tuple(int(round(v)) for v in c)


def _largest(parts, cls, fallback=None):
    ps = parts.get(cls, [])
    return _hex(max(ps, key=lambda p: p['area'])['med']) if ps else fallback


def default_colors(parts):
    """Colori di partenza della sagoma (mediane degli interni): pantaloni e scarpe."""
    upper_r = _largest(parts, 'upper-r')
    return {
        'pants': _hex(parts['pants'][0]['med']),
        'shoe-upper-l': _largest(parts, 'upper-l'),
        'shoe-upper-r': upper_r,
        'shoe-toe': _largest(parts, 'toe', upper_r),       # senza regione della punta: come la tomaia
        'shoe-tongue': _largest(parts, 'tongue'),
        'shoe-lace': _largest(parts, 'lace', _largest(parts, 'sole')),
        'shoe-sole': _largest(parts, 'sole'),
    }


# ---------------------------------------------------------------- punti di riferimento
def landmarks(cells, cls, to_xy):
    """Punti di riferimento del corpo, nelle coordinate finali: collo (sinistro e destro, un poco sopra la
    maglia) e gli angoli del riquadro di busto, braccia e pantaloni. Servono per adattare i vestiti: i vestiti
    sono disegnati su un corpo di riferimento e vengono deformati perché questi punti coincidano con quelli di
    ogni sagoma. `cells` deve avere i pantaloni prima dell'estensione sotto le scarpe."""
    def box(prefix, mask):
        ys, xs = np.nonzero(mask)
        u0, u1, v0, v1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        return {f'{prefix}-tl': to_xy(u0, v0), f'{prefix}-tr': to_xy(u1, v0),
                f'{prefix}-bl': to_xy(u0, v1), f'{prefix}-br': to_xy(u1, v1)}

    by_role = {c: i for i, c in cls.items() if c in ('head', 'torso', 'arm-left', 'arm-right', 'pants')}
    out = {}
    head = cells[by_role['head']]
    ys, xs = np.nonzero(head)
    row = ys.max() - 8 * K                       # il collo, poco sopra la fine della testa
    cols = np.nonzero(head[row])[0]
    out['neck-l'] = to_xy(cols.min(), row)
    out['neck-r'] = to_xy(cols.max() + 1, row)
    out.update(box('torso', cells[by_role['torso']]))
    out.update(box('armL', cells[by_role['arm-left']]))
    out.update(box('armR', cells[by_role['arm-right']]))
    out.update(box('pants', cells[by_role['pants']]))
    return {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in out.items()}


# ---------------------------------------------------------------- tutto insieme
def trace_body(sheet, box, ground=GROUND, verbose=False):
    """Traccia la figura in `box`. Le coordinate restano quelle del foglio, spostate in verticale in modo che
    le suole poggino su y = `ground` (stessa linea del suolo per tutte le sagome)."""
    seg = segment(sheet, box)
    info, cls = classify(seg)
    x0, y0 = box[:2]
    g = grow_labels(seg.lab, seg.dark)
    cells = {i: (g == i) for i in cls if cls[i] != 'pocket'}

    # linea del suolo: fondo delle suole
    bottom = max(np.nonzero(cells[i])[0].max() for i, c in cls.items() if c == 'sole') / K + y0
    dy = bottom - ground
    to_xy = lambda u, v: (x0 + u / K, y0 + v / K - dy)

    marks = landmarks(cells, cls, to_xy)

    # i pantaloni scendono sotto le scarpe
    shoe_cells = np.zeros_like(seg.dark)
    for i, c in cls.items():
        if c in SHOE_CLASSES:
            shoe_cells |= cells[i]
    pid = next(i for i, c in cls.items() if c == 'pants')
    cells[pid] = cells[pid] | (dilate(cells[pid], PAD * K) & shoe_cells)

    parts = {}
    for i, c in cls.items():
        if c == 'pocket':
            continue
        cell = fill_small_holes(cells[i], 30 * K * K)
        core = erode(seg.lab == i, 3 * K)
        med = np.median(seg.rgb[core], axis=0) if core.any() else info[i]['rgb']
        parts.setdefault(c, []).append(dict(
            id=int(i), d=trace_paths(cell, to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0),
            med=[float(v) for v in med], area=float(info[i]['area']), cx=float(info[i]['cx']), cy=float(info[i]['cy'] - dy)))
        if verbose:
            print(f'  regione {i:2d} {c:13s} area {info[i]["area"]:6.0f}')

    body_labels = {i for i, c in cls.items() if c in ('head', 'torso', 'pants', 'arm-left', 'arm-right')}
    seams = find_seams(seg, g, body_labels, to_xy) + find_folds(seg, g, pid, to_xy)
    for s in seams:
        s['part'] = cls[s['label']]
    # la cucitura interna dei pantaloni è piena come il contorno; le altre linee sono sottili
    longest_pants = max([s for s in seams if s['part'] == 'pants' and s['kind'] == 'seam'], key=lambda s: s['length'], default=None)
    for s in seams:
        s['fine'] = s is not longest_pants

    eyes = [dict(cx=e['cx'], cy=e['cy'] - dy, rx=e['rx'], ry=e['ry']) for e in seg.eyes]
    hid = next(i for i, c in cls.items() if c == 'head')
    ys, xs = np.nonzero(seg.lab == hid)
    X = xs / K + x0; Y = ys / K + y0 - dy
    ey = (eyes[0]['cy'] + eyes[1]['cy']) / 2
    head = dict(L=float(X.min() - 2.5), R=float(X[Y < ey + 45].max() + 2.5), T=float(Y.min() - 2.5), eyeY=float(ey),
                eyeX=float((eyes[0]['cx'] + eyes[1]['cx']) / 2))
    return dict(box=list(box), ground_shift=float(dy), parts=parts, seams=seams, eyes=eyes, head=head,
                landmarks=marks, colors=default_colors(parts))
