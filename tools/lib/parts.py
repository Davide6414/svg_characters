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
WAIST_UP = 30      # px: i pantaloni salgono sotto la maglia (livello sotto), così un'altra maglia non lascia buchi in vita
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


def find_seams(seg, g, allowed, to_xy, minlen=9.0, exclude=None):
    """Fessure scure dentro una stessa regione (orecchio, cuciture delle maniche, cucitura dei pantaloni…):
    pixel scuri che hanno una sola regione intorno. `allowed` = etichette delle regioni da considerare; `exclude` = maschera
    di pixel da non considerare (il confine fra due regioni fuse in una sola).
    Restituisce le linee (con l'etichetta della regione), già estese fino al contorno."""
    dark = seg.dark
    h, w = dark.shape
    mn, mx = _minmax_in_disk(g, SEAM_RADIUS * K)
    cand = dark & (mn == mx)
    if exclude is not None:
        cand &= ~exclude
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


# ---------------------------------------------------------------- estensioni sotto altri capi
def band_rect(cell, rows, extra, notch, inset=10, taper=0.0, wide_top=False):
    """Rettangolo largo come la fascia `rows` della regione (meno `inset` px per lato), che si allunga di `extra` px
    oltre la fascia: in alto se extra > 0, in basso se extra < 0. Con `taper` si stringe man mano che si allontana."""
    cols = np.nonzero(cell[rows].any(0))[0]
    out = np.zeros_like(cell)
    top_row = np.nonzero(cell.any(1))[0].min()
    top_cols = np.nonzero(cell[top_row:top_row + 6 * K].any(0))[0]     # il bordo alto (non la sua sola prima riga)
    x0, x1 = cols.min() + int(inset * K), cols.max() + 1 - int(inset * K)
    edge = rows.start if extra > 0 else rows.stop
    steps = range(int(abs(extra) * K) + int(notch * K))
    for d in steps:
        v = edge - int(abs(extra) * K) + d if extra > 0 else edge - int(notch * K) + d
        if not 0 <= v < cell.shape[0]:
            continue
        far = max(0, (edge - v) if extra > 0 else (v - edge))      # distanza oltre il bordo
        t = int(far * taper)
        a, b = x0 + t, x1 - t
        if v < top_row:                               # sopra la regione: non più larga del suo bordo alto
            row = cols if wide_top else top_cols      # (con `wide_top`: larga come la fascia, il bordo alto è a gradini)
        elif wide_top:
            row = cols
        else:                                         # dentro: non più larga della regione dal bordo alto fin qui
            row = np.nonzero(cell[top_row:max(v + 1, top_row + 6 * K)].any(0))[0]
        if row.size:
            a, b = max(a, row.min()), min(b, row.max() + 1)
        if a < b:
            out[v, a:b] = True
    return out


def extend_top(cell, up, notch=35, inset=5, taper=0.3, band_only=False, wide_top=False):
    """Parte alta dei pantaloni: un rettangolo largo come i primi `notch` px dall'alto, `up` px sopra il bordo alto e
    `notch` px sotto (riempie i vani fra il bordo alto frastagliato, l'orlo di una maglia, e i pantaloni), che si stringe
    salendo (la vita è più stretta dei fianchi). Così, con una maglia più corta o con un orlo diverso, non resta un buco.
    Con `band_only` restituisce solo la fascia (per il livello sotto: ridisegnare tutta la regione doppierebbe il contorno)."""
    rows = np.nonzero(cell.any(1))[0]
    band = band_rect(cell, slice(rows.min(), rows.min() + int(notch * K)), up, notch, inset=inset, taper=taper, wide_top=wide_top)
    return band if band_only else cell | band


def extend_bottom(cell, down, notch=25, inset=10, band_only=False, wide=0.0, hem=None):
    """Parte bassa di una maglia (in un livello sotto i pantaloni): un rettangolo largo come l'orlo, `down` px più in
    basso. Con pantaloni che cominciano più in basso dell'orlo non resta un buco in vita.
    `wide` (frazione 0-1): l'orlo è l'ultima riga larga almeno quella frazione della riga più larga, non l'ultima riga
    della regione. Serve quando la manica è unita al busto e arriva più in basso (il polsino non è l'orlo).
    `hem`: riga del bitmap dell'orlo, quando nessuna regola lo trova (le maniche a sbuffo sono larghe come il busto)."""
    rows = np.nonzero(cell.any(1))[0]
    last = rows.max()
    if hem is not None:
        last = hem
    elif wide:
        width = cell.sum(1)
        last = np.nonzero(width >= wide * width.max())[0].max()
    band = band_rect(cell, slice(last + 1 - int(notch * K), last + 1), -down, notch, inset=inset)
    return band if band_only else cell | band


