#!/usr/bin/env python3
"""
Disco-Kugel-Generator (v7): 3D-druckbare Kugel fuer quadratische Spiegelfliesen zum Aufkleben.
Hohl oder voll, mit 2 durchgehenden Bohrungen (z.B. M8-Gewindestangen) von Pol zu Pol, in beliebiger Groesse,
auf Wunsch automatisch in Teile zerlegt, die zum Druckbett passen.

Beispiele:
  py discoball.py --modus halb --durchmesser 300                     # 2 Halbkugeln, hohl (je 2x drucken)
  py discoball.py --modus halb --durchmesser 315 --innen voll --loch 6.8 --loch-abstand 15 --scheibe 14
  py discoball.py --modus teilen --bett 256x256x256 --durchmesser 300  # in beliebig viele Teile zerlegt, passend zum Bett
  py discoball.py --durchmesser 200 --fliese 20 --loch 6.5           # 20 cm Kugel, 2-cm-Fliesen, M6-Stangen

Modi:   halb = Halbkugel (2x drucken) | komplett = ganze Kugel | teilen = passend zum Druckbett zerlegt (--bett)
        teil = Viertel einer Halbkugel mit identischen Teilen (nur --stil sockel)
Innen:  hohl = Schale mit Fuehrungsrohren fuer die Stangen | voll = massiv (Infill stellst du im Slicer ein)
Alle Masse in mm. Benoetigt: numpy   (py -m pip install numpy);  nur fuer --stil facetten zusaetzlich scipy.
Hinweis: Die STL besteht aus einem geschlossenen Hauptkoerper (Schale/Pole/Rohre) plus je einer ebenen
         Klebeflaeche (Sockel) pro Spiegel; die Sockel ueberlappen die Schale und werden vom Slicer verschmolzen.
"""
import argparse, struct
import numpy as np

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('--durchmesser', type=float, default=300.0, help='Kugeldurchmesser bis Spiegeloberflaeche (Kachelmitte), mm')
p.add_argument('--fliese',      type=float, default=30.0,  help='Kantenlaenge der quadratischen Spiegel, mm')
p.add_argument('--dicke',       type=float, default=2.0,   help='Dicke der Spiegelfliesen, mm (nachmessen!)')
p.add_argument('--wand',        type=float, default=3.0,   help='Wandstaerke der Hohlkugel, mm')
p.add_argument('--sockel',      type=float, default=0.0,   help='Zugabe pro Seite der Klebeflaeche gegenueber dem Spiegel, mm (0 = exakt Spiegelgroesse)')
p.add_argument('--fuge',        type=float, default=1.0,   help='Mindestabstand zwischen den Spiegeln, mm')
p.add_argument('--innen',       choices=['hohl','voll'], default='hohl', help='hohl = Schale mit Fuehrungsrohren, voll = massiv')
p.add_argument('--loch',        type=float, default=8.5,   help='Bohrungsdurchmesser fuer die Stangen, mm (M8 -> 8.5)')
p.add_argument('--loch-abstand',type=float, default=20.0,  help='Abstand der 2. Bohrung von der Mittelachse, mm (0 = nur eine Bohrung)')
p.add_argument('--rohrwand',    type=float, default=2.4,   help='Wandstaerke der Fuehrungsrohre im Hohlraum, mm')
p.add_argument('--scheibe',     type=float, default=17.0,  help='Aussendurchmesser der Unterlegscheibe/Mutter, mm (bestimmt die flache Auflage)')
p.add_argument('--polabstand',  type=float, default=None,   help='Mindestabstand zwischen flacher Polflaeche und erster Spiegelreihe, mm (Standard: facetten 0.5, sockel 1.5)')
p.add_argument('--ueberstand',  type=float, default=0.8,   help='Nur facetten: wie weit eine Spiegelecke ueber die Nachbarfacette ragen darf (der Kleber gleicht es aus), mm')
p.add_argument('--platte',      type=float, default=4.0,   help='Dicke des massiven Pols (hohle Kugel), mm')
p.add_argument('--stil',        choices=['sockel','facetten'], default='sockel', help='sockel = runde Kugel mit quadratischen ebenen Klebeflaechen (Standard), facetten = Kugel aus ebenen Facetten')
p.add_argument('--sockelhoehe', type=float, default=0.0,   help='Hoehe der ebenen Klebeflaeche ueber der Kugelflaeche in der Spiegelmitte, mm (0 = beruehrt die Kugel genau in der Mitte; an den Ecken steht sie dann ~1,5 mm vor)')
p.add_argument('--mulde',       type=float, default=None,  help='Tiefe der flachen Mulde in der Spiegelmitte, mm. Standard (auto): so tief, dass die Klebeflaeche an den Kantenmitten buendig mit der Kugel ist; nur die Ecken stehen vor. 0 = Flaeche beruehrt die Kugel nur in der Mitte')
p.add_argument('--bett',        default=None,              help='Druckbett fuer --modus teilen, z.B. 330x320x325 (Bambu Lab A2L)')
p.add_argument('--schnitte',    default='auto',            help='Nur --modus teilen: Raster der Teile als NXxNYxNZ (z.B. 3x3x2) oder auto = moeglichst wenige Teile, die aufs Bett passen')
p.add_argument('--modus',       choices=['teil','halb','komplett','teilen'], default='halb', help='teilen = Kugel in beliebig viele Stuecke zerlegen, passend zum Druckbett (--bett); Schnitte duerfen durch Spiegelflaechen gehen')
p.add_argument('--winkel',      type=float, default=0.5,   help='Winkelschritt der Kugelflaeche in Grad (kleiner = glatter)')
p.add_argument('--out',         default=None,              help='Dateiname/Praefix der STL-Datei(en)')
A = p.parse_args()
GEO = 'halb' if A.modus == 'teilen' else A.modus
if A.polabstand is None: A.polabstand = 0.5 if A.stil == 'glatt' else 1.5

R      = A.durchmesser/2
PAD    = A.fliese + 2*A.sockel    # Kantenlaenge der ebenen Klebeflaeche
FLOOR  = R - A.dicke              # Klebeflaeche (Abstand von der Mitte); Spiegeloberflaeche liegt bei R
TOP    = FLOOR
if A.mulde is None:      # Mulde so tief, dass der Kreis Ebene/Kugel knapp ueber die Kantenmitte reicht
    DISH = np.sqrt(FLOOR**2 + (A.fliese/2 + 0.2)**2) - FLOOR
else:
    DISH = A.mulde
SHELL  = FLOOR + DISH - A.sockelhoehe   # Aussenradius der runden Kugel (zwischen den Spiegeln)
SHELLI = min(SHELL, FLOOR) - A.wand     # Innenradius (Mindestwand liegt in der Mitte der Mulde)
BASE   = SHELLI + A.wand/2        # Unterkante der Sockel (liegt in der Wand)
GLATT  = A.stil == 'facetten'
QUANT  = 4 if GEO == 'teil' else 1
if GLATT and GEO == 'teil': raise SystemExit('Viertel-Teile (--modus teil) gibt es nur mit --stil sockel. Fuer den Facetten-Stil: --modus halb oder komplett.')
EPS    = 0.03
HOLLOW = A.innen == 'hohl'

# Pol-Geometrie: flache Auflage statt Flansch
RHO    = A.loch/2                 # Bohrungsradius
RHOT   = RHO + A.rohrwand         # Rohr-Aussenradius
S      = A.loch_abstand           # Abstand 2. Bohrung
SEAT   = A.scheibe/2 + 0.5        # Auflageradius je Bohrung
R_O    = SEAT + S                 # Radius der flachen Polflaeche
Z_FLAT = np.sqrt(SHELL**2 - R_O**2)
Z_CEIL = Z_FLAT - A.platte
R_I    = np.sqrt(max(SHELLI**2 - Z_CEIL**2, 0))
HOLE2_AZ = np.pi/4 if GEO == 'teil' else 0.0
MINS = (2*RHOT + 2) if HOLLOW else (2*RHO + 4)
if S > 0 and S < MINS: raise SystemExit(f'--loch-abstand zu klein: mind. {MINS:.1f} mm' + (' (Fuehrungsrohre wuerden sich beruehren; --innen voll oder kleineres --rohrwand hilft)' if HOLLOW else ''))
if HOLLOW and not GLATT and R_I < S + RHOT + 1.5: raise SystemExit('Kugel zu klein fuer diese Bohrungen/Auflage (Hohlraum-Decke passt nicht). Kleineres --scheibe/--loch-abstand oder --innen voll waehlen.')

