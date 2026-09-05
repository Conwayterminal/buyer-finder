#!/usr/bin/env python3
"""Actions job: every LA County commercial/industrial/5+ unit parcel from the assessor parcel layer. Names are not public in
California; the card shows use, SF, units, year built, assessed values, Prop 13 base year (≈ last transfer year) and an
estimated price backed out of the assessment. Writes site/props/CA_Los_Angeles.json and site/data/CA.json."""
import requests, json, os, time, re, collections
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
U="https://public.gis.lacounty.gov/public/rest/services/LACounty_Cache/LACounty_Parcel/MapServer/0/query"
F="AIN,SitusFullAddress,SitusCity,SitusZIP,UseType,UseDescription,YearBuilt1,Units1,SQFTmain1,Units2,SQFTmain2,Roll_LandValue,Roll_ImpValue,Roll_LandBaseYear,Roll_ImpBaseYear,CENTER_LAT,CENTER_LON"
rows=[]
for W in ["UseType IN ('Commercial','Industrial')","UseType='Residential' AND Units1>=5"]:
    off=0
    while True:
        try: r=requests.post(U,data={"where":W,"outFields":F,"returnGeometry":"false","resultOffset":off,"resultRecordCount":1000,"orderByFields":"OBJECTID","f":"json"},timeout=180).json()
        except Exception as e: print("err",e,flush=True); time.sleep(5); continue
        if "error" in r: print(r["error"],flush=True); time.sleep(5); continue
        fs=r.get("features",[]); rows+=[f["attributes"] for f in fs]; off+=len(fs)
        if off%50000==0: print(W[:25],off,flush=True)
        if len(fs)<1000: break
print("LA parcels",len(rows),flush=True)
def asset(x):
    d=(x.get("UseDescription") or "").upper(); t=x.get("UseType")
    if t=="Residential": return "Multifamily 5+ units"
    if t=="Industrial": return "Industrial"
    if re.search(r"OFFICE|MEDICAL|BANK",d): return "Office"
    if re.search(r"HOTEL|MOTEL",d): return "Hotel"
    if re.search(r"PARKING|GARAGE",d): return "Garage / parking"
    if re.search(r"VACANT|LAND",d): return "Vacant land / development"
    if re.search(r"STORE.*(APT|RESID)|MIX",d): return "Mixed-use"
    return "Retail / commercial"
D=json.load(open("data.json")); ncols=len(D["cols"])
P=[];deals=[];seen=set()
for x in rows:
    if x.get("CENTER_LAT") is None or x["AIN"] in seen: continue
    seen.add(x["AIN"])
    try: yr=int(x["Roll_LandBaseYear"])
    except Exception: yr=None
    val=(x.get("Roll_LandValue") or 0)+(x.get("Roll_ImpValue") or 0); est=int(val/(1.02**max(0,2026-yr))) if yr else None
    units=(x.get("Units1") or 0)+(x.get("Units2") or 0); sf=(x.get("SQFTmain1") or 0)+(x.get("SQFTmain2") or 0)
    p={"id":"AIN "+x["AIN"],"county":"Los Angeles","town":(x.get("SitusCity") or "").title() or "Los Angeles","addr":(x.get("SitusFullAddress") or "").title() or "Address not listed","zip":str(x.get("SitusZIP") or "")[:5],"lat":round(x["CENTER_LAT"],5),"lng":round(x["CENTER_LON"],5),"type":asset(x),"desc":x.get("UseDescription"),
       "owner":"Undisclosed (CA - names not public)","llc":True,"mail":"","units":units or None,"sf":sf or None,"yb":int(x["YearBuilt1"]) if x.get("YearBuilt1") and int(x["YearBuilt1"])>1600 else None,"mkt":int(val) if val else None,"base":yr,"est":est,"sold":f"{yr}-01-01" if yr and yr>=1900 else None,"price":None}
    P.append(p)
    if yr and yr>=2020:
        deals.append([f"{yr}-01-01","Los Angeles County",p["town"],p["addr"],p["type"],(x.get("UseDescription") or "")[:40],p["units"],p["sf"],None,1,p["lat"],p["lng"],"","Undisclosed (CA - names not public)","California assessor roll: owner name not published; transfer year from Prop 13 base year; ≈ price backed out of assessed value","","","","",p["yb"],"",None,"AIN "+x["AIN"],None,None,None,"CA",None,None,None,None,est][:ncols])
os.makedirs("site/props",exist_ok=True)
json.dump(P,open("site/props/CA_Los_Angeles.json","w"),separators=(",",":"),allow_nan=False)
json.dump({"cols":D["cols"],"rows":deals,"pulled":D.get("pulled")},open("site/data/CA.json","w"),separators=(",",":"))
print("CA props",len(P),"transfers since 2020",len(deals),flush=True)
