"""Sagome aliene: dalla segmentazione alle parti del corpo (testa, maglia, braccia, pantaloncini, gambe).

Come per le sagome umane (`parts.py`) ogni parte è la cella di Voronoi della sua regione: il confine cade a metà del
tratto scuro del contorno, e il contorno si disegna come tratto centrato (var --line-w). Cambia la classificazione: un
alieno è tutto della stessa pelle, quindi testa, braccia e gambe si distinguono per posizione e non per colore, e non ci
sono scarpe (i piedi fanno parte delle gambe, con le linee delle dita).
"""
import numpy as np

from .geom import dilate, erode, fill_small_holes, grow_labels, trace_paths, zhang_suen
from .parts import _hex, find_seams, region_info
from .segment import K, segment

GROUND = 900.0            # y della linea del suolo, la stessa delle sagome umane
CENTER_X = 975.0          # x del centro di ogni figura (le coordinate orizzontali non contano: la build centra il riquadro)
HEIGHT = 690.0            # altezza (px) della figura più alta, come un adulto umano
ROLES = ('head', 'torso', 'arm-left', 'arm-right', 'pants', 'leg-left', 'leg-right')


# ---------------------------------------------------------------- classificazione
def _is_white(r):
    return r['rgb'].min() > 205 and r['rgb'].max() - r['rgb'].min() < 40


def _is_grey(r):
    return r['lum'] < 150 and r['rgb'].max() - r['rgb'].min() < 30


def _is_skin(r):
    red, green, blue = r['rgb']
    return green > red + 3 and green > blue + 18 and r['lum'] > 100


def classify_alien(seg, roles=None):
    """Assegna a ogni regione un ruolo: head, torso (la maglia), arm-left, arm-right, pants (i pantaloncini),
    leg-left, leg-right. Restituisce (info, classi). `roles` = {indice regione: ruolo} corregge una figura che si
    classifica male (per vedere gli indici: `-v`)."""
    x0, y0, x1, y1 = seg.box
    info = region_info(seg)
    e = seg.eyes[0]
    head = int(seg.lab[int((e['cy'] - y0) * K), int((e['cx'] - x0) * K)])
    inner = {i: r for i, r in info.items() if not r['bg'] and i != head}
    h = y1 - y0
    cls = {head: 'head'}
    cls[max((i for i, r in inner.items() if _is_white(r) and r['cy'] < y0 + 0.65 * h), key=lambda i: inner[i]['area'])] = 'torso'
    cls[max((i for i, r in inner.items() if _is_grey(r)), key=lambda i: inner[i]['area'])] = 'pants'
    # le quattro regioni di pelle più grandi (dopo la testa): le due più in basso sono le gambe (coi piedi), le altre le braccia
    skin = sorted((i for i, r in inner.items() if _is_skin(r) and i not in cls and r['area'] >= 300), key=lambda i: -info[i]['area'])[:4]
    if len(skin) < 4:
        raise ValueError(f'servono quattro regioni di pelle (due braccia, due gambe), trovate {len(skin)}: vedi -v o `roles`')
    skin.sort(key=lambda i: -info[i]['cy'])
    legs, arms = sorted(skin[:2], key=lambda i: info[i]['cx']), sorted(skin[2:], key=lambda i: info[i]['cx'])
    cls[legs[0]], cls[legs[1]] = 'leg-left', 'leg-right'
    cls[arms[0]], cls[arms[1]] = 'arm-left', 'arm-right'
    for i, role in (roles or {}).items():
        cls[i] = role
    return info, cls


def absorb_small(seg, g, info, cls, max_share=0.25):
    """Le regioni piccole che toccano UNA sola parte (un dito o una punta chiusi da una linea, un lembo di maglia) ne
    fanno parte: restano regioni a sé, col loro contorno, ma nello stesso gruppo. Quelle che ne toccano più d'una (lo
    sfondo racchiuso fra i piedi, fra il braccio e il busto) restano fuori, tranne il collo (pelle fra testa e maglia)."""
    base = dict(cls)
    cells = {i: (g == i) for i in base}
    for i, r in sorted(info.items()):
        if i in base or r['bg']:
            continue
        near = dilate(g == i, 2 * K)
        touched = {base[j] for j in base if (near & cells[j]).any()}
        if _is_skin(r) and 'head' in touched and touched <= {'head', 'torso'}:
            cls[i] = 'head'                                      # il collo, se il foglio lo separa dalla testa
            continue
        if len(touched) != 1:
            continue
        role = next(iter(touched))
        total = sum(info[j]['area'] for j in base if base[j] == role)
        if r['area'] < max_share * total:
            cls[i] = role
    return cls


# ---------------------------------------------------------------- misure
def stroke_width(seg):
    """Spessore tipico del contorno, in px del foglio: area scura / lunghezza dello scheletro."""
    sk = zhang_suen(seg.dark)
    return float(seg.dark.sum() / K / K) / max(float(sk.sum() / K), 1.0)


def _box(prefix, mask, to_xy):
    ys, xs = np.nonzero(mask)
    u0, u1, v0, v1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return {f'{prefix}-tl': to_xy(u0, v0), f'{prefix}-tr': to_xy(u1, v0), f'{prefix}-bl': to_xy(u0, v1), f'{prefix}-br': to_xy(u1, v1)}


