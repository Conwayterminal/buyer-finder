#!/usr/bin/env python3
"""Actions job: DOB permit-filing owner contacts (name, business, mailing address, type) for every NYC commercial lot,
from the full BIS Job Applications and DOB NOW bulk files. Writes p['dobc'] on every property card."""
import os, json, glob, subprocess, collections, time
import pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
lots=set()
for f in glob.glob("site/props/NY_*.json"):
    for p in json.load(open(f)): lots.add(int(p["bbl"]))
def dl(vid,name):
    if os.path.exists(name) and os.path.getsize(name)>10**7: return
    subprocess.run(["curl","-sSL","-o",name,f"https://data.cityofnewyork.us/api/views/{vid}/rows.csv?accessType=DOWNLOAD"],check=True); print("downloaded",name,os.path.getsize(name)//10**6,"MB",flush=True)
F=collections.defaultdict(list)
def iso(s):
    s=str(s or "")
    if "/" in s:
        try: mm,dd,yy=s[:10].split("/"); return f"{yy}-{mm}-{dd}"
        except Exception: return ""
    return s[:10]
dl("ic3t-wcy2","/tmp/bis.csv")
cols=None
for ch in pd.read_csv("/tmp/bis.csv",dtype=str,chunksize=500_000,low_memory=False):
    if cols is None: cols={c.strip().upper():c for c in ch.columns}; print([c for c in ch.columns if "OWNER" in c.upper() or c.upper() in ("BBL","PRE- FILING DATE")],flush=True)
    g=lambda n: ch[cols[n]] if n in cols else pd.Series([""]*len(ch),index=ch.index)
    bbl=pd.to_numeric(g("BBL"),errors="coerce")
    ch=ch[bbl.isin(lots)]; bbl=bbl[bbl.isin(lots)]
    for b,typ,fn,ln,biz,hn,st,city,state,zp,dt in zip(bbl,g("OWNER TYPE")[ch.index],g("OWNER'S FIRST NAME")[ch.index],g("OWNER'S LAST NAME")[ch.index],g("OWNER'S BUSINESS NAME")[ch.index],g("OWNER'S HOUSE NUMBER")[ch.index],g("OWNER'SHOUSE STREET NAME")[ch.index],g("CITY ")[ch.index] if "CITY " in cols else g("CITY")[ch.index],g("STATE")[ch.index],g("ZIP")[ch.index],g("PRE- FILING DATE")[ch.index]):
        d=iso(dt)
        if d<"2015-01-01": continue
        nm=" ".join(v for v in [str(fn or "").strip(),str(ln or "").strip()] if v and v!="nan").title(); bz=str(biz or "").strip().title()
        if bz.upper() in ("N-A","NA","N/A","NONE","NAN"): bz=""
        if not (nm or bz): continue
        mail=", ".join(v for v in [(" ".join(x for x in [str(hn or ""),str(st or "")] if x and x!="nan")).strip().title(),str(city or "").strip().title(),str(state or "").strip(),str(zp or "").strip()] if v and v!="Nan" and v!="nan")
        F[int(b)].append([d,nm,bz,mail,str(typ or "").strip()])
    print("BIS lots with filings",len(F),flush=True)
dl("w9ak-ipjd","/tmp/dobnow.csv")
cols=None
for ch in pd.read_csv("/tmp/dobnow.csv",dtype=str,chunksize=500_000,low_memory=False):
    if cols is None: cols={c.strip().upper():c for c in ch.columns}; print([c for c in ch.columns if "OWNER" in c.upper() or c.upper() in ("BBL","FILING DATE")],flush=True)
    g=lambda n: ch[cols[n]] if n in cols else pd.Series([""]*len(ch),index=ch.index)
    bbl=pd.to_numeric(g("BBL"),errors="coerce"); m=bbl.isin(lots); ch=ch[m]; bbl=bbl[m]
    for b,typ,fn,ln,biz,dt in zip(bbl,g("OWNER TYPE")[ch.index],g("OWNER FIRST NAME")[ch.index],g("OWNER LAST NAME")[ch.index],g("OWNER'S BUSINESS NAME")[ch.index],g("FILING DATE")[ch.index]):
        d=iso(dt)
        if d<"2015-01-01": continue
        nm=" ".join(v for v in [str(fn or "").strip(),str(ln or "").strip()] if v and v!="nan").title(); bz=str(biz or "").strip().title()
        if not (nm or bz): continue
        F[int(b)].append([d,nm,bz,"",str(typ or "").strip()])
    print("BIS+NOW lots with filings",len(F),flush=True)
n=0
for f in glob.glob("site/props/NY_*.json"):
    L=json.load(open(f))
    for p in L:
        fs=F.get(int(p["bbl"]))
        if not fs: continue
        fs.sort(reverse=True); seen=set(); out=[]
        for x in fs:
            k=(x[1],x[2])
            if k in seen: continue
            seen.add(k); out.append(x)
            if len(out)>=4: break
        p["dobc"]=out; n+=1
    json.dump(L,open(f,"w"),separators=(",",":"),allow_nan=False)
print("props with DOB contacts",n,flush=True)
