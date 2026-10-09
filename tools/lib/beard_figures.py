"""Barbe da un foglio di figure intere: ogni figura ha la stessa testa calva con una barba diversa.

Come per i capelli da figure (`hair_figures.py`) le figure si allineano alla testa di riferimento con gli occhi (stessa
posizione, scala dalla distanza fra gli occhi) e le coordinate finali sono quelle del riquadro dei capelli (`hairFrame`).
La barba è la regione scura e calda del viso basso; la zona della testa si segmenta come le sagome (regioni delimitate
dal contorno, che crescono fin dentro il tratto). Una barba ha:
- `fill`: la sagoma (con il buco della bocca, dove si vede la pelle);
- `ext`: la sagoma allargata oltre il contorno della testa del foglio. Nella testa di ogni sagoma la barba non combacia con
  il contorno del foglio: la build disegna `ext` fra il riempimento della testa e il suo contorno, ritagliata sulla
  testa, così la barba arriva sempre fino al bordo del viso e non resta una striscia di pelle;
- `outline`: il contorno (anche attorno al buco della bocca) e `lines`: le linee interne (baffi, ciocche);
- `dots`: la barba incolta, che sono puntini sulla pelle (e qualche tratto, come il segno della bocca).
"""
import numpy as np

from .geom import (catmull_d, dilate, erode, fill_small_holes, grow_labels, label_components, rdp, skeleton_lines,
                   trace_paths)
from .hair_figures import EYE_SPAN, EYE_X, EYE_Y, all_lines, find_eyes
from .segment import K, segment

EXTEND = 7.0        # px del foglio: quanto si allarga `ext` oltre il contorno della testa


