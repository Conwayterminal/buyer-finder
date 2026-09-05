import glob, pandas as pd
rows=[]
def sl(l,a,b): return l[a-1:b].strip()
for f in glob.glob("d_*/*.txt")+glob.glob("s2025/*.txt"):
    with open(f,"rb") as fh:
        for raw in fh:
            l=raw.decode("latin1")
            if len(l)<640: continue
            pc=sl(l,627,629)
            if pc not in ("4A","4B","4C","1","2","3A","15C"): continue
            try: price=int(sl(l,38,46) or 0); vprice=int(sl(l,47,55) or 0)
            except: continue
            price=max(price,vprice)
            if price<500000: continue
            rows.append(dict(cty=sl(l,1,2),dist=sl(l,3,4),nu=sl(l,35,37),price=price,addr=sl(l,298,322),deed=sl(l,339,344),rec=sl(l,345,350),block=sl(l,351,355),bsuf=sl(l,356,359),lot=sl(l,360,364),lsuf=sl(l,365,368),qual=sl(l,620,624),pc=pc,c4=sl(l,630,632),yb=sl(l,653,656),grantee=sl(l,204,238),gstreet=sl(l,239,263),gcity=sl(l,264,288),grantor=sl(l,110,144),assess=sl(l,74,82),etc=sl(l,369,369)))
d=pd.DataFrame(rows).drop_duplicates()
print(len(d)); print(d.pc.value_counts().to_dict()); print("grantee filled:",(d.grantee!="").sum()); print(d.head(3).to_dict("records"))
d.to_pickle("sr1a.pkl")
