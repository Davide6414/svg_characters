"""Tracciatura dei vestiti: capi disegnati su un corpo di riferimento.

Un foglio di vestiti ha figure affiancate che indossano capi diversi sullo stesso corpo. Ogni capo viene
segmentato come le sagome (regioni delimitate dal contorno, celle a metà del tratto) togliendo ciò che è corpo
(testa, mani) e ciò che non è il capo (scarpe, e la maglia o i pantaloni che stanno sotto). Il capo è scritto
nel riquadro del corpo di riferimento (la prima figura del foglio dei pantaloni): `build.mjs` lo deforma poi su
ogni sagoma, usando i punti di riferimento misurati su ogni corpo.

Ruoli dei colori di un capo (variabili CSS --shirt / --pants e le loro varianti):
  main    il colore principale
  trim    coste, colletti, bordi
  accent  cerniera, cordini, dettagli
  under   maglietta sotto un capo aperto
"""
import numpy as np

from .geom import dilate, erode, fill_small_holes, grow_labels, trace_paths
from .parts import GROUND, PAD, WAIST_UP, back_strip, extend_top, find_folds, find_seams, landmarks, region_info
from .segment import K, segment

SHOE_BAND = 45        # px sopra la cima delle suole: le regioni più in basso sono scarpe
HEM_LEVEL = 0.62      # frazione dell'altezza: sotto è il pantalone, sopra è il busto


def _skin(r):
    return r['rgb'][0] > 215 and 150 < r['rgb'][1] < 215 and 110 < r['rgb'][2] < 190 and r['rgb'][0] - r['rgb'][2] > 45


def _white(c):
    return min(c) > 215 and max(c) - min(c) < 25


def _dist(a, b):
    return float(np.sqrt(((np.array(a) - np.array(b)) ** 2).sum()))


def _hex(c):
    return '#%02x%02x%02x' % tuple(int(round(v)) for v in c)


def classify_outfit(seg, kind):
    """Divide le regioni di una figura vestita: (info, testa, scarpe, garment, nucleo del capo).
    kind='bottom': il capo sono i pantaloni (la maglietta bianca è il busto base);
    kind='top': il capo è ciò che copre il busto (i pantaloni sono quelli base)."""
    info = region_info(seg)
    x0, y0, x1, y1 = seg.box
    h = y1 - y0
    e = seg.eyes[0]
    head = int(seg.lab[int((e['cy'] - y0) * K), int((e['cx'] - x0) * K)])
    skin = [i for i, r in info.items() if not r['bg'] and i != head and _skin(r)]
    cand = [i for i, r in info.items() if not r['bg'] and i != head and i not in skin]
    soles = sorted([i for i in cand if info[i]['area'] >= 350], key=lambda i: -info[i]['cy'])[:2]
    sole_top = min(info[i]['cy'] for i in soles)
    shoes = [i for i in cand if info[i]['cy'] >= sole_top - SHOE_BAND]
    rest = [i for i in cand if i not in shoes]
    if kind == 'bottom':
        tees = [i for i in rest if _white(info[i]['rgb']) and info[i]['cy'] < y0 + HEM_LEVEL * h]
        tee = max(tees, key=lambda i: info[i]['area'])
        garment = [i for i in rest if i != tee]
    else:
        below = [i for i in rest if info[i]['cy'] > y0 + HEM_LEVEL * h]
        garment = [i for i in rest if i not in below]
    core = max(garment, key=lambda i: info[i]['area'])
    return info, head, soles, shoes, garment, core


def assign_roles(info, med, garment, core, overrides):
    """Ruolo di ogni regione del capo: automatico (colore simile al principale = main, bianco = under, grande =
    trim, piccola = accent) con correzioni esplicite `overrides` {indice regione: ruolo}."""
    roles = {}
    for i in garment:
        c = med[i]
        if i in overrides:
            roles[i] = overrides[i]
        elif _white(c) and not _white(med[core]):
            roles[i] = 'under'
        elif _dist(c, med[core]) <= 40:
            roles[i] = 'main'
        elif info[i]['area'] >= 300:
            roles[i] = 'trim'
        else:
            roles[i] = 'accent'
    return roles


