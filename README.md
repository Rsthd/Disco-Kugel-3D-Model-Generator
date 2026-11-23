# Disco-Kugel-Generator

Ein Python-Skript (`discoball.py`), das eine **3D-druckbare Disco-Kugel** als STL-Datei erzeugt. Auf die Kugel klebst du quadratische Spiegelfliesen (z. B. 3 × 3 cm). Größe, Spiegelgröße, Bohrungen und vieles mehr stellst du über Parameter ein. Das Skript berechnet das Spiegel-Layout selbst und prüft, dass sich keine Spiegel überlappen.

**Was du bekommst**

- Kugel in beliebiger Größe, **hohl** (spart Material) oder **voll** (massiv)
- **Quadratische, ebene Klebeflächen** in Spiegelgröße, die Kugel läuft rund dazwischen durch
- Klebefläche in der Mitte und an den Kantenmitten **bündig** mit der Kugel, nur die Ecken stehen ca. 0,7 mm vor
- **Zwei durchgehende Bohrungen** von Pol zu Pol (z. B. für M8-Gewindestangen), eine in der Mitte, eine daneben als Sicherung
- Flache Auflagefläche an den Polen für Muttern und Scheiben
- **Automatisches Zerlegen** in beliebig viele Teile (2, 8, 27 oder mehr), die auf dein Druckbett passen. Schnitte dürfen durch Spiegelflächen gehen, die Teile müssen nicht identisch sein
- Rechenzeit: wenige Sekunden

> **Hinweis:** Das Modell wurde geometrisch geprüft (geschlossene Netze, Kollisionsprüfung der Spiegel), aber nicht in jeder Einstellung gedruckt. Mach vor dem großen Druck einen kleinen Test, z. B. mit `--durchmesser 120 --fliese 15 --loch 6.5 --scheibe 13 --loch-abstand 15`.

---

## 1. Installation

Du brauchst **Python 3** und das Paket **numpy**. Mehr nicht (nur für den Facetten-Stil zusätzlich `scipy`).

### Windows

