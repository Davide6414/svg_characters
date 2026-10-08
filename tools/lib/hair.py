"""Tracciatura di uno stile di capelli da un foglio con sfondo trasparente.

La sagoma è il contorno (centro del tratto scuro) della silhouette; le linee interne (ciocche, separazioni)
sono scheletri del tratto scuro lontano dal bordo. Le coordinate finali sono quelle del "riquadro dei
capelli": la testa di riferimento a cui i capelli sono stati allineati (orecchio, scala).
"""
import numpy as np

from .geom import (catmull_d, dilate, erode, fmt, rdp, skeleton_lines, trace_paths, upsample)

K = 3
LINE_W = 5.4       # spessore del contorno nelle coordinate finali
T_BAND = 10.0      # px del foglio: fascia del contorno, escluse le linee interne
PULL = 2.5         # px del foglio: le linee interne si fermano prima del centro del contorno


class HairSheet:
    def __init__(self, image):
        a = np.asarray(image.convert('RGBA')).astype(np.float32)
        self.alpha = a[..., 3]
        self.rgb = a[..., :3]
        lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
        self.lum = np.where(self.alpha > 128, lum, 255.0)    # bianco fuori dalla sagoma


def _to_final(cfg):
    x0, y0 = cfg['box'][:2]; nx, ny = cfg['notch']; ex, ey = cfg['ear']; s = cfg['s']

    def f(px, py):
        return ((px / K + x0 - nx) * s + ex, (py / K + y0 - ny) * s + ey)
    return f


def _crop(arr, box):
    x0, y0, x1, y1 = box
    return arr[y0:y1, x0:x1]


def silhouette(sheet, cfg):
    """Percorso chiuso della sagoma, al centro del contorno."""
    s_mask = upsample(_crop(sheet.alpha, cfg['box']), K) > 127
    inner = erode(s_mask, (LINE_W / cfg['s'] / 2) * K)
    paths = trace_paths(inner, _to_final(cfg), opttol=2.5, alphamax=1.0, turd=30)
    assert len(paths) == 1, f'la sagoma dovrebbe essere un solo percorso, trovati {len(paths)}'
    return paths[0]


def fill_color(sheet, cfg):
    """Colore di riempimento: mediana dei pixel interni della sagoma."""
    s_mask = upsample(_crop(sheet.alpha, cfg['box']), K) > 127
    inner = erode(s_mask, 8 * K)
    x0, y0, x1, y1 = cfg['box']
    rgb = np.stack([upsample(sheet.rgb[y0:y1, x0:x1, c], K) for c in range(3)], -1)
    # fra i pixel interni, solo quelli chiari (esclude le linee interne scure)
    lum = upsample(_crop(sheet.lum, cfg['box']), K)
    vals = rgb[inner & (lum > np.percentile(lum[inner], 30))]
    return '#%02x%02x%02x' % tuple(int(round(v)) for v in np.median(vals, axis=0))


def _march(a, v, near, s_mask, dark, maxsteps):
    """Avanza da `a` lungo `v` finché tocca la fascia del contorno (punto) o esce dal tratto scuro (None)."""
    h, w = near.shape
    cur = np.array(a, float)
    for _ in range(maxsteps):
        cur = cur + v
        x, y = int(round(cur[0])), int(round(cur[1]))
        if not (0 <= x < w and 0 <= y < h) or not s_mask[y, x]:
            return None
        if near[y, x]:
            return cur
        if not dark[y, x]:
            xx, yy = int(round(cur[0] + 2 * v[0])), int(round(cur[1] + 2 * v[1]))
            if not (0 <= xx < w and 0 <= yy < h and dark[yy, xx]):
                return None
    return None


def _fit_quad(pts):
    p = np.array(pts, float)
    t = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]; t /= t[-1]
    p0, p2 = p[0], p[-1]
    b = 2 * t * (1 - t)
    mid = p - np.outer((1 - t) ** 2, p0) - np.outer(t ** 2, p2)
    return p0, (mid * b[:, None]).sum(0) / (b * b).sum(), p2


def interior_lines(sheet, cfg, long_raw=150, minlen=10.0):
    """Linee interne: [{d, raw}] dalla più lunga. Le corte (cunei che partono dalle tacche) sono archi
    quadratici che finiscono sul contorno; le lunghe sono curve Catmull-Rom."""
    to_final = _to_final(cfg)
    s_mask = upsample(_crop(sheet.alpha, cfg['box']), K) > 127
    lum = upsample(_crop(sheet.lum, cfg['box']), K)
    dark = (lum < 30) & s_mask
    e = erode(s_mask, (LINE_W / cfg['s'] / 2) * K)
    et = s_mask
    for _ in range(4):
        et = erode(et, T_BAND * K / 4)
    bd = e & ~erode(e, 1.5)
    near = dilate(bd, PULL * K)
    by, bx = np.nonzero(bd)
    out = []
    for pts in skeleton_lines(dark & et, minlen * K, max_lines=40):
        dist_end = [float(np.sqrt(((bx - pts[i][0]) ** 2 + (by - pts[i][1]) ** 2).min())) for i in (0, -1)]
        if len(pts) < long_raw:
            b_end = 0 if dist_end[0] <= dist_end[1] else -1
            pp = pts[::-1] if b_end == 0 else pts[:]            # pp[-1] = lato contorno
            trim = int(4 * K)
            core = pp[:-trim] if len(pp) > trim + 6 else pp
            p0, c1, p2 = _fit_quad(core)
            v = p2 - c1; v = v / (np.hypot(*v) + 1e-9)
            hit = _march(p2, v, near, s_mask, dark, int(26 * K))
            end = hit if hit is not None else p2 + v * trim
            a, b, c = to_final(*p0), to_final(*c1), to_final(*end)
            d = f'M{fmt(a[0])},{fmt(a[1])}Q{fmt(b[0])},{fmt(b[1])} {fmt(c[0])},{fmt(c[1])}'
        else:
            pts = list(pts)
            for e_i in (0, -1):
                if dist_end[0 if e_i == 0 else 1] > (T_BAND + 8) * K:
                    continue
                a = np.array(pts[e_i])
                bq = np.array(pts[e_i + 14] if e_i == 0 else pts[e_i - 15]) if len(pts) > 20 else np.array(pts[-1 if e_i == 0 else 0])
                v = a - bq; v /= np.hypot(*v) + 1e-9
                hit = _march(a, v, near, s_mask, dark, int(18 * K))
                if hit is not None:
                    pts.insert(0, tuple(hit)) if e_i == 0 else pts.append(tuple(hit))
            d = catmull_d(rdp(pts, 1.5 * K), to_final)
        out.append(dict(d=d, raw=len(pts)))
    return out
