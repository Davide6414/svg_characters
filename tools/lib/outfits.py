"""Tracciatura degli outfit: ogni figura del foglio indossa una maglia e dei pantaloni sul proprio corpo.

A differenza dei fogli dei vestiti maschili (stesso corpo, capi diversi), qui ogni figura è un corpo diverso: il
corpo di riferimento di un capo è la sagoma su cui è disegnato (stessa testa e stessa linea del suolo: si allinea
con la testa e il suolo). Le regioni della figura vengono assegnate a mano (tabella in `trace_outfits.py`) a un
capo e a un ruolo di colore:

  main, trim, accent, accent2, under   i colori del capo (variabili CSS --shirt… / --pants…)
  skin                                 pelle che il capo lascia scoperta (gambe sotto i pantaloncini, pancia, spalle)

Oltre alle regioni delimitate dal contorno ci sono dettagli senza contorno, che si ricavano dal colore dentro una
regione (fiore, risvolto, calze) e si disegnano sopra la regione senza tratto, e la pelle dello scollo, che sta
nella regione della testa (sotto la linea del collo della sagoma). La pancia scoperta sta in un livello sotto i
pantaloni (`layer: under`), così la sua posizione non dipende dai pantaloni scelti.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .geom import dilate, erode, fill_small_holes, grow_labels, label_components, trace_paths
from .parts import GROUND, PAD, find_folds, find_seams, region_info
from .segment import K, segment

SHOE_BAND = 45        # px sopra la cima delle suole: le regioni più in basso sono scarpe
STROKE_INSET = 2.5    # px: i dettagli senza contorno stanno dentro la cella, senza coprire il tratto del bordo
NECK_OVERLAP = 3.0    # px: la pelle dello scollo sale sul collo, per coprire il fondo della testa della sagoma


def _hex(c):
    return '#%02x%02x%02x' % tuple(int(round(v)) for v in c)


# Regole di colore per i dettagli (pixel RGB di una regione → maschera)
def _rule_white(rgb, ref_lum):
    return (rgb.min(-1) > 218) & (rgb.max(-1) - rgb.min(-1) < 36)


def _rule_orange(rgb, ref_lum):
    return (rgb[..., 0] > 225) & (rgb[..., 1] > 115) & (rgb[..., 1] < 200) & (rgb[..., 2] < 135)


def _rule_lighter(rgb, ref_lum):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) > ref_lum + 16


RULES = {'white': _rule_white, 'orange': _rule_orange, 'lighter': _rule_lighter}


def _smooth_mask(mask, sigma, min_area, close=0):
    """Toglie il rumore a una maschera di colore: chiusura (per le righe sottili, come la piega di una calza),
    sfocatura + soglia, componenti troppo piccole scartate."""
    if close:
        mask = erode(dilate(mask, close * K), close * K)
    img = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(sigma * K))
    m = np.array(img) > 127
    lab, n = label_components(m, conn=4)
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    keep = np.zeros(n + 1, bool)
    keep[1:] = sizes[1:] / (K * K) >= min_area
    return fill_small_holes(keep[lab], 12 * K * K)


def _extend_rows(mask, up, down):
    """Allunga una maschera in verticale: ogni pixel si ripete `up` righe sopra e `down` righe sotto."""
    out = mask.copy()
    for k in range(1, int(up * K) + 1):
        out[:-k] |= mask[k:]
    for k in range(1, int(down * K) + 1):
        out[k:] |= mask[:-k]
    return out


def _hull(mask):
    """Involucro convesso di una maschera (catena monotona sui bordi di ogni riga, poi riempimento del poligono)."""
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
    hull = half(pts)[:-1] + half(pts[::-1])[:-1]
    img = Image.new('L', (mask.shape[1], mask.shape[0]), 0)
    ImageDraw.Draw(img).polygon(hull, fill=255)
    return np.array(img) > 0


def _extend_top(cell, up, notch=35):
    """Parte alta dei pantaloni: un rettangolo largo come i primi `notch` px dall'alto, `up` px sopra il bordo alto e
    `notch` px sotto (riempie i vani fra il bordo alto frastagliato, l'orlo di una maglia, e i pantaloni). Così, con una maglia più
    corta o un orlo diverso, non resta un buco in vita."""
    rows = np.nonzero(cell.any(1))[0]
    top = rows.min()
    cols = np.nonzero(cell[top:top + int(notch * K)].any(0))[0]
    rect = np.zeros_like(cell)
    inset = int(10 * K)                                          # più stretto del bordo: non deve sporgere ai fianchi della maglia
    rect[max(0, top - int(up * K)):top + int(notch * K), cols.min() + inset:cols.max() + 1 - inset] = True
    return cell | rect


def trace_outfit(sheet, box, ref, spec, verbose=False):
    """Traccia maglia e pantaloni della figura in `box`. `ref` = dati (testa, punti di riferimento) della sagoma su
    cui è disegnata. `spec` = {'top': capo, 'bottom': capo}, ogni capo con `regions` {indice: ruolo}.
    Restituisce {'top': garment, 'bottom': garment}."""
    seg = segment(sheet, box)
    info = region_info(seg)
    x0, y0, x1, y1 = box
    e = seg.eyes
    head = int(seg.lab[int((e[0]['cy'] - y0) * K), int((e[0]['cx'] - x0) * K)])
    g = grow_labels(seg.lab, seg.dark)
    used = {i for kind in ('top', 'bottom') for i in spec[kind]['regions']}

    # suolo e allineamento alla sagoma: testa e linea del suolo
    cand = [i for i, r in info.items() if not r['bg'] and i != head and r['area'] >= 350]
    soles = sorted(cand, key=lambda i: -info[i]['cy'])[:2]
    sole_top = min(info[i]['cy'] for i in soles)
    shoes = [i for i, r in info.items() if not r['bg'] and i not in used and i != head and r['cy'] >= sole_top - SHOE_BAND]
    bottom_y = max(np.nonzero(g == i)[0].max() for i in soles) / K + y0
    dy = bottom_y - GROUND
    ys, xs = np.nonzero(seg.lab == head)
    head_t = float(ys.min() / K + y0 - dy - 2.5)
    eye_x = float((e[0]['cx'] + e[1]['cx']) / 2)
    rx, rt = ref['head']['eyeX'], ref['head']['T']
    s = (GROUND - rt) / (GROUND - head_t)

    def to_xy(u, v):
        x, y = x0 + u / K, y0 + v / K - dy
        return rx + (x - eye_x) * s, rt + (y - head_t) * s

    cells = {i: (g == i) for i in list(used) + shoes + [head]}
    shoe_cells = np.zeros_like(seg.dark)
    for i in shoes:
        shoe_cells |= cells[i]
    med = {}
    for i in used:
        core = erode(seg.lab == i, 2 * K)
        med[i] = np.median(seg.rgb[core], axis=0) if core.any() else info[i]['rgb']
    v_idx = np.arange(g.shape[0])[:, None]

    out = {}
    for kind in ('top', 'bottom'):
        cs = spec[kind]
        labels = set(cs['regions'])
        base, overlays, strokes = [], [], []          # ordine di disegno: regioni, dettagli senza contorno, tratti sopra i dettagli

        def trace(mask):
            return trace_paths(fill_small_holes(mask, 30 * K * K), to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0)

        def add(target, role, mask, color, layer, stroke, part=None):
            paths = trace(mask)
            if paths:
                target.append(dict(role=role, layer=layer, stroke=stroke, area=float(mask.sum() / (K * K)),
                                   med=[float(v) for v in color], d=paths, part=part))

        for i, role in cs['regions'].items():
            cell = cells[i]
            layer = cs.get('layers', {}).get(i, 'main')
            if i in cs.get('pad_under', {}):                      # pelle del livello sotto: si estende in verticale sotto i capi vicini
                pad = cs['pad_under'][i]
                near = np.zeros_like(seg.dark)
                for j in pad['near']:
                    near |= cells[j]
                cell = cell | (_extend_rows(cell, pad['up'], pad['down']) & near)
            if i in cs.get('behind', {}):                         # prosegue dietro le braccia (un pugno sui pantaloni)
                arms = np.zeros_like(seg.dark)
                for j in cs['behind'][i]:
                    arms |= g == j
                cell = cell | (_hull(cell) & arms)
            if i in cs.get('to_shoes', ()):                       # scende sotto le scarpe, così l'orlo non si vede
                cell = cell | (dilate(cell, PAD * K) & shoe_cells)
            details = cs.get('split', {}).get(i, ())
            # con dei dettagli sopra, la regione si disegna in due tempi: riempimento, dettagli, poi il tratto del bordo
            add(base, role, cell, med[i], layer, stroke=not details, part=cs.get('parts', {}).get(i))
            if i in cs.get('under_up', {}):                       # i pantaloni salgono sotto la maglia: nessun buco con altre maglie
                add(base, role, _extend_top(cells[i], cs['under_up'][i]), med[i], 'under', stroke=True)
            if details:
                add(strokes, 'open', cell, med[i], layer, stroke=True)
            if verbose:
                print(f'  {kind} regione {i:2d} {role:7s} area {info[i]["area"]:6.0f} {_hex(med[i])}')
            ref_lum = 0.299 * med[i][0] + 0.587 * med[i][1] + 0.114 * med[i][2]
            band = cells[i] & ~erode(cells[i], 4 * K)
            for drole, rule in details:
                m = _smooth_mask(RULES[rule](seg.rgb, ref_lum) & cells[i], 1.2, 25, close=3)
                m |= band & dilate(m, 4 * K)                      # fino al bordo: il tratto lo copre
                if m.any():
                    color = np.median(seg.rgb[m & ~seg.dark], axis=0)
                    if i in cs.get('to_shoes', ()):
                        m = m | (dilate(m, PAD * K) & shoe_cells)
                    add(overlays, drole, m, color, layer, stroke=False)
                    if verbose:
                        print(f'    dettaglio {drole:7s} {rule:8s} area {m.sum() / (K * K):6.0f} {_hex(color)}')
        if cs.get('neck'):                                        # pelle dello scollo: parte bassa della regione della testa
            cut = (ref['landmarks']['neck-l'][1] - rt) / s + head_t + dy - NECK_OVERLAP     # y del foglio
            m = _smooth_mask(erode(cells[head], STROKE_INSET * K) & (v_idx >= (cut - y0) * K), 0.8, 20)
            if m.any():
                add(overlays, 'skin', m, (252, 190, 154), 'main', stroke=False)
                if verbose:
                    print(f'    scollo area {m.sum() / (K * K):.0f}')

        # linee interne: fessure scure (cuciture, tasche, cordini) e pieghe chiare (solo dove richiesto; per i
        # pantaloni, la regione principale)
        seams = find_seams(seg, g, labels, to_xy)
        fold_regions = cs.get('folds', (max((i for i, r in cs['regions'].items() if r != 'skin'), key=lambda i: info[i]['area']),)
                              if kind == 'bottom' else ())
        for i in fold_regions:
            seams += find_folds(seg, g, i, to_xy)
        for sm in seams:                                       # tre spessori: contorno, fine (cuciture), filo (pieghe chiare e punti)
            sm['hair'] = sm['kind'] == 'fold' or sm.get('thick', 0) < 3.5
            sm['fine'] = not sm['hair'] and sm.get('thick', 0) < 4.7
            sm['layer'] = cs.get('layers', {}).get(sm['label'], 'main')
        dots = []
        for dt in seg.dots:
            u, v = (dt['cx'] - x0) * K, (dt['cy'] - y0) * K
            if g[int(v), int(u)] in labels:
                x, y = to_xy(u, v)
                dots.append(dict(cx=round(x, 1), cy=round(y, 1), r=round(dt['r'] * s, 1), layer='main'))

        # colori di partenza: il più esteso di ogni ruolo (la pelle usa il colore della sagoma)
        regions = sorted(base, key=lambda r: (not r['part'], -r['area'])) + overlays + strokes      # le parti sostitutive per prime
        colors = {}
        for role in ('main', 'trim', 'accent', 'accent2', 'under'):
            rs = [r for r in regions if r['role'] == role]
            if rs:
                colors[role] = _hex(max(rs, key=lambda r: r['area'])['med'])
        garment = dict(kind=kind, regions=regions, seams=seams, dots=dots, colors=colors,
                       replaces=sorted({r['part'] for r in regions if r['part']}))

        # l'orlo alto dei pantaloni (in vita, sotto la maglia) si aggancia a quello dei pantaloni della sagoma: il capo
        # è disegnato sotto una maglia di lunghezza diversa, e su un corpo più alto l'altezza in più verrebbe ingrandita
        marks = {}
        if kind == 'bottom':
            tops = [to_xy(0, np.nonzero(g == i)[0].min())[1] for i, r in cs['regions'].items() if r != 'skin']
            for corner in ('tl', 'tr'):
                marks[f'pants-{corner}'] = [ref['landmarks'][f'pants-{corner}'][0], round(float(min(tops)), 1)]
            garment['landmarks'] = marks

        # maniche più corte di quelle della sagoma di base: il braccio della sagoma comincia più in basso e fra manica e
        # braccio resterebbe un buco. Si aggancia l'orlo della manica all'inizio del braccio (punti di riferimento).
        if cs.get('arms'):
            for side, i in zip(('armL', 'armR'), cs['arms']):
                top = to_xy(0, np.nonzero(g == i)[0].min())[1]
                if top < ref['landmarks'][f'{side}-tl'][1]:
                    for corner in ('tl', 'tr'):
                        x = ref['landmarks'][f'{side}-{corner}'][0]
                        marks[f'{side}-{corner}'] = [x, round(float(top), 1)]
            garment['landmarks'] = marks
        out[kind] = garment
    return out