def hull(mask):
    """Involucro convesso di una maschera (catena monotona sui bordi di ogni riga, poi riempimento del poligono)."""
    from PIL import ImageDraw
    pts = []
    for y in np.nonzero(mask.any(1))[0]:
        xs = np.nonzero(mask[y])[0]
        pts += [(int(xs.min()), int(y)), (int(xs.max()), int(y))]
    pts = sorted(set(pts))

    def half(points):
        out = []
        for p in points:
            while len(out) >= 2 and (out[-1][0] - out[-2][0]) * (p[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0]) <= 0:
                out.pop()
            out.append(p)
        return out
    poly = half(pts)[:-1] + half(pts[::-1])[:-1]
    img = Image.new('L', (mask.shape[1], mask.shape[0]), 0)
    ImageDraw.Draw(img).polygon(poly, fill=255)
    return np.array(img) > 0


def hdilate(mask, r):
    """Allarga una maschera solo in orizzontale, di `r` px del bitmap per lato."""
    out = mask.copy()
    for k in range(1, int(r) + 1):
        out[:, k:] |= mask[:, :-k]
        out[:, :-k] |= mask[:, k:]
    return out


BACK = 10          # px: il livello dietro allarga un capo fin sotto le braccia (vedi back_strip)
FILL_NEAR = 14     # px: i riempimenti di fondo stanno vicino alle braccia
FILL_RIM = 9       # px: e coprono questa fascia dentro il bordo del busto
FILL_RIM_HIPS = 16  # px: e dei fianchi (i pantaloni corti o stretti sono più stretti dei pantaloni base)
FILL_NECK = 30     # px: la fascia di pelle allo scollo scende tanto sotto il collo
FILL_NECK_SIDE = 12  # px: e si allarga tanto oltre il collo (non arriva alle spalle)


def between_arms(arms, center):
    """Per ogni riga, le colonne fra il bordo interno del braccio a sinistra di `center` e quello del braccio a destra
    (con 2 px di margine); vuoto dove manca uno dei due."""
    out = np.zeros_like(arms)
    c = int(center)
    for row in range(arms.shape[0]):
        xs = np.nonzero(arms[row])[0]
        la, ra = xs[xs < c], xs[xs >= c]
        if la.size and ra.size:
            out[row, max(0, la.max() - 2 * K):ra.min() + 2 * K + 1] = True
    return out


