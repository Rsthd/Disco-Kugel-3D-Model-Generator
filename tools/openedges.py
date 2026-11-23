import sys, struct, numpy as np
f=sys.argv[1]
d=open(f,'rb').read(); n=struct.unpack('<I',d[80:84])[0]
t=np.frombuffer(d[84:],dtype=[('n','<f4',3),('v','<f4',(3,3)),('a','<u2')],count=n)['v']
v=t.reshape(-1,3)
for name,tol in (('exakt float32',None),('1e-3 Raster',1e-3),('1e-4 Raster',1e-4)):
    key=v.view(np.uint32).reshape(-1,3) if tol is None else np.round(v/tol).astype(np.int64)
    u,inv=np.unique(key,axis=0,return_inverse=True); fc=inv.reshape(-1,3)
    deg=(fc[:,0]==fc[:,1])|(fc[:,1]==fc[:,2])|(fc[:,2]==fc[:,0])
    fc2=fc[~deg]
    e=np.sort(np.concatenate([fc2[:,[0,1]],fc2[:,[1,2]],fc2[:,[2,0]]]),axis=1)
    ue,cnt=np.unique(e,axis=0,return_counts=True)
    print(f'{name:14s}: Dreiecke {n}, entartet {int(deg.sum())}, offene Kanten {int((cnt==1).sum())}, >2: {int((cnt>2).sum())}')
# Lage der offenen Kanten (exakt)
key=v.view(np.uint32).reshape(-1,3); u,inv=np.unique(key,axis=0,return_inverse=True); fc=inv.reshape(-1,3)
e=np.sort(np.concatenate([fc[:,[0,1]],fc[:,[1,2]],fc[:,[2,0]]]),axis=1); ue,cnt=np.unique(e,axis=0,return_counts=True)
P=v[np.unique(fc.ravel(),return_index=True)[1]]  # nicht benoetigt
vv=np.zeros((len(u),3)); vv[inv]=v
op=ue[cnt==1]
if len(op):
    m=(vv[op[:,0]]+vv[op[:,1]])/2
    L=np.linalg.norm(vv[op[:,0]]-vv[op[:,1]],axis=1)
    print('Laenge offener Kanten: min %.5f median %.5f max %.3f mm'%(L.min(),np.median(L),L.max()))
    print('Lage: x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f'%(m[:,0].min(),m[:,0].max(),m[:,1].min(),m[:,1].max(),m[:,2].min(),m[:,2].max()))
    r=np.linalg.norm(m[:,:2],axis=1); print('Abstand zur z-Achse der Kante: %.1f..%.1f mm'%(r.min(),r.max()))