# ---------------------------------------------------------------- Geometrie-Helfer (Kacheln)
def frame(lat, az):
    u = np.array([np.cos(lat)*np.cos(az), np.cos(lat)*np.sin(az), np.sin(lat)])
    e = np.array([-np.sin(az), np.cos(az), 0.0])
    n = np.array([-np.sin(lat)*np.cos(az), -np.sin(lat)*np.sin(az), np.cos(lat)])
    return u, e, n

def sat_overlap(CA, AA, hA, CB, AB, hB, margin):
    T = CB - CA
    axes = [AA[:,i] for i in range(3)] + [AB[:,j] for j in range(3)]
    for i in range(3):
        for j in range(3): axes.append(np.cross(AA[:,i], AB[:,j]))
    sep = np.zeros(len(CA), bool)
    for L in axes:
        nl = np.linalg.norm(L, axis=1); good = nl > 1e-9
        Ln = L/np.where(good, nl, 1)[:,None]
        rA = sum(hA[k]*np.abs(np.einsum('ij,ij->i', AA[:,k], Ln)) for k in range(3))
        rB = sum(hB[k]*np.abs(np.einsum('ij,ij->i', AB[:,k], Ln)) for k in range(3))
        sep |= good & (np.abs(np.einsum('ij,ij->i', T, Ln)) > rA + rB + margin)
    return ~sep

H_SLAB = np.array([A.fliese/2, A.fliese/2, A.dicke/2]); C_SLAB = (FLOOR+R)/2     # der Spiegel selbst
def row_boxes(lat, n):
    C, AX = [], []
    for i in range(n):
        u, e, nn = frame(lat, (i+0.5)*2*np.pi/n); C.append(u*C_SLAB); AX.append(np.stack([e, nn, u]))
    return np.array(C), np.array(AX)

FACET_M = -A.ueberstand    # negativ = Spiegelecke darf so weit ueber der Ebene des Nachbarn liegen
def facet_bad(C1, A1, C2, A2, fuge):
    """Glatter Stil: Spiegel zu dicht ODER ein Spiegel ragt ueber die Facette des Nachbarn hinaus."""
    i, j = np.meshgrid(np.arange(len(C1)), np.arange(len(C2)), indexing='ij'); i = i.ravel(); j = j.ravel()
    near = np.linalg.norm(C1[i]-C2[j], axis=1) < 3*A.fliese; i, j = i[near], j[near]
    if len(i) == 0: return False
    if sat_overlap(C1[i], A1[i], H_SLAB, C2[j], A2[j], H_SLAB, fuge).any(): return True
    h = A.fliese/2
    for X, Y in ((A1[i], A2[j]), (A2[j], A1[i])):
        for sa in (-1, 1):
            for sb in (-1, 1):
                p_ = FLOOR*X[:,2] + sa*h*X[:,0] + sb*h*X[:,1]
                if (np.einsum('ij,ij->i', p_, Y[:,2]) > FLOOR - FACET_M).any(): return True
    return False

def pairs_overlap(C1, A1, C2, A2, margin):
    if GLATT: return facet_bad(C1, A1, C2, A2, margin)
    i, j = np.meshgrid(np.arange(len(C1)), np.arange(len(C2)), indexing='ij'); i = i.ravel(); j = j.ravel()
    near = np.linalg.norm(C1[i]-C2[j], axis=1) < 3*PAD; i, j = i[near], j[near]
    if len(i) == 0: return False
    return bool(sat_overlap(C1[i], A1[i], H_SLAB, C2[j], A2[j], H_SLAB, margin).any())

def same_row_ok(lat, n, fuge):
    if n < 2: return True
    C, AX = row_boxes(lat, n)
    if GLATT: return not facet_bad(C[:1], AX[:1], C[1:2], AX[1:2], fuge)
    return not bool(sat_overlap(C[:1], AX[:1], H_SLAB, C[1:2], AX[1:2], H_SLAB, fuge).any())

def cut_ok(lat, n):
    u, e, nn = frame(lat, 0.5*2*np.pi/n)
    for c in (BASE, TOP):
        for sa in (-1, 1):
            for sb in (-1, 1):
                v = u*c + sa*PAD/2*e + sb*PAD/2*nn
                if v[1] < EPS or v[0] < EPS: return False
    return True

