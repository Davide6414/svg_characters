"""Capelli da un foglio di figure intere: ogni figura ha la testa con un'acconciatura diversa.

A differenza di `hair.py` (un foglio con i soli capelli su sfondo trasparente) qui i capelli vanno isolati dalla testa:
- occhi: le due macchie scure più spesse del contorno nella parte alta della figura (apertura morfologica, così
  resistono anche se toccano una ciocca);
- capelli: nella zona della testa (sopra la maglietta), i pixel non scuri lontani dal colore della pelle. Le regioni
  (capelli, pelle, resto) crescono poi fin dentro il contorno, come per le sagome: il confine cade a metà del tratto;
- contorno: solo dove nel foglio c'è un tratto scuro (fra capelli e fronte spesso c'è solo il cambio di colore), come
  linee aperte; la sagoma dei capelli è un riempimento senza tratto;
- linee interne (ciocche) e, se richiesto, capelli sparsi fuori dalla sagoma (sulla testa calva) e una zona rasata.
Le coordinate finali sono quelle del riquadro dei capelli (`hairFrame` del manifest): la testa delle figure ha le
proporzioni della testa di riferimento, quindi basta allineare gli occhi e scalare con la distanza fra gli occhi.
"""
import numpy as np

from .geom import (catmull_d, components_pts, dilate, erode, fill_small_holes, grow_labels, label_components,
                   longest_path, rdp, skeleton_lines, trace_paths, zhang_suen)
from .segment import DARK, K, segment

EYE_X, EYE_Y = 199.4, 357.0     # occhi nella testa di riferimento (media delle sagome riportate nel riquadro)
EYE_SPAN = 38.4                 # distanza fra gli occhi nella testa di riferimento
TOP_Y = 250.0                   # cima del cranio nella testa di riferimento (hairFrame.T)
SKIN_DIST = 60.0                # distanza di colore oltre la quale un pixel della testa è capelli


def all_lines(mask, minlen, max_lines=200):
    """Tutte le linee dello scheletro di `mask`, anche i rami: si prende il cammino più lungo, si toglie solo quello
    e si ricomincia (`skeleton_lines` invece scarta il resto della componente)."""
    work = zhang_suen(mask)
    lines = []
    for _ in range(max_lines):
        comps = [c for c in components_pts(work) if len(c) >= minlen]
        if not comps:
            break
        path = longest_path(max(comps, key=len))
        pm = np.zeros_like(work)
        for y, x in path:
            pm[y, x] = True
        work &= ~dilate(pm, 1.5)
        if len(path) >= minlen:
            lines.append([(float(x), float(y)) for y, x in path])
    return lines


def find_eyes(seg, box):
    """Centri dei due occhi: macchie scure spesse (resistono a un'apertura di raggio 4 px), allungate, in alto."""
    x0, y0, x1, y1 = box
    dark = seg.lum <= DARK + 10
    opened = dilate(erode(dark, 4 * K), 4 * K)
    lab, n = label_components(opened, conn=8)
    eyes = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        area = len(ys) / (K * K)
        if not 120 <= area <= 900 or ys.mean() / K > 0.45 * (y1 - y0):
            continue
        h, w = (ys.max() - ys.min() + 1) / K, (xs.max() - xs.min() + 1) / K
        if h > 1.8 * w:
            eyes.append((xs.mean() / K + x0, ys.mean() / K + y0, i))
    eyes.sort()
    if len(eyes) < 2:
        raise ValueError(f'occhi non trovati ({len(eyes)})')
    # la coppia più vicina in orizzontale, alla stessa altezza
    a, b = min(((a, b) for i, a in enumerate(eyes) for b in eyes[i + 1:] if abs(a[1] - b[1]) < 10),
               key=lambda p: abs(p[1][0] - p[0][0]))
    mask = dilate((lab == a[2]) | (lab == b[2]), 2 * K)
    return a[:2], b[:2], mask


