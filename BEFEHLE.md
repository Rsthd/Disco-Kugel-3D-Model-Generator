# Fertige Befehle (PowerShell, Windows)

Test-Kugel 315 mm, 30-mm-Spiegel (1 mm dick), M6-Stangen, 2 Haelften (je 1x drucken, zweite Haelfte umdrehen):

    py -3.12 discoball.py --modus halb --innen voll --durchmesser 315 --fliese 30 --dicke 1 --loch 6.5 --loch-abstand 14 --scheibe 19 --out disco315

Grosse Kugel 900 mm, 50-mm-Spiegel, Bett Bambu Lab A2L, in Teile geteilt:

    py -3.12 discoball.py --modus teilen --bett 330x320x325 --innen voll --durchmesser 900 --fliese 50 --loch 6.8 --loch-abstand 15 --scheibe 14 --out kugel900

Hinweise:
- `--dicke` = Spiegeldicke (+ Kleber); der Druckkoerper ist im Radius um diesen Wert kleiner.
- Auflage-Radius des Pols = `--scheibe`/2 + 0,5 + `--loch-abstand`. Bei 315 mm / 30 mm Spiegeln bleiben alle 7 Reihen bis 24,0 mm.
