#!/usr/bin/env python3
"""Actions job: every Connecticut commercial parcel (169 towns) from the state CAMA/parcel layer.
Union of: commercial CAMA models, state-use commercial/industrial/apartment codes, and descriptive matches.
Writes site/props/CT_<letter>.json (by town initial) + CT sales since 2020 at any price into data.json / site/data/CT.json,
carrying over registry principals/agents already resolved for CT owners."""
import requests, json, os, time, re, collections
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
U="https://services3.arcgis.com/3FL1kr7L4LvwA2Kb/arcgis/rest/services/Connecticut_CAMA_and_Parcel_Layer/FeatureServer/0/query"
W="Model IN ('94.0','95.0','96.0','97.0','98.0','99.0','94','95','96','97') OR State_Use LIKE '2%' OR State_Use LIKE '3%' OR State_Use LIKE '105%' OR State_Use LIKE '4%' OR State_Use_Description LIKE '%APART%' OR State_Use_Description LIKE '%COMM%' OR State_Use_Description LIKE '%INDUST%' OR State_Use_Description LIKE '%MIX%' OR State_Use_Description LIKE '%RETAIL%' OR State_Use_Description LIKE '%OFFICE%' OR State_Use_Description LIKE '%STORE%' OR State_Use_Description LIKE '%WAREHOUSE%' OR State_Use_Description LIKE '%HOTEL%' OR State_Use_Description LIKE '%MULTI%'"
F="Town_Name,Location,Property_City,ZIP_CODE,Owner,Co_Owner,Mailing_Address,Mailing_City,Mailing_State,Mailing_Zip,Sale_Price,Sale_Date,Prior_Sale_Date,Prior_Sale_Price,State_Use,State_Use_Description,Model,Living_Area,Effective_Area,Land_Acres,Zone,AYB,Assessed_Total,Appraised_Total,Occupancy,Parcel_ID,Link,Total_Rooms"
# towns first, then query town by town (the statewide LIKE filter is too slow for the server)
tj=requests.post(U,data={"where":"1=1","outFields":"Town_Name","returnDistinctValues":"true","returnGeometry":"false","f":"json"},timeout=180).json()
towns=sorted({f["attributes"]["Town_Name"] for f in tj.get("features",[]) if f["attributes"].get("Town_Name")})
print("towns",len(towns),flush=True)
rows=[]
for tn in towns:
    off=0; fails=0
    while True:
        try: r=requests.post(U,data={"where":f"Town_Name='{tn.replace(chr(39),chr(39)*2)}' AND ({W})","outFields":F,"f":"json","returnGeometry":"false","returnCentroid":"true","outSR":"4326","resultOffset":off,"resultRecordCount":2000,"orderByFields":"OBJECTID"},timeout=180).json()
        except Exception as e: fails+=1; print("err",tn,e,flush=True); time.sleep(5); 
        else:
            if "error" in r: fails+=1; print(tn,r["error"],flush=True); time.sleep(5)
            else:
                fs=r.get("features",[])
                for f in fs:
                    a=f["attributes"]; c=f.get("centroid") or {}; a["lat"]=c.get("y"); a["lng"]=c.get("x"); rows.append(a)
                off+=len(fs)
                if len(fs)<2000: break
        if fails>5: break
    print(tn,len(rows),flush=True)
print("CT parcels",len(rows),flush=True)
def cls(a):
    s=(str(a.get("State_Use_Description") or "")+" "+str(a.get("Occupancy") or "")).upper(); mdl=str(a.get("Model") or "").split(".")[0]; su=str(a.get("State_Use") or "")
    if re.search(r"SFR|SINGLE|CONDO CONV|ACCESSORY|ACC APT|1 FAM|ONE FAM|TWO FAM|2 FAM|DUPLEX",s) and not re.search(r"MIX|STORE",s): return None
    if re.search(r"MIX|STORE.*(APT|RES)|RES.*(COMM|STORE)|COMM.*RES",s): return "Mixed-use"
    if re.search(r"APART|MULTI|5\+|UNITS|APT|DWELLINGS",s) or su.startswith("105"): return "Walkup multifamily"
    if mdl=="96" or re.search(r"INDUST|MANUF|WAREHOUSE|DISTRIB|FLEX",s) or su.startswith("3"): return "Industrial"
    if re.search(r"HOTEL|MOTEL|INN\b|LODG",s): return "Hotel"
    if re.search(r"OFFICE|MEDICAL|PROF",s): return "Office"
    if re.search(r"FOUR|4 FAM|4-FAM|THREE|3 FAM|3-FAM",s): return "Small residential (3-4 family)"
    if re.search(r"VACANT|LAND|LOT",s): return "Vacant land / development"
    if mdl in ("94","95","97","98","99") or su.startswith("2") or re.search(r"RETAIL|STORE|SHOP|RESTAUR|GAS|AUTO|BANK|COMM|SERVICE|PLAZA",s): return "Retail / commercial"
    return None
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|COMPANY|LLP)\b",re.I)
from datetime import datetime
def pdate(s):
    s=str(s or "").strip()
    for fmt in ("%d-%b-%y","%m/%d/%Y","%Y-%m-%d","%Y%m%d","%d-%b-%Y","%m/%d/%y"):
        try: return datetime.strptime(s,fmt).strftime("%Y-%m-%d")
        except Exception: pass
    return None
