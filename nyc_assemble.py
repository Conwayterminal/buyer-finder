import pandas as pd, numpy as np, json, re
P=pd.read_pickle("pluto_all.pkl"); P["bbl"]=pd.to_numeric(P.bbl,errors="coerce").round().astype("Int64"); P=P.drop_duplicates("bbl")
for c in ["latitude","longitude","lotarea","bldgarea","comarea","resarea","officearea","retailarea","garagearea","strgearea","factryarea","numbldgs","numfloors","unitsres","unitstotal","lotfront","lotdepth","bldgfront","bldgdepth","assessland","assesstot","exempttot","yearbuilt","yearalter1","builtfar","residfar","commfar","facilfar"]: P[c]=pd.to_numeric(P[c],errors="coerce")
R=pd.read_pickle("dof_roll.pkl"); R["bbl"]=pd.to_numeric(R.parid,errors="coerce").round().astype("Int64")
for c in ["curmkttot","curmktland","curacttot","curactland","curtxbtot","curactextot","finmkttot","finacttot","fintxbtot","units","bld_story","lot_frt","lot_dep","bld_frt","bld_dep","gross_sqft","residential_area_gross","retail_area_gross","office_area_gross"]: R[c]=pd.to_numeric(R[c],errors="coerce")
R=R.drop_duplicates("bbl")
D=P.merge(R.drop(columns=["boro","block","lot"]),on="bbl",how="left")
# violations
H=pd.read_pickle("hpd_open.pkl"); H["bbl"]=pd.to_numeric(H.bbl,errors="coerce").round().astype("Int64"); H["n"]=pd.to_numeric(H.n,errors="coerce"); H=H.groupby("bbl",as_index=False).agg(n=("n","sum"),last=("last","max"))
BM={"MANHATTAN":1,"BRONX":2,"BROOKLYN":3,"QUEENS":4,"STATEN ISLAND":5,"1":1,"2":2,"3":3,"4":4,"5":5}
def mkbbl(df):
    b=df.boro.astype(str).str.upper().map(BM); return (b*1e9+pd.to_numeric(df.block,errors="coerce")*1e4+pd.to_numeric(df.lot,errors="coerce")).round().astype("Int64")
DB=pd.read_pickle("dob_active.pkl"); DB["bbl"]=mkbbl(DB); DB["n"]=pd.to_numeric(DB.n,errors="coerce"); DB=DB.groupby("bbl",as_index=False).n.sum()
EC=pd.read_pickle("ecb_active.pkl"); EC["bbl"]=mkbbl(EC); EC["n"]=pd.to_numeric(EC.n,errors="coerce"); EC["due"]=pd.to_numeric(EC.due,errors="coerce"); EC=EC.groupby("bbl",as_index=False).agg(n=("n","sum"),due=("due","sum"))
L=pd.read_pickle("liens.pkl"); L["bbl"]=(L.borough.astype(int)*1e9+pd.to_numeric(L.block)*1e4+pd.to_numeric(L.lot)).round().astype("Int64"); L=L.groupby("bbl").agg(lien_last=("month","max"),lien_n=("month","count")).reset_index()
D=D.merge(H[["bbl","n","last"]].rename(columns={"n":"hpd_open","last":"hpd_last"}),on="bbl",how="left").merge(DB[["bbl","n"]].rename(columns={"n":"dob_active"}),on="bbl",how="left").merge(EC[["bbl","n","due"]].rename(columns={"n":"ecb_active","due":"ecb_due"}),on="bbl",how="left").merge(L,on="bbl",how="left")
# attach deals from the live database
J=json.load(open("../repo/data.json")); C={k:i for i,k in enumerate(J["cols"])}
deals={}
def na(s): 
    s=re.sub(r"[^A-Z0-9 ]","",str(s or "").upper()); s=re.sub(r"\b(STREET)\b","ST",s); s=re.sub(r"\b(AVENUE)\b","AVE",s); s=re.sub(r"\b(PLACE)\b","PL",s); s=re.sub(r"\b(ROAD)\b","RD"," "+s).strip(); s=re.sub(r"\b(EAST)\b","E",s); s=re.sub(r"\b(WEST)\b","W",s); s=re.sub(r"(\d+)(ST|ND|RD|TH)\b",r"\1",s); return re.sub(r"\s+"," ",s).strip()
