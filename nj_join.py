import pandas as pd, requests, time, pickle, os
c=pd.read_pickle("comp.pkl"); s=pd.read_pickle("sr1a.pkl"); s=s[s.pc.isin(["4A","4B","4C","1","3A","15C"])].copy()
def pins(r):
    b=r.block.lstrip("0") or "0"; l=r.lot.lstrip("0") or "0"; out=[]
    for bs in ({r.bsuf,r.bsuf.lstrip("0")} if r.bsuf else {""}):
        for ls in ({r.lsuf,r.lsuf.lstrip("0")} if r.lsuf else {""}):
            p=r.cty+r.dist+"_"+b+("."+bs if bs else "")+"_"+l+("."+ls if ls else "")
            out.append(p+("_"+r.qual if r.qual else "")); 
            if r.qual: out.append(p)
    return list(dict.fromkeys(out))
s["pins"]=s.apply(pins,axis=1); s["pin"]=s.pins.str[0]
have=set(c.PAMS_PIN)
s["mpin"]=s.pins.map(lambda L: next((p for p in L if p in have),None))
print("matched",s.mpin.notna().mean(), len(s))
need=sorted(set(p for L in s[s.mpin.isna()].pins for p in L[:1]))
print("to fetch",len(need))
pickle.dump(need,open("need.pkl","wb")); s.to_pickle("sr1a2.pkl")
