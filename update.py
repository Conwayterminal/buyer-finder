#!/usr/bin/env python3
"""Conway Buyer Finder — daily updater.
Pulls new $1M+ commercial deeds from ACRIS (NYC Open Data), enriches with PLUTO, HPD and mortgage
filings, appends to data.json, rebuilds Conway_Buyer_Finder.html. Idempotent; safe to run daily.
Usage: python3 update.py [--days 10]
"""
import requests, pandas as pd, numpy as np, json, re, sys, time, math, os
from datetime import date, timedelta
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
DAYS=int(sys.argv[sys.argv.index("--days")+1]) if "--days" in sys.argv else 10
B="https://data.cityofnewyork.us/resource/"
def q(ds,params):
    for a in range(6):
        try:
            r=requests.get(B+ds+".json",params=params,timeout=150)
            if r.status_code==200: return r.json()
        except Exception: pass
        time.sleep(3)
    return []
def inlist(ds,ids,extra,sel,n=400):
    out=[]
    for i in range(0,len(ids),n):
        out+=q(ds,{"$where":"document_id in("+",".join("'%s'"%x for x in ids[i:i+n])+")"+extra,"$select":sel,"$limit":50000})
    return out
D=json.load(open("data.json")); cols=D["cols"]; C={k:i for i,k in enumerate(cols)}
have=set((r[C["doc"]]) for r in D["rows"] if r[C["doc"]])
have_addr=set((r[C["addr"]],r[C["date"]],r[C["price"]]) for r in D["rows"])
since=(date.today()-timedelta(days=DAYS)).isoformat()
print("since",since)
# 1) new deeds
m=q("bnx9-e6tj",{"$where":f"doc_type in('DEED','DEEDO') AND document_amt>=500000 AND recorded_datetime>='{since}' AND recorded_borough in('1','2','3','4')","$select":"document_id,recorded_borough,document_date,document_amt","$limit":50000})
m=pd.DataFrame(m); m=m[~m.document_id.isin(have)] if len(m) else m
print("new deed docs",len(m))
if len(m):
    ids=m.document_id.tolist()
    L=pd.DataFrame(inlist("8h5j-fqxa",ids,"","document_id,borough,block,lot,unit"))
    L=L[L.unit.isna()|(L.unit.astype(str).str.strip()=="")] if "unit" in L else L
    for c in ["borough","block","lot"]: L[c]=pd.to_numeric(L[c],errors="coerce")
    L["bbl"]=(L.borough*1e9+L.block*1e4+L.lot).round().astype("Int64")
    P=pd.DataFrame(inlist("636b-3b5g",ids,"","document_id,party_type,name,address_1,city"))
    G=P[P.party_type=="2"].groupby("document_id").agg(grantee=("name",lambda x:" | ".join(sorted(set(str(v).strip() for v in x)))),g_addr=("address_1",lambda x:" | ".join(sorted(set(str(v).strip() for v in x if pd.notna(v))))),g_city=("city",lambda x:"; ".join(sorted(set(str(v).strip() for v in x if pd.notna(v)))))).reset_index()
    R=P[P.party_type=="1"].groupby("document_id").agg(grantor=("name",lambda x:" | ".join(sorted(set(str(v).strip() for v in x))))).reset_index()
    nlots=L.groupby("document_id").size().rename("nlots").reset_index()
    X=L.merge(m,on="document_id").merge(G,on="document_id",how="left").merge(R,on="document_id",how="left").merge(nlots,on="document_id")
    # PLUTO
    bbls=sorted(set(int(b) for b in X.bbl.dropna()))
    pl=[]
    for i in range(0,len(bbls),400):
        pl+=q("64uk-42ks",{"$where":"bbl in("+",".join("'%d.00000000'"%x for x in bbls[i:i+400])+")","$select":"bbl,address,latitude,longitude,unitsres,bldgarea,lotarea,ownername,bldgclass,zonedist1,yearbuilt","$limit":50000})
    pl=pd.DataFrame(pl)
    if len(pl):
        pl["bbl"]=pd.to_numeric(pl.bbl,errors="coerce").round().astype("Int64"); pl=pl.drop_duplicates("bbl")
        for c in ["latitude","longitude","unitsres","bldgarea","lotarea","yearbuilt"]: pl[c]=pd.to_numeric(pl[c],errors="coerce")
        X=X.merge(pl,on="bbl",how="left")
        X["bc"]=X.bldgclass.astype(str).str.upper().str.strip()
        print("pluto matched",X.bldgclass.notna().sum(),"of",len(X)); print(X.bc.str[0].value_counts().head(8).to_dict())
        X=X[X.bc.str[0].isin(list("CDSKOEFGVHLMIWZ"))&~X.bc.isin(["C6","C8","D0","D4"])&X.latitude.notna()]
        # HPD
        rows=list(X[["borough","block","lot"]].drop_duplicates().itertuples(index=False))
        regs=[]
        for i in range(0,len(rows),60):
            w=" OR ".join("(boroid='%d' AND block='%d' AND lot='%d')"%(int(b),int(bl),int(l)) for b,bl,l in rows[i:i+60])
            regs+=q("tesw-yqqr",{"$where":w,"$select":"registrationid,boroid,block,lot","$limit":50000})
        hp={}
        if regs:
            RG=pd.DataFrame(regs)
            for c in ["boroid","block","lot"]: RG[c]=pd.to_numeric(RG[c],errors="coerce")
            RG["bbl"]=(RG.boroid*1e9+RG.block*1e4+RG.lot).round().astype("Int64")
            con=inlist("feu5-w2e2",sorted(set(RG.registrationid)),"","registrationid,type,corporationname,firstname,lastname,businesshousenumber,businessstreetname,businesscity,businesszip",500) if False else []
            ids2=sorted(set(RG.registrationid))
            for i in range(0,len(ids2),500):
                con+=q("feu5-w2e2",{"$where":"registrationid in("+",".join("'%s'"%x for x in ids2[i:i+500])+")","$select":"registrationid,type,corporationname,firstname,lastname,businesshousenumber,businessstreetname,businesscity,businesszip","$limit":50000})
            CN=pd.DataFrame(con).merge(RG[["registrationid","bbl"]],on="registrationid") if con else pd.DataFrame()
            cl=lambda v:"" if v is None or str(v).lower() in("nan","none") else str(v).strip()
            for bbl,grp in (CN.groupby("bbl") if len(CN) else []):
                pri=grp[grp.type.isin(["HeadOfficer","IndividualOwner","JointOwner","Officer"])]
                people=sorted(set((cl(r.get("firstname"))+" "+cl(r.get("lastname"))).strip().title() for _,r in pri.iterrows() if (cl(r.get("firstname"))+cl(r.get("lastname")))))
                corp=sorted(set(cl(r.get("corporationname")) for _,r in grp[grp.type.isin(["CorporateOwner","Agent"])].iterrows() if cl(r.get("corporationname"))))
                addr=(pri.iloc[0] if len(pri) else grp.iloc[0])
                hp[int(bbl)]=(", ".join(people)[:200],", ".join(corp)[:200],(cl(addr.get("businesshousenumber"))+" "+cl(addr.get("businessstreetname"))+", "+cl(addr.get("businesscity"))+" "+cl(addr.get("businesszip"))).strip(" ,").title())
        # mortgages (acq loans) on the new BBLs
        mt={}
        bb2=[(int(b),int(bl),int(l)) for b,bl,l in rows]
        lg=[]
        for i in range(0,len(bb2),60):
            w=" OR ".join("(borough='%d' AND block='%d' AND lot='%d')"%c for c in bb2[i:i+60])
            lg+=q("8h5j-fqxa",{"$where":w,"$select":"document_id,borough,block,lot","$limit":50000})
        if lg:
            LG=pd.DataFrame(lg).drop_duplicates()
            for c in ["borough","block","lot"]: LG[c]=pd.to_numeric(LG[c],errors="coerce")
            LG["bbl"]=(LG.borough*1e9+LG.block*1e4+LG.lot).round().astype("Int64")
            mm=pd.DataFrame(inlist("bnx9-e6tj",sorted(set(LG.document_id))," AND doc_type='MTGE' AND document_date>='2020-01-01'","document_id,document_date,document_amt"))
            if len(mm):
                mm["document_date"]=pd.to_datetime(mm.document_date); mm["document_amt"]=pd.to_numeric(mm.document_amt,errors="coerce")
                mp=pd.DataFrame(inlist("636b-3b5g",mm.document_id.tolist()," AND party_type='2'","document_id,name"))
                ln=mp.groupby("document_id").name.agg(lambda x:" | ".join(sorted(set(str(v).strip().title() for v in x)))) if len(mp) else pd.Series(dtype=str)
                mm=mm.merge(LG[["document_id","bbl"]].drop_duplicates(),on="document_id")
                mm["lender"]=mm.document_id.map(ln)
                for bbl,grp in mm.groupby("bbl"): mt[int(bbl)]=grp
        # neighborhood centroids from existing data
        nb={}
        for r in D["rows"]:
            k=(r[C["nbhd"]],r[C["boro"]]); nb.setdefault(k,[]).append((r[C["lat"]],r[C["lng"]]))
        nbc=[(k,float(np.median([p[0] for p in v])),float(np.median([p[1] for p in v]))) for k,v in nb.items()]
        def nearest(lat,lng,boro):
            best=None;bd=1e9
            for (n,b),la,ln in nbc:
                if b!=boro: continue
                d=(la-lat)**2+(ln-lng)**2
                if d<bd: bd=d;best=n
            return best or boro
        BN={1:"Manhattan",2:"Bronx",3:"Brooklyn",4:"Queens"}
        AC={"C":"Walkup multifamily","D":"Elevator multifamily","S":"Mixed-use","K":"Retail","O":"Office","E":"Warehouse","F":"Industrial","G":"Garage / parking","V":"Vacant land / development","H":"Hotel","L":"Loft","M":"Religious","I":"Health / institutional","W":"Education","Z":"Misc"}
        def co_of(t):
            mm_=re.search(r"C/O\s*([^|,;]+)",str(t or ""),re.I); return mm_.group(1).strip().title() if mm_ else ""
        def is_shell(n):
            n=str(n or "").upper(); return bool(re.search(r"\b(LLC|L\.L\.C|LP|CORP|INC|REALTY|ASSOCIATES|HOLDINGS|OWNER|PROPERTIES|PARTNERS|TRUST|EQUITIES|VENTURES|GROUP)\b",n))
        # mailing-address clusters from existing data
        lab={}
        for r in D["rows"]:
            if r[C["mail"]] and not r[C["conf"]].startswith("LLC"): lab.setdefault(r[C["mail"]].upper(),{}).setdefault(r[C["owner"]],0); lab[r[C["mail"]].upper()][r[C["owner"]]]+=1
        print("qualifying after class filter",len(X)); dup=sum(1 for r in X.itertuples() if (str(r.address or "").strip().title(),str(r.document_date)[:10],int(float(r.document_amt))) in have_addr); print("already in DOF data",dup)
        added=0
        for r in X.itertuples():
            boro=BN[int(r.borough)]; addr=str(r.address or "").strip().title(); dt=str(r.document_date)[:10]; price=int(float(r.document_amt))
            if (addr,dt,price) in have_addr or r.document_id in have: continue
            g=str(r.grantee or ""); mail=(str(r.g_addr or "")+", "+str(r.g_city or "")).strip(", ").title()
            people,corp,haddr=hp.get(int(r.bbl),("","",""))
            co=co_of(g) or co_of(r.g_addr)
            if people: owner,conf=people,"HPD registration (principal)"
            elif co: owner,conf=co,"Deed c/o"
            elif corp and corp.upper() not in g.upper(): owner,conf=corp,"HPD registration (corp/agent)"
            elif g and not is_shell(g): owner,conf=g.title(),"Deed grantee (named)"
            else:
                owner,conf=(g.title() or "Unknown"),"LLC only - research"
                if mail.upper() in lab: owner=max(lab[mail.upper()],key=lab[mail.upper()].get); conf="Same mailing address as "+owner
            acq=None
            if int(r.bbl) in mt:
                grp=mt[int(r.bbl)]; sd=pd.Timestamp(dt)
                a=grp[(grp.document_date>=sd-pd.Timedelta(days=45))&(grp.document_date<=sd+pd.Timedelta(days=120))&(grp.document_amt>0)]
                if len(a): a=a.sort_values("document_amt",ascending=False).iloc[0]; acq=[str(a.lender or ""),int(a.document_amt),round(a.document_amt/price,2) if r.nlots==1 else None]
            units=int(r.unitsres) if pd.notna(r.unitsres) and r.unitsres>0 else None
            sf=int(r.bldgarea) if pd.notna(r.bldgarea) and r.bldgarea>0 else None
            D["rows"].append([dt,boro,nearest(r.latitude,r.longitude,boro),addr,AC.get(r.bc[0],"Other"),r.bc,units,sf,price,int(r.nlots),round(r.latitude,5),round(r.longitude,5),g.title()[:150],owner[:150],conf,str(r.grantor or "").title()[:120],mail[:120],haddr[:120],str(r.ownername or "").title()[:80],int(r.yearbuilt) if pd.notna(r.yearbuilt) else None,str(r.zonedist1 or ""),int(r.lotarea) if pd.notna(r.lotarea) else None,r.document_id,acq,None,None,"NY",int(r.bbl)])
            have_addr.add((addr,dt,price)); added+=1
        print("added",added)
# 2) resale / refi refresh for existing rows: new MTGE & DEED docs in window on any tracked BBL
D["pulled"]=date.today().isoformat()
json.dump(D,open("data.json","w"),separators=(",",":"))
html=open("template.html").read().replace("__COLS__",json.dumps(D["cols"]))
os.makedirs("site",exist_ok=True); open("site/index.html","w").write(html); open("Conway_Buyer_Finder.html","w").write(html)
print("rows now",len(D["rows"]),"->","site/index.html")
# split per-market data files for the site
C2={k:i for i,k in enumerate(D["cols"])}
for st in sorted(set(r[C2["st"]] for r in D["rows"] if r[C2["st"]])):
    json.dump({"cols":D["cols"],"rows":[r for r in D["rows"] if r[C2["st"]]==st],"pulled":D["pulled"]},open(f"site/data/{st}.json","w"),separators=(",",":"))