def n_for(lat, fuge):
    n = int(2*np.pi*R*np.cos(lat)//(A.fliese + 0.5*fuge))
    if QUANT > 1: n = n//QUANT*QUANT
    while n >= max(QUANT, 3):
        if same_row_ok(lat, n, fuge) and (QUANT == 1 or cut_ok(lat, n)): return n
        n -= QUANT
    return 0

def inner_edge(lat):
    if GLATT: return FLOOR*np.cos(lat) - (A.fliese/2 + 0.3)*np.sin(lat)
    return R*np.cos(lat) - (PAD/2)*np.sin(lat)

def layout(fuge):
    lat = np.radians(1.0)
    while (FLOOR*np.sin(lat) - A.fliese/2*np.cos(lat) < 0.5) if GLATT else (BASE*np.sin(lat) - PAD/2*np.cos(lat) < 0.4): lat += np.radians(0.02)
    rows = []
    while lat < np.radians(88):
        n = n_for(lat, fuge)
        if n == 0 or inner_edge(lat) < R_O + A.polabstand: break
        if rows:
            C1, A1 = row_boxes(*rows[-1]); C2, A2 = row_boxes(lat, n)
            if pairs_overlap(C1, A1, C2, A2, fuge): lat += np.radians(0.05); continue
        rows.append((lat, n)); lat += ((A.fliese if GLATT else PAD) + fuge)/R
    return rows

def best_layout():
    best = None
    for extra in np.arange(0, 2.01, 0.25):          # etwas groessere Fugen testen, falls dadurch mehr Fliesen passen
        rows = layout(A.fuge + extra); cnt = sum(n for _, n in rows)
        if best is None or cnt > best[0]: best = (cnt, rows, A.fuge + extra)
    return best[1], best[2]

ROWS, FUGE_USED = best_layout()

def tiles():
    out = []
    for lat, n in ROWS:
        for s in (1, -1):
            if GEO != 'komplett' and s < 0: continue
            for i in range(n):
                az = (i+0.5)*2*np.pi/n
                if GEO == 'teil' and az > np.pi/2: continue
                out.append((s*lat, az))
    return out

# ---------------------------------------------------------------- Netz-Erzeugung
def orient(tris, ref):
    nrm = np.cross(tris[:,1]-tris[:,0], tris[:,2]-tris[:,0])
    flip = np.einsum('ij,ij->i', nrm, ref) < 0
    tris = tris.copy(); tris[flip] = tris[flip][:, ::-1]
    return tris

def quad(p0, p1, p2, p3, ref):
    t = np.array([[p0,p1,p2],[p0,p2,p3]], float)
    return orient(t, np.tile(np.asarray(ref,float), (2,1)))

def pad_solid(lat, az):
    """Sockel: Quader mit ebener Klebeflaeche (Oberseite bei FLOOR), unten in der Wand verankert."""
    u, e, n = frame(lat, az)
    W = lambda a, b, c: a*e + b*n + c*u
    h = PAD/2
    sq = lambda c: [W(-h,-h,c), W(h,-h,c), W(h,h,c), W(-h,h,c)]
    ob, ot = sq(BASE), sq(FLOOR)
    refs_out = [-n, e, n, -e]
    T = [quad(*ob, -u), quad(*ot, u)]
    for k in range(4):
        k2 = (k+1) % 4
        T.append(quad(ob[k], ob[k2], ot[k2], ot[k], refs_out[k]))
    return np.concatenate(T)

# ---- Triangulierung ebener Flaechen mit Loechern (Ear-Clipping mit Bruecken) ----
def _area(P): return 0.5*np.sum(P[:,0]*np.roll(P[:,1],-1) - np.roll(P[:,0],-1)*P[:,1])

def _seg_cross(p, q, a, b, same):
    """Echte Kreuzung der Strecke pq mit Kanten a->b (Arrays); same: Kanten, die einen Endpunkt teilen, ignorieren."""
    def cr(o, x, y): return (x[...,0]-o[...,0])*(y[...,1]-o[...,1]) - (x[...,1]-o[...,1])*(y[...,0]-o[...,0])
    d1, d2 = cr(p, q, a), cr(p, q, b); d3, d4 = cr(a, b, p), cr(a, b, q)
    return (d1*d2 < -1e-12) & (d3*d4 < -1e-12) & ~same

def _inside(pt, poly):
    x, y = pt; xs, ys = poly[:,0], poly[:,1]; xs2, ys2 = np.roll(xs,-1), np.roll(ys,-1)
    c = ((ys > y) != (ys2 > y)) & (x < (xs2-xs)*(y-ys)/np.where(ys2==ys, 1e-30, ys2-ys) + xs)
    return bool(c.sum() % 2)

def triangulate(outer, holes):
    outer = np.asarray(outer, float)
    if _area(outer) < 0: outer = outer[::-1]
    holes = [np.asarray(h, float) for h in holes]
    holes = [h if _area(h) < 0 else h[::-1] for h in holes]
    P = np.concatenate([outer] + holes) if holes else outer
    offs = np.cumsum([0, len(outer)] + [len(h) for h in holes])
    poly = list(range(len(outer)))
    hidx = [list(range(offs[k+1], offs[k+2])) for k in range(len(holes))]
    for k in sorted(range(len(holes)), key=lambda k: -holes[k][:,0].max()):
        H = hidx[k]; others = [hidx[j] for j in range(len(holes)) if j != k and hidx[j] is not None]
        edges = []
        for ring in [poly, H] + others:
            r = np.array(ring); edges.append(np.stack([r, np.roll(r,-1)], 1))
        E = np.concatenate(edges); Ea, Eb = P[E[:,0]], P[E[:,1]]
        pairs = [(float(np.linalg.norm(P[h]-P[v])), h, v) for h in H for v in poly]; pairs.sort()
        polyxy, hxy = P[poly], P[H]
        for _, h, v in pairs:
            same = (E[:,0] == h) | (E[:,1] == h) | (E[:,0] == v) | (E[:,1] == v)
            if _seg_cross(P[h], P[v], Ea, Eb, same).any(): continue
            mid = (P[h]+P[v])/2
            if not _inside(mid, polyxy) or _inside(mid, hxy): continue
            i = poly.index(v); j = H.index(h)
            poly = poly[:i+1] + H[j:] + H[:j] + [h, v] + poly[i+1:]
            break
        else: raise RuntimeError('Keine Bruecke zum Loch gefunden')
        hidx[k] = None
    tris, idx, m, pos = [], list(poly), len(poly), 0
    while len(idx) > 3:
        m = len(idx); found = False
        for t in range(m):
            k = (pos + t) % m
            i0, i1, i2 = idx[k-1], idx[k], idx[(k+1) % m]
            a, b, c = P[i0], P[i1], P[i2]
            if (b[0]-a[0])*(c[1]-b[1]) - (b[1]-a[1])*(c[0]-b[0]) <= 1e-12: continue
            others = np.array([q for q in idx if q not in (i0, i1, i2)])
            ok = True
            if len(others):
                Q = P[others]
                same = (np.abs(Q-a).sum(1) < 1e-9) | (np.abs(Q-b).sum(1) < 1e-9) | (np.abs(Q-c).sum(1) < 1e-9)
                def cr(o, x, y): return (x[0]-o[0])*(y[1]-o[1]) - (x[1]-o[1])*(y[0]-o[0])
                s1 = (b[0]-a[0])*(Q[:,1]-a[1]) - (b[1]-a[1])*(Q[:,0]-a[0])
                s2 = (c[0]-b[0])*(Q[:,1]-b[1]) - (c[1]-b[1])*(Q[:,0]-b[0])
                s3 = (a[0]-c[0])*(Q[:,1]-c[1]) - (a[1]-c[1])*(Q[:,0]-c[0])
                ok = not bool(((s1 >= -1e-12) & (s2 >= -1e-12) & (s3 >= -1e-12) & ~same).any())
            if ok:
                tris.append((i0, i1, i2)); idx.pop(k); pos = k % max(len(idx),1); found = True; break
        if not found: raise RuntimeError('Ear-Clipping fehlgeschlagen')
    tris.append(tuple(idx))
    return P, np.array(tris)

def _simplify_ring(R, ang_tol=1e-6):
    """Positionen (Indizes) der Eckpunkte eines Rings ohne Zwischenpunkte auf geraden Strecken und ohne doppelte Punkte."""
    n = len(R)
    d = np.linalg.norm(R - np.roll(R, 1, axis=0), axis=1)
    dup = d < 1e-9
    idx = np.where(~dup)[0]
    if len(idx) < 3: return list(range(n))
    Q = R[idx]
    e1 = Q - np.roll(Q, 1, axis=0); e2 = np.roll(Q, -1, axis=0) - Q
    cr = e1[:,0]*e2[:,1] - e1[:,1]*e2[:,0]; l1 = np.linalg.norm(e1, axis=1); l2 = np.linalg.norm(e2, axis=1)
    col = (np.abs(cr) <= ang_tol*np.maximum(l1*l2, 1e-30)) & ((e1*e2).sum(1) > 0)
    keep = idx[~col]
    return [int(k) for k in keep] if len(keep) >= 3 else list(range(n))

def triangulate_clean(outer, holes):
    """Wie triangulate(), aber die Flaeche wird ohne die vielen Zwischenpunkte auf geraden Randstuecken in gut geformte Dreiecke zerlegt;
    die Zwischenpunkte werden danach als Faecher wieder eingesetzt (Netz bleibt dicht, keine flaechenlosen Splitter-Dreiecke)."""
    outer = np.asarray(outer, float)
    if _area(outer) < 0: outer = outer[::-1]
    holes = [np.asarray(h, float) for h in holes]
    holes = [h if _area(h) < 0 else h[::-1] for h in holes]
    rings = [outer] + holes
    offs = np.cumsum([0] + [len(r) for r in rings])
    keeps = [_simplify_ring(r) for r in rings]
    if all(len(k) == len(r) for k, r in zip(keeps, rings)):
        return triangulate(outer, holes)
    sp = []; s2o = []
    for r, k, o in zip(rings, keeps, offs[:-1]):
        sp.append(r[k]); s2o += [o + kk for kk in k]
    Ps, Ts = triangulate(sp[0], sp[1:])
    P = np.concatenate(rings)
    s2o = np.array(s2o)
    tris = [tuple(int(x) for x in s2o[t]) for t in Ts]
    alive = [True]*len(tris); de = {}
    for i, (a, b, c) in enumerate(tris):
        for e in ((a, b), (b, c), (c, a)): de.setdefault(e, []).append(i)
    for r, k, o in zip(rings, keeps, offs[:-1]):
        n = len(r)
        for m in range(len(k)):
            p0 = k[m]; p1 = k[(m+1) % len(k)]
            chain = []; q = (p0 + 1) % n
            while q != p1: chain.append(o + q); q = (q + 1) % n
            if not chain: continue
            u, v = o + p0, o + p1
            lst = [t for t in de.get((u, v), []) if alive[t]]
            if len(lst) != 1: continue
            t = lst[0]; w = [x for x in tris[t] if x != u and x != v]
            if len(w) != 1: continue
            w = w[0]; seq = [u] + chain + [v]
            alive[t] = False
            a_, b_, c_ = tris[t]
            for e in ((a_, b_), (b_, c_), (c_, a_)):
                if t in de.get(e, []): de[e].remove(t)
            for i in range(len(seq)-1):
                nt = (seq[i], seq[i+1], w); tris.append(nt); alive.append(True); j = len(tris)-1
                for e in ((nt[0], nt[1]), (nt[1], nt[2]), (nt[2], nt[0])): de.setdefault(e, []).append(j)
    T = np.array([t for t, al in zip(tris, alive) if al], dtype=np.int64)
    return P, T

def planar(outer, holes, z, nz):
    P, T = triangulate(outer, holes)
    P3 = np.concatenate([P, np.full((len(P),1), z)], 1)
    return orient(P3[T], np.tile([0,0,nz], (len(T),1)))

def poly_plane(pts_rz, az, ref):
    """Ebene Flaeche in der Halbebene az: pts_rz = [(r,z),...]."""
    P, T = triangulate(np.array(pts_rz), [])
    P3 = np.stack([P[:,0]*np.cos(az), P[:,0]*np.sin(az), P[:,1]], 1)
    return orient(P3[T], np.tile(ref, (len(T),1)))

def cylinder(cx, cy, r, z0, z1, ang, outward):
    x = cx + r*np.cos(ang); y = cy + r*np.sin(ang)
    a = np.stack([x[:-1], y[:-1], np.full(len(x)-1, z0)], 1); b = np.stack([x[1:], y[1:], np.full(len(x)-1, z0)], 1)
    c = np.stack([x[1:], y[1:], np.full(len(x)-1, z1)], 1); d = np.stack([x[:-1], y[:-1], np.full(len(x)-1, z1)], 1)
    t = np.concatenate([np.stack([a,b,c],1), np.stack([a,c,d],1)])
    ref = np.stack([t[:,:,0].mean(1)-cx, t[:,:,1].mean(1)-cy, np.zeros(len(t))], 1)*(1 if outward else -1)
    return orient(t, ref)

def ring_flat(cx, cy, r0, r1, z, ang, nz):
    x0, y0 = cx + r0*np.cos(ang), cy + r0*np.sin(ang); x1, y1 = cx + r1*np.cos(ang), cy + r1*np.sin(ang)
    P0 = np.stack([x0, y0, np.full(len(x0), z)], 1); P1 = np.stack([x1, y1, np.full(len(x0), z)], 1)
    a, b, c, d = P0[:-1], P0[1:], P1[1:], P1[:-1]
    t = np.concatenate([np.stack([a,b,c],1), np.stack([a,c,d],1)])
    return orient(t, np.tile([0,0,nz], (len(t),1)))

def sphere_patch(r, ang, lat, outward):
    AZ, LAT = np.meshgrid(ang, lat, indexing='ij')
    Pt = np.stack([r*np.cos(LAT)*np.cos(AZ), r*np.cos(LAT)*np.sin(AZ), r*np.sin(LAT)], -1)
    a, b, c, d = Pt[:-1,:-1], Pt[1:,:-1], Pt[1:,1:], Pt[:-1,1:]
    t = np.concatenate([np.stack([a,b,c],2).reshape(-1,3,3), np.stack([a,c,d],2).reshape(-1,3,3)])
    return orient(t, t.mean(1)*(1 if outward else -1))

def dish_radius(AZ, LAT):
    """Radius der Kugeloberflaeche: rund (SHELL), ausser in den flachen Mulden der Spiegel (Ebene bei FLOOR)."""
    W = np.stack([np.cos(LAT)*np.cos(AZ), np.cos(LAT)*np.sin(AZ), np.sin(LAT)], -1)
    r = np.full(AZ.shape, float(SHELL))
    if DISH <= 1e-9: return r
    cmin = np.cos(np.radians(14))
    for lat, n in ROWS:
        for i in range(n):
            u = frame(lat, (i+0.5)*2*np.pi/n)[0]
            dot = W @ u
            m = dot > cmin
            if m.any(): r[m] = np.minimum(r[m], FLOOR/dot[m])
    return r

def sphere_patch_dish(ang, lat):
    AZ, LAT = np.meshgrid(ang, lat, indexing='ij')
    r = dish_radius(AZ, LAT)
    Pt = r[...,None]*np.stack([np.cos(LAT)*np.cos(AZ), np.cos(LAT)*np.sin(AZ), np.sin(LAT)], -1)
    a, b, c, d = Pt[:-1,:-1], Pt[1:,:-1], Pt[1:,1:], Pt[:-1,1:]
    t = np.concatenate([np.stack([a,b,c],2).reshape(-1,3,3), np.stack([a,c,d],2).reshape(-1,3,3)])
    return orient(t, t.mean(1)), r

def body(a0, a1, hole2):
    """Hauptkoerper der oberen Haelfte (z >= 0): Schale/Pol/Rohre als EIN geschlossener Koerper."""
    full = abs((a1-a0) - 2*np.pi) < 1e-9
    step = A.winkel
    nb = max(int(np.ceil(np.degrees(a1-a0)/step)), 8)
    ns = 36 if full else 9
    ab = np.linspace(a0, a1, nb+1); asm = np.linspace(a0, a1, ns+1)
    ah = np.linspace(0, 2*np.pi, 37)
    c2 = (S*np.cos(HOLE2_AZ), S*np.sin(HOLE2_AZ))
    use2 = hole2 and S > 0
    lat_o = np.arccos(R_O/SHELL); lo = np.linspace(0, lat_o, max(int(np.ceil(np.degrees(lat_o)/step)), 4)+1)
    sp, rr = sphere_patch_dish(ab, lo)
    if abs(rr[:, -1] - SHELL).max() > 1e-6 or abs(rr[:, 0] - SHELL).max() > 1e-6: raise SystemExit('Die Mulden reichen bis an den Pol bzw. den Aequator - bitte --polabstand erhoehen oder --mulde kleiner waehlen.')
    T = [sp]
    arc = lambda r, ang: np.stack([r*np.cos(ang), r*np.sin(ang)], 1)
    def hole2_poly(r): return np.stack([c2[0]+r*np.cos(ah[:-1]), c2[1]+r*np.sin(ah[:-1])], 1)
    # --- Polflaeche oben (Normale +z)
    if full:
        outer = arc(R_O, ab[:-1]); holes = [arc(RHO, asm[:-1])]
    else:
        outer = np.concatenate([arc(R_O, ab), arc(RHO, asm[::-1])])
        holes = []
    if use2: holes.append(hole2_poly(RHO))
    T.append(planar(outer, holes, Z_FLAT, +1))
    # --- Bohrungen (Wand zeigt zur Bohrungsachse)
    T.append(cylinder(0, 0, RHO, 0, Z_FLAT, asm, False))
    if use2: T.append(cylinder(c2[0], c2[1], RHO, 0, Z_FLAT, ah, False))
    if HOLLOW:
        # Rohr um die Mittelbohrung und um Bohrung 2, Boden der Rohre in der Aequatorebene
        T.append(ring_flat(0, 0, RHO, RHOT, 0, asm, -1)); T.append(cylinder(0, 0, RHOT, 0, Z_CEIL, asm, True))
        if use2:
            T.append(ring_flat(c2[0], c2[1], RHO, RHOT, 0, ah, -1)); T.append(cylinder(c2[0], c2[1], RHOT, 0, Z_CEIL, ah, True))
        # Hohlraum-Decke (Normale -z) und Innenkugel
        if full:
            outer = arc(R_I, ab[:-1]); holes = [arc(RHOT, asm[:-1])]
        else:
            outer = np.concatenate([arc(R_I, ab), arc(RHOT, asm[::-1])]); holes = []
        if use2: holes.append(hole2_poly(RHOT))
        T.append(planar(outer, holes, Z_CEIL, -1))
        li = np.arccos(R_I/SHELLI); lin = np.linspace(0, li, max(int(np.ceil(np.degrees(li)/step)), 4)+1)
        T.append(sphere_patch(SHELLI, ab, lin, False))
        T.append(ring_flat(0, 0, SHELLI, SHELL, 0, ab, -1))
        # Schnittflaechen
        if not full:
            for az_, sg in ((a0, -1), (a1, 1)):
                prof = [(RHO,0), (RHOT,0), (RHOT,Z_CEIL), (R_I,Z_CEIL)]
                prof += [(SHELLI*np.cos(l), SHELLI*np.sin(l)) for l in lin[::-1]][:]
                prof += [(SHELL*np.cos(l), SHELL*np.sin(l)) for l in lo]
                prof += [(RHO, Z_FLAT)]
                prof = [prof[0]] + [q for k, q in enumerate(prof[1:], 1) if np.hypot(q[0]-prof[k-1][0], q[1]-prof[k-1][1]) > 1e-9]
                ref = sg*frame(0, az_)[1]
                T.append(poly_plane(prof, az_, ref))
    else:
        # massiv: Boden in der Aequatorebene mit den Bohrungen
        if full:
            outer = arc(SHELL, ab[:-1]); holes = [arc(RHO, asm[:-1])]
        else:
            outer = np.concatenate([arc(SHELL, ab), arc(RHO, asm[::-1])]); holes = []
        if use2: holes.append(hole2_poly(RHO))
        T.append(planar(outer, holes, 0.0, -1))
        if not full:
            for az_, sg in ((a0, -1), (a1, 1)):
                prof = [(RHO,0), (SHELL,0)] + [(SHELL*np.cos(l), SHELL*np.sin(l)) for l in lo[1:]] + [(RHO, Z_FLAT)]
                T.append(poly_plane(prof, az_, sg*frame(0, az_)[1]))
    return np.concatenate(T)

# ---------------------------------------------------------------- Glatter Stil: Kugel aus ebenen Facetten
def facet_polyhedron():
    """Konvexer Koerper = Schnitt aller Spiegel-Ebenen (Abstand FLOOR von der Mitte) + Polebene (+ Aequatorebene bei Halbkugel)."""
    from scipy.spatial import HalfspaceIntersection
    top_lat = ROWS[-1][0]
    ZP = FLOOR*np.sin(top_lat) + (A.fliese/2 + 0.3)*np.cos(top_lat)      # Polebene: knapp ueber der obersten Spiegelkante
    planes = [(frame(lat, az)[0], FLOOR, 'f') for lat, az in tiles() if lat > 0]     # obere Haelfte; bei 'komplett' wird gespiegelt
    planes.append((np.array([0,0,1.0]), ZP, 'top'))
    planes.append((np.array([0,0,-1.0]), 0.0, 'eq'))
    for k, d in enumerate((1,-1)):
        planes.append((np.array([d,0,0.0]), R+40, 'box')); planes.append((np.array([0,d,0.0]), R+40, 'box'))
    H = np.array([[*n_, -d] for n_, d, _ in planes])
    interior = np.array([0, 0, ZP/2])
    hs = HalfspaceIntersection(H, interior)
    V = hs.intersections
    Vr = np.round(V, 4); uniq, inv = np.unique(Vr, axis=0, return_inverse=True); inv = inv.ravel()
    Vu = np.array([V[inv == k].mean(0) for k in range(len(uniq))])
    faces = []
    for n_, d, kind in planes:
        if kind == 'box': continue
        idx = np.where(np.abs(Vu@n_ - d) < 2e-3)[0]
        if len(idx) < 3: continue
        pts = Vu[idx]; c = pts.mean(0)
        e1 = np.cross([0,0,1.0], n_) if abs(n_[2]) < 0.9 else np.array([1.0,0,0])
        e1 /= np.linalg.norm(e1); e2 = np.cross(n_, e1)
        ang = np.arctan2((pts-c)@e2, (pts-c)@e1)
        faces.append((kind, n_, pts[np.argsort(ang)]))
    return faces, ZP, Vu

def body_facets():
    step = A.winkel
    nb = max(int(np.ceil(360/step)), 8); ns = 36
    ab = np.linspace(0, 2*np.pi, nb+1); asm = np.linspace(0, 2*np.pi, ns+1); ah = np.linspace(0, 2*np.pi, 37)
    c2 = (S*np.cos(HOLE2_AZ), S*np.sin(HOLE2_AZ)); use2 = S > 0
    arc = lambda r, ang: np.stack([r*np.cos(ang), r*np.sin(ang)], 1)
    hole2_poly = lambda r: np.stack([c2[0]+r*np.cos(ah[:-1]), c2[1]+r*np.sin(ah[:-1])], 1)
    faces, ZP, Vu = facet_polyhedron()
    SHELLI_G = FLOOR - A.wand
    zc_lim = np.sqrt(SHELLI_G**2 - ((S if use2 else 0) + RHOT + 2.5)**2)
    Z_CEIL_G = min(ZP - A.platte, zc_lim); R_I_G = np.sqrt(SHELLI_G**2 - Z_CEIL_G**2)
    bores = [arc(RHO, asm[:-1])] + ([hole2_poly(RHO)] if use2 else [])
    T = []
    for kind, n_, pts in faces:
        if kind == 'f':
            fan = np.array([[pts[0], pts[k], pts[k+1]] for k in range(1, len(pts)-1)])
            T.append(orient(fan, np.tile(n_, (len(fan),1))))
        elif kind == 'top':
            T.append(planar(pts[:,:2], bores, ZP, +1))
        elif kind == 'eq':
            T.append(planar(pts[:,:2], [arc(SHELLI_G, ab[:-1])] if HOLLOW else bores, 0.0, -1))
    T.append(cylinder(0, 0, RHO, 0, ZP, asm, False))
    if use2: T.append(cylinder(c2[0], c2[1], RHO, 0, ZP, ah, False))
    if HOLLOW:
        T.append(ring_flat(0, 0, RHO, RHOT, 0, asm, -1)); T.append(cylinder(0, 0, RHOT, 0, Z_CEIL_G, asm, True))
        if use2:
            T.append(ring_flat(c2[0], c2[1], RHO, RHOT, 0, ah, -1)); T.append(cylinder(c2[0], c2[1], RHOT, 0, Z_CEIL_G, ah, True))
        holes = [arc(RHOT, asm[:-1])] + ([hole2_poly(RHOT)] if use2 else [])
        T.append(planar(arc(R_I_G, ab[:-1]), holes, Z_CEIL_G, -1))
        li = np.arccos(R_I_G/SHELLI_G); lin = np.linspace(0, li, max(int(np.ceil(np.degrees(li)/step)), 4)+1)
        T.append(sphere_patch(SHELLI_G, ab, lin, False))
    info = dict(ZP=ZP, rmax=np.linalg.norm(Vu, axis=1).max(), nfacets=sum(1 for f in faces if f[0] == 'f'),
                cap_apothem=min(np.linalg.norm(np.cross(f[1], [0,0,1.0])) * 0 + 0 for f in faces[:1]) if False else None,
                xy=(Vu[:,0].max()-Vu[:,0].min(), Vu[:,1].max()-Vu[:,1].min()))
    return np.concatenate(T), info

def mirror_z(t):
    t = t.copy(); t[:,:,2] *= -1
    return t[:, ::-1]

def build_pieces(variant='N'):
    """variant: 'N' = ohne 2. Bohrung im Teil, 'P' = Teil mit 2. Bohrung (nur modus teil)."""
    az0, az1 = (0, np.pi/2) if GEO == 'teil' else (0, 2*np.pi)
    hole2 = (GEO != 'teil') or variant == 'P'
    pieces = {}
    if GLATT:
        b, _ = body_facets(); pieces['korpus'] = b
        if GEO == 'komplett': pieces['korpus_sued'] = mirror_z(b)
        return pieces
    b = body(az0, az1, hole2)
    pieces['korpus'] = b
    if GEO == 'komplett': pieces['korpus_sued'] = mirror_z(b)
    for k, (lat, az) in enumerate(tiles()):
        pieces[f'kachel{k}'] = pad_solid(lat, az)
    return pieces

# ---------------------------------------------------------------- Netzbereinigung

def _faces_ok(F):
    e = np.sort(np.concatenate([F[:,[0,1]], F[:,[1,2]], F[:,[2,0]]]), axis=1)
    ue, cnt = np.unique(e, axis=0, return_counts=True)
    return int((cnt == 1).sum()), int((cnt > 2).sum())

def _drop_duplicates(F):
    """Doppelte Flaechen (gleiche Eckpunkte) entfernen; gegenlaeufige Paare heben sich auf."""
    if len(F) == 0: return F
    key = np.sort(F, axis=1)
    order = np.lexsort((key[:,2], key[:,1], key[:,0]))
    ks = key[order]
    same = np.all(ks[1:] == ks[:-1], axis=1)
    if not same.any(): return F
    # Gruppen mit mehr als einer Flaeche
    starts = np.where(np.concatenate([[True], ~same]))[0]; ends = np.concatenate([starts[1:], [len(ks)]])
    drop = np.zeros(len(F), bool)
    for s, e in zip(starts, ends):
        if e - s < 2: continue
        ids = order[s:e]
        par = []
        for i in ids:
            a, b, c = F[i]; srt = tuple(sorted((a, b, c)))
            cyc = [(a, b, c), (b, c, a), (c, a, b)]
            par.append(1 if srt in cyc else -1)
        pos = [i for i, p in zip(ids, par) if p > 0]; neg = [i for i, p in zip(ids, par) if p < 0]
        k = min(len(pos), len(neg))
        for i in pos[:k] + neg[:k]: drop[i] = True
        for i in pos[k+1:] + neg[k+1:]: drop[i] = True
    return F[~drop]

def _remove_slivers(P, F, hs, limit=40):
    def geom(f):
        a, b, c = P[f[0]], P[f[1]], P[f[2]]
        el = (np.linalg.norm(b-a), np.linalg.norm(c-b), np.linalg.norm(a-c))
        L = max(el); ar = np.linalg.norm(np.cross(b-a, c-a))/2
        return el, L, (2*ar/L if L > 0 else 0.0)
    A_ = P[F[:,0]]; B_ = P[F[:,1]]; C_ = P[F[:,2]]
    area = np.linalg.norm(np.cross(B_-A_, C_-A_), axis=1)/2
    L = np.maximum.reduce([np.linalg.norm(B_-A_,axis=1), np.linalg.norm(C_-B_,axis=1), np.linalg.norm(A_-C_,axis=1)])
    h = np.where(L > 0, 2*area/np.maximum(L, 1e-30), 0)
    bad = np.where((h < hs) & (L > 3*hs))[0]
    if len(bad) == 0: return F
    faces = [tuple(int(x) for x in f) for f in F]; alive = [True]*len(faces)
    de = {}
    for i, (a, b, c) in enumerate(faces):
        for e in ((a, b), (b, c), (c, a)): de.setdefault(e, []).append(i)
    work = list(bad); steps = 0; maxsteps = limit*len(bad) + 1000
    def kill(i):
        alive[i] = False; a, b, c = faces[i]
        for e in ((a, b), (b, c), (c, a)):
            lst = de.get(e)
            if lst and i in lst: lst.remove(i)
    def add(f):
        faces.append(f); alive.append(True); i = len(faces)-1; a, b, c = f
        for e in ((a, b), (b, c), (c, a)): de.setdefault(e, []).append(i)
        return i
    while work and steps < maxsteps:
        steps += 1; i = work.pop()
        if not alive[i]: continue
        f = faces[i]; el, Lm, hh = geom(f)
        if not (hh < hs and Lm > 3*hs): continue
        k = int(np.argmax(el)); a, b, c = f[k], f[(k+1) % 3], f[(k+2) % 3]
        nb = de.get((b, a), [])
        if len(nb) != 1: continue
        j = nb[0]; g = faces[j]
        d = [v for v in g if v != a and v != b]
        if len(d) != 1: continue
        d = d[0]
        kill(i); kill(j)
        if d == c: continue
        for nf in ((b, c, d), (c, a, d)):
            if nf[0] != nf[1] and nf[1] != nf[2] and nf[2] != nf[0]: work.append(add(nf))
    return np.array([f for f, al in zip(faces, alive) if al], dtype=np.int64).reshape(-1, 3)

def _remove_fins(P, F, hs, tol=3e-3):
    """Streifen aus aneinandergrenzenden Nadeldreiecken (alle auf einer Linie, Flaeche ~0) entfernen:
    die Nachbarflaechen beider Seiten werden an allen Linienpunkten geteilt und dann direkt verklebt."""
    A_ = P[F[:,0]]; B_ = P[F[:,1]]; C_ = P[F[:,2]]
    area = np.linalg.norm(np.cross(B_-A_, C_-A_), axis=1)/2
    L = np.maximum.reduce([np.linalg.norm(B_-A_,axis=1), np.linalg.norm(C_-B_,axis=1), np.linalg.norm(A_-C_,axis=1)])
    h = np.where(L > 0, 2*area/np.maximum(L, 1e-30), 0)
    bad = set(np.where((h < hs) & (L > 3*hs))[0].tolist())
    if not bad: return F
    faces = [tuple(int(x) for x in f) for f in F]
    de = {}
    for i, (a, b, c) in enumerate(faces):
        for e in ((a, b), (b, c), (c, a)): de[e] = i
    seen = set(); comps = []
    for s in bad:
        if s in seen: continue
        comp = [s]; seen.add(s); k = 0
        while k < len(comp):
            a, b, c = faces[comp[k]]; k += 1
            for e in ((b, a), (c, b), (a, c)):
                j = de.get(e)
                if j is not None and j in bad and j not in seen: seen.add(j); comp.append(j)
        comps.append(comp)
    dead = set(); add = []
    for comp in comps:
        cs = set(comp)
        V = sorted({v for i in comp for v in faces[i]})
        pts = P[V]; c0 = pts.mean(axis=0)
        u, s_, vt = np.linalg.svd(pts-c0, full_matrices=False)
        dirv = vt[0]
        perp = pts-c0 - np.outer((pts-c0)@dirv, dirv)
        if np.linalg.norm(perp, axis=1).max() > tol: continue
        tpar = {v: float((P[v]-c0)@dirv) for v in V}
        order = sorted(V, key=lambda v: tpar[v])
        bnd = []
        okc = True
        for i in comp:
            a, b, c = faces[i]
            for (x, y) in ((a, b), (b, c), (c, a)):
                j = de.get((y, x))
                if j is None: okc = False
                elif j not in cs: bnd.append((x, y, j))
        if not okc: continue
        outside = {}
        for (x, y, j) in bnd:
            if j in dead: okc = False; break
        if not okc: continue
        newf = []
        for (x, y, j) in bnd:
            f = faces[j]
            for r in range(3):
                if f[r] == y and f[(r+1) % 3] == x: z = f[(r+2) % 3]; break
            else: okc = False; break
            t0, t1 = tpar[y], tpar[x]
            lo, hi = min(t0, t1), max(t0, t1)
            mids = [v for v in order if lo < tpar[v] < hi and v not in (x, y, z)]
            mids.sort(key=lambda v: tpar[v], reverse=(t0 > t1))
            chain = [y] + mids + [x]
            for p, q in zip(chain[:-1], chain[1:]): newf.append((p, q, z))
            outside[j] = True
        if not okc: continue
        for i in comp: dead.add(i)
        for j in outside: dead.add(j)
        add.extend(newf)
    if not dead: return F
    out = [f for i, f in enumerate(faces) if i not in dead] + add
    return np.array(out, dtype=np.int64).reshape(-1, 3)

def _try(tris, g):
    q = np.round(tris.reshape(-1,3)/g).astype(np.int64)
    uq, inv = np.unique(q, axis=0, return_inverse=True)
    F = inv.ravel().reshape(-1,3); P = uq.astype(float)*g
    F = F[(F[:,0] != F[:,1]) & (F[:,1] != F[:,2]) & (F[:,2] != F[:,0])]
    F = _drop_duplicates(F)
    F = _remove_slivers(P, F, hs=1.5*g)
    F = _drop_duplicates(F)
    for _ in range(4):
        F2 = _remove_fins(P, F, hs=1.5*g)
        if len(F2) == len(F) and np.array_equal(F2, F): break
        if _faces_ok(F2) != (0, 0): break
        F = _drop_duplicates(F2)
        F = _remove_slivers(P, F, hs=1.5*g)
        F = _drop_duplicates(F)
    used = np.unique(F.ravel()); remap = -np.ones(len(P), np.int64); remap[used] = np.arange(len(used))
    P2 = P[used]; F2 = remap[F]
    o, m = _faces_ok(F2)
    return P2[F2], (o == 0 and m == 0), (o, m)

def clean_mesh(tris, g=1e-3):
    """Eckpunkte auf ein Raster legen, entartete/flaechenlose Dreiecke entfernen. Liefert (Dreiecke, ok, (offen, >2), verwendetes Raster)."""
    tris = np.asarray(tris, float)
    if len(tris) == 0: return tris, True, (0, 0), g
    best = None
    for gg in (g, 2*g, 5*g, 10*g):
        out, ok, st = _try(tris, gg)
        if ok: return out, True, st, gg
        if best is None or sum(st) < sum(best[2]): best = (out, False, st, gg)
    return best

def merged_clean(bodies):
    """Jeden Koerper einzeln bereinigen (Raster, entartete Dreiecke, Splitter) und zusammenfuegen. Liefert (Dreiecke, Anzahl nicht perfekt dichter Koerper)."""
    outs, bad = [], 0
    for t in bodies.values():
        c, ok, st, g = clean_mesh(t)
        if len(c): outs.append(c)
        if not ok: bad += 1
    return (np.concatenate(outs) if outs else np.zeros((0,3,3))), bad

def write_stl(path, tris):
    tris = tris.astype('<f4')
    nrm = np.cross(tris[:,1]-tris[:,0], tris[:,2]-tris[:,0]); nrm /= np.maximum(np.linalg.norm(nrm,axis=1,keepdims=True),1e-20)
    rec = np.zeros(len(tris), dtype=[('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]); rec['n']=nrm; rec['v']=tris
    with open(path,'wb') as f:
        f.write(b'Disco ball'.ljust(80,b' ')); f.write(struct.pack('<I',len(tris))); f.write(rec.tobytes())


# ---------------------------------------------------------------- Teilen in mehrere Stuecke
def clip_closed(tris, n, d, eps=1e-7):
    """Geschlossenen Koerper an der Ebene n.p = d beschneiden (behalten wird n.p <= d) und die Schnittflaeche verschliessen."""
    n = np.asarray(n, float); dist = tris @ n - d
    ins = dist <= eps
    cop = (np.abs(dist) <= eps).all(1)                      # Dreiecke, die in der Schnittebene liegen
    nrm = np.cross(tris[:,1]-tris[:,0], tris[:,2]-tris[:,0])
    face_out = (nrm @ n) > 0                                # zeigt die Flaeche nach aussen aus der behaltenen Seite?
    full = (ins.all(1) & ~cop) | (cop & face_out)
    out = (~ins.any(1)) | (cop & ~face_out)
    mixed = ~(full | out)
    parts = [tris[full]]
    for tri, dd in zip(tris[mixed], dist[mixed]):
        poly = []
        for i in range(3):
            a, b = tri[i], tri[(i+1) % 3]; da, db = dd[i], dd[(i+1) % 3]
            ia, ib = da <= eps, db <= eps
            if ia: poly.append(a)
            if ia != ib: poly.append(a + (da/(da-db))*(b-a))
        for k in range(1, len(poly)-1): parts.append(np.array([[poly[0], poly[k], poly[k+1]]]))
    body_ = np.concatenate(parts) if parts else np.zeros((0,3,3))
    if len(body_) == 0: return body_
    ar = np.linalg.norm(np.cross(body_[:,1]-body_[:,0], body_[:,2]-body_[:,0]), axis=1)
    body_ = body_[ar > 1e-12]
    if not mixed.any(): return body_
    # Schnittkante finden: Kanten ohne Gegenkante
    V = body_.reshape(-1,3); key = np.round(V*1e4).astype(np.int64)
    uniq, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
    pos = np.zeros((len(uniq),3)); cnt = np.zeros(len(uniq)); np.add.at(pos, inv, V); np.add.at(cnt, inv, 1); pos /= cnt[:,None]
    f = inv.reshape(-1,3); f = f[(f[:,0] != f[:,1]) & (f[:,1] != f[:,2]) & (f[:,2] != f[:,0])]
    E = np.concatenate([f[:,[0,1]], f[:,[1,2]], f[:,[2,0]]]); M = len(uniq)
    codes = set((E[:,0]*M + E[:,1]).tolist())
    bnd = [(a, b) for a, b in E.tolist() if (b*M + a) not in codes]
    if not bnd: return body_
    nxt = {}
    for a, b in bnd: nxt.setdefault(a, []).append(b)
    used, loops = set(), []
    for a, b in bnd:
        if (a, b) in used: continue
        used.add((a, b)); loop = [a]; cur = b; ok = True
        while cur != a:
            loop.append(cur)
            cand = [c for c in nxt.get(cur, []) if (cur, c) not in used]
            if not cand: ok = False; break
            used.add((cur, cand[0])); cur = cand[0]
        if not ok: raise RuntimeError('Schnittkante nicht geschlossen')
        loops.append(loop)
    e1 = np.cross(n, [0,0,1.0]) if abs(n[2]) < 0.9 else np.array([1.0,0,0]); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
    polys = [np.stack([pos[l] @ e1, pos[l] @ e2], 1) for l in loops]
    areas = [abs(_area(q)) for q in polys]
    depth, parent = [], []
    for i, q in enumerate(polys):
        cont = [j for j in range(len(polys)) if j != i and areas[j] > areas[i] and _inside(q[0], polys[j])]
        depth.append(len(cont)); parent.append(min(cont, key=lambda j: areas[j]) if cont else None)
    caps = []
    for i in range(len(polys)):
        if depth[i] % 2: continue
        holes = [polys[k] for k in range(len(polys)) if depth[k] % 2 and parent[k] == i]
        P, T = triangulate_clean(polys[i], holes)
        P3 = n*d + P[:,0:1]*e1 + P[:,1:2]*e2
        caps.append(orient(P3[T], np.tile(n, (len(T),1))))
    return np.concatenate([body_] + caps)

def clip_bodies(bodies, planes):
    out = {}
    for name, t in bodies.items():
        for n, d in planes:
            t = clip_closed(t, n, d)
            if len(t) == 0: break
        if len(t): out[name] = t
    return out

def parse_bett(sp):
    import re
    v = [float(x) for x in re.split(r'[x,;* ]+', sp.strip()) if x]
    if len(v) != 3: raise SystemExit('--bett bitte als BreiteXTiefeXHoehe angeben, z.B. 330x320x325')
    return v

def fits(dims, bett, margin=2.0):
    X, Y, Zb = bett; dx, dy, dz = dims
    return dz <= Zb - margin and ((dx <= X - margin and dy <= Y - margin) or (dx <= Y - margin and dy <= X - margin))

def nonempty_cells(xs, ys, zs, rout, rin):
    """Welche Rasterzellen enthalten Material? (Kugelschale zwischen rin und rout)"""
    lo = np.stack(np.meshgrid(xs[:-1], ys[:-1], zs[:-1], indexing='ij'), -1).reshape(-1,3)
    hi = np.stack(np.meshgrid(xs[1:], ys[1:], zs[1:], indexing='ij'), -1).reshape(-1,3)
    near = np.linalg.norm(np.clip(0, lo, hi), axis=1); far = np.linalg.norm(np.maximum(np.abs(lo), np.abs(hi)), axis=1)
    return (near <= rout) & (far >= rin), lo, hi

def choose_grid(ex, ey, ez, rout, rin, bett):
    best = None
    for nz in range(2, 15):
        for nx in range(1, 25):
            for ny in range(1, 25):
                cell = (2*ex/nx, 2*ey/ny, 2*ez/nz)
                if not fits(cell, bett): continue
                xs, ys, zs = (np.linspace(-e_, e_, n_+1) for e_, n_ in ((ex, nx), (ey, ny), (ez, nz)))
                cnt = int(nonempty_cells(xs, ys, zs, rout, rin)[0].sum())
                key = (cnt, nz, nx*ny)
                if best is None or key < best[0]: best = (key, nx, ny, nz)
    return best

def teilen_main():
    if not A.bett: raise SystemExit('Fuer --modus teilen bitte das Druckbett angeben, z.B. --bett 330x320x325')
    bett = parse_bett(A.bett)
    north = build_pieces('N')
    def ohne_aequator(t):
        nn_ = np.cross(t[:,1]-t[:,0], t[:,2]-t[:,0]); ln = np.linalg.norm(nn_, axis=1)
        return t[~((np.abs(t[:,:,2]) < 1e-6).all(1) & (ln > 1e-9) & (np.abs(nn_[:,2]) > 0.999*ln))]
    # Nord- und Suedhaelfte ohne die beiden Aequatorflaechen zu EINEM geschlossenen Hauptkoerper verbinden (kein Spalt, keine Innenflaeche)
    bodies = {'korpus': np.concatenate([ohne_aequator(north['korpus']), ohne_aequator(mirror_z(north['korpus']))])}
    for k, t in north.items():
        if k != 'korpus': bodies[k] = t; bodies[k+'_sued'] = mirror_z(t)
    V = np.concatenate([t.reshape(-1,3) for t in bodies.values()]); lo_, hi_ = V.min(0), V.max(0)
    ex, ey, ez = np.maximum(np.abs(lo_), np.abs(hi_))
    rout = np.linalg.norm(V, axis=1).max(); rin = SHELLI if HOLLOW else 0.0
    if A.schnitte == 'auto':
        best = choose_grid(ex, ey, ez, rout, rin, bett)
        if best is None: raise SystemExit(f'Die Kugel laesst sich mit diesem Raster nicht auf das Bett {bett} verteilen. Kleineren --durchmesser waehlen.')
        _, nx, ny, nz = best
    else:
        try: nx, ny, nz = (int(v) for v in A.schnitte.lower().split('x'))
        except Exception: raise SystemExit('--schnitte bitte als NXxNYxNZ angeben, z.B. 3x3x2')
        if nz < 2: raise SystemExit('--schnitte: NZ muss mindestens 2 sein (jedes Teil braucht eine ebene Standflaeche)')
    xs, ys, zs = (np.linspace(-e_, e_, n_+1) for e_, n_ in ((ex, nx), (ey, ny), (ez, nz)))
    ok, clo, chi = nonempty_cells(xs, ys, zs, rout, rin)
    cell = (2*ex/nx, 2*ey/ny, 2*ez/nz)
    print(f'Bett {bett[0]:g} x {bett[1]:g} x {bett[2]:g} mm -> Raster {nx} x {ny} x {nz} (Zellen {cell[0]:.0f} x {cell[1]:.0f} x {cell[2]:.0f} mm), {int(ok.sum())} Teile')
    if not fits(cell, bett): print('WARNUNG: Zellen passen evtl. nicht aufs Bett.')
    bbox = {k: (t.reshape(-1,3).min(0), t.reshape(-1,3).max(0)) for k, t in bodies.items()}
    base = A.out[:-4] if A.out and A.out.endswith('.stl') else (A.out or f'disco_teilen_{A.innen}_{A.durchmesser:g}mm')
    lines = []; idx = 0
    for c in np.where(ok)[0]:
        i, j, l = np.unravel_index(c, (nx, ny, nz))
        cl, ch = clo[c], chi[c]
        planes = []
        for ax_, (a_lo, a_hi, edge_lo, edge_hi) in enumerate(((cl[0], ch[0], -ex, ex), (cl[1], ch[1], -ey, ey), (cl[2], ch[2], -ez, ez))):
            e_ = np.zeros(3); e_[ax_] = 1.0
            if a_lo > edge_lo + 1e-6: planes.append((-e_, -a_lo))
            if a_hi < edge_hi - 1e-6: planes.append((e_, a_hi))
        sub = {k: t for k, t in bodies.items() if k.startswith('korpus') or ((bbox[k][1] >= cl - 1e-6).all() and (bbox[k][0] <= ch + 1e-6).all())}
        piece = clip_bodies(sub, planes)
        if not piece: continue
        tris, nbad = merged_clean(piece)
        if nbad: print(f'  HINWEIS: {nbad} Teilkoerper in diesem Teil nicht perfekt dicht - bitte im Slicer reparieren lassen')
        flipped = bool(l == 0)                      # unterste Schicht: umdrehen, damit die Schnittflaeche unten liegt
        if flipped: tris = tris * np.array([1.0, -1.0, -1.0])
        tris = tris - np.array([0, 0, tris[:,:,2].min()])
        idx += 1; v = tris.reshape(-1,3); dims = v.max(0) - v.min(0)
        out = f'{base}_teil{idx:02d}_x{i+1}y{j+1}z{l+1}.stl'; write_stl(out, tris)
        fit = 'ok' if fits(dims, bett) else 'PASST NICHT'
        print(f'  {out}: {dims.round(0)} mm [{fit}]' + ('  (umgedreht gedruckt)' if flipped else ''))
        lines.append(f'{out}\tx{i+1} y{j+1} z{l+1}\t{dims[0]:.0f} x {dims[1]:.0f} x {dims[2]:.0f} mm\t' + ('umgedreht (Schnittflaeche nach unten)' if flipped else 'wie gespeichert'))
    with open(f'{base}_uebersicht.txt', 'w', encoding='utf-8') as f:
        f.write(f'Disco-Kugel {A.durchmesser:g} mm, Spiegel {A.fliese:g} mm, Raster {nx} x {ny} x {nz}, {idx} Teile - jede Datei 1x drucken\n')
        f.write('Datei\tPosition (x: links-rechts, y: vorne-hinten, z: unten-oben)\tGroesse\tDruckage\n'); f.write('\n'.join(lines) + '\n')
    print(f'Fertig: {idx} Teile, jede Datei 1x drucken. Uebersicht: {base}_uebersicht.txt')
    print('Tipp: Die Position (x,y,z) sagt dir, wo das Teil in der Kugel sitzt. Teile der untersten Schicht (z1) werden umgedreht gedruckt (Schnittflaeche unten) und beim Zusammenbau wieder nach unten gesetzt.')

if __name__ == '__main__':
    if A.modus == 'teilen':
        teilen_main(); raise SystemExit(0)
    print(f'Kugel {A.durchmesser:g} mm ({A.innen}), Fliesen {A.fliese:g} mm: {len(ROWS)} Reihen je Halbkugel, Kacheln pro Reihe {[n for _,n in ROWS]}  (Fuge {FUGE_USED:.2f} mm)')
    print(f'Pol: flache Auflage Radius {R_O:.1f} mm, Bohrung {A.loch:g} mm' + (f', 2. Bohrung im Abstand {S:g} mm' if S > 0 else ''))
    if GLATT:
        _, inf = body_facets()
        print(f'Facetten-Stil: Kugel aus {inf["nfacets"]} ebenen Facetten je Halbkugel, Spiegel direkt aufkleben (keine Sockel). Pol-Ebene bei z={inf["ZP"]:.1f} mm, groesster Radius {inf["rmax"]:.1f} mm')
    if GLATT:
        faces_, ZP_, _ = facet_polyhedron()
        cap = [f for f in faces_ if f[0] == 'top'][0][2][:,:2]
        for nm, cxy in (('Mittelbohrung', (0.0, 0.0)), ('2. Bohrung', (S*np.cos(HOLE2_AZ), S*np.sin(HOLE2_AZ)))):
            if nm == '2. Bohrung' and S <= 0: continue
            q = np.roll(cap, -1, axis=0) - cap; w = np.array(cxy) - cap
            t = np.clip(np.einsum('ij,ij->i', w, q)/np.einsum('ij,ij->i', q, q), 0, 1)
            dist = np.linalg.norm(w - q*t[:,None], axis=1).min()
            if dist < SEAT - 0.01: print(f'HINWEIS: Scheibe/Mutter an der {nm} ragt {SEAT-dist:.1f} mm ueber die ebene Polflaeche hinaus (kleinere --scheibe oder anderen --loch-abstand waehlen).')
    if S > 0 and S < A.scheibe + 1: print(f'HINWEIS: Bohrungsabstand {S:g} mm ist kleiner als Scheibendurchmesser {A.scheibe:g} mm - die Scheiben ueberlappen sich (Mutter/Scheibe kleiner waehlen oder Abstand vergroessern).')
    corner = np.sqrt(FLOOR**2 + 2*(PAD/2)**2)
    if not GLATT and corner - SHELL > 1.5: print(f'WARNUNG: Spiegel sind im Verhaeltnis zur Kugel gross - die Ecken der Klebeflaechen stehen {corner-SHELL:.1f} mm vor (kleinere Spiegel oder groessere Kugel waehlen, Faustregel: Kugelradius mind. 2,5 x Spiegelkante).')
    variants = ['N', 'P'] if (A.modus == 'teil' and S > 0) else ['N']
    base = A.out[:-4] if A.out and A.out.endswith('.stl') else (A.out or f'disco_{A.modus}_{A.innen}_{A.durchmesser:g}mm_fliese{A.fliese:g}')
    for v in variants:
        pieces = build_pieces(v)
        tris, nbad = merged_clean(pieces)
        if nbad: print(f'HINWEIS: {nbad} Teilkoerper nicht perfekt dicht - bitte im Slicer reparieren lassen')
        out = base + (f'_{v}' if len(variants) > 1 else '') + '.stl'
        write_stl(out, tris); allv = tris.reshape(-1,3)
        print(out, '| Dreiecke:', len(tris), '| Groesse (x,y,z):', (allv.max(0)-allv.min(0)).round(1), 'mm')
    if A.modus == 'halb': print('Tipp: 2x drucken; zweite Haelfte umdrehen (um die waagerechte Achse durch die 2. Bohrung), dann passen Bohrungen und Fliesen.')
    if A.modus == 'teil' and S > 0: print('Tipp: _N 6x und _P 2x drucken (P = Teil mit der 2. Bohrung).')
