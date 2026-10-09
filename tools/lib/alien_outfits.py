"""Vestiti alieni: ogni figura del foglio dei vestiti indossa una maglia e dei pantaloncini (o una gonna) sul proprio corpo.

I fogli dei vestiti sono i fogli delle sagome nude (`trace_alien.py`) con i capi disegnati sopra: stessa posa, stessa
scala, stesse teste e piedi (scarto misurato < 0.3 px). Basta quindi dare alla figura le stesse coordinate della
sagoma, ancorate agli occhi (`head.eyeX/eyeY` del `.json` della sagoma) e alla scala del foglio, e i capi cadono
esattamente sul corpo, senza deformazioni né punti di riferimento da agganciare.

Le regioni della figura (indici con `-v`) vanno assegnate a mano a un capo e a un ruolo di colore (tabella in
`trace_alien_outfits.py`):

  main, trim, accent, accent2   i colori del capo (variabili CSS --shirt… / --pants…)
  skin                          pelle che il capo lascia scoperta fra le sue parti

Un capo sostituisce le parti del corpo che il capo di base nasconde e che lui, invece, lascia vedere:
  - una maglia (`top`) porta le proprie braccia (`arms`): una manica più corta, o nessuna, scopre il braccio più in alto
    di dove comincia quello della sagoma, che sotto la maglietta di base è nascosto;
  - dei pantaloni o una gonna (`bottom`) portano le proprie gambe (`legs`): l'orlo più alto scopre la coscia;
  - se il collo del capo è più basso di quello della sagoma, la maglia aggiunge il pezzo di collo che manca (`neck`).
Le parti vengono tracciate dalla stessa figura: contorni, dita e piedi coincidono con quelli della sagoma.

I capi stanno in livelli diversi (vedi `alien_clothes_export.py`): davanti (`garment`), dietro le braccia (`back`: la
coda di un mantello), sotto i pantaloncini (`under`: la maglia scende dietro, così, con dei pantaloncini che cominciano più
in basso dell'orlo, non resta un buco in vita).
"""
import numpy as np

from .alien import _is_skin, stroke_width
from .geom import catmull_d, dilate, erode, fill_small_holes, grow_labels, rdp, skeleton_lines, trace_paths
from .outfits import RULES, _extend_rows, _smooth_mask
from .parts import extend_bottom, find_folds, find_seams, region_info
from .segment import K, segment

SMALL = 400            # px²: le regioni non assegnate più piccole di così si uniscono al capo (o alla parte) con cui confinano
STROKE_INSET = 2.5     # px: i dettagli senza contorno stanno dentro la cella, senza coprire il tratto del bordo
NECK_UP = 4.0          # px sopra la riga del collo della sagoma da cui comincia il pezzo di collo che il capo aggiunge
NECK_MIN = 1.2         # px: il collo del capo è più lungo di quello della sagoma di almeno tanto → serve il pezzo di collo
BAND_OVERLAP = 6.0     # px: la fascia sotto la maglia scende fin dentro i pantaloncini di base


def _hex(c):
    return '#%02x%02x%02x' % tuple(int(round(v)) for v in c)


def _outline_runs(cell, dark, to_xy, minlen=8.0):
    """Il contorno vero di una cella: i tratti del suo bordo che cadono sul tratto scuro del foglio, come linee aperte. Dove
    la cella è stata tagliata da una linea che nel disegno non c'è (la spalla scoperta che si fonde col collo) il bordo non
    sta sul tratto scuro e non si disegna."""
    ring = cell & ~erode(cell, 1.5 * K) & dilate(dark, 1)
    return [catmull_d(rdp(l, 0.9 * K), to_xy) for l in skeleton_lines(ring, minlen * K)]


def _rows(mask):
    r = np.nonzero(mask.any(1))[0]
    return (r.min(), r.max()) if r.size else (0, 0)


