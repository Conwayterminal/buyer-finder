import pandas as pd, numpy as np, re, json
d=pd.read_pickle("ct_cama.pkl"); d["dt"]=pd.to_datetime(d.Sale_Date,errors="coerce",format="mixed"); d=d[d.dt>="2020-09-01"].copy()
def num(s):
    try: return float(str(s).split("-")[0])
    except: return None
d["code"]=d.State_Use.map(num)
desc=d.State_Use_Description.fillna("").str.upper()+" "+d.Model.fillna("").astype(str).str.upper()+" "+d.Occupancy.fillna("").astype(str).str.upper()
def cls(r):
    s=desc.loc[r.name]; c=r.code
    if re.search(r"SFR|SINGLE|CONDO CONV|ACCESSORY|ACC APT|1 FAM|ONE FAM",s): return None
    mdl=str(r.Model or "").split(".")[0]
    if mdl=="94": return "Retail" if not re.search(r"OFFICE|APART|MIX|HOTEL|MOTEL",s) else cls_desc(s)
    if mdl=="96": return "Industrial"
    if re.search(r"MIX|STORE.*(APT|RES)|RES.*(COMM|STORE)|COMM.*RES",s): return "Mixed-use"
    if re.search(r"APART|MULTI|5\+|UNITS|APT|DWELLINGS",s) or (c is not None and 105<=c<106): return "Elevator multifamily" if re.search(r"HI.?RISE|ELEV",s) else "Walkup multifamily"
    if re.search(r"INDUST|MANUF|WAREHOUSE|DISTRIB|FLEX",s) or (c is not None and 300<=c<400): return "Industrial"
    if re.search(r"HOTEL|MOTEL|INN\b|LODG",s): return "Hotel"
    if re.search(r"OFFICE|MEDICAL|PROF",s): return "Office"
    if re.search(r"RETAIL|STORE|SHOP|RESTAUR|GAS|AUTO|BANK|COMM|SERVICE|CAR WASH|DEALER|DAY CARE|PLAZA",s) or (c is not None and 200<=c<300): return "Retail"
    if re.search(r"VACANT|LAND|DEVELOP|LOT",s) and not re.search(r"RESIDENT|RES ",s): return "Vacant land / development"
    if re.search(r"VACANT|LAND",s) and re.search(r"COMM|IND",s): return "Vacant land / development"
    if re.search(r"FOUR|4 FAM|4-FAM|THREE|3 FAM|3-FAM",s): return "Small residential (3-4 family)"
    if re.search(r"CHURCH|RELIG|SCHOOL|MUNIC|EXEMPT|UTILITY|NURSING|HOSPITAL|CEMET",s): return "Institutional"
    return None
def cls_desc(s):
    if re.search(r"MIX",s): return "Mixed-use"
    if re.search(r"HOTEL|MOTEL",s): return "Hotel"
    if re.search(r"OFFICE",s): return "Office"
    if re.search(r"APART",s): return "Walkup multifamily"
    return "Retail"
d["asset"]=d.apply(cls,axis=1)
keep=d[d.asset.notna()&~d.asset.isin(["Institutional"])].copy()
print(len(keep)); print(keep.asset.value_counts().to_dict())
def owner(r):
    o=str(r.Owner or "").strip(); co=str(r.Co_Owner or "").strip()
    return (o+(" & "+co if co and co.upper()!="NAN" else "")).title()
def is_shell(n): return bool(re.search(r"\b(LLC|L\.L\.C|LP|CORP|INC|REALTY|ASSOCIATES|HOLDINGS|PROPERTIES|PARTNERS|TRUST|EQUITIES|VENTURES|GROUP)\b",n.upper()))
rows=[]
for r in keep.itertuples():
    if pd.isna(r.lat): continue
    own=owner(r); addr=str(r.Location or "").strip().title() or "Address not listed"
    conf="Owner of record (assessor) - LLC, research" if is_shell(own) else "Owner of record (assessor)"
    mail=", ".join(x for x in [str(r.Mailing_Address or "").strip().title(),str(r.Mailing_City or "").strip().title(),str(r.Mailing_State or "").strip()] if x and x.lower()!="nan")
    sf=int(r.Effective_Area) if pd.notna(r.Effective_Area) and r.Effective_Area>0 else (int(r.Living_Area) if pd.notna(r.Living_Area) and r.Living_Area>0 else None)
    rows.append([r.dt.strftime("%Y-%m-%d"),"Connecticut",str(r.Town_Name).title(),addr,r.asset,str(r.State_Use or ""),None,sf,int(r.Sale_Price),1,round(r.lat,5),round(r.lng,5),own[:150],own[:150],conf,"",mail[:120],"",own[:80],int(r.AYB) if pd.notna(r.AYB) and r.AYB>1600 else None,str(r.Zone or ""),int(r.Land_Acres*43560) if pd.notna(r.Land_Acres) else None,str(r.Link or ""),None,None,None,"CT"])
json.dump(rows,open("ct_rows.json","w"),separators=(",",":")); print("rows",len(rows))
