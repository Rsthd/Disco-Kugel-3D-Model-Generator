import numpy as np

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

def _try(tris, g):
    q = np.round(tris.reshape(-1,3)/g).astype(np.int64)
    uq, inv = np.unique(q, axis=0, return_inverse=True)
    F = inv.ravel().reshape(-1,3); P = uq.astype(float)*g
    F = F[(F[:,0] != F[:,1]) & (F[:,1] != F[:,2]) & (F[:,2] != F[:,0])]
    F = _drop_duplicates(F)
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