def trace_alien_outfit(sheet, box, body, scale, spec, base_sheet, verbose=False):
    """Traccia i capi della figura in `box`. `body` = `.json` della sagoma su cui è disegnata (head, landmarks), `scale` =
    la scala del foglio delle sagome, `base_sheet` = il foglio delle sagome nude (serve a sapere dove la testa della sagoma ha dei tratti
    che il capo non ha). `spec` = {'top': capo, 'bottom': capo, …} (vedi `trace_alien_outfits.py`).
    Restituisce {'top': garment, 'bottom': garment}, ognuno con i suoi livelli (`layers`), le parti del corpo che
    sostituisce (`replaces`) e i colori di partenza."""
    seg = segment(sheet, box, bridge=spec.get('bridge', ()), seal=spec.get('seal', 0), dots=(6, 60), eye_aspect=1.15,
                  dark=spec.get('dark', 34))
    if len(seg.eyes) < 2:
        raise ValueError(f'servono due occhi, trovati {len(seg.eyes)}')
    x0, y0 = box[:2]
    info = region_info(seg)
    # i buchi minuscoli nel tratto sono tratto, non regioni (come per le sagome)
    tiny = np.isin(seg.lab, [i for i in range(1, seg.n_lab + 1) if i not in info])
    seg.dark = seg.dark | tiny
    lab = seg.lab.copy()
    lab[tiny] = 0
    g = grow_labels(lab, seg.dark)

    # coordinate: ancorate agli occhi (la sagoma e il foglio dei vestiti hanno gli stessi occhi)
    ex = float(np.mean([e['cx'] for e in seg.eyes]))
    ey = float(np.mean([e['cy'] for e in seg.eyes]))
    bx, by = body['head']['eyeX'], body['head']['eyeY']
    to_xy = lambda u, v: (bx + (x0 + u / K - ex) * scale, by + (y0 + v / K - ey) * scale)
    sheet_v = lambda Y: (ey + (Y - by) / scale - y0) * K            # riga del bitmap di una y finale
    stroke = stroke_width(seg)

    head = int(seg.lab[int((seg.eyes[0]['cy'] - y0) * K), int((seg.eyes[0]['cx'] - x0) * K)])
    top, bottom = spec['top'], spec['bottom']
    used = set(top['regions']) | set(bottom['regions'])
    for cs in (top, bottom):
        for js in cs.get('absorb', {}).values():
            used |= set(js)

    # braccia e gambe: le quattro regioni di pelle più grandi (le due più in basso sono le gambe), salvo indicazione
    skin = sorted((i for i, r in info.items() if not r['bg'] and i != head and i not in used and _is_skin(r) and r['area'] >= 300),
                  key=lambda i: -info[i]['area'])[:4]
    skin.sort(key=lambda i: -info[i]['cy'])
    legs = spec.get('legs') or sorted(skin[:2], key=lambda i: info[i]['cx'])
    arms = spec.get('arms') or sorted(skin[2:], key=lambda i: info[i]['cx'])
    cells = {i: (g == i) for i in list(used) + list(legs) + [a for a in arms if a is not None] + [head]}

    # il collo: la testa della sagoma finisce con un colletto (la maglietta ci passa sopra); un capo con lo scollo più basso o con una
    # spalla scoperta lascia vedere quei tratti (il contorno inferiore della testa, che nel foglio dei vestiti non c'è). Si copre con
    # un pezzo di pelle davanti alla testa: la parte della regione della testa del foglio dei vestiti dalla prima riga con un tratto
    # "vecchio" in giù, col suo contorno vero.
    bseg = segment(base_sheet, box, dots=(6, 60), eye_aspect=1.15)
    be = bseg.eyes[0]
    base_head = grow_labels(bseg.lab, bseg.dark) == int(bseg.lab[int((be['cy'] - y0) * K), int((be['cx'] - x0) * K)])
    ring = dilate(base_head, 2 * K) & ~erode(base_head, 2 * K)                       # dove la sagoma disegna il contorno della testa
    head_cell = cells[head]
    stale = ring & ~dilate(seg.dark, 1.5 * K) & erode(head_cell, 1.5 * K)           # …e il foglio dei vestiti non lo disegna, su pelle
    rows = np.arange(g.shape[0])[:, None]
    neck_cell, neck_row = None, None
    if stale.sum() > 40 * K * K / 4:
        neck_row = _rows(stale)[0] - NECK_UP * K
        neck_cell = head_cell & (rows >= neck_row)
    if verbose:
        print(f'  collo: tratti della sagoma da coprire: {int(stale.sum() / K / K)} px²' + (f', pezzo dalla y={y0 + neck_row / K:.0f}' if neck_cell is not None else ''))
    merged_arm = None
    if arms[0] is None or arms[1] is None:                           # un braccio è nella regione della testa (una spalla scoperta)
        if neck_cell is None:
            raise ValueError('braccio fuso con la testa, ma la testa non ha tratti da coprire: controllare `arms`')
        merged_arm = 0 if arms[0] is None else 1
        arms = [neck_cell if a is None else a for a in arms]

    # regioni piccole non assegnate: se confinano con una sola parte e ne hanno il colore si uniscono (un dito chiuso da un
    # tratto, un lembo di stoffa); altrimenti restano fuori (lo sfondo racchiuso fra braccio e busto)
    parts_of = {i: ('top', cs) for cs in (top,) for i in cs['regions']}
    parts_of.update({i: ('bottom', bottom) for i in bottom['regions']})
    arm_ids = [a for a in arms if isinstance(a, (int, np.integer))]
    extra = {}                                                       # indice di regione → regione a cui si unisce
    ignore = set(spec.get('ignore', ()))
    owners = {**{i: i for i in used}, **{i: i for i in legs}, **{i: i for i in arm_ids}}
    for i, r in sorted(info.items()):
        if i in owners or i in ignore or i == head or r['bg'] or r['area'] > SMALL:
            continue
        near = dilate(g == i, 2 * K)
        touch = {j: int((near & cells[j]).sum()) for j in owners if j in cells and j != head}
        touch = {j: v for j, v in touch.items() if v}
        if len(touch) != 1:
            continue
        j = next(iter(touch))
        core = erode(seg.lab == i, 1 * K)
        c = np.median(seg.rgb[core if core.any() else seg.lab == i], axis=0)
        ref = np.median(seg.rgb[erode(seg.lab == j, 2 * K)], axis=0) if erode(seg.lab == j, 2 * K).any() else info[j]['rgb']
        if np.linalg.norm(c - ref) < 40:
            extra[i] = j
            cells[i] = g == i
    if verbose and extra:
        print('  regioni piccole unite:', {i: j for i, j in extra.items()})

    med = {}
    for i in list(cells):
        core = erode(seg.lab == i, 2 * K)
        med[i] = np.median(seg.rgb[core], axis=0) if core.any() else info[i]['rgb'] if i in info else np.array([128, 128, 128.])
    v_idx = np.arange(g.shape[0])[:, None]

    def trace(mask):
        return trace_paths(fill_small_holes(mask, 60 * K * K), to_xy, opttol=1.6 * K / 2, alphamax=1.0, turd=20, smooth=1.0)

    # linee interne di tutte le regioni che disegniamo (cuciture, pieghe di stoffa, dita e piedi delle parti di pelle)
    labels = set(used) | set(legs) | set(arm_ids) | set(extra)
    all_seams = [s for s in find_seams(seg, g, labels, to_xy, minlen=top.get('min_seam', 9.0)) if s['thick'] >= 1.5]

    out = {}
    for kind, cs in (('top', top), ('bottom', bottom)):
        detail_colors = {}
        layers = {k: [] for k in ('garment', 'back', 'under')}      # livelli del capo (alla fine anche braccia/gambe)
        base, overlays, strokes = {k: [] for k in layers}, {k: [] for k in layers}, {k: [] for k in layers}
        region_ids = list(cs['regions'])

        def add(target, layer, cls, mask, stroke_on):
            paths = trace(mask)
            if paths:
                target[layer].append(dict(cls=cls + (' c-stroke' if stroke_on else ''), d=paths))

        members = {i: [i] + [j for j, k in extra.items() if k == i] for i in region_ids}
        for i in region_ids:
            role = cs['regions'][i]
            layer = 'back' if i in cs.get('back', ()) else 'garment'
            cell = cells[i]
            for j in cs.get('absorb', {}).get(i, ()):
                cell = cell | cells[j] if j in cells else cell | (g == j)
            if i in cs.get('smooth', {}):
                r = cs['smooth'][i] * K
                cell = dilate(erode(cell, r), r) & cell
            details = cs.get('split', {}).get(i, ())
            cls = f'c-{role}'
            add(base, layer, cls, cell, not details)
            for j in members[i][1:]:                                 # le regioni piccole unite: stesso ruolo, proprio contorno
                add(base, layer, cls, cells[j], True)
            if details:
                add(strokes, layer, 'c-open', cell, True)
            ref_lum = 0.299 * med[i][0] + 0.587 * med[i][1] + 0.114 * med[i][2]
            band = cells[i] & ~erode(cells[i], 4 * K)
            for drole, rule, *opt in details:
                raw = RULES[rule](seg.rgb, ref_lum) & cells[i] & ~seg.dark
                m = _smooth_mask(raw, 1.2, opt[0] if opt else 25, close=3)
                m |= band & dilate(m, 4 * K)                         # fino al bordo: il tratto lo copre
                if m.any():
                    add(overlays, layer, f'c-{drole}', m, False)
                    # il colore: fra i pixel che rispettano la regola, la metà più lontana dal colore della regione (i bordi
                    # sfumati di un dettaglio piccolo tirano verso il fondo)
                    px = seg.rgb[raw & m] if (raw & m).any() else seg.rgb[m]
                    far = np.linalg.norm(px - med[i], axis=1)
                    detail_colors.setdefault(drole, np.median(px[far >= np.median(far)], axis=0))
                    if verbose:
                        print(f'    dettaglio {drole:7s} {rule:8s} area {m.sum() / (K * K):6.0f} {_hex(detail_colors[drole])}')
            if verbose:
                print(f'  {kind} regione {i:2d} {role:7s} area {info[i]["area"]:6.0f} {_hex(med[i])}')

        # la maglia scende dietro i pantaloncini (`under_down`): nessun buco in vita quando i pantaloncini di base cominciano più in basso
        # dell'orlo; i pantaloni salgono dietro la maglietta (`under_up`): nessun buco quando cominciano più in basso del suo orlo
        tee_hem = sheet_v(body['landmarks']['torso-bl'][1])                     # riga del fondo della maglietta di base
        band = cs.get('under_down') if kind == 'top' else cs.get('under_up')
        if band:
            union = np.zeros_like(seg.dark)
            for i in band['regions']:
                union |= cells[i]
            role = band.get('role', cs['regions'][band['regions'][0]])
            if kind == 'top':
                last = _rows(union)[1]
                move = (tee_hem + BAND_OVERLAP * K - last) / K
                if move > 0.5 and band.get('width') == 'pants':       # largo come i pantaloncini di base (la pancia sotto una maglia corta)
                    L, R = body['landmarks']['pants-tl'][0], body['landmarks']['pants-tr'][0]
                    cols = [int(((X - bx) / scale + ex - x0) * K) for X in (L, R)]
                    shape = np.zeros_like(seg.dark)
                    shape[int(last - band.get('notch', 25) * K):int(tee_hem + BAND_OVERLAP * K), cols[0] + int(band.get('inset', 2) * K):cols[1] - int(band.get('inset', 2) * K)] = True
                else:
                    shape = extend_bottom(union, move, notch=band.get('notch', 25), inset=band.get('inset', 2), band_only=True, wide=band.get('wide', 0.0)) if move > 0.5 else None
            else:
                first = _rows(union)[0]
                move = band['up'] if 'up' in band else (first - (tee_hem - BAND_OVERLAP * K)) / K
                shape = _extend_rows(union, move, 0) if move > 0.5 else None            # ogni colonna sale di `move` px: segue l'orlo alto, anche obliquo
            if shape is not None and shape.any():
                add(base, 'under', f'c-{role}', shape, True)
                if verbose:
                    print(f'  {kind}: fascia {"sotto" if kind == "top" else "sopra"} le regioni {band["regions"]} ({role}), {move:.1f} px')

        # il pezzo di collo (solo dove il capo scopre più collo della sagoma); con una spalla scoperta è già nel braccio
        if kind == 'top' and neck_cell is not None and merged_arm is None and cs.get('neck', True):
            m = erode(neck_cell, 0.6 * K)
            add(base, 'garment', 'c-skin', m, False)
            for d in _outline_runs(neck_cell, seg.dark, to_xy):
                layers['garment'].append(dict(cls='c-open c-stroke', d=[d], first=True))

        # pelle sostitutiva: braccia per la maglia, gambe per i pantaloni
        skin_parts = {}
        owned = ([('arm-left', arms[0], 0), ('arm-right', arms[1], 1)] if kind == 'top'
                 else [('leg-left', legs[0], 0), ('leg-right', legs[1], 1)])
        for name, idx, side in owned:
            rows_ = []
            if isinstance(idx, np.ndarray):                           # braccio fuso col collo: solo il contorno vero
                m = idx
                paths = trace(m)
                rows_.append(dict(cls='c-skin', d=paths))
                for d in _outline_runs(m, seg.dark, to_xy):
                    rows_.append(dict(cls='c-open c-stroke', d=[d]))
                lab_ids = set()
            else:
                m = cells[idx]
                rows_.append(dict(cls='c-skin c-stroke', d=trace(m)))
                for j in [j for j, k in extra.items() if k == idx]:
                    rows_.append(dict(cls='c-skin c-stroke', d=trace(cells[j])))
                lab_ids = {idx} | {j for j, k in extra.items() if k == idx}
            for s in all_seams:
                if s['label'] in lab_ids:
                    rows_.append(dict(cls='c-open c-stroke', d=[s['d']]))
            skin_parts[name] = rows_

        # linee interne dei capi
        merged = np.zeros_like(seg.dark)
        for i, js in cs.get('absorb', {}).items():
            for j in js:
                merged |= dilate(seg.dark & dilate(cells[i], 2 * K) & dilate(g == j, 2 * K), 2 * K)
        seams = [s for s in all_seams if s['label'] in set(region_ids) | {j for j, k in extra.items() if k in region_ids}
                 and s['label'] not in cs.get('no_seams', ())]
        for i in cs.get('folds', ()):
            seams += find_folds(seg, g, i, to_xy)
        for s in seams:
            owner = extra.get(s['label'], s['label'])
            layer = 'back' if owner in cs.get('back', ()) else 'garment'
            thick = s.get('thick', 0)
            width = ' c-fold' if s['kind'] == 'fold' else ''
            fine = ' c-fine' if (s['kind'] == 'fold' or thick < 0.8 * stroke) else ''
            strokes[layer].append(dict(cls=f'c-open c-stroke{fine}{width}', d=[s['d']]))

        # primo il collo (davanti a tutto), poi regioni, dettagli, contorni sopra i dettagli, linee interne
        garment = dict(kind=kind, layers={}, parts=skin_parts, replaces=['arms'] if kind == 'top' else ['legs'])
        for k in layers:
            first = [r for r in layers[k] if r.get('first')]
            garment['layers'][k] = first + base[k] + overlays[k] + [r for r in layers[k] if not r.get('first')] + strokes[k]
        colors = {}
        for role in ('main', 'trim', 'accent', 'accent2'):
            ids = [i for i, r in cs['regions'].items() if r == role]
            if ids:
                colors[role] = _hex(med[max(ids, key=lambda i: info[i]['area'])])
        for drole, c in detail_colors.items():                        # i ruoli che esistono solo come dettaglio
            colors.setdefault(drole, _hex(c))
        garment['colors'] = colors
        out[kind] = garment
    return out