def back_strip(garment, arms, rows=None):
    """Livello dietro di un capo: una striscia larga fino a BACK px oltre i suoi fianchi, solo dove sulla figura c'è un
    braccio (che la nasconde). Quando il capo si abbina a un altro disegnato su un foglio diverso (o alla maglietta
    base) e fra braccio e capo resterebbe una fessura sottile, la striscia la riempie; uno spazio largo fra braccio e
    fianco resta com'è. `rows` = (prima, ultima) riga in cui vale."""
    # solo fra le braccia: fuori (oltre il braccio lontano, o dalla manica in fuori) la striscia sporgerebbe
    center = np.nonzero(garment)[1].mean()
    strip = hdilate(garment, BACK * K) & ~garment & dilate(arms, 2 * K) & between_arms(arms, center)
    if rows is not None:
        v = np.arange(strip.shape[0])[:, None]
        strip &= (v >= rows[0]) & (v <= rows[1])
    return strip


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
    maglia) e gli angoli del riquadro di busto, braccia e pantaloni. Servono alla build per i capi disegnati su un
    corpo di riferimento (i primi dieci capi maschili: vengono deformati perché questi punti coincidano con quelli
    della sagoma) e per i punti che un capo corregge da sé. Il pugno (riga di massima larghezza del braccio) tiene allineate le cuffie al polso. `cells` deve avere i pantaloni prima dell'estensione sotto le scarpe."""
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
    def fist(prefix, mask):
        """Il pugno: riga di massima larghezza nella metà bassa del braccio, con i suoi estremi a sinistra e a destra.
        Aggancia le cuffie dei vestiti al polso anche quando braccia e mani hanno proporzioni diverse."""
        ys, xs = np.nonzero(mask)
        v0, v1 = ys.min(), ys.max() + 1
        widths = np.array([mask[v].sum() for v in range(v0, v1)], float)
        smooth = np.convolve(widths, np.ones(2 * K + 1) / (2 * K + 1), mode='same')
        low = int(len(smooth) * 0.45)
        v = v0 + low + int(np.argmax(smooth[low:]))
        cols = np.nonzero(mask[v])[0]
        return {f'{prefix}-fl': to_xy(cols.min(), v), f'{prefix}-fr': to_xy(cols.max() + 1, v)}

    def edges(mask, v, left_arm, right_arm):
        """Bordi del busto alla riga v: dove comincia il braccio davanti (a sinistra) e quello dietro (a destra),
        o il bordo della maglia se lì il braccio non c'è."""
        cols = np.nonzero(mask[v])[0]
        lo, hi = cols.min(), cols.max() + 1
        la, ra = np.nonzero(left_arm[v])[0], np.nonzero(right_arm[v])[0]
        if la.size and abs(la.max() + 1 - lo) <= 4 * K:
            lo = la.max() + 1
        if ra.size and abs(ra.min() - hi) <= 4 * K:
            hi = ra.min()
        return lo, hi

    # Larghezza del busto contro le braccia (al petto, sotto le maniche, e in vita) e dei fianchi: senza questi punti i
    # vestiti seguono solo i riquadri, e su un corpo più largo resta uno spicchio vuoto fra braccio e fianco.
    T, AL, AR, PA = (cells[by_role[r]] for r in ('torso', 'arm-left', 'arm-right', 'pants'))
    tv = np.nonzero(T.any(1))[0]
    arm_top = max(np.nonzero(AL.any(1))[0].min(), np.nonzero(AR.any(1))[0].min())
    for name, v in (('chest', arm_top + 8 * K), ('waist', tv.max() - 6 * K)):
        lo, hi = edges(T, v, AL, AR)
        out[f'{name}-l'], out[f'{name}-r'] = to_xy(lo, v), to_xy(hi, v)
    pv = max(np.nonzero(PA.any(1))[0].min(), tv.max()) + 10 * K        # sotto l'orlo della maglia: i pantaloni si vedono interi
    cols = np.nonzero(PA[pv])[0]
    out['hip-l'], out['hip-r'] = to_xy(cols.min(), pv), to_xy(cols.max() + 1, pv)

    # Gambe: dove sono i piedi (la cima di ogni scarpa) e, sopra ciascuno, l'altezza del ginocchio (a metà fra la vita e
    # le scarpe). Tengono al loro posto orli, pantaloncini e calze: senza, un capo corto disegnato su un bambino diventa
    # enorme su un adulto. Le larghezze no: quelle dei pantaloni base sono uno stile (svasati, dritti), non il corpo.
    shoe_l = np.zeros_like(PA); shoe_r = np.zeros_like(PA)
    soles = sorted((i for i, c in cls.items() if c == 'sole'), key=lambda i: np.nonzero(cells[i])[1].mean())
    for i, c in cls.items():
        if c in ('upper-l', 'tongue') or i == soles[0]:
            shoe_l |= cells[i]
        elif c in ('upper-r', 'toe', 'lace') or i == soles[-1]:
            shoe_r |= cells[i]
    pants_top = np.nonzero(PA.any(1))[0].min()
    for side, m in (('l', shoe_l), ('r', shoe_r)):
        ys, xs = np.nonzero(m)
        top, bottom = ys.min(), ys.max() + 1
        cx = xs[ys < top + 8 * K].mean()
        out[f'foot-{side}'] = to_xy(cx, top)                        # la cima della scarpa (la caviglia)
        out[f'sole-{side}'] = to_xy(xs.mean(), bottom)              # sotto la scarpa, a terra
        out[f'knee-{side}'] = to_xy(cx, (pants_top + top) / 2)

    out.update(box('torso', cells[by_role['torso']]))
    out.update(box('armL', cells[by_role['arm-left']]))
    out.update(fist('armL', cells[by_role['arm-left']]))
    out.update(box('armR', cells[by_role['arm-right']]))
    out.update(fist('armR', cells[by_role['arm-right']]))
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

    # i pantaloni salgono sotto la maglia (livello sotto: si vede solo dove una maglia più corta lascerebbe un buco)
    pid = next(i for i, c in cls.items() if c == 'pants')
    # e proseguono sotto la mano davanti (nel foglio la copre, e con un braccio diverso resterebbe un incavo)
    front = next(i for i, c in cls.items() if c == 'arm-left')
    cells[pid] = cells[pid] | (hull(cells[pid]) & cells[front])
    under = extend_top(cells[pid], WAIST_UP, band_only=True)

    pants_cell = cells[pid].copy()

    # i pantaloni scendono sotto le scarpe
    shoe_cells = np.zeros_like(seg.dark)
    for i, c in cls.items():
        if c in SHOE_CLASSES:
            shoe_cells |= cells[i]
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

    parts['pants-under'] = [dict(id=-1, d=trace_paths(fill_small_holes(under, 30 * K * K), to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0),
                                 med=parts['pants'][0]['med'], area=float(under.sum() / (K * K)), cx=0.0, cy=0.0)]
    # Riempimenti di fondo, dietro a tutto: qualunque capo si scelga, fra braccio e busto (o fianchi) non resta una
    # fessura. Sono il bordo del busto e dei pantaloni vicino alle braccia (dentro e sotto il braccio), nel colore del
    # capo scelto, e una fascia di pelle allo scollo (si vede solo dove la maglia scelta è più scollata della base).
    arms = np.zeros_like(seg.dark)
    for i, c in cls.items():
        if c in ('arm-left', 'arm-right'):
            arms |= cells[i]
    tid = next(i for i, c in cls.items() if c == 'torso')
    torso = cells[tid]
    near = dilate(arms, FILL_NEAR * K)
    arm_top = np.nonzero(arms.any(1))[0].min()
    v = np.arange(torso.shape[0])[:, None]
    # dentro il bordo vicino alle braccia (fra le due braccia: non nelle maniche della maglietta base, che sono più larghe
    # di quelle di altri capi), e fuori solo dove il braccio lo copre (sulla sagoma base non si vede)
    AL = cells[next(i for i, c in cls.items() if c == 'arm-left')]
    AR = cells[next(i for i, c in cls.items() if c == 'arm-right')]
    between = np.zeros_like(torso)
    for row in range(torso.shape[0]):
        la, ra = np.nonzero(AL[row])[0], np.nonzero(AR[row])[0]
        if la.size and ra.size:
            between[row, max(0, la.max() - 2 * K):ra.min() + 2 * K + 1] = True
    rim = lambda m, inside=None, depth=FILL_RIM: ((m & ~erode(m, depth * K) & near & (inside if inside is not None else True))
                                                  | (hdilate(m, BACK * K) & ~m & dilate(arms, 1.5 * K)))
    tv = np.nonzero(torso.any(1))[0]
    pv = np.nonzero(pants_cell.any(1))[0]
    head_cell = cells[next(i for i, c in cls.items() if c == 'head')]
    neck_v = np.nonzero(head_cell.any(1))[0].max()
    nc = np.nonzero(head_cell[neck_v - 8 * K])[0]                 # le colonne del collo, con un margine
    neck_cols = np.zeros_like(torso)
    neck_cols[:, max(0, nc.min() - FILL_NECK_SIDE * K):nc.max() + 1 + FILL_NECK_SIDE * K] = True
    fills = {
        'fill-top': rim(torso, between) & (v >= arm_top),
        'fill-bottom': rim(pants_cell, between, FILL_RIM_HIPS) & (v >= pv.min()) & (v <= pv.min() + 60 * K),
        'fill-neck': torso & ~head_cell & (v <= neck_v + FILL_NECK * K) & neck_cols,
    }
    for name, m in fills.items():
        parts[name] = [dict(id=-1, d=trace_paths(fill_small_holes(m, 30 * K * K), to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0),
                            med=[0, 0, 0], area=float(m.sum() / (K * K)), cx=0.0, cy=0.0)] if m.any() else []

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
