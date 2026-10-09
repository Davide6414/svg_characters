"""Segmentazione di una figura: regioni delimitate dal contorno scuro, occhi e scarpe unite.

Il contorno è la rete di pixel scuri (luminanza ≤ DARK). Le regioni sono le componenti connesse
del resto; gli occhi (macchie scure staccate dalla rete) vengono riempiti e registrati a parte.
"""
import numpy as np
from PIL import Image, ImageDraw

from .geom import dilate, erode, label_components, upsample

K = 2          # fattore di sovracampionamento dei bitmap
DARK = 34      # soglia di luminanza del contorno (separa il nero dei riempimenti, ≈ 44-56, dal tratto, < 25)
EYE_ZONE = 0.35         # gli occhi stanno nel 35% superiore della figura
SHOE_ZONE = 60           # px dal fondo della figura: le regioni delle scarpe hanno il baricentro qui dentro
SOLE_THICKNESS = 14.0    # px: spessore tipico della suola (se manca una suola pulita di riferimento)


class Seg:
    """Risultato della segmentazione di una figura."""

    def __init__(self, box, lum, rgb, dark, lab, n_lab, eyes, dots=()):
        self.box, self.lum, self.rgb, self.dark = box, lum, rgb, dark
        self.lab, self.n_lab, self.eyes, self.dots = lab, n_lab, eyes, list(dots)
        self.sizes = np.bincount(lab.ravel(), minlength=n_lab + 1)
        self.border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]).tolist()) - {0}

    def to_sheet(self, u, v):
        """Coordinate del bitmap → coordinate del foglio."""
        return self.box[0] + u / K, self.box[1] + v / K


def _eyes_and_fill(dark, box):
    """Separa gli occhi dalla rete del contorno: restituisce (maschera scura senza occhi, occhi, puntini).

    Occhi = macchie scure staccate dalla rete, allungate, nella parte alta della figura: vengono riempite (non devono
    bucare la regione della testa) e registrate. Le macchie minuscole si riempiono e si registrano come puntini
    (bottoni, rivetti; sulle sagome sono solo sporco e si ignorano). Le altre macchie
    staccate (per esempio le pieghe di un pantalone) restano scure: sono linee interne."""
    x0, y0, x1, y1 = box
    dl, nd = label_components(dark, conn=8)
    sizes = np.bincount(dl.ravel(), minlength=nd + 1)
    net = int(np.argmax(sizes[1:])) + 1
    eyes, dots = [], []
    for i in range(1, nd + 1):
        if i == net:
            continue
        m = dl == i
        area = sizes[i] / (K * K)
        if area < 120:
            ys, xs = np.nonzero(m)
            if area >= 12:                      # solo i puntini tondi: i frammenti di una linea sono allungati
                ev = np.linalg.eigvalsh(np.cov(np.vstack([xs, ys]) / K))
                if ev[1] <= 2.2 * max(ev[0], 1e-6):
                    dots.append(dict(cx=float(xs.mean() / K + x0), cy=float(ys.mean() / K + y0), r=float(np.sqrt(area / np.pi))))
            dark = dark & ~m
            continue
        ys, xs = np.nonzero(m)
        cov = np.cov(np.vstack([xs, ys]) / K)
        rx, ry = 2 * np.sqrt(cov[0, 0]), 2 * np.sqrt(cov[1, 1])
        cy = ys.mean() / K + y0
        if cy < y0 + EYE_ZONE * (y1 - y0) and ry > 1.5 * rx:
            eyes.append(dict(cx=float(xs.mean() / K + x0), cy=float(cy), area=float(area), rx=float(rx), ry=float(ry)))
            dark = dark & ~m
    eyes.sort(key=lambda e: e['cx'])
    return dark, eyes, dots


def _otsu(values):
    hist, edges = np.histogram(values, bins=64, range=(0, 256))
    total = hist.sum(); sum_all = (hist * (edges[:-1] + 2)).sum()
    best, thr, w0, s0 = -1.0, 128.0, 0, 0.0
    for i, h in enumerate(hist):
        w0 += h; s0 += h * (edges[i] + 2)
        if w0 == 0 or w0 == total:
            continue
        m0, m1 = s0 / w0, (sum_all - s0) / (total - w0)
        var = w0 * (total - w0) * (m0 - m1) ** 2
        if var > best:
            best, thr = var, edges[i + 1]
    return thr


