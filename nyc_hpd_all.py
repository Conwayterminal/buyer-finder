import pandas as pd, json, glob, collections, sys
R=pd.read_csv("hpd_reg_all.csv",dtype=str,usecols=["RegistrationID","BoroID","Block","Lot","LastRegistrationDate"])
R["bbl"]=(pd.to_numeric(R.BoroID,errors="coerce")*10**9+pd.to_numeric(R.Block,errors="coerce")*10**4+pd.to_numeric(R.Lot,errors="coerce")).astype("Int64")
R=R.sort_values("LastRegistrationDate").drop_duplicates("bbl",keep="last")
C=pd.read_csv("hpd_con_all.csv",dtype=str,usecols=["RegistrationID","Type","CorporationName","FirstName","LastName","BusinessHouseNumber","BusinessStreetName","BusinessCity","BusinessState","BusinessZip"]).merge(R[["RegistrationID","bbl","LastRegistrationDate"]],on="RegistrationID")
C=C.fillna("")
C["person"]=(C.FirstName.str.strip()+" "+C.LastName.str.strip()).str.strip().str.title()
C["baddr"]=(C.BusinessHouseNumber.str.strip()+" "+C.BusinessStreetName.str.strip()).str.strip().str.title()+", "+C.BusinessCity.str.strip().str.title()+" "+C.BusinessState.str.strip()+" "+C.BusinessZip.str.strip()
out={}
for row in C.itertuples(index=False):
    b=int(row.bbl); o=out.setdefault(b,{"p":set(),"c":set(),"a":set(),"m":set(),"addr":"","reg":str(row.LastRegistrationDate)[:10]})
    if row.Type in ("HeadOfficer","IndividualOwner","JointOwner","Officer"):
        if row.person: o["p"].add(row.person)
        if not o["addr"] and row.baddr.strip(", "): o["addr"]=row.baddr.strip(", ")
    elif row.Type=="CorporateOwner" and row.CorporationName.strip(): o["c"].add(row.CorporationName.strip())
    elif row.Type=="Agent" and row.CorporationName.strip(): o["a"].add(row.CorporationName.strip())
    elif row.Type=="SiteManager" and row.person: o["m"].add(row.person)
for b,o in out.items():
    for k in ("p","c","a","m"): o[k]=sorted(o[k])[:4]
print("lots with HPD registration",len(out))
json.dump(out,open("hpd_all.json","w"),separators=(",",":"))
n=0
for f in glob.glob("../repo/site/props/NY_*.json"):
    L=json.load(open(f))
    for p in L:
        h=out.get(int(p["bbl"]))
        if h: p["hpdc"]=h; n+=1
    json.dump(L,open(f,"w"),separators=(",",":"),allow_nan=False)
print("props with HPD contacts",n)
