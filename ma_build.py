#!/usr/bin/env python3
"""Actions job: every Massachusetts commercial parcel (all 351 towns) from MassGIS, with owner, last sale, building data.
Writes site/props/MA_<townid-range>.json for property lookup and appends MA sales since 2020 to data.json/site/data/MA.json."""
import requests, json, os, time, re, collections
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
U="https://services1.arcgis.com/hGdibHYSPO59RG1h/arcgis/rest/services/Massachusetts_Property_Tax_Parcels/FeatureServer/0/query"
W="(USE_CODE LIKE '3%' OR USE_CODE LIKE '4%' OR USE_CODE LIKE '0%' OR USE_CODE LIKE '11%' OR USE_CODE LIKE '12%' OR USE_CODE LIKE '105%') AND POLY_TYPE IN ('TAX','FEE')"
F="LOC_ID,PROP_ID,MAP_PAR_ID,TOWN_ID,BLDG_VAL,LAND_VAL,TOTAL_VAL,FY,LOT_SIZE,LOT_UNITS,LS_DATE,LS_PRICE,LS_BOOK,LS_PAGE,USE_CODE,USE_DESC,SITE_ADDR,CITY,ZIP,OWNER1,OWN_ADDR,OWN_CITY,OWN_STATE,OWN_ZIP,ZONING,YEAR_BUILT,BLD_AREA,UNITS,STORIES,STYLE"
rows=[];off=0
while True:
    try: r=requests.post(U,data={"where":W,"outFields":F,"returnGeometry":"false","returnCentroid":"true","outSR":"4326","resultOffset":off,"resultRecordCount":2000,"orderByFields":"OBJECTID","f":"json"},timeout=180).json()
    except Exception as e: print("err",e,flush=True); time.sleep(5); continue
    if "error" in r: print(r["error"],flush=True); time.sleep(5); continue
    fs=r.get("features",[])
    for f in fs:
        a=f["attributes"]; c=f.get("centroid") or {}; a["lat"]=c.get("y"); a["lng"]=c.get("x"); rows.append(a)
    off+=len(fs)
    if off%20000==0: print(off,flush=True)
    if len(fs)<2000: break
print("MA parcels",len(rows),flush=True)
def asset(uc,desc):
    u=str(uc or ""); d=str(desc or "").upper()
    if u.startswith("11") or u.startswith("12") or "APART" in d: return "Multifamily 5+ units" if not u.startswith("111") else "Multifamily 4-8 units"
    if u.startswith("105"): return "Small residential (3-4 family)"
    if u.startswith("0"): return "Mixed-use"
    if u.startswith("4"): return "Industrial"
    if u.startswith("30") or "HOTEL" in d or "MOTEL" in d: return "Hotel"
    if u.startswith("34") or "OFFICE" in d or "MEDICAL" in d: return "Office"
    if u.startswith("39") or "VACANT" in d or "LAND" in d: return "Vacant land / development"
    if u.startswith("33") or "GARAGE" in d or "PARK" in d: return "Garage / parking"
    return "Retail / commercial"
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|COMPANY|LLP|NOMINEE)\b",re.I)
def dt(s):
    s=str(s or "");
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s)==8 and s.isdigit() else None
props=collections.defaultdict(list); deals=[]
for a in rows:
    if a.get("lat") is None: continue
    own=str(a.get("OWNER1") or "").strip().title(); addr=str(a.get("SITE_ADDR") or "").strip().title(); town=str(a.get("CITY") or "").strip().title()
    lot=a.get("LOT_SIZE"); lot_sf=int(lot*43560) if lot and str(a.get("LOT_UNITS"))=="A" else (int(lot) if lot else None)
    sale=dt(a.get("LS_DATE")); price=a.get("LS_PRICE") or None
    p={"id":a.get("LOC_ID"),"pid":a.get("PROP_ID"),"town":town,"tid":a.get("TOWN_ID"),"addr":addr,"zip":str(a.get("ZIP") or "")[:5],"lat":round(a["lat"],5),"lng":round(a["lng"],5),
       "type":asset(a.get("USE_CODE"),a.get("USE_DESC")),"uc":a.get("USE_CODE"),"ucd":a.get("USE_DESC"),"owner":own[:100],"mail":", ".join(v for v in [str(a.get("OWN_ADDR") or "").title(),str(a.get("OWN_CITY") or "").title(),str(a.get("OWN_STATE") or "")] if v and v!="None")[:120],
       "llc":bool(ent.search(own)),"units":a.get("UNITS"),"sf":a.get("BLD_AREA"),"stories":a.get("STORIES"),"yb":a.get("YEAR_BUILT"),"lot":lot_sf,"zone":a.get("ZONING"),"mkt":a.get("TOTAL_VAL"),"bv":a.get("BLDG_VAL"),"lv":a.get("LAND_VAL"),"fy":a.get("FY"),
       "sold":sale,"price":int(price) if price else None,"book":a.get("LS_BOOK"),"page":a.get("LS_PAGE")}
    props[int(a.get("TOWN_ID") or 0)//15].append(p)
    if sale and sale>="2020-09-01" and price and price>0:
        deals.append([sale,town,town,addr,p["type"],str(a.get("USE_CODE") or ""),int(a["UNITS"]) if a.get("UNITS") else None,int(a["BLD_AREA"]) if a.get("BLD_AREA") else None,int(price),1,p["lat"],p["lng"],own[:150],own[:150],"Owner of record (MassGIS assessor)"+(" - LLC, research" if p["llc"] else ""),"",p["mail"],"",own[:80],int(a["YEAR_BUILT"]) if a.get("YEAR_BUILT") else None,str(a.get("ZONING") or ""),lot_sf,f"Bk {a.get('LS_BOOK')} Pg {a.get('LS_PAGE')}" if a.get("LS_BOOK") else "",None,None,None,"MA",None,None,None,None,int(a["TOTAL_VAL"]) if a.get("TOTAL_VAL") else None])
os.makedirs("site/props",exist_ok=True)
for k,L in props.items(): json.dump(L,open(f"site/props/MA_{k:02d}.json","w"),separators=(",",":"),allow_nan=False)
D=json.load(open("data.json")); C={k:i for i,k in enumerate(D["cols"])}
deals=[d[:len(D["cols"])] for d in deals]
json.dump({"cols":D["cols"],"rows":deals,"pulled":D.get("pulled")},open("site/data/MA.json","w"),separators=(",",":"))
towns=sorted({(p["tid"],p["town"]) for L in props.values() for p in L},key=lambda x:x[1]); json.dump(towns,open("site/props/MA_towns.json","w"))
print("MA props",sum(len(v) for v in props.values()),"MA deals since 2020",len(deals),"shards",len(props),flush=True)

# launch
