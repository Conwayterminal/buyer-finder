#!/usr/bin/env python3
"""Actions job: every commercial parcel in New York State outside NYC (57 counties) from the statewide assessment roll
(Open NY 7vem-aaz7): owner, mailing, class, full market value, front/depth, deed book/page. Coordinates come from the roll's
grid coordinates (NY State Plane feet, zone detected per county against Census-geocoded samples). Writes
site/props/NYS_<county>.json; buyer search gets no new rows (the roll has no sale dates) — this is the property layer."""
import requests, json, os, time, re, csv, collections, statistics
from pyproj import Transformer
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
U="https://data.ny.gov/resource/7vem-aaz7.json"
S="county_name,municipality_name,swis_code,print_key_code,roll_section,property_class,property_class_description,parcel_address_number,parcel_address_street,parcel_address_suff,front,depth,grid_coordinates_east,grid_coordinates_north,deed_book,page,primary_owner_first_name,primary_owner_last_name,additional_owner_1_first,additional_owner_1_last_name,mailing_address_number,mailing_address_street,mailing_address_suff,mailing_address_city,mailing_address_state,mailing_address_zip,mailing_address_po_box,full_market_value,assessment_total,county_taxable_value"
W="roll_year=2025 AND ((property_class>=400 AND property_class<500) OR property_class in(330,331,340,341,350,351,280,281))"
rows=[];off=0
while True:
    try: j=requests.get(U,params={"$select":S,"$where":W,"$limit":50000,"$offset":off,"$order":"swis_code,print_key_code"},timeout=300).json()
    except Exception as e: print("err",e,flush=True); time.sleep(5); continue
    if isinstance(j,dict): print(j,flush=True); time.sleep(5); continue
    rows+=j; off+=len(j); print(off,flush=True)
    if len(j)<50000: break
print("NYS commercial parcels",len(rows),flush=True)
ZONES={"East":"EPSG:2260","Central":"EPSG:2261","West":"EPSG:2262","LongIsland":"EPSG:2263","East27":"EPSG:32015","Central27":"EPSG:32016","West27":"EPSG:32017","LI27":"EPSG:32018"}
T={k:Transformer.from_crs(v,"EPSG:4326",always_xy=True) for k,v in ZONES.items()}
def addr(r): return " ".join(v for v in [r.get("parcel_address_number",""),r.get("parcel_address_street",""),r.get("parcel_address_suff","")] if v).strip()
# sample geocode: up to 3 addressed parcels per county via Census batch
bycounty=collections.defaultdict(list)
for r in rows:
    try: x=float(r.get("grid_coordinates_east") or 0); y=float(r.get("grid_coordinates_north") or 0)
    except Exception: continue
    if x>0 and y>0 and addr(r) and r.get("parcel_address_number"): bycounty[r["county_name"]].append(r)
samples=[]
for c,L in bycounty.items():
    for r in L[::max(1,len(L)//6)][:6]: samples.append((c+"|"+str(len(samples)),addr(r).replace('"',''),r.get("municipality_name",""),str(r.get("mailing_address_zip") or "")[:5],float(r["grid_coordinates_east"]),float(r["grid_coordinates_north"])))
body="\n".join(f'{k},"{a}","{m}",NY,' for k,a,m,z,x,y in samples)
got={}
try:
    rr=requests.post("https://geocoding.geo.census.gov/geocoder/locations/addressbatch",files={"addressFile":("a.csv",body)},data={"benchmark":"Public_AR_Current"},timeout=900)
    for line in rr.text.splitlines():
        p=next(csv.reader([line]))
        if len(p)>=6 and p[2]=="Match": lon,lat=p[5].split(","); got[p[0]]=(float(lon),float(lat))
except Exception as e: print("geo err",e,flush=True)
zone_for={}
for c in bycounty:
    best=None
    for zn,tr in T.items():
        errs=[]
        for k,a,m,z,x,y in samples:
            if not k.startswith(c+"|") or k not in got: continue
            lon,lat=tr.transform(x,y); errs.append(abs(lon-got[k][0])+abs(lat-got[k][1]))
        if errs:
            e=statistics.median(errs)
            if best is None or e<best[1]: best=(zn,e)
    zone_for[c]=best[0] if best and best[1]<0.05 else None
    print(c,best,flush=True)
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|CO\b|COMPANY|LLP)\b",re.I)
def cls(pc,desc):
    pc=int(pc); d=str(desc or "").upper()
    if pc in (411,): return "Multifamily 5+ units"
    if pc in (280,281): return "Multifamily 5+ units"
    if pc in (330,331,340,341,350,351): return "Vacant land / development"
    if pc in (480,481,482,483,484,485,486): return "Mixed-use" if pc in (480,481,483) else "Retail / commercial"
    if 410<=pc<=419: return "Hotel" if pc in (414,415,417,418) else "Multifamily 5+ units"
    if 440<=pc<=449: return "Industrial"
    if 460<=pc<=469: return "Office"
    if pc in (438,439,435): return "Garage / parking"
    return "Retail / commercial"
props=collections.defaultdict(list); n=0; skipped=0
for r in rows:
    zn=zone_for.get(r["county_name"])
    try: x=float(r.get("grid_coordinates_east") or 0); y=float(r.get("grid_coordinates_north") or 0)
    except Exception: x=y=0
    if not zn or x<=0 or y<=0: skipped+=1; continue
    lon,lat=T[zn].transform(x,y)
    if not (40<lat<45.1 and -80<lon<-71.7): skipped+=1; continue
    own=" ".join(v for v in [r.get("primary_owner_first_name",""),r.get("primary_owner_last_name","")] if v).strip().title()
    own2=" ".join(v for v in [r.get("additional_owner_1_first",""),r.get("additional_owner_1_last_name","")] if v).strip().title()
    mail=", ".join(v for v in [" ".join(w for w in [r.get("mailing_address_number",""),r.get("mailing_address_street",""),r.get("mailing_address_suff","")] if w).title() or ("PO Box "+r["mailing_address_po_box"] if r.get("mailing_address_po_box") else ""),str(r.get("mailing_address_city") or "").title(),r.get("mailing_address_state","")] if v)
    fmv=r.get("full_market_value"); f=r.get("front"); d=r.get("depth")
    p={"id":f"{r.get('swis_code')} {r.get('print_key_code')}","county":r["county_name"],"town":str(r.get("municipality_name") or "").title(),"addr":addr(r).title() or "Address not listed","lat":round(lat,5),"lng":round(lon,5),"type":cls(r["property_class"],r.get("property_class_description")),"pc":r["property_class"],"desc":r.get("property_class_description"),
       "owner":(own+(" & "+own2 if own2 else ""))[:100],"llc":bool(ent.search(own)),"mail":mail[:120],"mkt":int(float(fmv)) if fmv else None,"av":int(float(r["assessment_total"])) if r.get("assessment_total") else None,"lotF":float(f) if f and float(f)>0 else None,"lotD":float(d) if d and float(d)>0 else None,"book":r.get("deed_book"),"page":r.get("page"),"sold":None,"price":None}
    props[r["county_name"]].append(p); n+=1
os.makedirs("site/props",exist_ok=True)
for c,L in props.items(): json.dump(L,open(f"site/props/NYS_{c.replace(' ','_')}.json","w"),separators=(",",":"),allow_nan=False)
json.dump(sorted({(p["county"],p["town"]) for L in props.values() for p in L}),open("site/props/NYS_towns.json","w"))
print("NYS props",n,"skipped (no zone/coords)",skipped,"counties",len(props),flush=True)
