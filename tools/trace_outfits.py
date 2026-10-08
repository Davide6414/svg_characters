#!/usr/bin/env python3
"""Traccia gli outfit di un foglio in cui ogni figura indossa maglia e pantaloni sul proprio corpo.

Uso:
  python3 tools/trace_outfits.py reference/vestiti-femminili.webp --group femmina \\
      --bodies src/bodies/femmina --out src/clothes/femmina

Per ogni figura (da sinistra a destra) scrive in --out `tops/<id>.svg + .json` e `bottoms/<id>.svg + .json`. Ogni capo
è disegnato sulla sagoma della figura (stesso nome in --bodies): il suo json dice su quale (`on`) e `build.mjs` lo
adatta alle altre. A differenza di `trace_clothes.py` (stesso corpo, capi diversi) qui le regioni di ogni figura si
assegnano a mano nella tabella OUTFITS: per vedere gli indici si lancia con -v.

Ogni capo ha:
  regions    {indice regione: ruolo}. Ruoli: main, trim, accent, accent2, under, skin (pelle lasciata scoperta)
  split      {indice regione: [(ruolo, regola), …]} dettagli senza contorno ricavati dal colore dentro la regione
             (regole: white, orange, lighter) e disegnati sopra senza tratto
  behind     {indice: regioni dei bracci} la regione prosegue dietro le braccia (un pugno sui pantaloni lascia un vuoto)
  to_shoes   regioni che scendono sotto le scarpe (pantaloni, calze, gambe), così l'orlo non si vede
  layers     {indice: 'under'} regioni che stanno sotto i pantaloni (la pancia scoperta di un top corto)
  pad_under  {indice: dict(near=regioni vicine, up=, down=)} allunga in verticale quelle regioni sotto le regioni vicine
  under_up   {indice: px} i pantaloni salgono di tanti px sotto la maglia (in un livello sotto), così con una maglia
             più corta o con un orlo diverso non resta un buco in vita
  neck       True se lo scollo lascia vedere la pelle sotto il collo della sagoma (V, scollo ampio, cappuccio aperto)
  parts      {indice: 'arms'} regioni che sostituiscono le braccia della sagoma (spalle e braccia scoperte)
  arms       (braccio sinistro, braccio destro): indici delle regioni dei bracci, per le maniche corte (vedi sotto)
  folds      regioni dove cercare anche le pieghe chiare (per i pantaloni: la regione principale, in automatico)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.clothes_export import write_garment           # noqa: E402
from lib.outfits import trace_outfit                    # noqa: E402
from lib.sheet import Sheet                             # noqa: E402

# Una riga per figura, da sinistra a destra: la sagoma su cui è disegnata, la maglia e i pantaloni.
OUTFITS = [
    dict(body='bambina',
         top=dict(id='maglietta-fiore', name='Maglietta con fiore', regions={3: 'main'}, arms=(4, 5),
                  split={3: [('accent', 'white'), ('accent2', 'orange')]}),                       # petali e centro del fiore
         bottom=dict(id='pantaloncini', name='Pantaloncini risvoltati', regions={6: 'main', 7: 'skin', 8: 'skin'},
                     behind={6: (3,)}, under_up={6: 30},
                     split={6: [('trim', 'lighter')], 7: [('under', 'white')], 8: [('under', 'white')]},   # risvolto e calze
                     to_shoes=(7, 8))),
    dict(body='ragazza',
         top=dict(id='felpa-cappuccio', name='Felpa con cappuccio', regions={3: 'main', 4: 'under', 5: 'accent', 6: 'accent'},
                  neck=True, folds=(3,)),                                                                      # cordini e maglietta sotto
         bottom=dict(id='jeans-scuri', name='Jeans scuri', regions={7: 'main'}, to_shoes=(7,),
                     behind={7: (3, 4, 5, 6)}, under_up={7: 30})),
    dict(body='slanciata',
         top=dict(id='top-corto', name='Top corto', regions={3: 'main', 4: 'skin', 5: 'skin', 6: 'skin', 8: 'skin'},
                  layers={8: 'under'}, pad_under={8: dict(near=(3, 9), up=14, down=40)}, parts={4: 'arms', 5: 'arms', 6: 'arms'}, neck=True),   # braccia e pancia scoperte
         bottom=dict(id='jeans-a-zampa', name='Jeans a zampa', regions={9: 'main'}, to_shoes=(9,))),
    dict(body='adulta',
         top=dict(id='maglietta-v', name='Maglietta scollo a V', regions={3: 'main'}, arms=(6, 7), neck=True),
         bottom=dict(id='pantaloni-neri', name='Pantaloni neri larghi', regions={9: 'main'}, to_shoes=(9,),
                     behind={9: (3,)}, under_up={9: 30})),
    dict(body='robusta',
         top=dict(id='cardigan', name='Cardigan', regions={3: 'main', 4: 'main', 5: 'under', 6: 'main', 9: 'main'}, neck=True,
                  folds=(3, 4)),
         bottom=dict(id='pantaloni-marroni', name='Pantaloni marroni', regions={10: 'main'}, to_shoes=(10,), behind={10: (3, 4, 5, 7, 8)})),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', help='foglio con gli outfit')
    ap.add_argument('--group', required=True, help='gruppo delle sagome (es. femmina)')
    ap.add_argument('--bodies', required=True, help='cartella delle sagome tracciate (es. src/bodies/femmina)')
    ap.add_argument('--out', required=True, help='cartella di destinazione (es. src/clothes/femmina)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    sheet = Sheet(a.sheet)
    boxes = sheet.figures()
    if len(boxes) != len(OUTFITS):
        sys.exit(f'Il foglio ha {len(boxes)} figure ma la tabella ne ha {len(OUTFITS)}')
    for spec, box in zip(OUTFITS, boxes):
        with open(os.path.join(a.bodies, spec['body'] + '.json'), encoding='utf8') as f:
            ref = json.load(f)
        if a.verbose:
            print(spec['body'])
        res = trace_outfit(sheet, box, ref, spec, verbose=a.verbose)
        for kind, folder in (('top', 'tops'), ('bottom', 'bottoms')):
            cs, garment = spec[kind], res[kind]
            write_garment(os.path.join(a.out, folder), cs['id'], cs['name'], garment, on=f'{a.group}/{spec["body"]}')
            print(f'{folder}/{cs["id"]}: {len(garment["regions"])} regioni, {len(garment["seams"])} linee, {len(garment["dots"])} puntini, colori {garment["colors"]}')


if __name__ == '__main__':
    main()
