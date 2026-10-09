#!/usr/bin/env python3
"""Traccia gli outfit di un foglio in cui ogni figura indossa maglia e pantaloni sul proprio corpo.

Uso:
  python3 tools/trace_outfits.py reference/vestiti-femminili.webp \\
      --bodies src/bodies/femmina --out src/clothes/femmina

La tabella delle figure si sceglie dal nome del foglio (OUTFITS[nome senza estensione]).

Per ogni figura (da sinistra a destra) scrive in `--out/<sagoma>/` i file `tops/<id>.svg + .json` e
`bottoms/<id>.svg + .json`. Ogni capo resta alla sagoma su cui è disegnato (stesso nome in --bodies): non si adatta ad
altre corporature. A differenza di `trace_clothes.py` (stesso corpo, capi diversi) qui le regioni di ogni figura si
assegnano a mano nelle tabelle OUTFITS: per vedere gli indici si lancia con -v.

Ogni capo ha:
  regions    {indice regione: ruolo}. Ruoli: main, trim, accent, accent2, under, skin (pelle lasciata scoperta)
  split      {indice regione: [(ruolo, regola[, area minima]), …]} dettagli senza contorno ricavati dal colore dentro
             la regione (regole: white, orange, lighter, darker, red, lilac) e disegnati sopra senza tratto
  behind     {indice: regioni dei bracci} la regione prosegue dietro le braccia (un pugno sui pantaloni lascia un vuoto)
  to_shoes   regioni che scendono sotto le scarpe (pantaloni, calze, gambe), così l'orlo non si vede
  layers     {indice: 'under'} regioni che stanno sotto i pantaloni (la pancia scoperta di un top corto)
  pad_under  {indice: dict(near=regioni vicine, up=, down=)} allunga in verticale quelle regioni sotto le regioni vicine
  widen      {indice: (regioni vicine,)} allarga la regione in orizzontale fino alle regioni vicine, se distano meno di 25 px
             (la pancia sotto le braccia: così fra pancia e braccio non restano due tratti che si fondono in un cuneo nero)
  under_up   {indice: px} i pantaloni salgono di tanti px sotto la maglia (in un livello sotto), così con una maglia
             più corta o con un orlo diverso non resta un buco in vita
  under_down {indice: px | (px, rientro[, larghezza[, y]])} lo stesso per una maglia corta o infilata: scende sotto i pantaloni
             (rientro ai lati in px, 10 se non detto). `larghezza` (0-1): l'orlo è l'ultima riga larga almeno quella
             frazione della più larga, non l'ultima riga della regione (la manica lunga unita al busto arriva più in basso)
             e, come quarto valore, la y dell'orlo nel foglio (le maniche a sbuffo sono larghe quanto il busto: nessuna regola lo trova)
  join       {indice: (altre regioni,)} regioni da unire in una sola (le gambe dei leggings sotto un abito): il confine
             resta come cucitura
  absorb     {indice: (altre regioni,)} lo stesso senza cucitura (la fessura fra braccio e pancia che il foglio lascia
             vuota diventa pelle della pancia: niente linea fra le due)
  extend_top {indice: px | (px, rientro)} la regione sale di tanti px, con i bordi alti pieni (i fianchi nascosti da un
             abito, una vita da raddrizzare); il rientro tiene gli angoli dentro il profilo
  clip_top   regioni da cui togliere le strisce strette in alto (un pezzo di pantalone che risale lungo un braccio)
  to_waist   regioni che salgono fino alla vita dei pantaloni della sagoma (quando nel foglio la vita è nascosta)
  neck       la pelle sotto il collo della sagoma fa parte della maglia (scollo a V, cappuccio aperto, o solo il bordo
             del colletto): True per le maglie se non detto altrimenti
  neck_up    px: la pelle del collo sale anche sopra la riga del collo della sagoma, ma in un livello dietro la testa:
             riempie la fessura fra il collo della sagoma e il bavero o lo scollo del foglio
  parts      {indice: 'arms'} regioni che sostituiscono le braccia della sagoma (spalle e braccia scoperte)
  arms       (braccio sinistro, braccio destro): indici delle regioni dei bracci, per le maniche corte (vedi sotto)
  folds      regioni dove cercare anche le pieghe chiare (per i pantaloni: la regione principale, in automatico)

Ogni riga della tabella (figura) può avere anche, oltre a `top` e `bottom`:
  bridge     [((x1, y1), (x2, y2)), …] segmenti scuri, in px del foglio, che chiudono un'interruzione del contorno (nei fogli
             generati a volte manca un pezzo di tratto e la regione si fonde con lo sfondo)
  seal       px: ispessisce il tratto per chiudere le crepe di un pixel
  dark       soglia di luminanza del contorno (34): più alta se un tratto interno è più chiaro (il fiocco di un abito rosa)
  cuts       [(regione, y)] divide la regione con un taglio orizzontale a y (px del foglio): un abito senza la linea della vita;
             la parte sotto è la regione numero (ultimo indice + 1), stampata con -v
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.clothes_export import write_garment           # noqa: E402
from lib.outfits import trace_outfit                    # noqa: E402
from lib.sheet import Sheet                             # noqa: E402

# Per ogni foglio una riga per figura, da sinistra a destra: la sagoma su cui è disegnata, la maglia e i pantaloni.
OUTFITS = {}
OUTFITS['vestiti-femminili'] = [
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
         top=dict(id='top-corto', name='Top corto', regions={3: 'main', 4: 'skin', 5: 'skin', 6: 'skin', 8: 'skin'}, absorb={8: (7,)},
                  layers={8: 'under'}, pad_under={8: dict(near=(3, 4, 9), up=14, down=60)}, widen={8: (4, 6)}, parts={4: 'arms', 5: 'arms', 6: 'arms'}, neck=True),   # braccia e pancia scoperte
         bottom=dict(id='jeans-a-zampa', name='Jeans a zampa', regions={9: 'main'}, to_shoes=(9,))),
    dict(body='adulta',
         top=dict(id='maglietta-v', name='Maglietta scollo a V', regions={3: 'main'}, arms=(6, 7), neck=True),
         bottom=dict(id='pantaloni-neri', name='Pantaloni neri larghi', regions={9: 'main'}, to_shoes=(9,),
                     behind={9: (3,)}, under_up={9: 30})),
    dict(body='robusta',
         top=dict(id='cardigan', name='Cardigan', regions={3: 'main', 4: 'main', 5: 'under', 6: 'main', 9: 'main'}, neck=True,
                  folds=(3, 4), under_down={5: (25, 6)}),                                             # la maglietta sotto scende sotto i pantaloni
         bottom=dict(id='pantaloni-marroni', name='Pantaloni marroni', regions={10: 'main'}, to_shoes=(10,), behind={10: (7, 8)},
                     clip_top=(10,), to_waist=(10,), under_up={10: 12})),                          # via la striscia lungo il braccio; vita piatta
]


OUTFITS['vestiti-femminili-2'] = [
    dict(body='bambina',
         top=dict(id='abitino', name='Abitino con colletto', regions={5: 'main', 3: 'trim', 4: 'trim'}, arms=(6, 7),
                  split={5: [('accent', 'white'), ('accent2', 'orange')]}, folds=(5,)),             # colletto, fiore, pieghe
         bottom=dict(id='leggings', name='Leggings', regions={8: 'main', 14: 'skin'}, join={8: (9,)}, to_shoes=(8, 14),
                     behind={8: (5,)}, extend_top={8: 45}, under_up={8: 30})),                         # le gambe unite fino in vita
    dict(body='ragazza',
         top=dict(id='maglia-righe', name='Maglia a righe', regions={3: 'main', 4: 'trim', 5: 'trim'},
                  split={3: [('accent', 'red')]}),                                                     # righe e polsini
         bottom=dict(id='jeans-cargo', name='Jeans cargo', regions={8: 'main', 6: 'main', 7: 'main', 11: 'main', 12: 'main',
                                                                    13: 'main', 14: 'main'},
                     to_shoes=(8,), behind={8: (3, 4, 5)}, under_up={8: 30})),
    dict(body='slanciata',
         top=dict(id='giacca-jeans', name='Giacca di jeans', regions={5: 'main', 6: 'main', 3: 'main', 4: 'main', 8: 'main',
                                                                      9: 'main', 10: 'main', 11: 'trim', 12: 'trim', 7: 'under'},
                  neck=True, under_down={7: (30, 0), 5: (20, 4), 6: (20, 4)}),                        # il top e i lembi scendono sotto i pantaloni
         bottom=dict(id='jeans-neri', name='Jeans neri risvoltati', regions={18: 'main', 14: 'main', 15: 'main', 16: 'main',
                                                                             19: 'trim', 20: 'trim', 21: 'skin', 22: 'skin'},
                     to_shoes=(21, 22), behind={18: (5, 6, 7)}, extend_top={18: (16, 12)}, under_up={18: 12})),     # la vita arriva alla cintura (nel foglio la giacca copre i fianchi)
    dict(body='adulta',
         top=dict(id='maglione-v', name='Maglione a coste', regions={3: 'main'}, arms=(4, 6), neck=True, folds=(3,)),
         bottom=dict(id='pantaloni-oliva', name='Pantaloni oliva', regions={5: 'main', 7: 'skin'}, to_shoes=(5, 7),
                     behind={5: (3,)}, under_up={5: 30})),
    dict(body='robusta',
         top=dict(id='cardigan-fiori', name='Cardigan e maglia a fiori', regions={3: 'main', 4: 'main', 6: 'main', 9: 'main', 5: 'under'},
                  split={5: [('accent', 'lilac')]}, neck=True, folds=(3, 4), under_down={5: (25, 6)}),  # fiori sulla maglia
         bottom=dict(id='pantaloni-scuri', name='Pantaloni marrone scuro', regions={10: 'main'}, to_shoes=(10,),
                     behind={10: (7, 8)}, clip_top=(10,), to_waist=(10,), under_up={10: 12})),
]

# Terzo set: abiti e gonne. Un abito sta in due capi (corpetto con le maniche e gonna con cintura e fiocchi) sulla stessa
# figura: la gonna porta con sé le gambe nude (come i pantaloncini) e il corpetto si abbina a pantaloni qualsiasi.
OUTFITS['vestiti-femminili-3'] = [
    dict(body='bambina',
         top=dict(id='abito-sbuffo', name='Abito con maniche a sbuffo', regions={3: 'main'}, arms=(4, 5), under_down={3: (30, 1)}, neck_up=20),
         bottom=dict(id='gonna-fiocco', name='Gonna con cintura e fiocco', regions={9: 'main', 7: 'trim', 6: 'trim', 10: 'skin', 11: 'skin'},
                     to_shoes=(10, 11), behind={9: (4, 5)}, under_up={9: 20})),
    dict(body='ragazza', seal=1.0, bridge=[((348, 712), (346, 723)), ((484, 705), (487, 720))],     # al foglio manca un pezzo del contorno della gonna
         top=dict(id='camicetta-colletto', name='Camicetta con colletto', regions={6: 'main', 3: 'trim', 5: 'trim'}, arms=(8, 9), under_down={6: (30, 1)}),
         bottom=dict(id='gonna-rosa', name='Gonna a campana rosa', regions={12: 'main', 11: 'trim', 14: 'skin', 15: 'skin'},
                     to_shoes=(14, 15), behind={12: (8, 9)}, under_up={12: 20})),
    dict(body='slanciata',
         top=dict(id='blusa-quadrata', name='Blusa con scollo quadrato', regions={3: 'main', 4: 'main'}, neck=True,
                  absorb={3: (5,)}, under_down={3: (30, 1, 0.5)}),                                                                  # il cuneo fra manica e busto
         bottom=dict(id='pantaloni-marroni-cintura', name='Pantaloni marroni con cintura',
                     regions={9: 'main', 7: 'accent', 6: 'accent', 8: 'accent'}, to_shoes=(9,), behind={9: (10, 11)}, under_up={9: 20})),
    dict(body='adulta',
         top=dict(id='blazer-beige', name='Blazer beige', regions={3: 'main', 4: 'main', 6: 'main', 8: 'trim', 12: 'trim', 5: 'under'},
                  neck=True, folds=(3, 4), under_down={5: (25, 0)}, absorb={3: (7,)}),                             # cuneo fra manica e giacca
         bottom=dict(id='pantaloni-neri-cintura', name='Pantaloni neri con cintura', regions={13: 'main', 9: 'accent', 10: 'accent', 11: 'accent'},
                     to_shoes=(13,), behind={13: (14, 15)}, under_up={13: 40},
                     pad_under={13: dict(near=(3, 4, 6, 8), up=14, down=0)})),                           # il bordo alto è l'orlo del blazer
    dict(body='robusta',
         top=dict(id='abito-portafoglio', name='Abito a portafoglio (corpetto)', regions={3: 'main', 4: 'main'}, arms=(6, 7), neck=True,
                  under_down={3: 85}, neck_up=40),
         bottom=dict(id='gonna-portafoglio', name='Gonna a portafoglio con fiocco',
                     regions={10: 'main', 8: 'trim', 9: 'trim', 11: 'trim', 12: 'trim', 13: 'trim', 14: 'skin', 15: 'skin'},
                     to_shoes=(14, 15), behind={10: (6, 7)}, under_up={10: 20})),
]

OUTFITS['vestiti-femminili-4'] = [
    dict(body='bambina', dark=80,                                                                # il contorno del fiocco è più chiaro
         top=dict(id='abito-rosa', name='Abito rosa senza maniche', regions={3: 'main', 4: 'skin', 5: 'skin'},
                  parts={4: 'arms', 5: 'arms'}, neck=True, absorb={3: (10,)}, under_down={3: (70, 1, 0.5)}),
         bottom=dict(id='gonna-tulle', name='Gonna a ruota con fiocco', regions={11: 'main', 9: 'trim', 7: 'trim', 8: 'trim', 6: 'trim',
                                                                             16: 'skin', 17: 'skin'},
                     absorb={11: (15,)}, to_shoes=(16, 17), behind={11: (4, 5)}, under_up={11: 20}, folds=(11,))),
    dict(body='ragazza',
         top=dict(id='abito-bordeaux', name='Abito bordeaux con spalline', regions={5: 'main', 4: 'skin', 6: 'skin', 8: 'skin'},
                  parts={6: 'arms', 8: 'arms'}, neck=True, absorb={5: (10,)}, under_down={5: (55, 1, 0.5)}),
         bottom=dict(id='gonna-bordeaux', name='Gonna a ruota con fiocco', regions={18: 'main', 16: 'main', 17: 'main', 11: 'trim', 12: 'trim',
                                                                               13: 'trim', 14: 'trim', 20: 'skin', 22: 'skin'},
                     absorb={20: (24,), 22: (23,)}, to_shoes=(20, 22), behind={18: (6, 8)}, under_up={18: 20})),
    dict(body='slanciata', cuts=[(9, 497)],
         top=dict(id='abito-nero', name='Abito nero con spalline (corpetto)', regions={9: 'main', 5: 'skin', 6: 'skin', 15: 'skin', 7: 'skin'},
                  parts={6: 'arms', 15: 'arms'}, neck=True, absorb={9: (16,)}, under_down={9: (40, 1, 0.5)}),
         bottom=dict(id='gonna-lunga-nera', name='Gonna lunga con spacco', regions={67: 'main', 21: 'main', 24: 'main', 18: 'skin'},
                     absorb={67: (24, 25, 26), 21: (33,), 18: (29, 32)}, to_shoes=(18,), behind={67: (6, 15)}, under_up={67: 30})),
    dict(body='adulta',
         top=dict(id='camicetta-bluse', name='Camicetta a portafoglio', regions={4: 'main'}, arms=(22, 21), neck=True, folds=(4,),
                  absorb={4: (5,)}, under_down={4: (60, 6, 0, 492)}),
         bottom=dict(id='gonna-verde', name='Gonna verde con fiocco', regions={17: 'main', 19: 'main', 7: 'trim', 11: 'trim', 12: 'trim',
                                                                            13: 'trim', 16: 'trim', 18: 'trim', 23: 'skin', 24: 'skin'},
                     absorb={23: (27, 25), 24: (26,)}, to_shoes=(23, 24), behind={17: (22, 21)}, under_up={17: 20})),
    dict(body='robusta', bridge=[((1391, 540.5), (1397, 540.5)), ((1410, 540), (1416, 540))],   # il tratto interno della fibbia ha due interruzioni
         top=dict(id='tuta-blu', name='Tuta blu senza maniche (corpetto)', regions={5: 'main', 7: 'main', 6: 'skin', 9: 'skin', 8: 'skin'},
                  parts={6: 'arms', 9: 'arms'}, neck=True, neck_up=40, absorb={5: (10,)}, under_down={5: (90, 1, 0.5)}),
         bottom=dict(id='tuta-pantaloni', name='Pantaloni larghi con cintura', regions={16: 'main', 17: 'main', 15: 'main', 13: 'trim',
                                                                              12: 'trim', 14: 'trim', 11: 'accent'},      # cintura e fibbia dorata
                     join={16: (17,)}, to_shoes=(16,), behind={16: (6, 9)}, under_up={16: 20})),
]

OUTFITS['vestiti-maschili-outfit'] = [
    dict(body='bambino',
         top=dict(id='maglietta-riga', name='Maglietta con riga', regions={3: 'main'}, arms=(4, 5),
                  split={3: [('accent', 'darker')]}),                                                  # la riga sul petto
         bottom=dict(id='bermuda-cargo', name='Bermuda cargo', regions={7: 'main', 6: 'main', 8: 'main', 9: 'main', 10: 'main',
                                                                       11: 'main', 12: 'skin', 13: 'skin', 14: 'under', 15: 'under'},
                     to_shoes=(14, 15), behind={7: (3,)}, under_up={7: 30})),                          # gambe e calze
    dict(body='ragazzo',
         top=dict(id='felpa-rossa', name='Felpa con cappuccio', regions={3: 'main'}, neck=True, folds=(3,)),
         bottom=dict(id='jeans-grigi', name='Jeans grigi', regions={11: 'main'}, join={11: (12,)}, to_shoes=(11,),
                     behind={11: (3,)}, under_up={11: 30})),
    dict(body='slanciato',
         top=dict(id='camicia-risvoltata', name='Camicia con maniche arrotolate',
                  regions={3: 'main', 6: 'main', 4: 'main', 7: 'main', 8: 'main', 9: 'main', 5: 'under'}, neck=True,
                  under_down={5: (25, 0)}),
         bottom=dict(id='pantaloni-kaki', name='Pantaloni kaki', regions={12: 'main'}, to_shoes=(12,),
                     behind={12: (3, 5, 6)}, under_up={12: 30})),
    dict(body='adulto',
         top=dict(id='polo-blu', name='Polo blu', regions={3: 'main', 4: 'main'}, arms=(6, 7),
                  split={4: [('trim', 'lighter', 10)]}, under_down={3: 30}),                           # bottoni della patta; infilata
         bottom=dict(id='pantaloni-cintura', name='Pantaloni con cintura',
                     regions={10: 'main', 15: 'main', 9: 'accent', 11: 'accent', 12: 'accent', 13: 'accent', 14: 'accent', 8: 'trim'},
                     to_shoes=(10,), under_up={10: 30})),                                              # cintura e fibbia
    dict(body='robusto',
         top=dict(id='cardigan-grigio', name='Cardigan grigio', regions={3: 'main', 4: 'main', 5: 'under'}, neck=True,
                  folds=(3, 4), under_down={5: (25, 0)}),
         bottom=dict(id='jeans-chiari', name='Jeans chiari', regions={6: 'main'}, to_shoes=(6,),
                     behind={6: (3, 4, 5)}, under_up={6: 30})),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheet', help='foglio con gli outfit')
    ap.add_argument('--bodies', required=True, help='cartella delle sagome tracciate (es. src/bodies/femmina)')
    ap.add_argument('--out', required=True, help='cartella dei capi del gruppo (es. src/clothes/femmina): uno strato per sagoma')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    stem = os.path.splitext(os.path.basename(a.sheet))[0]
    if stem not in OUTFITS:
        sys.exit(f'Nessuna tabella per il foglio {stem}: aggiungere OUTFITS[{stem!r}]')
    table = OUTFITS[stem]
    sheet = Sheet(a.sheet)
    boxes = sheet.figures()
    if len(boxes) != len(table):
        sys.exit(f'Il foglio ha {len(boxes)} figure ma la tabella ne ha {len(table)}')
    for spec, box in zip(table, boxes):
        with open(os.path.join(a.bodies, spec['body'] + '.json'), encoding='utf8') as f:
            ref = json.load(f)
        if a.verbose:
            print(spec['body'])
        res = trace_outfit(sheet, box, ref, spec, verbose=a.verbose)
        for kind, folder in (('top', 'tops'), ('bottom', 'bottoms')):
            cs, garment = spec[kind], res[kind]
            write_garment(os.path.join(a.out, spec['body'], folder), cs['id'], cs['name'], garment)
            print(f'{folder}/{cs["id"]}: {len(garment["regions"])} regioni, {len(garment["seams"])} linee, {len(garment["dots"])} puntini, colori {garment["colors"]}')


if __name__ == '__main__':
    main()
