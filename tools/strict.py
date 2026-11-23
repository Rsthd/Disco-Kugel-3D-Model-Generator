import sys, glob, struct, numpy as np
pre=sys.argv[1]; files=sorted(glob.glob(pre+'_teil*.stl')); tot=0; bad=0; sl=0; slmax=0
for f in files:
    d=open(f,'rb').read(); n=struct.unpack('<I',d[80:84])[0]
    t=np.frombuffer(d[84:],dtype=[('n','<f4',3),('v','<f4',(3,3)),('a','<u2')],count=n)['v']
    v=t.reshape(-1,3); key=v.view(np.uint32).reshape(-1,3)
    u,inv=np.unique(key,axis=0,return_inverse=True); fc=inv.ravel().reshape(-1,3)
    deg=int(((fc[:,0]==fc[:,1])|(fc[:,1]==fc[:,2])|(fc[:,2]==fc[:,0])).sum())
    e=np.sort(np.concatenate([fc[:,[0,1]],fc[:,[1,2]],fc[:,[2,0]]]),axis=1); _,cnt=np.unique(e,axis=0,return_counts=True)
    c=t.astype(float); nr=np.cross(c[:,1]-c[:,0],c[:,2]-c[:,0]); A=np.linalg.norm(nr,axis=1)/2
    L=np.maximum.reduce([np.linalg.norm(c[:,1]-c[:,0],axis=1),np.linalg.norm(c[:,2]-c[:,1],axis=1),np.linalg.norm(c[:,0]-c[:,2],axis=1)]); h=2*A/np.maximum(L,1e-30)
    s5=int((h<5e-5).sum()); vol=np.einsum('ij,ij->i',c[:,0],np.cross(c[:,1],c[:,2])).sum()/6/1e6
    ok=(cnt==1).sum()==0 and (cnt>2).sum()==0 and deg==0 and vol>0
    tot+=vol; sl+=s5; slmax=max(slmax,s5)
    if not ok or s5>0:
        bad+= (not ok); print('  ',f.split('/')[-1],'offen',int((cnt==1).sum()),'>2',int((cnt>2).sum()),'entartet',deg,'Splitter<0.05um',s5,'Vol %.2f l'%vol)
print(len(files),'Dateien | nicht dicht:',bad,'| Splitter (h<0.05 um) gesamt',sl,'| Volumen-Summe %.1f l'%tot)
