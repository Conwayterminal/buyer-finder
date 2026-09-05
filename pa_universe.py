#!/usr/bin/env python3
"""Actions job: every Philadelphia commercial property (OPA categories 2-6) with owner, mailing, c/o, sale history,
building data, assessed value, and L&I open violation counts. Writes site/props/PA_Philadelphia.json and site/data/PA.json."""
import requests, json, os, re, collections, time
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
Q="https://phl.carto.com/api/v2/sql"
def sql(q):
    for a in range(5):
        try:
            r=requests.get(Q,params={"q":q},timeout=600).json()
            if "rows" in r: return r["rows"]
            print(r,flush=True)
        except Exception as e: print("err",e,flush=True)
        time.sleep(5)
    return []
rows=[];off=0
while True:
    ch=sql(f"SELECT parcel_number,location,zip_code,owner_1,owner_2,mailing_care_of,mailing_street,mailing_city_state,sale_date,sale_price,category_code,building_code_description,total_area,total_livable_area,year_built,number_stories,zoning,market_value,taxable_land,taxable_building,ST_Y(the_geom) AS lat,ST_X(the_geom) AS lng FROM opa_properties_public WHERE category_code IN ('2','3','4','5','6') ORDER BY parcel_number LIMIT 50000 OFFSET {off}")
    rows+=ch; off+=len(ch); print(off,flush=True)
    if len(ch)<50000: break
print("PA properties",len(rows),flush=True)
viol=collections.defaultdict(int)
for r in sql("SELECT opa_account_num, count(*) AS n FROM violations WHERE violationstatus='OPEN' GROUP BY opa_account_num"): viol[str(r["opa_account_num"])]=r["n"]
print("accounts with open L&I violations",len(viol),flush=True)
def asset(x):
    b=(x.get("building_code_description") or "").upper(); c=x["category_code"]
    if c=="2": return "Hotel" if "HOTEL" in b or "MOTEL" in b else "Multifamily 5+ units"
    if c=="3": return "Mixed-use"
    if c=="4": return "Office" if "OFFICE" in b else ("Garage / parking" if "GARAGE" in b or "PARKING" in b else "Retail / commercial")
    if c=="5": return "Industrial"
    return "Vacant land / development"
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|COMPANY|LLLP|LLP)\b",re.I)
D=json.load(open("data.json")); ncols=len(D["cols"])
P=[];deals=[]
for x in rows:
    if x.get("lat") is None: continue
    own=" & ".join(v.strip().title() for v in [x.get("owner_1") or "",x.get("owner_2") or ""] if v.strip()); co=(x.get("mailing_care_of") or "").strip().title()
    mail=", ".join(v.strip().title() for v in [x.get("mailing_street") or "",x.get("mailing_city_state") or ""] if v.strip())
    m=re.search(r"(\d+)\s*(?:UNIT|APT|FAM)",(x.get("building_code_description") or "").upper()); units=int(m.group(1)) if m else None
    sf=x.get("total_livable_area") or None; yb=x.get("year_built"); yb=int(yb) if yb and str(yb).isdigit() and int(yb)>1600 else None
    p={"id":x["parcel_number"],"county":"Philadelphia","town":"Philadelphia","addr":(x.get("location") or "").title(),"zip":str(x.get("zip_code") or "")[:5],"lat":round(x["lat"],5),"lng":round(x["lng"],5),"type":asset(x),"cat":x["category_code"],"desc":x.get("building_code_description"),
       "owner":own[:100],"co":co,"mail":mail[:120],"llc":bool(ent.search(own)),"units":units,"sf":int(sf) if sf and sf>0 else None,"stories":x.get("number_stories"),"yb":yb,"lot":int(x["total_area"]) if x.get("total_area") else None,"zone":x.get("zoning"),"mkt":int(x["market_value"]) if x.get("market_value") else None,
       "tax":int((float(x.get("taxable_land") or 0)+float(x.get("taxable_building") or 0))*0.013998) or None,"sold":(x.get("sale_date") or "")[:10] or None,"price":int(x["sale_price"]) if x.get("sale_price") else None,"viol":viol.get(str(x["parcel_number"]),0)}
    P.append(p)
    if p["sold"] and p["sold"]>="2020-09-01" and p["price"] and p["price"]>0:
        owner,conf=(co+" ("+own+")","Mailing c/o on tax roll (Philadelphia OPA)") if co and p["llc"] else (own,"Owner of record (Philadelphia OPA) - LLC, research" if p["llc"] else "Owner of record (Philadelphia OPA)")
        if p["price"]<25000: conf+=" - nominal price, likely not arm's-length"
        deals.append([p["sold"],"Philadelphia","ZIP "+p["zip"],p["addr"],p["type"],(x.get("building_code_description") or "")[:40],units,p["sf"],p["price"],1,p["lat"],p["lng"],own[:150],owner[:150],conf,"",mail[:120],"","",yb,x.get("zoning") or "",p["lot"],"OPA "+x["parcel_number"],None,None,None,"PA",None,None,None,None,p["mkt"]][:ncols])
os.makedirs("site/props",exist_ok=True)
json.dump(P,open("site/props/PA_Philadelphia.json","w"),separators=(",",":"),allow_nan=False)
json.dump({"cols":D["cols"],"rows":deals,"pulled":D.get("pulled")},open("site/data/PA.json","w"),separators=(",",":"))
print("PA props",len(P),"deals since 2020 any price",len(deals),"with open violations",sum(1 for p in P if p["viol"]),flush=True)
