import sys, glob, struct, numpy as np
def load(p):
    d=open(p,'rb').read(); n=struct.unpack('<I',d[80:84])[0]
    return np.frombuffer(d[84:],dtype=[('n','<f4',3),('v','<f4',(3,3)),('a','<u2')],count=n)['v'].astype(float)
tot=0; bad=0; files=sorted(glob.glob(sys.argv[1]+'_teil*.stl'))
for f in files:
    t=load(f); v=t.reshape(-1,3); q=np.round(v*1e4).astype(np.int64)
    _,inv=np.unique(q,axis=0,return_inverse=True); fc=inv.reshape(-1,3)
    fc=fc[(fc[:,0]!=fc[:,1])&(fc[:,1]!=fc[:,2])&(fc[:,2]!=fc[:,0])]
    e=np.sort(np.concatenate([fc[:,[0,1]],fc[:,[1,2]],fc[:,[2,0]]]),axis=1)
    _,cnt=np.unique(e,axis=0,return_counts=True)
    vol=np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6/1e6
    tot+=vol
    if (cnt==1).any() or vol<=0:
        bad+=1; print('PROBLEM',f,'offen',(cnt==1).sum(),'>2',(cnt>2).sum(),'Vol %.2f l'%vol)
print(len(files),'Dateien, fehlerhaft:',bad,'| Gesamtvolumen (Summe der Teile) %.1f l'%tot)