# registry principals already resolved for CT owners (from earlier run) 
D=json.load(open("data.json")); C={k:i for i,k in enumerate(D["cols"])}
reg_by_owner={}
for r in D["rows"]:
    if r[C["st"]]=="CT" and r[C["reg"]]: reg_by_owner[re.sub(r"\(.*?\)","",r[C["grantee"]] or r[C["owner"]]).strip().upper()]=r[C["reg"]]
props=collections.defaultdict(list); deals=[]
for a in rows:
    if a.get("lat") is None: continue
    t=cls(a)
    if not t: continue
    own=(str(a.get("Owner") or "").strip()+((" & "+str(a.get("Co_Owner")).strip()) if a.get("Co_Owner") and str(a.get("Co_Owner")).strip() else "")).title()
    addr=str(a.get("Location") or "").strip().title() or "Address not listed"; town=str(a.get("Town_Name") or "").title()
    sf=a.get("Effective_Area") or a.get("Living_Area"); mail=", ".join(v for v in [str(a.get("Mailing_Address") or "").title(),str(a.get("Mailing_City") or "").title(),str(a.get("Mailing_State") or "")] if v and v!="None")
    sale=pdate(a.get("Sale_Date")); price=a.get("Sale_Price"); reg=reg_by_owner.get(own.upper())
    p={"id":a.get("Parcel_ID"),"town":town,"addr":addr,"zip":str(a.get("ZIP_CODE") or "")[:5],"lat":round(a["lat"],5),"lng":round(a["lng"],5),"type":t,"uc":a.get("State_Use"),"ucd":a.get("State_Use_Description"),"owner":own[:100],"mail":mail[:120],"llc":bool(ent.search(own)),
       "sf":int(sf) if sf else None,"lot":int(float(a["Land_Acres"])*43560) if a.get("Land_Acres") else None,"yb":a.get("AYB"),"zone":a.get("Zone"),"mkt":a.get("Appraised_Total"),"av":a.get("Assessed_Total"),"sold":sale,"price":int(price) if price else None,"prior":pdate(a.get("Prior_Sale_Date")),"priorP":a.get("Prior_Sale_Price"),"card":a.get("Link"),"reg":reg}
    props[town[:1] or "_"].append(p)
    if sale and sale>="2020-09-01" and price and price>0:
        conf=("CT business registry principal(s) of the owner LLC" if reg and reg.get("principals") else ("Owner of record (assessor) - LLC, research" if p["llc"] else "Owner of record (assessor)"))
        owner_disp=(", ".join(x.split(" (")[0] for x in reg["principals"][:3])+" ("+own+")")[:150] if reg and reg.get("principals") and p["llc"] else own[:150]
        row=[sale,"Connecticut",town,addr,t,str(a.get("State_Use") or ""),None,p["sf"],int(price),1,p["lat"],p["lng"],own[:150],owner_disp,conf,"",mail[:120],"",own[:80],int(a["AYB"]) if a.get("AYB") and a["AYB"]>1600 else None,str(a.get("Zone") or ""),p["lot"],str(a.get("Link") or ""),None,None,None,"CT",None,None,reg,None,int(a["Appraised_Total"]) if a.get("Appraised_Total") else None]
        deals.append(row[:len(D["cols"])])
os.makedirs("site/props",exist_ok=True)
for k,L in props.items(): json.dump(L,open(f"site/props/CT_{k}.json","w"),separators=(",",":"),allow_nan=False)
json.dump({"cols":D["cols"],"rows":deals,"pulled":D.get("pulled")},open("site/data/CT.json","w"),separators=(",",":"))
json.dump(sorted({(p["town"][:1],p["town"]) for L in props.values() for p in L},key=lambda x:x[1]),open("site/props/CT_towns.json","w"))
print("CT props",sum(len(v) for v in props.values()),"CT deals since 2020 (any price)",len(deals),flush=True)

# launch
