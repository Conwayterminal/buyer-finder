import pandas as pd, json, re
d=pd.read_pickle("ma.pkl"); d=d[d.USE_CODE.astype(str)!="132"]
d["dt"]=pd.to_datetime(d.LS_DATE,errors="coerce",format="%Y%m%d"); d["price"]=pd.to_numeric(d.LS_PRICE,errors="coerce")
def asset(uc,desc):
    uc=str(uc); dsc=str(desc or "").upper()
    if uc.startswith("111"): return "Multifamily 4-8 units"
    if uc.startswith("112"): return "Multifamily 9+ units"
    if uc in("109",): return "Multifamily (multiple houses)"
    if uc.startswith("013") or uc.startswith("031"): return "Mixed-use"
    if uc.startswith("130") or uc.startswith("131") or uc.startswith("39") or uc.startswith("44"): return "Vacant land / development"
    if uc.startswith("4"): return "Industrial"
    if uc.startswith("34"): return "Office"
    if uc.startswith("30"): return "Hotel"
    if uc.startswith("33") or uc.startswith("336"): return "Garage / parking"
    return "Retail / commercial"
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|TRS|TRUSTEE|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|COMPANY|LLLP|LLP|NOMINEE)",re.I)
rows=[]; props=[]
for r in d.itertuples():
    if pd.isna(r.lat): continue
    own=re.sub(r"\s+"," ",str(r.OWNER1 or "")).strip().title(); co=str(r.OWN_CO or "").strip().title() if isinstance(r.OWN_CO,str) else ""
    mail=", ".join(v for v in [str(r.OWN_ADDR or "").strip().title(),str(r.OWN_CITY or "").strip().title(),str(r.OWN_STATE or "").strip()] if v and v.lower()!="nan")
    a=asset(r.USE_CODE,r.USE_DESC); sf=int(r.BLD_AREA) if pd.notna(r.BLD_AREA) and r.BLD_AREA>0 else None; units=int(r.UNITS) if pd.notna(r.UNITS) and r.UNITS>0 else None
    yb=int(r.YEAR_BUILT) if pd.notna(r.YEAR_BUILT) and r.YEAR_BUILT>1600 else None; lot=int(r.LOT_SIZE*43560) if pd.notna(r.LOT_SIZE) and r.LOT_SIZE>0 else None
    conf=("Owner of record (MassGIS assessor) - LLC, research" if ent.search(own) else "Owner of record (MassGIS assessor)")
    if co and ent.search(own): owner,conf=co+" ("+own+")","c/o on assessor roll (MassGIS)"
    else: owner=own
    st_=str(r.STORIES) if isinstance(r.STORIES,str) else (str(int(r.STORIES)) if pd.notna(r.STORIES) else "")
    props.append({"id":r.LOC_ID,"addr":str(r.SITE_ADDR or "").title(),"city":str(r.CITY or "").title(),"zip":str(r.ZIP or "")[:5],"lat":round(r.lat,5),"lng":round(r.lng,5),"type":a,"uc":str(r.USE_CODE),"desc":str(r.USE_DESC or "")[:60],"owner":owner[:120],"ownRaw":own[:120],"mail":mail[:120],"units":units,"sf":sf,"stories":st_,"yb":yb,"lot":lot,"zone":str(r.ZONING or "")[:20] if isinstance(r.ZONING,str) else "","val":int(r.TOTAL_VAL) if pd.notna(r.TOTAL_VAL) else None,"bval":int(r.BLDG_VAL) if pd.notna(r.BLDG_VAL) else None,"lval":int(r.LAND_VAL) if pd.notna(r.LAND_VAL) else None,"sold":r.dt.strftime("%Y-%m-%d") if pd.notna(r.dt) else None,"price":int(r.price) if pd.notna(r.price) and r.price>0 else None,"book":f"{r.LS_BOOK}/{r.LS_PAGE}" if isinstance(r.LS_BOOK,str) else ""})
    if pd.notna(r.dt) and r.dt>=pd.Timestamp("2020-09-01") and pd.notna(r.price) and r.price>0:
        rows.append([r.dt.strftime("%Y-%m-%d"),"Massachusetts",str(r.CITY or "").title(),str(r.SITE_ADDR or "").title(),a,str(r.USE_CODE),units,sf,int(r.price),1,round(r.lat,5),round(r.lng,5),own[:150],owner[:150],conf+(" - nominal price, likely not arm's-length" if r.price<25000 else ""),"",mail[:120],"",own[:80],yb,str(r.ZONING or "")[:20] if isinstance(r.ZONING,str) else "",lot,f"Registry {r.LS_BOOK}/{r.LS_PAGE}" if isinstance(r.LS_BOOK,str) else "",None,None,None,"MA",None,None,None,None,int(r.TOTAL_VAL) if pd.notna(r.TOTAL_VAL) else None])
json.dump(rows,open("rows.json","w"),separators=(",",":")); json.dump(props,open("props.json","w"),separators=(",",":"),allow_nan=False)
import collections,os; print("MA deals",len(rows),"MA props",len(props),os.path.getsize("props.json")//1024//1024,"MB"); print(collections.Counter(x[4] for x in rows).most_common())
