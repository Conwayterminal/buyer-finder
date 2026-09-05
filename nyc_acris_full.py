#!/usr/bin/env python3
"""Resumable, runs in GitHub Actions with a persistent cache dir (./acris_cache).
Pulls EVERY ACRIS deed and mortgage since 2015 for all four boroughs (any price), the lots they attach to,
and lender names; then rolls sales/debt onto every NYC commercial lot in site/props and every deal in data.json.
Budget per run: ~5 hours. State: acris_cache/state.json + parquet parts."""
import requests, pandas as pd, json, os, sys, time
CACHE="acris_cache"; os.makedirs(CACHE,exist_ok=True)
BUDGET=int(sys.argv[1]) if len(sys.argv)>1 else 17000
t0=time.time(); left=lambda: BUDGET-(time.time()-t0)
B="https://data.cityofnewyork.us/resource/"
def q(ds,params,tries=6):
    for a in range(tries):
        try:
            r=requests.get(B+ds+".json",params=params,timeout=300)
            if r.status_code==200: return r.json()
            print(ds,r.status_code,r.text[:120],flush=True)
        except Exception as e: print("err",e,flush=True)
        time.sleep(5*(a+1))
    return None
sp=os.path.join(CACHE,"state.json"); st=json.load(open(sp)) if os.path.exists(sp) else {"phase":"master","m_off":0,"l_idx":0,"p_idx":0}
def save(): json.dump(st,open(sp,"w"))
def append(name,rows):
    if not rows: return
    p=os.path.join(CACHE,name); df=pd.DataFrame(rows)
    if os.path.exists(p): df=pd.concat([pd.read_parquet(p),df],ignore_index=True)
    df.to_parquet(p,index=False)
# ---- phase 1: master docs (deeds + mortgages since 2015), paged by 50k
if st["phase"]=="master":
    W="doc_type in('DEED','DEEDO','DEED, LE','DEED, TS','DEED, RC','MTGE','AGMT','ASST','SAT') AND document_date>='2015-01-01' AND recorded_borough in('1','2','3','4','5')"
    while left()>600:
        j=q("bnx9-e6tj",{"$where":W,"$select":"document_id,recorded_borough,doc_type,document_date,document_amt","$limit":50000,"$offset":st["m_off"],"$order":"document_id"})
        if j is None: break
        append("master.parquet",j); st["m_off"]+=len(j); save(); print("master",st["m_off"],flush=True)
        if len(j)<50000: st["phase"]="legals"; save(); break
# ---- phase 2: legals for all docs (BBL per doc)
if st["phase"]=="legals":
    ids=pd.read_parquet(os.path.join(CACHE,"master.parquet")).document_id.tolist(); n=len(ids)
    buf=[]
    while st["l_idx"]<n and left()>300:
        ch=ids[st["l_idx"]:st["l_idx"]+500]
        j=q("8h5j-fqxa",{"$where":"document_id in("+",".join("'%s'"%x for x in ch)+")","$select":"document_id,borough,block,lot,unit","$limit":50000})
        if j is None: break
        buf+=j; st["l_idx"]+=500
        if len(buf)>200000: append("legals.parquet",buf); buf=[]; save(); print("legals",st["l_idx"],"/",n,flush=True)
    append("legals.parquet",buf); save(); print("legals",st["l_idx"],"/",n,flush=True)
    if st["l_idx"]>=n: st["phase"]="parties"; save()
# ---- phase 3: parties (grantee for deeds, lender for mortgages)
if st["phase"]=="parties":
    m=pd.read_parquet(os.path.join(CACHE,"master.parquet")); ids=m.document_id.tolist(); n=len(ids)
    buf=[]
    while st["p_idx"]<n and left()>300:
        ch=ids[st["p_idx"]:st["p_idx"]+500]
        j=q("636b-3b5g",{"$where":"document_id in("+",".join("'%s'"%x for x in ch)+") AND party_type='2'","$select":"document_id,name,address_1,city","$limit":50000})
        if j is None: break
        buf+=j; st["p_idx"]+=500
        if len(buf)>200000: append("parties.parquet",buf); buf=[]; save(); print("parties",st["p_idx"],"/",n,flush=True)
    append("parties.parquet",buf); save(); print("parties",st["p_idx"],"/",n,flush=True)
    if st["p_idx"]>=n: st["phase"]="build"; save()
# ---- phase 4: build per-lot sales + debt and merge into props
if st["phase"]=="build":
    m=pd.read_parquet(os.path.join(CACHE,"master.parquet")); L=pd.read_parquet(os.path.join(CACHE,"legals.parquet")); P=pd.read_parquet(os.path.join(CACHE,"parties.parquet"))
    for c in ["borough","block","lot"]: L[c]=pd.to_numeric(L[c],errors="coerce")
    L=L[L.unit.isna()|(L.unit.astype(str).str.strip()=="")]; L["bbl"]=(L.borough*1e9+L.block*1e4+L.lot).round().astype("Int64")
    m["document_date"]=pd.to_datetime(m.document_date,errors="coerce"); m["document_amt"]=pd.to_numeric(m.document_amt,errors="coerce")
    G=P.groupby("document_id").name.agg(lambda x:" | ".join(sorted(set(str(v).strip().title() for v in x)))[:150]).rename("party2")
    D=L.merge(m,on="document_id").merge(G,on="document_id",how="left").sort_values("document_date")
    D.to_parquet(os.path.join(CACHE,"docs_by_lot.parquet"),index=False)
    deeds=D[D.doc_type.str.startswith("DEED")&(D.document_amt>0)]; mtg=D[(D.doc_type=="MTGE")&(D.document_amt>0)]
    lastdeed=deeds.groupby("bbl").tail(1).set_index("bbl"); ndeeds=deeds.groupby("bbl").size(); lastmtg=mtg.groupby("bbl").tail(1).set_index("bbl"); nmtg=mtg.groupby("bbl").size(); summtg=mtg[mtg.document_date>="2020-01-01"].groupby("bbl").document_amt.sum()
    import glob
    for f in glob.glob("site/props/NY_*.json"):
        props=json.load(open(f)); hit=0
        for p in props:
            b=p["bbl"]
            if b in lastdeed.index:
                d=lastdeed.loc[b]; p["lastDeed"]=[d.document_date.strftime("%Y-%m-%d"),int(d.document_amt),d.party2 or ""]; p["nDeeds"]=int(ndeeds.get(b,0))
                if not p.get("sold") and d.document_date>=pd.Timestamp("2020-09-01"): p["sold"]=p["lastDeed"][0]; p["price"]=p["lastDeed"][1]; p["buyer"]=p["buyer"] or (d.party2 or ""); p["conf"]=p["conf"] or "ACRIS deed grantee"
                hit+=1
            if b in lastmtg.index:
                d=lastmtg.loc[b]; p["lastMtg"]=[d.document_date.strftime("%Y-%m-%d"),int(d.document_amt),d.party2 or ""]; p["nMtg"]=int(nmtg.get(b,0)); p["mtgSince2020"]=int(summtg.get(b,0))
        json.dump(props,open(f,"w"),separators=(",",":"),allow_nan=False); print(f,"lots with deed",hit,flush=True)
    st["phase"]="done"; save()
print("phase",st["phase"],json.dumps({k:v for k,v in st.items()}))
