import sys, time, numpy as np
cells=[tuple(int(c) for c in a.split(',')) for a in sys.argv[1:]] or [(1,1,1),(0,1,0)]
sys.argv=['x','--modus','teilen','--bett','330x320x325','--innen','voll','--durchmesser','900','--fliese','50','--loch','6.8','--loch-abstand','15','--scheibe','14']
import discoball as D
north=D.build_pieces('N')
def oa(t):
    nn_=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); ln=np.linalg.norm(nn_,axis=1)
    return t[~((np.abs(t[:,:,2])<1e-6).all(1)&(ln>1e-9)&(np.abs(nn_[:,2])>0.999*ln))]
bodies={'korpus':np.concatenate([oa(north['korpus']),oa(D.mirror_z(north['korpus']))])}
for k,t in north.items():
    if k!='korpus': bodies[k]=t; bodies[k+'_sued']=D.mirror_z(t)
V=np.concatenate([t.reshape(-1,3) for t in bodies.values()]); lo,hi=V.min(0),V.max(0)
ex,ey,ez=np.maximum(np.abs(lo),np.abs(hi))
xs,ys,zs=(np.linspace(-e,e,4) for e in (ex,ey,ez))
bb={k:(t.reshape(-1,3).min(0),t.reshape(-1,3).max(0)) for k,t in bodies.items()}
def metrics(c):
    v=c.astype(np.float32).reshape(-1,3); key=v.view(np.uint32).reshape(-1,3)
    u,inv=np.unique(key,axis=0,return_inverse=True); fc=inv.ravel().reshape(-1,3)
    deg=((fc[:,0]==fc[:,1])|(fc[:,1]==fc[:,2])|(fc[:,2]==fc[:,0])).sum()
    e=np.sort(np.concatenate([fc[:,[0,1]],fc[:,[1,2]],fc[:,[2,0]]]),axis=1); _,cnt=np.unique(e,axis=0,return_counts=True)
    nr=np.cross(c[:,1]-c[:,0],c[:,2]-c[:,0]); A=np.linalg.norm(nr,axis=1)/2
    L=np.maximum.reduce([np.linalg.norm(c[:,1]-c[:,0],axis=1),np.linalg.norm(c[:,2]-c[:,1],axis=1),np.linalg.norm(c[:,0]-c[:,2],axis=1)]); h=2*A/np.maximum(L,1e-30)
    vol=np.einsum('ij,ij->i',c[:,0],np.cross(c[:,1],c[:,2])).sum()/6/1e6
    return f'Dreiecke {len(c):6d} | offen {int((cnt==1).sum()):5d} >2 {int((cnt>2).sum()):3d} entartet {int(deg):4d} | Splitter(h<1e-3,L>5e-3) {int(((h<1e-3)&(L>5e-3)).sum()):5d} | Vol {vol:.4f} l'
for (i,j,l) in cells:
    cl=np.array([xs[i],ys[j],zs[l]]); ch=np.array([xs[i+1],ys[j+1],zs[l+1]]); planes=[]
    for ax,(a,b,el,eh) in enumerate(((cl[0],ch[0],-ex,ex),(cl[1],ch[1],-ey,ey),(cl[2],ch[2],-ez,ez))):
        e_=np.zeros(3); e_[ax]=1
        if a>el+1e-6: planes.append((-e_,-a))
        if b<eh-1e-6: planes.append((e_,b))
    sub={k:t for k,t in bodies.items() if k.startswith('korpus') or ((bb[k][1]>=cl-1e-6).all() and (bb[k][0]<=ch+1e-6).all())}
    t0=time.time(); piece=D.clip_bodies(sub,planes); tris=np.concatenate(list(piece.values())); t1=time.time()
    print(f'Zelle x{i+1}y{j+1}z{l+1}: Schneiden {t1-t0:.1f} s'); print('  roh      :',metrics(tris))
    cs=[D.clean_mesh(t)[0] for t in piece.values()]; c=np.concatenate(cs); print('  bereinigt:',metrics(c),'| %.1f s'%(time.time()-t1))
