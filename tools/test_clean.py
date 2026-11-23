import sys, struct, time, numpy as np
sys.path.insert(0,'.')
from cleanmesh import clean_mesh
def load(p):
    d=open(p,'rb').read(); n=struct.unpack('<I',d[80:84])[0]
    return np.frombuffer(d[84:],dtype=[('n','<f4',3),('v','<f4',(3,3)),('a','<u2')],count=n)['v'].astype(float)
def vol(t): return np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6/1e6
def slices_area(t, zs):
    out=[]
    for z in zs:
        d=t[:,:,2]-z; seg=[]
        for tri,dd in zip(t,d):
            if dd.min()>=0 or dd.max()<=0: continue
            pts=[]
            for i in range(3):
                a,b=dd[i],dd[(i+1)%3]
                if a*b<0: k=a/(a-b); pts.append(tri[i]+k*(tri[(i+1)%3]-tri[i]))
            if len(pts)==2: seg.append((pts[0][:2],pts[1][:2]))
        # Flaeche ueber Randintegral
        out.append(sum((p[0]*q[1]-q[0]*p[1]) for p,q in seg)/2)
    return out
for f in sys.argv[1:]:
    t=load(f); t0=time.time()
    c,ok,st,g=clean_mesh(t)
    print(f, '| vorher',len(t),'Dreiecke -> nachher',len(c),'| ok',ok,'offen/>2',st,'Raster',g,'| %.1f s'%(time.time()-t0))
    print('   Volumen vorher %.4f l nachher %.4f l'%(vol(t),vol(c)))
    # exakte float32-Pruefung
    v=c.astype(np.float32).reshape(-1,3); key=v.view(np.uint32).reshape(-1,3)
    u,inv=np.unique(key,axis=0,return_inverse=True); fc=inv.ravel().reshape(-1,3)
    e=np.sort(np.concatenate([fc[:,[0,1]],fc[:,[1,2]],fc[:,[2,0]]]),axis=1); _,cnt=np.unique(e,axis=0,return_counts=True)
    deg=((fc[:,0]==fc[:,1])|(fc[:,1]==fc[:,2])|(fc[:,2]==fc[:,0])).sum()
    nr=np.cross(c[:,1]-c[:,0],c[:,2]-c[:,0]); A=np.linalg.norm(nr,axis=1)/2; L=np.maximum.reduce([np.linalg.norm(c[:,1]-c[:,0],axis=1),np.linalg.norm(c[:,2]-c[:,1],axis=1),np.linalg.norm(c[:,0]-c[:,2],axis=1)]); h=2*A/np.maximum(L,1e-30)
    print('   float32 exakt: offen',int((cnt==1).sum()),'>2',int((cnt>2).sum()),'entartet',int(deg),'| Splitter h<1e-3 mit L>5e-3:',int(((h<1e-3)&(L>5e-3)).sum()))
    zs=np.linspace(t[:,:,2].min()+3,t[:,:,2].max()-3,5)
    a0=slices_area(t,zs); a1=slices_area(c,zs)
    print('   Schnittflaechen (mm2) vorher/nachher:',[ '%.1f/%.1f'%(x,y) for x,y in zip(a0,a1)])
