#!/usr/bin/env python3
"""Milwaukee (WI) from the city's Master Property file (MPROP): every commercial/manufacturing/5+ unit parcel with owner,
mailing, class, land use, units, building area, stories, year built, lot, zoning, assessed value, last conveyance date and fee."""
import os, io, csv, re, json, time, requests
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
URL="https://data.milwaukee.gov/dataset/562ab824-48a5-42cd-b714-87e205e489ba/resource/0a2c7f31-cd15-4151-8222-09dd57d5f16d/download/mprop.csv"
r=requests.get(URL,timeout=600); r.raise_for_status()
rd=csv.DictReader(io.StringIO(r.content.decode("latin1")))
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|CO\b|COMPANY|LLP|BANK)\b",re.I)
def num(x):
    try: return float(x)
    except Exception: return None
props=[]; deals=[]; D=json.load(open("data.json")); n=len(D["cols"])
for x in rd:
    cls=(x.get("C_A_CLASS") or "").strip(); lu=(x.get("LAND_USE_GP") or x.get("LAND_USE") or "").strip(); units=num(x.get("NR_UNITS"))
    if not (cls in ("2","3") or (cls=="1" and units and units>=5)): continue   # 2=commercial, 3=manufacturing, 1=residential (5+ units)
    lat=num(x.get("GEO_LATITUDE") or x.get("LATITUDE")); lng=num(x.get("GEO_LONGITUDE") or x.get("LONGITUDE"))
    if not lat: continue
    own=" ".join(v for v in [(x.get("OWNER_NAME_1") or "").strip(),(x.get("OWNER_NAME_2") or "").strip()] if v).title()
    addr=" ".join(v for v in [(x.get("HOUSE_NR_LO") or "").strip(),(x.get("SDIR") or "").strip(),(x.get("STREET") or "").strip(),(x.get("STTYPE") or "").strip()] if v).title()
    cd=(x.get("CONVEY_DATE") or "").strip(); sold=f"{cd[:4]}-{cd[4:6]}-{cd[6:8]}" if len(cd)==8 else None
    if sold and (sold>time.strftime("%Y-%m-%d") or sold<"1900-01-01"): sold=None
    price=num(x.get("CONVEY_FEE")); bt=(x.get("BLDG_TYPE") or "").strip().upper()
    t="Multifamily 5+ units" if (cls=="1" or "APART" in bt or (units and units>=5 and cls=="2")) else ("Industrial" if cls=="3" or "WAREHOUSE" in bt or "MANUF" in bt else ("Office" if "OFFICE" in bt else ("Hotel" if "HOTEL" in bt or "MOTEL" in bt else ("Vacant land / development" if "VACANT" in lu.upper() or not bt else "Retail / commercial"))))
    p={"id":x.get("TAXKEY"),"county":"Milwaukee","town":"Milwaukee","addr":addr or "Address not listed","zip":"","lat":round(lat,5),"lng":round(lng,5),"type":t,"uc":cls,"ucd":bt or lu,"owner":own[:100],"mail":", ".join(v for v in [(x.get("OWNER_MAIL_ADDR") or "").strip().title(),(x.get("OWNER_CITY_STATE") or "").strip().title()] if v)[:120],"llc":bool(ent.search(own)),
       "units":int(units) if units else None,"sf":int(num(x.get("BLDG_AREA")) or 0) or None,"stories":x.get("NR_STORIES"),"yb":int(num(x.get("YR_BUILT")) or 0) or None,"lot":int(num(x.get("LOT_AREA")) or 0) or None,"zone":(x.get("ZONING") or "").strip(),"mkt":int(num(x.get("C_A_TOTAL")) or 0) or None,"sold":sold,"price":int(price) if price else None,"nbhd":x.get("NEIGHBORHOOD")}
    props.append(p)
    if sold and sold>="2020-09-01" and price and price>0:
        deals.append([sold,"Milwaukee","Milwaukee",p["addr"],t,cls,p["units"],p["sf"],int(price),1,p["lat"],p["lng"],own[:150],own[:150],"Owner of record after conveyance (Milwaukee MPROP)"+(" - LLC, research" if p["llc"] else ""),"",p["mail"],"","",p["yb"],p["zone"],p["lot"],"Taxkey "+str(p["id"]),None,None,None,"WI",None,None,None,None,p["mkt"]][:n])
os.makedirs("site/props",exist_ok=True)
json.dump(props,open("site/props/WI_Milwaukee.json","w"),separators=(",",":"),allow_nan=False)
json.dump({"cols":D["cols"],"rows":deals,"pulled":time.strftime("%Y-%m-%d")},open("site/data/WI.json","w"),separators=(",",":"))
reg=json.load(open("site/props/states.json")); reg["WI"]={"name":"Wisconsin (Milwaukee)","areaLabel":"City","areas":["Milwaukee"],"props":len(props),"deals":len(deals),"note":"City of Milwaukee master property file: owner, mailing, class, units, building area, year built, zoning, assessed value, last conveyance date and fee."}
json.dump(reg,open("site/props/states.json","w"),indent=0)
print("WI props",len(props),"deals",len(deals),flush=True)