def landmarks(cells, cls, to_xy):
    """Punti di riferimento (coordinate finali): collo e riquadri di busto, braccia, pantaloncini e gambe; il suolo sotto
    ogni piede. Servono ai capi e agli accessori che verranno disegnati su questi corpi."""
    by_role = {}
    for i, c in cls.items():
        by_role[c] = cells[i] if c not in by_role else by_role[c] | cells[i]            # una parte può avere più regioni
    out = {}
    head = by_role['head']
    ys, xs = np.nonzero(head)
    row = ys.max() - 8 * K                                 # il collo, poco sopra la fine della testa
    cols = np.nonzero(head[row])[0]
    out['neck-l'], out['neck-r'] = to_xy(cols.min(), row), to_xy(cols.max() + 1, row)
    for role, prefix in (('torso', 'torso'), ('arm-left', 'armL'), ('arm-right', 'armR'), ('pants', 'pants'), ('leg-left', 'legL'), ('leg-right', 'legR')):
        out.update(_box(prefix, by_role[role], to_xy))
    for side, role in (('l', 'leg-left'), ('r', 'leg-right')):
        ys, xs = np.nonzero(by_role[role])
        out[f'sole-{side}'] = to_xy(xs.mean(), ys.max() + 1)
    return {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in out.items()}


# ---------------------------------------------------------------- tutto insieme
def trace_alien_body(sheet, box, scale, ground=GROUND, roles=None, bridge=(), seal=0, verbose=False):
    """Traccia la figura in `box`. Le coordinate del foglio vengono scalate di `scale` (la stessa per tutte le figure di un
    foglio, così le altezze restano confrontabili) e spostate in modo che i piedi poggino su y = `ground`."""
    seg = segment(sheet, box, bridge=bridge, seal=seal, dots=(6, 3.5), eye_aspect=1.15)
    if len(seg.eyes) < 2:
        raise ValueError(f'servono due occhi, trovati {len(seg.eyes)}')
    info, cls = classify_alien(seg, roles)
    x0, y0 = box[:2]
    g = grow_labels(seg.lab, seg.dark)
    cls = absorb_small(seg, g, info, cls)
    cells = {i: (g == i) for i in cls}

    bottom = max(np.nonzero(cells[i])[0].max() for i, c in cls.items() if c.startswith('leg')) / K + y0     # i piedi: linea del suolo
    cx = (min(np.nonzero(cells[i])[1].min() for i in cls) + max(np.nonzero(cells[i])[1].max() for i in cls)) / 2 / K + x0
    to_xy = lambda u, v: (CENTER_X + (x0 + u / K - cx) * scale, ground - (bottom - (y0 + v / K)) * scale)
    sx = lambda v: v * scale

    parts = {}
    for i, c in cls.items():
        cell = fill_small_holes(cells[i], 30 * K * K)
        core = erode(seg.lab == i, 3 * K)
        med = np.median(seg.rgb[core], axis=0) if core.any() else info[i]['rgb']
        parts.setdefault(c, []).append(dict(d=trace_paths(cell, to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0),
                                            med=[float(v) for v in med], area=float(info[i]['area'])))
        if verbose:
            print(f'  regione {i:2d} {c:9s} area {info[i]["area"]:6.0f}')
    if verbose:
        for i, r in sorted(info.items()):
            if i not in cls and not r['bg']:
                print(f'  regione {i:2d} (non usata) area {r["area"]:6.0f} colore {_hex(r["rgb"])}')

    # linee interne (dita delle mani e dei piedi, pieghe della maglia, tasche dei pantaloncini): pixel scuri con una sola
    # regione intorno; sulla maglia e sui pantaloncini sono sottili, sulla pelle come il contorno
    seams = find_seams(seg, g, set(cls), to_xy)
    for s in seams:
        s['part'] = cls[s['label']]
        s['fine'] = s['part'] in ('torso', 'pants')

    eyes = []
    for e in seg.eyes:
        ex, ey = to_xy((e['cx'] - x0) * K, (e['cy'] - y0) * K)
        eyes.append(dict(cx=ex, cy=ey, rx=sx(e['rx']), ry=sx(e['ry'])))
    # le narici: puntini tondi sul viso, sotto gli occhi
    eye_y = np.mean([e['cy'] for e in seg.eyes])
    nostrils = []
    for d in seg.dots:
        if abs(d['cy'] - eye_y) < 90:
            nx, ny = to_xy((d['cx'] - x0) * K, (d['cy'] - y0) * K)
            nostrils.append(dict(cx=nx, cy=ny, r=max(sx(d['r']), 1.3)))
    nostrils.sort(key=lambda n: n['cx'])

    hid = max((i for i, c in cls.items() if c == 'head'), key=lambda i: info[i]['area'])
    ys, xs = np.nonzero(seg.lab == hid)
    X = np.array([to_xy(u, v)[0] for u, v in zip(xs[::7], ys[::7])]); Y = np.array([to_xy(u, v)[1] for u, v in zip(xs[::7], ys[::7])])
    eyeY = float(np.mean([e['cy'] for e in eyes]))
    head = dict(L=float(X.min()), R=float(X.max()), T=float(Y.min()), eyeY=eyeY, eyeX=float(np.mean([e['cx'] for e in eyes])))

    main = lambda role: max(parts[role], key=lambda p: p['area'])['med']             # la regione più grande della parte
    colors = {'skin': _hex(main('head')), 'shirt': _hex(main('torso')), 'pants': _hex(main('pants'))}
    ex, ey = int((seg.eyes[0]['cx'] - x0) * K), int((seg.eyes[0]['cy'] - y0) * K)
    colors['eye'] = _hex(seg.rgb[ey - 2:ey + 3, ex - 2:ex + 3].reshape(-1, 3).mean(0))
    return dict(box=list(box), parts=parts, seams=seams, eyes=eyes, nostrils=nostrils, head=head,
                landmarks=landmarks(cells, cls, to_xy), colors=colors, stroke=stroke_width(seg) * scale)
