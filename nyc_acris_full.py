#!/usr/bin/env python3
"""GitHub Actions job: every ACRIS deed and mortgage (any price) since 2010 on every NYC commercial lot.
Downloads the three ACRIS bulk CSVs, filters to the 270k lots in props/, and writes per-lot histories
sharded by borough+block into site/props/hist/. Also refreshes debt fields on the property cards."""
import os, csv, json, sys, glob, subprocess, collections, time
import pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
csv.field_size_limit(10**9)
lots=set()
for f in glob.glob("site/props/NY_*.json"):
    for p in json.load(open(f)): lots.add(int(p["bbl"]))
print("lots",len(lots),flush=True)
def dl(vid,name):
    if os.path.exists(name) and os.path.getsize(name)>10**8: return
    url=f"https://data.cityofnewyork.us/api/views/{vid}/rows.csv?accessType=DOWNLOAD"
    print("downloading",name,flush=True); subprocess.run(["curl","-sSL","-o",name,url],check=True); print("done",os.path.getsize(name)//10**6,"MB",flush=True)
# 1) legals -> document ids on our lots
dl("8h5j-fqxa","/tmp/legals.csv")
docs={}  # document_id -> bbl
t0=time.time()
for ch in pd.read_csv("/tmp/legals.csv",usecols=["DOCUMENT ID","BOROUGH","BLOCK","LOT"],dtype=str,chunksize=2_000_000):
    b=pd.to_numeric(ch.BOROUGH,errors="coerce"); bl=pd.to_numeric(ch.BLOCK,errors="coerce"); lo=pd.to_numeric(ch.LOT,errors="coerce")
    bbl=(b*10**9+bl*10**4+lo)
    m=bbl.isin(lots)
    for d,x in zip(ch["DOCUMENT ID"][m],bbl[m]): docs.setdefault(d,int(x))
    print("legals scanned; docs on our lots:",len(docs),round(time.time()-t0),flush=True)
# 2) master -> keep deeds/mortgages/assignments/satisfactions since 2010
dl("bnx9-e6tj","/tmp/master.csv")
KEEP={"DEED","DEEDO","DEED, LE","DEED, TS","DEED, RC","MTGE","AGMT","ASST","SAT","AL&R","M&CON","ASPM","SPRD"}
M={}
for ch in pd.read_csv("/tmp/master.csv",usecols=["DOCUMENT ID","DOC. TYPE","DOC. DATE","DOC. AMOUNT","RECORDED / FILED"],dtype=str,chunksize=2_000_000):
    ch=ch[ch["DOCUMENT ID"].isin(docs.keys())&ch["DOC. TYPE"].isin(KEEP)]
    for r in ch.itertuples(index=False):
        d=str(r[2] or "")[:10]; rec=str(r[4] or "")[:10]
        # dates come as MM/DD/YYYY
        def iso(s):
            try: mm,dd,yy=s.split("/"); return f"{yy}-{mm}-{dd}"
            except Exception: return ""
        d=iso(d) or iso(rec)
        if d<"2010-01-01": continue
        try: amt=float(r[3])
        except Exception: amt=0
        M[r[0]]={"t":r[1],"d":d,"a":int(amt)}
    print("master kept",len(M),flush=True)
# 3) parties for those docs
dl("636b-3b5g","/tmp/parties.csv")
P=collections.defaultdict(lambda:{"1":[],"2":[]})
for ch in pd.read_csv("/tmp/parties.csv",usecols=["DOCUMENT ID","PARTY TYPE","NAME","ADDRESS 1","CITY","STATE"],dtype=str,chunksize=2_000_000):
    ch=ch[ch["DOCUMENT ID"].isin(M.keys())]
    for r in ch.itertuples(index=False):
        if r[1] in ("1","2") and isinstance(r[2],str): P[r[0]][r[1]].append([r[2].strip().title()[:80],", ".join(v for v in [str(r[3] or "").title(),str(r[4] or "").title(),str(r[5] or "")] if v and v!="Nan")[:100]])
    print("parties kept",len(P),flush=True)
# 4) per-lot history
hist=collections.defaultdict(list)
for doc,m in M.items():
    bbl=docs.get(doc)
    if bbl is None: continue
    p=P.get(doc,{"1":[],"2":[]})
    hist[bbl].append({"id":doc,"t":m["t"],"d":m["d"],"a":m["a"],"from":p["1"][:4],"to":p["2"][:4]})
for v in hist.values(): v.sort(key=lambda x:x["d"])
# open debt estimate: mortgages (MTGE/AGMT) not followed by a SAT of the same lender... approximate: sum of MTGE since last DEED, minus those with later SAT amount match
def debt(h):
    lastdeed=max([x["d"] for x in h if x["t"].startswith("DEED")],default="1900")
    mt=[x for x in h if x["t"] in ("MTGE","AGMT") and x["d"]>=lastdeed]
    sats=[x for x in h if x["t"]=="SAT" and x["d"]>=lastdeed]
    open_=[]
    for x in mt:
        if any(s["d"]>x["d"] and abs(s["a"]-x["a"])<=1 for s in sats): continue
        open_.append(x)
    return open_
shards=collections.defaultdict(dict)
for bbl,h in hist.items():
    shards[f"NY_{bbl//10**9}_{(bbl//10**4)%10**5//100}"][str(bbl)]=h
os.makedirs("site/props/hist",exist_ok=True)
for k,v in shards.items(): json.dump(v,open(f"site/props/hist/{k}.json","w"),separators=(",",":"))
print("shards",len(shards),"lots with history",len(hist),flush=True)
# 5) refresh card fields: last deed at any price, open debt, debt/sf
for f in glob.glob("site/props/NY_*.json"):
    L=json.load(open(f)); n=0
    for p in L:
        h=hist.get(int(p["bbl"]))
        if not h: continue
        deeds=[x for x in h if x["t"].startswith("DEED") and x["d"]>="2020-01-01"]
        if deeds and (not p.get("sold") or deeds[-1]["d"]>p["sold"]):
            ld=deeds[-1]; p["sold"]=ld["d"]; p["price"]=ld["a"] or None; p["nsales"]=len(deeds)
            if not p.get("buyer") and ld["to"]: p["buyer"]=", ".join(x[0] for x in ld["to"][:2]); p["conf"]="Deed grantee (ACRIS)"
        od=debt(h); p["debt"]=sum(x["a"] for x in od) if od else 0; p["debtN"]=len(od)
        p["lender"]=od[-1]["to"][0][0] if od and od[-1]["to"] else None; p["debtD"]=od[-1]["d"] if od else None
        p["hist"]=len(h); n+=1
    json.dump(L,open(f,"w"),separators=(",",":"),allow_nan=False); print(f,"updated",n,flush=True)
