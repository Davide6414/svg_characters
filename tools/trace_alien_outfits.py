#!/usr/bin/env python3
"""Traccia i vestiti alieni da un foglio in cui ogni figura indossa un capo sulla propria sagoma.

Uso:
  python3 tools/trace_alien_outfits.py reference/vestiti-alieni-maschili.webp \\
      --bodies-sheet reference/sagome-aliene-maschili.webp --bodies src/alien/bodies/maschio \\
      --names bambino,ragazzo,adulto,curvo --out src/alien/clothes/maschio

Il foglio dei vestiti è il foglio delle sagome nude con i capi disegnati sopra (`--bodies-sheet`, per la scala, e
`--bodies`, i `.json` delle sagome, per l'ancoraggio agli occhi). Per ogni figura (da sinistra a destra) scrive, in
`--out/<sagoma>/`, `tops/<id>.svg|json` (la maglia, con le sue braccia) e `bottoms/<id>.svg|json` (i pantaloni o la gonna,
con le loro gambe). Le regioni di ogni figura si assegnano a mano ai ruoli di colore nelle tabelle qui sotto: `-v` stampa gli
indici di regione (area, colore) di ogni figura.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.alien import HEIGHT                              # noqa: E402
from lib.alien_clothes_export import write_garment        # noqa: E402
from lib.alien_outfits import trace_alien_outfit          # noqa: E402
from lib.sheet import Sheet                               # noqa: E402

# Tabelle per figura, per nome del foglio dei vestiti (stem del file) e della sagoma.
#   top / bottom   il capo: id, name, regions {indice: ruolo (main, trim, accent, accent2, skin)} e, se serve:
#       split {regione: [(ruolo, regola[, area minima])]}   dettagli senza contorno ricavati dal colore dentro la regione
#                                                           (regole: white, darker, lighter, orange, red, lilac)
#       absorb {regione: [regioni]}   regioni fuse in una sola, senza cucitura
#       back [regioni]                regioni dietro le braccia (la coda di un mantello)
#       under_down dict(regions=[…], role=…, inset=…, wide=…, width='pants')   la maglia scende dietro i pantaloncini di base, fino al fondo della
#                                     maglietta: una fascia larga come l'orlo di quelle regioni, del ruolo `role` (anche `skin`: pancia)
#       under_up    dict(regions=[…], …, up=px)   i pantaloni salgono dietro la maglietta di base (stessa cosa, in alto; `up`: di quanto,
#                                     se l'orlo della maglietta non è orizzontale)
#       folds [regioni]               pieghe chiare sottili (una tasca)
#       smooth {regione: px}          toglie i bernoccoli (apertura morfologica)
#       neck False                    niente pezzo di collo
#   arms / legs   (sinistra, destra) indici di regione, se la scelta automatica (le 4 regioni di pelle più grandi) non va;
#                 None = il braccio è fuso col collo (spalla scoperta)
#   ignore        regioni che non si disegnano (lo sfondo racchiuso fra il braccio e il busto)
#   bridge, seal, dark   come per le sagome
OUTFITS = {
    'vestiti-alieni-maschili': {
        'bambino': dict(
            top=dict(id='tunica-cappuccio', name='Tunica con cappuccio', regions={3: 'trim', 4: 'main', 5: 'main', 6: 'trim', 7: 'trim'},
                     under_down=dict(regions=[4, 5], role='main', wide=0.5)),
            bottom=dict(id='gonnellino', name='Gonnellino con cintura', regions={14: 'main', 11: 'trim', 13: 'trim', 12: 'accent'},
                        split={14: [('accent2', 'darker')]}),
            ignore=(10,)),
        'ragazzo': dict(
            top=dict(id='tunica-banda', name='Tunica a banda', regions={3: 'trim', 5: 'trim', 4: 'main'}, under_down=dict(regions=[4, 5], role='skin', width='pants')),
            bottom=dict(id='kilt-scuro', name='Kilt scuro', regions={12: 'trim', 10: 'accent', 11: 'trim', 13: 'trim', 14: 'main', 15: 'main'},
                        split={14: [('accent2', 'white')]}),
            ignore=(9,)),
        'adulto': dict(
            top=dict(id='poncho', name='Poncho con rombo', regions={3: 'trim', 4: 'main', 8: 'skin'}, split={4: [('trim', 'darker')]},
                     under_down=dict(regions=[4], role='skin', width='pants')),
            bottom=dict(id='kilt-verde', name='Kilt verde', regions={9: 'trim', 10: 'accent', 11: 'main', 12: 'accent'},
                        split={11: [('accent2', 'white')]}),
            ignore=(13,)),
        'curvo': dict(
            top=dict(id='mantellina', name='Mantellina', regions={3: 'main', 4: 'main', 5: 'accent', 6: 'main', 7: 'trim'},
                     under_down=dict(regions=[7], role='skin', width='pants')),
            bottom=dict(id='bermuda', name='Bermuda', regions={12: 'main', 13: 'main'}, under_up=dict(regions=[12, 13], role='main', up=30)),
            ignore=(11, 14)),
    },
    'vestiti-alieni-femminili': {
        'bambina': dict(
            top=dict(id='tunica-spallina', name='Tunica con spallina', regions={3: 'trim', 4: 'trim', 5: 'accent', 8: 'main'},
                     under_down=dict(regions=[8], role='main', wide=0.5)),
            bottom=dict(id='gonna-avvolgente', name='Gonna avvolgente', regions={11: 'trim', 12: 'trim', 13: 'accent', 14: 'main', 15: 'main', 16: 'accent2'},
                        split={14: [('trim', 'darker')]}),
            ignore=(9, 10)),
        'ragazza': dict(
            top=dict(id='tunica-monospalla', name='Tunica monospalla', regions={3: 'trim', 6: 'trim', 7: 'main', 4: 'accent'},
                     under_down=dict(regions=[7], role='skin', width='pants')),
            bottom=dict(id='gonna-malva', name='Gonna malva', regions={10: 'trim', 11: 'main', 12: 'main', 13: 'trim'},
                        split={11: [('accent', 'white')]}),
            arms=(None, 5), ignore=(8, 9)),
        'adulta': dict(
            top=dict(id='corpetto-pendente', name='Corpetto con pendente', regions={3: 'trim', 4: 'trim', 5: 'main', 8: 'accent', 9: 'trim'},
                     under_down=dict(regions=[5], role='skin', width='pants')),
            bottom=dict(id='gonna-pannello', name='Gonna a pannello', regions={12: 'trim', 13: 'accent', 14: 'accent', 15: 'main', 16: 'accent2', 17: 'accent2'},
                        split={15: [('accent', 'white')]}),
            ignore=(10, 11)),
        'curva': dict(
            top=dict(id='mantello', name='Mantello con fibbia', regions={3: 'main', 4: 'main', 5: 'main', 6: 'accent', 7: 'trim', 10: 'main', 17: 'main', 12: 'main'},
                     back=(10, 17, 12), split={10: [('trim', 'white')], 17: [('trim', 'white')]}, under_down=dict(regions=[7], role='skin', width='pants')),
            bottom=dict(id='gonna-sbieca', name='Gonna sbieca', regions={14: 'trim', 16: 'main', 15: 'main', 18: 'trim', 20: 'main'}),
            ignore=(13, 19)),
    },
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', help='foglio dei vestiti')
    ap.add_argument('--bodies-sheet', required=True, help='foglio delle sagome nude (per la scala)')
    ap.add_argument('--bodies', required=True, help='cartella delle sagome (es. src/alien/bodies/maschio)')
    ap.add_argument('--names', required=True, help='nomi delle sagome, da sinistra a destra, separati da virgola')
    ap.add_argument('--out', required=True, help='cartella dei vestiti (es. src/alien/clothes/maschio)')
    ap.add_argument('--only', help='solo queste sagome (separate da virgola)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    stem = os.path.splitext(os.path.basename(a.sheet))[0]
    sheet = Sheet(a.sheet)
    base_sheet = Sheet(a.bodies_sheet)
    names = [n.strip() for n in a.names.split(',')]
    boxes = sheet.figures()
    if len(boxes) != len(names):
        sys.exit(f'Il foglio ha {len(boxes)} figure ma sono stati dati {len(names)} nomi')
    margin = 10                                                       # il margine di Sheet.figures()
    scale = HEIGHT / max(b[3] - b[1] - 2 * margin for b in Sheet(a.bodies_sheet).figures())
    for name, box in zip(names, boxes):
        if a.only and name not in a.only.split(','):
            continue
        spec = OUTFITS[stem][name]
        with open(os.path.join(a.bodies, name + '.json'), encoding='utf8') as f:
            body = json.load(f)
        if a.verbose:
            print(name)
        res = trace_alien_outfit(sheet, box, body, scale, spec, base_sheet, verbose=a.verbose)
        for kind, folder in (('top', 'tops'), ('bottom', 'bottoms')):
            cs = spec[kind]
            write_garment(os.path.join(a.out, name, folder), cs['id'], cs['name'], res[kind])
        print(f'{name}: {spec["top"]["id"]} + {spec["bottom"]["id"]}')


if __name__ == '__main__':
    main()