def trace_garment(sheet, box, kind, ref=None, overrides=None, verbose=False):
    """Traccia il capo della figura in `box`. `ref` = dati del corpo di riferimento (testa) per portare il capo nel
    suo riquadro; se manca, questa figura è il riferimento."""
    overrides = overrides or {}
    seg = segment(sheet, box)
    info, head, soles, shoes, garment, core = classify_outfit(seg, kind)
    x0, y0 = box[:2]
    g = grow_labels(seg.lab, seg.dark)
    cells = {i: (g == i) for i in garment + shoes}

    # linea del suolo e allineamento al corpo di riferimento
    bottom = max(np.nonzero(g == i)[0].max() for i in soles) / K + y0
    dy = bottom - GROUND
    e = seg.eyes
    ys, xs = np.nonzero(seg.lab == head)
    head_t = float(ys.min() / K + y0 - dy - 2.5)
    eye_x = float((e[0]['cx'] + e[1]['cx']) / 2)
    if ref is None:
        s, rx, rt = 1.0, eye_x, head_t
    else:
        rx, rt = ref['head']['eyeX'], ref['head']['T']
        s = (GROUND - rt) / (GROUND - head_t)

    def to_xy(u, v):
        x, y = x0 + u / K, y0 + v / K - dy
        return rx + (x - eye_x) * s, rt + (y - head_t) * s

    med = {}
    for i in garment:
        core_mask = erode(seg.lab == i, 2 * K)
        med[i] = np.median(seg.rgb[core_mask], axis=0) if core_mask.any() else info[i]['rgb']
    roles = assign_roles(info, med, garment, core, overrides)

    # i pantaloni salgono sotto la maglia (livello sotto), così un'altra maglia più corta non lascia buchi in vita
    under = extend_top(cells[core], WAIST_UP, band_only=True) if kind == 'bottom' else None

    # livello dietro: il capo continua sotto le braccia (vedi back_strip)
    arms = np.zeros_like(seg.dark)
    for i, r in info.items():
        if not r['bg'] and i != head and i not in garment and i not in shoes and _skin(r):
            arms |= g == i
    gar = np.zeros_like(seg.dark)
    for i in garment:
        gar |= cells[i]
    back = None
    if arms.any() and kind == 'top':                  # i pantaloni: basta il riempimento della sagoma
        gv = np.nonzero(gar.any(1))[0]
        rows = (np.nonzero(arms.any(1))[0].min(), gv.max()) if kind == 'top' else (gv.min(), gv.min() + 60 * K)
        back = back_strip(gar, arms, rows)
        if back.sum() <= 20 * K * K:
            back = None

    # i pantaloni scendono sotto le scarpe, così l'orlo non si vede
    if kind == 'bottom':
        shoe_cells = np.zeros_like(seg.dark)
        for i in shoes:
            shoe_cells |= cells[i]
        # anche le regioni che toccano le scarpe (risvolti, coste alle caviglie)
        near_shoes = dilate(shoe_cells, 2 * K)
        for i in garment:
            if i == core or (cells[i] & near_shoes).any():
                cells[i] = cells[i] | (dilate(cells[i], PAD * K) & shoe_cells)

    regions = []
    for i in sorted(garment, key=lambda i: -info[i]['area']):
        cell = fill_small_holes(cells[i], 30 * K * K)
        regions.append(dict(id=int(i), role=roles[i], area=float(info[i]['area']), med=[float(v) for v in med[i]],
                            d=trace_paths(cell, to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0)))
        if verbose:
            print(f'  regione {i:2d} {roles[i]:7s} area {info[i]["area"]:6.0f} {_hex(med[i])}')

    if back is not None:
        regions.append(dict(id=-2, role=roles[core], layer='back', area=float(back.sum() / (K * K)), med=[float(v) for v in med[core]],
                            d=trace_paths(back, to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0)))
    if under is not None:
        regions.append(dict(id=-1, role=roles[core], layer='under', area=float(under.sum() / (K * K)), med=[float(v) for v in med[core]],
                            d=trace_paths(fill_small_holes(under, 30 * K * K), to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0)))

    labels = set(garment)
    seams = find_seams(seg, g, labels, to_xy)
    if kind == 'bottom':
        seams += find_folds(seg, g, core, to_xy)
    for sm in seams:
        sm['fine'] = sm['kind'] == 'fold' or sm.get('thick', 0) < 4.7
    dots = []
    for dt in seg.dots:
        u, v = (dt['cx'] - x0) * K, (dt['cy'] - y0) * K
        if g[int(v), int(u)] in labels:
            x, y = to_xy(u, v)
            dots.append(dict(cx=round(x, 1), cy=round(y, 1), r=round(dt['r'] * s, 1)))

    # colori di partenza per ruolo (il più esteso di ogni ruolo)
    colors = {}
    for role in ('main', 'trim', 'accent', 'under'):
        rs = [r for r in regions if r['role'] == role]
        if rs:
            colors[role] = _hex(max(rs, key=lambda r: r['area'])['med'])
    return dict(kind=kind, regions=regions, seams=seams, dots=dots, colors=colors,
                head=dict(T=head_t, eyeX=eye_x, scale=float(s)))