def trace_beard_figure(sheet, box, spec, verbose=False):
    seg = segment(sheet, box)
    x0, y0, x1, y1 = box
    (ex0, ey0), (ex1, ey1), eye_mask = find_eyes(seg, box)
    eye_x, eye_y, span = (ex0 + ex1) / 2, (ey0 + ey1) / 2, abs(ex1 - ex0)
    s = EYE_SPAN / span * spec.get('scale', 1.0)

    def to_xy(u, v):
        return EYE_X + (x0 + u / K - eye_x) * s, EYE_Y + (y0 + v / K - eye_y) * s

    h, w = seg.lab.shape
    rows = np.arange(h)[:, None]
    cols = np.arange(w)[None, :]
    # il viso basso: sotto gli occhi, attorno a loro, fino al collo
    zone = ((rows >= (eye_y - y0 + 4) * K) & (rows <= (eye_y - y0 + spec.get('below', 125)) * K)
            & (cols >= (eye_x - x0 - 105) * K) & (cols <= (eye_x - x0 + 70) * K))
    rgb = seg.rgb
    lum = seg.lum
    # la barba: pixel scuri e caldi (marrone) nel viso basso. Il bordo sfumato del contorno ha colori simili ma è sottile:
    # un'apertura lo toglie; una barba a ciocche ha tratti neri dentro, che la chiusura ricompone.
    warm_dark = zone & ~eye_mask & (lum < 125) & (rgb[..., 0] - rgb[..., 2] > 14)
    solid = dilate(erode(warm_dark, 1.5 * K), 1.5 * K) & warm_dark
    lab_b, n_b = label_components(solid, conn=8)
    sizes_b = np.bincount(lab_b.ravel(), minlength=n_b + 1)
    keep = np.zeros(n_b + 1, bool)
    keep[1:] = sizes_b[1:] >= 120 * K * K
    beard_px = keep[lab_b]
    beard_px = erode(dilate(beard_px, 3 * K), 3 * K) | beard_px            # chiusura: le ciocche nere dentro la barba
    skin_px = (rgb[..., 0] > 200) & (rgb[..., 1] > 150) & (rgb[..., 1] < 215) & (rgb[..., 0] - rgb[..., 2] > 45)
    # etichette per la crescita: 1 resto, 2 pelle, 3 barba; 0 = da assegnare (il contorno e i pixel sfumati)
    REST, SKIN, BEARD = 1, 2, 3
    lab = np.full((h, w), REST, np.int32)
    lab[skin_px & ~seg.dark] = SKIN
    lab[beard_px & ~seg.dark] = BEARD
    lab[eye_mask] = SKIN
    lab[seg.dark & ~eye_mask] = 0
    near_edge = dilate(seg.dark | beard_px, 2.5 * K)
    lab[~skin_px & ~beard_px & ~seg.dark & near_edge & ~eye_mask & (lab == REST)] = 0    # pixel sfumati attorno al contorno
    g = grow_labels(lab, lab == 0)
    beard_labels = [1] if beard_px.any() else []
    cell = fill_small_holes(g == BEARD, 60 * K * K) if beard_labels else np.zeros((h, w), bool)
    outside = g == REST
    fill, ext, outline, lines = [], [], [], []
    color = '#2a211c'
    if cell.any():
        fill = trace_paths(cell, to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20 * K, smooth=1.0)
        # allargata solo verso l'esterno (non sulla pelle del viso: sopra il bordo della barba resta la pelle)
        ext_mask = cell | (dilate(cell, EXTEND * K) & outside)
        ext = trace_paths(ext_mask, to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20 * K, smooth=1.0)
        near_dark = dilate(seg.dark, 2.5 * K)
        edge = cell & ~erode(cell, 1.0)
        outlined = dilate(edge & near_dark, 1.5 * K)
        outline = [catmull_d(rdp(p, 1.1 * K), to_xy) for p in all_lines(outlined, 6 * K)]
        inner = seg.dark & erode(cell, 4.5 * K)
        for p in all_lines(inner, spec.get('min_line', 10) * K):
            pm = np.zeros((h, w), bool)
            for x, y in p:
                pm[int(y), int(x)] = True
            thick = float((dilate(pm, 3 * K) & seg.dark).sum() / len(p) / K)
            lines.append(dict(d=catmull_d(rdp(p, 1.1 * K), to_xy), thick=thick))
        core = erode(cell, 3 * K)
        vals = seg.rgb[core if core.any() else cell]
        color = '#%02x%02x%02x' % tuple(int(round(v)) for v in np.median(vals, axis=0))
    dots, marks = [], []
    if spec.get('stubble'):
        # puntini sulla pelle: macchie scure piccole (nel foglio sono grigie, non nere come il contorno) lontane dal
        # contorno spesso della testa; il segno della bocca è l'unica macchia più grande
        lum = seg.lum
        thick_outline = dilate(erode(seg.dark, 2.5 * K), 0.8 * K)
        cand = (lum < spec.get('dot_lum', 100)) & zone & ~eye_mask & ~thick_outline
        lab_d, n_d = label_components(cand, conn=8)
        sizes = np.bincount(lab_d.ravel(), minlength=n_d + 1)
        for i in range(1, n_d + 1):
            area = sizes[i] / (K * K)
            if area < 1.5:
                continue
            ys, xs = np.nonzero(lab_d == i)
            if area <= spec.get('dot_max', 22):
                dots.append(to_xy(xs.mean(), ys.mean()))
        big = [i for i in range(1, n_d + 1) if spec.get('dot_max', 22) < sizes[i] / (K * K) < spec.get('mark_max', 60)]   # il segno della bocca
        for i in big:
            m = lab_d == i
            for p in skeleton_lines(dilate(m, 0.5 * K), 5 * K, max_lines=3):
                marks.append(catmull_d(rdp(p, 1.1 * K), to_xy))
        vals = seg.rgb[(lum < 60) & zone & ~eye_mask & ~thick_outline]
        if len(vals):
            color = '#%02x%02x%02x' % tuple(int(round(v)) for v in np.median(vals, axis=0))
    if verbose:
        print(f'  occhi ({eye_x:.0f}, {eye_y:.0f}) distanza {span:.1f} → scala {s:.3f}; barba {len(beard_labels)} regioni, '
              f'sagoma {len(fill)} percorsi, contorno {len(outline)}, linee {len(lines)}, puntini {len(dots)}, colore {color}')
    return dict(fill=fill, ext=ext, outline=outline, lines=lines, dots=dots, marks=marks, color=color)
