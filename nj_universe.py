#!/usr/bin/env python3
"""Actions job: every New Jersey commercial parcel (classes 4A/4B/4C, vacant class 1, 3+ unit class 2) from the
NJOGIS MOD-IV composite (owner names withheld by the state), plus every SR-1A deed sale since 2020 at any price
(names redacted; buyer mailing address from the tax roll where the roll still reflects that sale)."""
import requests, json, os, time, re, collections, glob, zipfile, io
import pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
U="https://services2.arcgis.com/XVOqAjTOJ5P6ngMu/arcgis/rest/services/Parcels_Composite_NJ_WM/FeatureServer/0/query"
F="PAMS_PIN,PCL_MUN,PROP_CLASS,COUNTY,MUN_NAME,PROP_LOC,ST_ADDRESS,CITY_STATE,BLDG_DESC,LAND_DESC,CALC_ACRE,PROP_USE,BLDG_CLASS,DEED_DATE,YR_CONSTR,SALES_CODE,SALE_PRICE,DWELL,COMM_DWELL,NET_VALUE,LAND_VAL,IMPRVT_VAL,FAC_NAME,ZONING,LOT_SIZE"
def pull(where):
    rows=[];off=0
    while True:
        try: r=requests.post(U,data={"where":where,"outFields":F,"f":"json","returnGeometry":"false","returnCentroid":"true","outSR":"4326","resultOffset":off,"resultRecordCount":2000,"orderByFields":"OBJECTID"},timeout=180).json()
        except Exception as e: print("err",e,flush=True); time.sleep(5); continue
        if "error" in r:
            if "Invalid" in str(r["error"]) and "ZONING" in F: raise SystemExit(r["error"])
            print(r["error"],flush=True); time.sleep(5); continue
        fs=r.get("features",[])
        for f in fs:
            a=f["attributes"]; c=f.get("centroid") or {}; a["lat"]=c.get("y"); a["lng"]=c.get("x"); rows.append(a)
        off+=len(fs)
        if off%40000==0: print(where[:30],off,flush=True)
        if len(fs)<2000: break
    return rows
# probe field validity
probe=requests.post(U,data={"where":"1=1","outFields":F,"resultRecordCount":1,"returnGeometry":"false","f":"json"},timeout=60).json()
if "error" in probe:
    F="PAMS_PIN,PCL_MUN,PROP_CLASS,COUNTY,MUN_NAME,PROP_LOC,ST_ADDRESS,CITY_STATE,BLDG_DESC,LAND_DESC,CALC_ACRE,PROP_USE,BLDG_CLASS,DEED_DATE,YR_CONSTR,SALES_CODE,SALE_PRICE,DWELL,COMM_DWELL,NET_VALUE,LAND_VAL,IMPRVT_VAL,FAC_NAME"
rows=pull("PROP_CLASS IN ('4A','4B','4C')")+pull("PROP_CLASS='1'")+pull("PROP_CLASS='2' AND DWELL>=3")
print("NJ parcels",len(rows),flush=True)
def asset(a):
    pc=str(a.get("PROP_CLASS")); txt=(str(a.get("BLDG_DESC") or "")+" "+str(a.get("PROP_USE") or "")+" "+str(a.get("FAC_NAME") or "")).upper()
    if pc=="4C": return "Multifamily 5+ units"
    if pc=="4B": return "Industrial"
    if pc=="1": return "Vacant land / development"
    if pc=="2": return "Small residential (3-4 family)"
    if re.search(r"MIX|APT|RES",txt): return "Mixed-use"
    if re.search(r"HOTEL|MOTEL",txt): return "Hotel"
    if re.search(r"OFF|MED|PROF",txt): return "Office"
    if re.search(r"WHSE|WAREHOUSE|INDUST|MFG",txt): return "Industrial"
    return "Retail / commercial"
def d6(x):
    x=str(x or "").strip()
    if len(x)==8 and x.isdigit(): return f"{x[:4]}-{x[4:6]}-{x[6:8]}"
    if len(x)==6 and x.isdigit():
        y=int(x[:2]); y=2000+y if y<50 else 1900+y; return f"{y}-{x[2:4]}-{x[4:6]}"
    if re.match(r"\d{4}-\d{2}-\d{2}",x): return x[:10]
    if re.match(r"\d{1,2}/\d{1,2}/\d{4}",x): m,d,y=x.split("/"); return f"{y}-{int(m):02d}-{int(d):02d}"
    return None