1. Python installieren: [python.org/downloads](https://www.python.org/downloads/windows/) herunterladen, beim Installieren den Haken **„Add python.exe to PATH“** setzen. Alternativ in der PowerShell: `winget install Python.Python.3.12`
2. PowerShell öffnen und numpy installieren:
   ```
   py -m pip install numpy
   ```

### macOS / Linux

```
python3 -m pip install numpy
```

(macOS mit Homebrew: `brew install python`. Debian/Ubuntu: `sudo apt install python3 python3-pip`.)

### Tipp bei Problemen mit sehr neuen Python-Versionen

Wenn `pip` für die neueste Python-Version `numpy` nicht installieren kann oder das Skript sagt „No module named numpy“, obwohl du es installiert hast, liegt das oft an mehreren Python-Versionen nebeneinander. Nimm dann eine etwas ältere Version (z. B. 3.12) und rufe **alles** damit auf:

```
py -3.12 -m pip install numpy
py -3.12 discoball.py ...
```

Mit `py -0` siehst du unter Windows, welche Versionen installiert sind.

### Skript bereitstellen

Lege `discoball.py` in einen Ordner, öffne dort ein Terminal und starte:

```
py discoball.py --help
```

Die erzeugten STL-Dateien landen im gleichen Ordner. (Unter macOS/Linux `python3` statt `py`.)

---

## 2. Schnellstart

| Ziel | Befehl |
|---|---|
| 30-cm-Kugel, 3-cm-Spiegel, 2 Halbkugeln (hohl) | `py discoball.py --modus halb --durchmesser 300` |
| Dasselbe, aber massiv | `py discoball.py --modus halb --durchmesser 300 --innen voll` |
| 315-mm-Kugel, massiv, 6,8-mm-Bohrungen (M8-Kernloch) | `py discoball.py --modus halb --innen voll --durchmesser 315 --fliese 30 --loch 6.8 --loch-abstand 15 --scheibe 14` |
| Zerlegt für ein 256-mm-Druckbett | `py discoball.py --modus teilen --bett 256x256x256 --durchmesser 300` |
| Riesenkugel (90 cm, 5-cm-Spiegel) in Teilen für ein 330×320×325-Bett | `py discoball.py --modus teilen --bett 330x320x325 --innen hohl --durchmesser 900 --fliese 50 --loch 6.8 --loch-abstand 15 --scheibe 14` |
| 20-cm-Kugel mit 2-cm-Spiegeln, M6-Stangen | `py discoball.py --durchmesser 200 --fliese 20 --loch 6.5 --scheibe 13 --loch-abstand 15` |

Das Skript schreibt eine kurze Zusammenfassung, zum Beispiel:

```
Kugel 315 mm (voll), Fliesen 30 mm: 7 Reihen je Halbkugel, Kacheln pro Reihe [31, 29, 26, 22, 17, 11, 5]  (Fuge 1.00 mm)
Pol: flache Auflage Radius 22.5 mm, Bohrung 6.8 mm, 2. Bohrung im Abstand 15 mm
disco_halb_voll_315mm_fliese30.stl | Dreiecke: ... | Groesse (x,y,z): [313.2 313.6 154.6] mm
```

Die Größe zeigt dir, ob das Teil auf dein Druckbett passt. Die Anzahl der Spiegel pro Halbkugel ist die Summe der „Kacheln pro Reihe“ (hier 141, also 282 für die ganze Kugel).

---

## 3. Wie die Kugel aufgebaut ist

**Durchmesser.** `--durchmesser` ist der Abstand zwischen zwei gegenüberliegenden Spiegeloberflächen, gemessen durch die Spiegelmitten. Die Spiegelecken stehen minimal darüber. Das gedruckte Teil ist etwa 2 mm kleiner als der Nenndurchmesser (315 mm → ca. 313 mm Breite), weil der Spiegel selbst noch dazukommt.

**Spiegeldicke.** `--dicke` (Standard 2 mm) ist die Dicke deiner Spiegelfliese. Die Klebefläche liegt um diese Dicke unter dem Nenndurchmesser. **Miss deine Spiegel nach**, sonst wird die Kugel etwas zu groß oder zu klein.

**Klebefläche und Mulde.** Auf einer runden Kugel kann ein ebener Spiegel nie überall bündig aufliegen. Das Skript schneidet deshalb unter jedem Spiegel eine **sehr flache Mulde** in die Kugel (Standard: etwa 0,7 mm tief bei 30-mm-Spiegeln auf 30 cm). Die Fläche ist so in der Mitte und an den Kantenmitten bündig, und nur die Ecken stehen etwa 0,7 mm vor. Zwischen den Spiegeln bleibt die Kugel rund.

**Hohl und voll.**
- `hohl`: Schale mit 3 mm Wand. Durch den Hohlraum laufen zwei **Führungsrohre** für die Stangen, die beiden Hälften richten sich daran aus. An den Polen sitzt eine 4 mm dicke massive Platte mit flacher Auflage für Muttern und Scheiben.
- `voll`: massiv. Den Infill stellst du im Slicer ein (z. B. 10–15 %).

**Bohrungen.** Eine Bohrung sitzt immer genau in der Mitte, die zweite im Abstand `--loch-abstand` daneben. Mit `--loch-abstand 0` gibt es nur die Mittelbohrung. An beiden Polen gibt es eine ebene Auflage (Radius = Scheibenradius + Lochabstand), damit Muttern und Scheiben plan aufliegen.

**Layout.** Die Spiegel sitzen in Reihen vom Äquator zum Pol. Das Skript legt die Reihen so eng, wie es geht, solange zwischen den Spiegeln mindestens `--fuge` Abstand bleibt und sie sich nicht berühren. Die Anzahl pro Reihe ergibt sich automatisch. Die Reihen liegen so, dass keine Spiegel den Äquator berühren. Dadurch passen die Halbkugeln exakt aneinander.

**STL-Aufbau.** Die STL enthält einen geschlossenen Hauptkörper (Kugel, Pole, Rohre) und je einen kleinen Quader als Klebefläche pro Spiegel. Diese überlappen die Kugel; der Slicer verschmilzt sie beim Slicen (PrusaSlicer, Bambu Studio, OrcaSlicer, Cura). Wenn dein Slicer sie nicht zusammenführt oder Warnungen zeigt, schau in den Abschnitt „Fehlerbehebung“.

---

## 4. Alle Parameter

Alle Maße in Millimetern. Reihenfolge der Parameter ist egal.

### Kugel und Spiegel

| Parameter | Standard | Bedeutung |
|---|---|---|
| `--durchmesser` | 300 | Kugeldurchmesser bis Spiegeloberfläche (Kachelmitte) |
| `--fliese` | 30 | Kantenlänge der quadratischen Spiegel |
| `--dicke` | 2.0 | Dicke der Spiegelfliesen (nachmessen!) |
| `--fuge` | 1.0 | Mindestabstand zwischen den Spiegeln. Kleiner = mehr Spiegel. Das Skript probiert zusätzlich bis zu 2 mm größere Fugen, wenn dadurch mehr Spiegel passen. |
| `--sockel` | 0.0 | Zugabe pro Seite der Klebefläche gegenüber dem Spiegel, z. B. `0.5` für etwas Spielraum beim Aufsetzen (muss kleiner als die halbe Fuge bleiben, sonst verschmelzen benachbarte Flächen) |

### Aufbau der Kugel

| Parameter | Standard | Bedeutung |
|---|---|---|
| `--innen` | hohl | `hohl` (Schale mit Führungsrohren) oder `voll` (massiv) |
| `--wand` | 3.0 | Wandstärke der Hohlkugel (Minimum in der Mitte der Mulde) |
| `--mulde` | auto | Tiefe der flachen Mulde unter jedem Spiegel. `auto` = so tief, dass die Fläche an den Kantenmitten bündig ist. `0` = Fläche berührt die Kugel nur in der Mitte (Ecken stehen dann ca. 1,5 mm vor) |
| `--sockelhoehe` | 0.0 | Zusätzliche Höhe der Klebefläche über der Kugel (für Sonderfälle, meist nicht nötig) |
| `--platte` | 4.0 | Dicke der massiven Polplatte (nur hohl) |
| `--rohrwand` | 2.4 | Wandstärke der Führungsrohre (nur hohl) |

### Bohrungen

| Parameter | Standard | Bedeutung |
|---|---|---|
| `--loch` | 8.5 | Bohrungsdurchmesser. Für eine M8-Stange mit Spiel `8.5`. `6.8` ist das Kernloch, wenn du ein M8-Gewinde schneiden willst |
| `--loch-abstand` | 20 | Abstand der 2. Bohrung von der Mitte. `0` = nur eine Bohrung. Mindestens `loch + 4` (voll) bzw. `2 · (loch/2 + rohrwand) + 2` (hohl) |
| `--scheibe` | 17 | Außendurchmesser deiner Scheibe/Mutter. Bestimmt die Größe der flachen Polauflage. Kleinere Werte lassen am Pol Platz für zusätzliche Spiegel |
| `--polabstand` | 1.5 | Mindestabstand zwischen Polfläche und der ersten Spiegelreihe |

### Modus und Zerlegen

| Parameter | Standard | Bedeutung |
|---|---|---|
| `--modus` | halb | `halb`, `komplett`, `teilen` oder `teil` (siehe unten) |
| `--bett` | – | Druckbett für `--modus teilen`, z. B. `330x320x325` (Breite × Tiefe × Höhe) |
| `--schnitte` | auto | Nur bei `teilen`: Raster der Teile als `NXxNYxNZ`, z. B. `3x3x2`. `auto` wählt das Raster mit den wenigsten Teilen, die noch aufs Bett passen. NZ muss mindestens 2 sein |

### Feintuning und Ausgabe

| Parameter | Standard | Bedeutung |
|---|---|---|
| `--winkel` | 0.5 | Winkelschritt der Kugelfläche in Grad. Kleiner = glatter, aber größere Datei |
| `--stil` | sockel | `sockel` (runde Kugel mit quadratischen Klebeflächen) oder `facetten` (siehe unten) |
| `--ueberstand` | 0.8 | Nur `facetten`: wie weit eine Spiegelecke über die Nachbarfacette ragen darf |
| `--out` | automatisch | Dateiname bzw. Präfix der STL-Datei(en) |

---

## 5. Die Modi im Detail

### `halb` (Standard): 2 Halbkugeln

Erzeugt die obere Halbkugel. **Du druckst sie 2-mal.** Die zweite Hälfte kommt umgedreht nach unten (um die waagerechte Achse durch beide Bohrungen gedreht). Dann liegen die Bohrungen genau gegenüber, und die Spiegelmuster passen zusammen. Dateiname: `disco_halb_<innen>_<D>mm_fliese<F>.stl`.

Gedruckt wird mit der **flachen Schnittfläche (Äquator) nach unten**.

### `komplett`: ganze Kugel

Eine STL mit der kompletten Kugel (beide Hälften nebeneinanderliegend aneinandergesetzt). Nur sinnvoll für Ansicht oder sehr große Drucker. Gedruckt braucht sie viel Stützmaterial.

### `teilen`: beliebig viele Teile, passend zum Druckbett

```
py discoball.py --modus teilen --bett 330x320x325 --durchmesser 900 --fliese 50 --innen hohl
```

Das Skript legt ein Raster aus senkrechten und waagerechten Schnittebenen durch die Kugel (`NX × NY × NZ` Zellen). Jede Zelle ist ein eigenes Teil. Bei `auto` wählt es das Raster mit den **wenigsten Teilen**, bei dem jede Zelle noch aufs Bett passt (mit 2 mm Luft). Zellen ohne Material (bei hohlen Kugeln die Mitte) entfallen.

- **Beispiele:** 315 mm auf einem 330×320-Bett: 2 Halbkugeln. 300 mm auf einem 256-mm-Bett: 8 Teile. 900 mm auf einem 330×320×325-Bett: 3 × 3 × 3 Raster, hohl 26 Teile, massiv 27 Teile.
- **Die Teile sind alle verschieden.** Das Skript schreibt pro Teil eine Datei, **jede wird genau 1× gedruckt**: `<name>_teil07_x1y3z1.stl`. Die Zahlen `x1y3z1` geben die Position in der Kugel an (x: links nach rechts, y: vorne nach hinten, z: unten nach oben).
- **Übersichtsdatei:** `<name>_uebersicht.txt` listet alle Teile mit Position, Größe und Druckhinweis auf. Hebe sie beim Zusammenbau auf.
- **Gedruckt wird immer mit einer ebenen Schnittfläche nach unten.** Die Teile der untersten Schicht (`z1`) sind dafür schon **um 180° gedreht** gespeichert. Beim Zusammenbau setzt du sie wieder nach unten, so dass der Pol mit der Bohrung unten liegt.
- **Schnitte durch Spiegelflächen** sind erlaubt. Ein Spiegel, der auf einer Naht sitzt, klebst du erst, wenn die Nachbarteile verklebt sind, und zwar über die Naht hinweg.
- **Eigenes Raster:** Mit `--schnitte 4x4x3` erzwingst du ein anderes Raster, zum Beispiel mehr, aber kleinere Teile.
- **Rechenzeit:** Eine 900-mm-Kugel mit 27 Teilen braucht etwa eine bis zwei Minuten.
- **Hohl spart viel:** Bei großen Kugeln ist `--innen hohl` fast immer sinnvoll. Die Teilezahl ändert sich kaum, aber der Materialverbrauch sinkt enorm (bei 900 mm etwa 9 l statt 378 l Volumen).

### `teil`: Viertel mit identischen Teilen

```
py discoball.py --modus teil --durchmesser 300
```

Ein Viertel einer Halbkugel. Die Spiegelreihen werden so gelegt, dass die Schnitte **zwischen** den Spiegeln verlaufen, und alle Teile sind identisch (außer dem Teil mit der 2. Bohrung). Das ergibt weniger Spiegel pro Reihe als bei `teilen`. Du bekommst zwei Dateien: `_N` (6× drucken) und `_P` (2× drucken, mit der 2. Bohrung). Nur mit `--stil sockel`.

### `--stil facetten`: Kugel aus ebenen Flächen

Statt runder Kugel mit quadratischen Klebeflächen entsteht ein vielflächiger Körper, auf dessen Flächen die Spiegel direkt liegen. Die Flächen sind keine Quadrate mehr, sondern unregelmäßige Vielecke. Braucht `scipy` (`py -m pip install scipy`) und funktioniert nur mit `--modus halb` und `komplett`. Gedacht als Alternative, der Standardstil sieht meist sauberer aus.

---

## 6. Beispiele und Spiegelzahlen

Spiegelzahl pro Halbkugel mit den jeweils angegebenen Einstellungen (für die ganze Kugel mal 2). Die Zahl hängt von `--fuge`, `--loch-abstand` und `--scheibe` ab.

| Kugel | Spiegel | Besonderheiten | Spiegel pro Halbkugel |
|---|---|---|---|
| 200 mm | 20 mm | `--loch 6.5 --scheibe 13 --loch-abstand 15` | 118 |
| 250 mm | 25 mm | Standardwerte | 121 |
| 300 mm | 30 mm | Standardwerte | 124 |
| 315 mm | 30 mm | `--loch 6.8 --loch-abstand 15 --scheibe 14` | 141 |
| 400 mm | 30 mm | Standardwerte | 225 |

**Mehr Spiegel am Pol:** Mit kleinerem `--scheibe` und `--loch-abstand` schrumpft die flache Polfläche. Dann passt manchmal noch eine zusätzliche Reihe darum (bei 315 mm von 6 auf 7 Reihen). Bei Mutter statt Scheibe sind `--scheibe 14 --loch-abstand 15` gut, die Muttern berühren sich dann fast.

**Kleine Kugeln:** Sind die Spiegel im Verhältnis zur Kugel groß, stehen die Ecken der Klebeflächen weiter vor (bei Radius = 4 × Spiegelkante ca. 0,9 mm, bei 2,5 × ca. 1,5 mm). Ab etwa einem Kugelradius von 2,5 × Spiegelkante gibt das Skript eine Warnung aus. Dann besser kleinere Spiegel oder eine größere Kugel wählen. Außerdem braucht die flache Polauflage Platz: Bei kleinen Kugeln `--scheibe` und `--loch-abstand` verkleinern, sonst gehen am Pol viele Spiegelplätze verloren.

---

## 7. Drucken

- **Lage:** Flache Schnittfläche (Äquator) nach unten, Kuppel nach oben.
- **Stützen:** Einschalten. Die Wölbung der Kuppel und bei hohlen Kugeln die flache Decke im Hohlraum (ca. 60 mm breit) brauchen sie. Organische/Baum-Stützen sind meist am einfachsten.
- **Bettgröße:** Das Teil ist etwa 2 mm kleiner als der Nenndurchmesser (315 mm → 313,2 × 313,6 mm). Bei knappem Platz Skirt und Brim ausschalten und das Teil mittig platzieren. Reicht das Bett nicht, nimm `--modus teilen`.
- **Material:** Hohle Halbkugel 315 mm: ca. 0,55 l Volumen, etwa 0,7 kg PLA. Massiv hängt stark vom Infill ab. Wähle z. B. 10–15 %.
- **Dateigröße:** Eine Halbkugel hat je nach Größe 10–25 MB. Das lädt in jedem gängigen Slicer.

---

## 8. Zusammenbau

1. Alle Teile drucken (Halbkugel jeweils 2-mal, bei `teilen` jede Datei 2-mal).
2. **Probe stecken:** Gewindestangen durch die Mittelbohrung und die zweite Bohrung stecken, die Hälften ohne Kleber zusammensetzen und die Passung prüfen. Die Stangen richten die Teile aus.
3. Hälften an der Naht verkleben (Epoxid oder Sekundenkleber-Gel), dabei die Stangen als Führung nutzen.
4. Muttern und Scheiben an beiden Polen auf die flachen Auflagen schrauben.
5. **Spiegel kleben:** Einen Kleber verwenden, der für Spiegelrückseiten geeignet ist (kein säurevernetzendes Silikon, das die Verspiegelung angreifen kann). Einen Tropfen in die Mitte der Klebefläche, den Spiegel aufsetzen und leicht andrücken. Abstandshalter aus Karton zwischen den Spiegeln halten die Fugen gleichmäßig. Bei `teilen` Spiegel auf den Nähten erst kleben, wenn die Teile verklebt sind.

---

## 9. Fehlerbehebung

| Meldung / Problem | Lösung |
|---|---|
| Slicer meldet offene Kanten / Netzfehler, Artefakte an Schnittflächen | Mit der aktuellen Version wird jedes Teil beim Export automatisch bereinigt (Eckpunkte verschweißt, entartete Dreiecke entfernt) und auf Wasserdichtheit geprüft. Alte STL-Dateien neu erzeugen. Meldet das Skript `HINWEIS`, bitte Befehl und Teilenamen angeben. |
| `No module named 'numpy'` | `py -m pip install numpy` mit **derselben** Python-Version, mit der du das Skript startest (siehe Abschnitt 1) |
| `unrecognized arguments: --...` | Du hast eine ältere Version von `discoball.py`. Lade die aktuelle herunter |
| `--loch-abstand zu klein: mind. ... mm` | Abstand der 2. Bohrung vergrößern, oder `--innen voll` bzw. kleineres `--rohrwand` wählen |
| `Kugel zu klein fuer diese Bohrungen/Auflage` | Kleineres `--scheibe`/`--loch-abstand` oder `--innen voll` |
| `Die Mulden reichen bis an den Pol bzw. den Aequator` | `--polabstand` erhöhen oder `--mulde` kleiner wählen |
| `Fuer --modus teilen bitte das Druckbett angeben` | `--bett 330x320x325` (oder dein Maß) ergänzen |
| `Die Kugel laesst sich mit diesem Raster nicht auf das Bett ... verteilen` | Die Zellen müssten kleiner als das Bett sein. Prüfe `--bett` (Breite x Tiefe x Höhe) oder wähle einen kleineren `--durchmesser` |
| `--schnitte: NZ muss mindestens 2 sein` | Bei `--schnitte NXxNYxNZ` den dritten Wert auf 2 oder mehr setzen |
| `HINWEIS: Scheibe/Mutter ragt ... ueber die ebene Polflaeche` | Kleineres `--scheibe` oder anderen `--loch-abstand` |
| Hinweis, dass sich Scheiben überlappen | `--loch-abstand` größer als `--scheibe + 1` wählen oder kleinere Scheiben/Muttern |
| Slicer zeigt fehlende Taschen/Warnungen wegen Überlappungen | Das Teil als **ein Objekt** laden und Slicer-Reparatur nutzen. Gelingt es nicht, Rückmeldung mit Slicer-Name und Version geben |

---

## 10. Grenzen

- Ein ebener Spiegel auf einer Kugel kann nie überall bündig sein. Die Ecken stehen immer etwas vor (bei 30 mm auf 30 cm ca. 0,7 mm).
- Pro Spiegel gibt es nur quadratische Klebeflächen. Dreieckige oder rechteckige Spiegel werden nicht unterstützt.
- Die Spiegelanzahl ergibt sich aus der Geometrie, du kannst einzelne Spiegel nicht per Hand ein- oder ausschalten.
- Der Viertel-Modus `teil` ist nur im Stil `sockel` möglich.
- Das Modell ist ein Hobby-Werkzeug. Prüfe Maße und Passung immer mit einem Teststück, bevor du viel Filament verbrauchst.