def trace_hair_figure(sheet, box, spec, verbose=False):
    seg = segment(sheet, box)
    x0, y0, x1, y1 = box
    (ex0, ey0), (ex1, ey1), eye_mask = find_eyes(seg, box)
    eye_x, eye_y, span = (ex0 + ex1) / 2, (ey0 + ey1) / 2, abs(ex1 - ex0)
    s = EYE_SPAN / span * spec.get('scale', 1.0)
    kx, ky = spec.get('kx', 1.0), spec.get('ky', 1.0)

    def to_xy(u, v):
        x, y = x0 + u / K, y0 + v / K
        return EYE_X + (x - eye_x) * s * kx, EYE_Y + (y - eye_y) * s * ky + spec.get('dy', 0.0)

    h, w = seg.lab.shape
    rows = np.arange(h)[:, None]
    # pelle: il colore attorno agli occhi (guance e fronte), senza i pixel scuri
    face = np.zeros((h, w), bool)
    cu, cv = int((eye_x - x0) * K), int((eye_y - y0) * K)
    face[max(0, cv - 40 * K):cv + 30 * K, max(0, cu - 30 * K):cu + 30 * K] = True
    skin_px = seg.rgb[face & ~seg.dark & (seg.lum > 120)]
    skin = np.median(skin_px, axis=0)
    # la maglietta: la regione chiara grande sotto la testa; la zona della testa finisce un poco sotto il suo bordo alto
    tee_top = None
    for i in range(1, seg.n_lab + 1):
        if i in seg.border or seg.sizes[i] < 3000 * K * K:
            continue
        m = seg.lab == i
        c = np.median(seg.rgb[m], axis=0)
        ys = np.nonzero(m)[0]
        if c.min() > 215 and ys.mean() / K + y0 > eye_y + 60:
            tee_top = ys.min() if tee_top is None else min(tee_top, ys.min())
    limit = tee_top + int(spec.get('below_tee', 15) * K)
    zone = (rows < limit) & (seg.lab > 0) & ~eye_mask
    tee = np.zeros((h, w), bool)
    for i in np.unique(seg.lab[tee_top:tee_top + 10 * K]):
        if i and i not in seg.border and seg.rgb[seg.lab == i].mean(0).min() > 200:
            tee |= seg.lab == i
    dist = np.linalg.norm(seg.rgb - skin, axis=-1)
    warm = seg.rgb[..., 0] - seg.rgb[..., 2]                      # la pelle è calda (rosso ≫ blu), i capelli grigi no
    background = (seg.rgb.min(-1) > 236) & (seg.rgb.max(-1) - seg.rgb.min(-1) < 14)
    # i pixel sfumati attorno al contorno non contano (hanno colori di mezzo): restano da assegnare, ci pensa la crescita
    clear = zone & ~tee & ~dilate(seg.dark, 1.5 * K) & ~background
    hair = clear & ((dist > SKIN_DIST) | (warm < skin[0] - skin[2] - 45))
    skinlike = clear & ~hair
    # pulizia: via i pezzetti, chiusi i buchi piccoli (riflessi chiari)
    lab, n = label_components(hair, conn=4)
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    keep = np.zeros(n + 1, bool); keep[1:] = sizes[1:] >= 40 * K * K
    hair = fill_small_holes(keep[lab], 60 * K * K)
    shaved = np.zeros_like(hair)
    if spec.get('shaved'):                     # zona rasata: i capelli più chiari della media
        lum = seg.lum
        ref = np.median(lum[hair])
        shaved = hair & (lum > ref + spec['shaved'])
        lab, n = label_components(shaved, conn=4)
        sizes = np.bincount(lab.ravel(), minlength=n + 1)
        keep = np.zeros(n + 1, bool); keep[1:] = sizes[1:] >= 150 * K * K
        shaved = fill_small_holes(keep[lab], 60 * K * K)
        hair &= ~shaved
    # etichette per la crescita (a parità vince la più alta: i capelli): 1 resto, 2 pelle, 3 rasato, 4 capelli;
    # 0 = da assegnare (contorno e pixel sfumati della testa)
    REST, SKIN, SHAVED, HAIR = 1, 2, 3, 4
    lab = np.full((h, w), REST, np.int32)
    lab[zone & ~tee & ~background] = 0
    lab[skinlike] = SKIN
    lab[hair] = HAIR
    lab[shaved] = SHAVED
    lab[seg.dark] = 0
    g = grow_labels(lab, lab == 0)
    if spec.get('fit_top'):                   # testa calva: la cima del cranio si vede, si allinea anche quella
        top = np.nonzero((g == SKIN).any(1))[0].min() / K + y0 - 2.5
        ky = (EYE_Y - TOP_Y) / ((eye_y - top) * s)
        if verbose:
            print(f'  cima del cranio {top:.0f}: ky {ky:.3f}')
    cell = fill_small_holes(g == HAIR, 60 * K * K)
    cell_shaved = g == SHAVED
    # contorno: il bordo della sagoma dove nel foglio c'è un tratto scuro
    near_dark = dilate(seg.dark, 2.5 * K)
    edge = (cell | cell_shaved) & ~erode(cell | cell_shaved, 1.0)
    outlined = dilate(edge & near_dark, 1.5 * K)
    outline = [catmull_d(rdp(p, 1.1 * K), to_xy) for p in all_lines(outlined, 6 * K)]
    # linee interne: tratti scuri dentro la sagoma, lontani dal bordo
    inner = seg.dark & erode(cell | cell_shaved, 4.5 * K)
    lines = []
    for p in all_lines(inner, spec.get('min_line', 10) * K):
        pm = np.zeros((h, w), bool)
        for x, y in p:
            pm[int(y), int(x)] = True
        thick = float((dilate(pm, 3 * K) & seg.dark).sum() / len(p) / K)
        lines.append(dict(d=catmull_d(rdp(p, 1.1 * K), to_xy), thick=thick, length=len(p) / K))
    # capelli sparsi sopra una testa calva: tratti scuri sottili fuori dalla sagoma, sopra la testa
    strays = []
    if spec.get('strays'):
        others = (g != REST)
        loose = seg.dark & (g == REST) & ~dilate(others, 3.0 * K) & (rows < (eye_y - y0 - 40) * K)
        for p in skeleton_lines(dilate(loose, 0.5 * K), 8 * K, max_lines=12):
            strays.append(catmull_d(rdp(p, 1.1 * K), to_xy))
    fill = trace_paths(cell, to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20 * K, smooth=1.0)
    fill_shaved = trace_paths(cell_shaved, to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20 * K, smooth=1.0) if cell_shaved.any() else []
    core = erode(hair, 3 * K)
    vals = seg.rgb[core if core.any() else hair]
    color = '#%02x%02x%02x' % tuple(int(round(v)) for v in np.median(vals, axis=0))
    if verbose:
        print(f'  occhi ({eye_x:.0f}, {eye_y:.0f}) distanza {span:.1f} → scala {s:.3f}; pelle {skin.astype(int)}; '
              f'sagoma {len(fill)} percorsi, contorno {len(outline)}, linee {len(lines)}, sparsi {len(strays)}, colore {color}')
    return dict(fill=fill, shaved=fill_shaved, outline=outline, lines=lines, strays=strays, color=color)