addr_ix={}
for r in D.itertuples():
    if pd.notna(r.bbl) and isinstance(r.address,str): addr_ix.setdefault((int(r.bbl)//10**9, na(r.address)),int(r.bbl))
BNI={"Manhattan":1,"Bronx":2,"Brooklyn":3,"Queens":4,"Staten Island":5}
unmatched=0
for r in J["rows"]:
    if r[C["st"]]!="NY": continue
    b=r[C["bbl"]]
    if not b:
        b=addr_ix.get((BNI.get(r[C["boro"]]),na(r[C["addr"]])))
        if not b: unmatched+=1; continue
    deals.setdefault(int(b),[]).append(r)
print("deals attached",sum(len(v) for v in deals.values()),"unmatched no-bbl deals",unmatched)
RATE={"1":0.20085,"2":0.12500,"2A":0.12500,"2B":0.12500,"2C":0.12500,"3":0.11181,"4":0.10762}
AC={"C":"Walkup multifamily","D":"Elevator multifamily","S":"Mixed-use","K":"Retail","O":"Office","E":"Warehouse","F":"Industrial","G":"Garage / parking","V":"Vacant land / development","H":"Hotel","L":"Loft","M":"Religious","I":"Health / institutional","W":"Education","Z":"Misc"}
BN={1:"Manhattan",2:"Bronx",3:"Brooklyn",4:"Queens",5:"Staten Island"}
out={b:[] for b in BN.values()}
def iv(x): return int(x) if pd.notna(x) else None
def sv(x): return "" if x is None or (isinstance(x,float) and pd.isna(x)) or str(x).lower()=="nan" else str(x)
def fv(x,d=2): return round(float(x),d) if pd.notna(x) else None
for r in D.itertuples():
    if pd.isna(r.latitude) or pd.isna(r.bbl): continue
    bbl=int(r.bbl); boro=BN.get(bbl//10**9); 
    if not boro: continue
    ds=sorted(deals.get(bbl,[]),key=lambda x:x[C["date"]],reverse=True); last=ds[0] if ds else None
    tc=str(r.curtaxclass) if isinstance(r.curtaxclass,str) else ""
    tax=iv(r.curtxbtot*RATE.get(tc,0.10762)) if pd.notna(r.curtxbtot) else None
    sf=r.bldgarea if pd.notna(r.bldgarea) and r.bldgarea>0 else r.gross_sqft
    rec={"bbl":bbl,"addr":str(r.address or "").title(),"zip":str(r.zipcode or "")[:5],"boro":boro,"cd":sv(r.cd),"lat":round(r.latitude,5),"lng":round(r.longitude,5),
         "bc":sv(r.bldgclass),"type":AC.get(str(r.bldgclass)[:1],"Other"),"tc":tc,"lu":sv(r.landuse),
         "owner":(sv(r.owner) or sv(r.ownername)).title()[:100],"units":iv(r.unitsres),"unitsT":iv(r.unitstotal),"sf":iv(sf),"stories":fv(r.numfloors,1),"lot":iv(r.lotarea),"lotF":fv(r.lotfront,1),"lotD":fv(r.lotdepth,1),"bF":fv(r.bldgfront,1),"bD":fv(r.bldgdepth,1),
         "yb":iv(r.yearbuilt),"alt":iv(r.yearalter1),"zone":sv(r.zonedist1),"far":fv(r.builtfar),"maxFar":fv(max(r.residfar or 0,r.commfar or 0)),"resA":iv(r.resarea),"comA":iv(r.comarea),"offA":iv(r.officearea),"retA":iv(r.retailarea),
         "mkt":iv(r.curmkttot),"av":iv(r.curacttot),"txb":iv(r.curtxbtot),"tax":tax,"hpd":iv(r.hpd_open),"dob":iv(r.dob_active),"ecb":iv(r.ecb_active),"ecbDue":iv(r.ecb_due),"lien":r.lien_last if isinstance(r.lien_last,str) else None,
         "sold":last[C["date"]] if last else None,"price":last[C["price"]] if last else None,"buyer":last[C["owner"]] if last else None,"conf":last[C["conf"]] if last else None,"acq":last[C["acq"]] if last else None,"refi":last[C["refi"]] if last else None,"nsales":len(ds),"pd":last[C["pd"]] if last else None,"dobc":last[C["dob"]] if last else None}
    out[boro].append(rec)
import os; os.makedirs("../repo/site/props",exist_ok=True)
for b,L2 in out.items():
    json.dump(L2,open(f"../repo/site/props/NY_{b.replace(' ','_')}.json","w"),separators=(",",":"),allow_nan=False); print(b,len(L2),os.path.getsize(f"../repo/site/props/NY_{b.replace(' ','_')}.json")//1024//1024,"MB")
tot=sum(len(v) for v in out.values()); print("total",tot,"with sale since 2020",sum(1 for v in out.values() for x in v if x["sold"]),"with open HPD",sum(1 for v in out.values() for x in v if x["hpd"]),"with lien",sum(1 for v in out.values() for x in v if x["lien"]))