def _central_height(xs):
    """Altezza mediana (px del foglio) di una regione nelle colonne centrali."""
    cols = np.bincount(xs - xs.min()); c = len(cols)
    return float(np.median(cols[c // 5:c - c // 5])) / K


def _split_merged_shoes(lab, dark, lum, box):
    """Su alcune figure tomaia e suola sono un'unica regione perché fra le due manca la linea (nero su bianco,
    o bianco su bianco con la sola ombra). Le separa: per colore se la regione è a due toni, altrimenti con un
    taglio parallelo al bordo inferiore, a una distanza pari allo spessore di una suola pulita.
    Restituisce (etichette, maschera scura) con i pixel scartati assegnati al contorno."""
    x0, y0, x1, y1 = box
    h, w = lab.shape
    n = int(lab.max())
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]).tolist())
    info = {}
    for i in range(1, n + 1):
        if i in border:
            continue
        m = lab == i
        area = m.sum() / (K * K)
        if area < 400 or area > 2600:
            continue
        ys, xs = np.nonzero(m)
        if ys.mean() / K + y0 < y1 - SHOE_ZONE:
            continue
        info[i] = dict(m=m, area=area, height=(ys.max() - ys.min()) / K, ys=ys, xs=xs)
    clean = [r for r in info.values() if r['height'] <= 22 and r['area'] >= 500]
    thick = float(np.median([_central_height(r['xs']) for r in clean])) if clean else SOLE_THICKNESS
    for r in info.values():
        if r['height'] < 27 or r['area'] < 900:
            continue                                  # non è unita: tomaia e suola sono già regioni distinte
        m = r['m']
        core = erode(m, 2.5 * K)
        vals = lum[core] if core.any() else lum[m]
        if vals.std() > 25:                           # due toni: tomaia scura o grigia + suola chiara
            thr = _otsu(vals)
            parts = [m & (lum < thr), m & (lum >= thr)]
        else:                                         # un solo tono: taglio geometrico
            bottom = np.full(w, -1)
            for x in np.unique(r['xs']):
                bottom[x] = r['ys'][r['xs'] == x].max()
            upper = m & (np.arange(h)[:, None] < bottom[None, :] - thick * K)
            parts = [upper, m & ~upper]
        lab[m] = 0
        for part in parts:
            l2, k = label_components(part, conn=4)
            sizes = np.bincount(l2.ravel(), minlength=k + 1)
            for j in range(1, k + 1):
                if sizes[j] / (K * K) >= 30:
                    n += 1
                    lab[l2 == j] = n
    return lab, dark | (lab == 0)


def segment(sheet, box, bridge=(), seal=0):
    """Segmenta la figura inclusa in `box` del foglio. `bridge`: segmenti ((x1, y1), (x2, y2)), in px del foglio, che
    chiudono un'interruzione del contorno (nei fogli generati a volte manca un pezzo di tratto e la regione si fonde con
    lo sfondo): si disegnano come tratto scuro prima di dividere le regioni. `seal` (px del foglio): ispessisce il tratto
    per chiudere le crepe di un pixel (un contorno sottile o sfumato, sopra la soglia di luminanza in qualche punto)."""
    x0, y0, x1, y1 = box
    lum = upsample(sheet.lum[y0:y1, x0:x1], K)
    rgb = np.stack([upsample(sheet.rgb[y0:y1, x0:x1, c], K) for c in range(3)], -1)
    dark0 = lum <= DARK
    if bridge:
        img = Image.new('L', (dark0.shape[1], dark0.shape[0]), 0)
        draw = ImageDraw.Draw(img)
        for (ax, ay), (bx, by) in bridge:
            draw.line([((ax - x0) * K, (ay - y0) * K), ((bx - x0) * K, (by - y0) * K)], fill=255, width=int(4 * K))
        dark0 = dark0 | (np.asarray(img) > 127)
    if seal:
        dark0 = dilate(dark0, seal * K)
    dark, eyes, dots = _eyes_and_fill(dark0, box)
    lab, n = label_components(~dark, conn=4)
    lab, dark = _split_merged_shoes(lab, dark, lum, box)
    # rinumera 1..n senza buchi
    ids = np.unique(lab[lab > 0])
    remap = np.zeros(lab.max() + 1, np.int32)
    remap[ids] = np.arange(1, len(ids) + 1)
    lab = remap[lab]
    return Seg(box, lum, rgb, dark, lab, len(ids), eyes, dots)