props=collections.defaultdict(list); pin_owner={}
for a in rows:
    if a.get("lat") is None: continue
    cty=str(a.get("COUNTY") or "").title(); mun=str(a.get("MUN_NAME") or "").title(); addr=str(a.get("PROP_LOC") or "").strip().title() or "Address not listed"
    mail=", ".join(v for v in [str(a.get("ST_ADDRESS") or "").strip().title(),str(a.get("CITY_STATE") or "").strip().title()] if v and v!="None")
    acre=a.get("CALC_ACRE"); p={"id":a.get("PAMS_PIN"),"county":cty,"town":mun,"addr":addr,"lat":round(a["lat"],5),"lng":round(a["lng"],5),"type":asset(a),"pc":a.get("PROP_CLASS"),"desc":a.get("BLDG_DESC"),"use":a.get("PROP_USE"),
       "owner":"Undisclosed (NJ withholds names)","mail":mail[:120],"units":a.get("DWELL"),"cunits":a.get("COMM_DWELL"),"yb":a.get("YR_CONSTR"),"lot":int(float(acre)*43560) if acre else None,"mkt":a.get("NET_VALUE"),"lv":a.get("LAND_VAL"),"iv":a.get("IMPRVT_VAL"),"sold":d6(a.get("DEED_DATE")),"price":a.get("SALE_PRICE") or None,"nu":a.get("SALES_CODE"),"zone":a.get("ZONING")}
    props[cty or "_"].append(p); pin_owner[a.get("PAMS_PIN")]=(mail, d6(a.get("DEED_DATE")), a.get("SALE_PRICE"))
os.makedirs("site/props",exist_ok=True)
for k,L in props.items(): json.dump(L,open(f"site/props/NJ_{k.replace(' ','_')}.json","w"),separators=(",",":"),allow_nan=False)
json.dump(sorted({(p["county"],p["town"]) for L in props.values() for p in L}),open("site/props/NJ_towns.json","w"))
print("NJ props",sum(len(v) for v in props.values()),flush=True)
# SR-1A all sales (any price) since 2020
deals=[]
def sl(l,a,b): return l[a-1:b].strip()
base="https://www.nj.gov/treasury/taxation/lpt/statdata/"
files=["Sales2020.zip","Sales2021.zip","Sales2022.zip","Sales2023.zip","Sales2024.zip","Sales2025.zip","YTDSR1A2026.zip"]
D=json.load(open("data.json")); C={k:i for i,k in enumerate(D["cols"])}
munname={}
for L in props.values():
    for p in L: munname[str(p["id"]).split("_")[0]]=(p["county"],p["town"])
cent=collections.defaultdict(list)
for L in props.values():
    for p in L: cent[str(p["id"]).split("_")[0]].append((p["lat"],p["lng"]))
import statistics
centroid={k:(statistics.median(x[0] for x in v),statistics.median(x[1] for x in v)) for k,v in cent.items()}
pin_ll={p["id"]:(p["lat"],p["lng"]) for L in props.values() for p in L}
for fn in files:
    try: z=zipfile.ZipFile(io.BytesIO(requests.get(base+fn,headers={"User-Agent":"Mozilla/5.0"},timeout=300).content))
    except Exception as e: print("skip",fn,e,flush=True); continue
    for name in z.namelist():
        if not name.lower().endswith(".txt"): continue
        for raw in z.open(name):
            l=raw.decode("latin1")
            if len(l)<640: continue
            pc=sl(l,627,629)
            if pc not in ("4A","4B","4C","1","2"): continue
            try: price=max(int(sl(l,38,46) or 0),int(sl(l,47,55) or 0))
            except Exception: continue
            if price<=0: continue
            deed=sl(l,339,344) or sl(l,345,350); dt=d6(deed)
            if not dt or dt<"2020-09-01": continue
            cty,dist=sl(l,1,2),sl(l,3,4); b=(sl(l,351,355).lstrip("0") or "0")+(("."+sl(l,356,359).lstrip("0")) if sl(l,356,359) else ""); lo=(sl(l,360,364).lstrip("0") or "0")+(("."+sl(l,365,368).lstrip("0")) if sl(l,365,368) else "")
            pin=f"{cty}{dist}_{b}_{lo}"; q=sl(l,620,624)
            ll=pin_ll.get(pin+("_"+q if q else "")) or pin_ll.get(pin) or centroid.get(cty+dist)
            if not ll: continue
            c_t=munname.get(cty+dist,("",""))
            po=pin_owner.get(pin+("_"+q if q else "")) or pin_owner.get(pin)
            mail=po[0] if po and (po[1]==dt or (po[2] and int(po[2])==price)) else ""
            if pc=="2" and int(sl(l,630,632) or 0)<3 and "3" not in sl(l,630,632): 
                pass
            deals.append([dt,c_t[0]+" County",c_t[1],sl(l,298,322).title() or "Address not listed",{"4A":"Retail / commercial","4B":"Industrial","4C":"Multifamily 5+ units","1":"Vacant land / development","2":"Small residential"}[pc],pc,None,None,price,1,round(ll[0],5),round(ll[1],5),"",("Undisclosed - mail to "+mail) if mail else "Undisclosed (NJ)","NJ withholds names (Daniel's Law)"+(" - buyer mailing address from tax roll" if mail else "")+(" Non-usable sale code "+sl(l,35,37)+"." if sl(l,35,37) not in ("","00") else ""),"",mail[:120],"","",int(sl(l,653,656)) if sl(l,653,656).isdigit() and int(sl(l,653,656))>1600 else None,"",None,pin.replace("_","/"),None,None,None,"NJ",None,None,None,None,None][:len(D["cols"])])
    print(fn,"deals so far",len(deals),flush=True)
json.dump({"cols":D["cols"],"rows":deals,"pulled":D.get("pulled")},open("site/data/NJ.json","w"),separators=(",",":"))
print("NJ deals since 2020 (any price)",len(deals),flush=True)
