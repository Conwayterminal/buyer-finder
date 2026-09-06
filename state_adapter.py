#!/usr/bin/env python3
"""Generic statewide-parcel adapter. Usage: python3 state_adapter.py <STATE_CODE>
Reads states.json (service URL, filter, field map, classifier), pulls every commercial parcel, writes
site/props/<ST>_<Area>.json + site/props/<ST>_areas.json + site/data/<ST>.json (sales since 2020 when the layer has them),
and registers the state in site/props/states.json for the Property lookup picker."""
import sys, os, re, json, time, collections, requests
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
ST=sys.argv[1]; cfg=json.load(open("states.json"))[ST]
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|CO\b|COMPANY|LLLP|LLP|LTD)\b",re.I)
def g(a,k):
    f=cfg["fields"].get(k)
    if not f: return None
    if isinstance(f,list): return " ".join(str(a.get(x) or "").strip() for x in f).strip() or None
    return a.get(f)
def classify(a):
    uc=str(g(a,"use") or ""); d=str(g(a,"usedesc") or "").upper()
    for rule in cfg["classify"]:
        if rule.get("prefix") and any(uc.startswith(p) for p in rule["prefix"]): return rule["type"]
        if rule.get("regex") and re.search(rule["regex"],d+" "+uc): return rule["type"]
    return cfg.get("default_type")
def pdate(v):
    if v is None or v=="": return None
    if isinstance(v,(int,float)):
        if v>10**11: v=v/1000
        if v>10**8: return time.strftime("%Y-%m-%d",time.gmtime(v))
        s=str(int(v))
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s)==8 else None
    s=str(v).strip().split(" ")[0].split("T")[0]
    import datetime
    for fmt in ("%Y-%m-%d","%m/%d/%Y","%m-%d-%Y","%Y%m%d","%d-%b-%y","%m/%d/%y"):
        try: return datetime.datetime.strptime(s,fmt).strftime("%Y-%m-%d")
        except Exception: pass
    return None
def num(v):
    try:
        x=float(v); return None if x!=x else x
    except Exception: return None
U=cfg["url"]+"/query"; F=",".join(sorted({x for v in cfg["fields"].values() for x in (v if isinstance(v,list) else [v])}))
rows=[]; off=0; page=cfg.get("page",2000); point=cfg.get("point_layer",False)
while True:
    try:
        r=requests.post(U,data={"where":cfg["where"],"outFields":F,"f":"json","returnGeometry":"true" if point else "false","returnCentroid":"false" if point else "true","outSR":"4326","resultOffset":off,"resultRecordCount":page,"orderByFields":cfg.get("order","OBJECTID")},timeout=300).json()
    except Exception as e: print("err",e,flush=True); time.sleep(5); continue
    if "error" in r: print(r["error"],flush=True); time.sleep(5); page=max(500,page//2); continue
    fs=r.get("features",[])
    for f in fs:
        a=f["attributes"]; c=f.get("geometry") if point else f.get("centroid"); c=c or {}; a["_lat"]=c.get("y"); a["_lng"]=c.get("x"); rows.append(a)
    off+=len(fs)
    if off%20000<page: print(off,flush=True)
    if len(fs)<page: break
print(ST,"parcels",len(rows),flush=True)
props=collections.defaultdict(list); deals=[]; D=json.load(open("data.json")); ncols=len(D["cols"])
for a in rows:
    if a["_lat"] is None: continue
    t=classify(a)
    if not t: continue
    own=re.sub(r"\s+"," ",str(g(a,"owner") or "")).strip().title(); own2=re.sub(r"\s+"," ",str(g(a,"owner2") or "")).strip().title()
    if own2 and own2!=own: own=own+" & "+own2
    mail=", ".join(v for v in [str(g(a,"mail") or "").strip().title(),str(g(a,"mailcity") or "").strip().title(),str(g(a,"mailstate") or "").strip()] if v and v.lower()!="none")
    area=str(g(a,"area") or cfg.get("area_default") or ST).strip().title(); town=str(g(a,"town") or area).strip().title()
    sf=num(g(a,"sf")); units=num(g(a,"units")); yb=num(g(a,"yb")); lot=num(g(a,"lot")); mkt=num(g(a,"mkt")); price=num(g(a,"price")); sold=pdate(g(a,"sold"))
    if cfg.get("lot_acres") and lot: lot=lot*43560
    p={"id":str(g(a,"id") or ""),"county":area,"town":town,"addr":str(g(a,"addr") or "").strip().title() or "Address not listed","zip":str(g(a,"zip") or "")[:5],"lat":round(a["_lat"],5),"lng":round(a["_lng"],5),"type":t,"uc":str(g(a,"use") or ""),"ucd":str(g(a,"usedesc") or ""),
       "owner":own[:100],"co":str(g(a,"co") or "").strip().title(),"mail":mail[:120],"llc":bool(ent.search(own)),"units":int(units) if units else None,"sf":int(sf) if sf else None,"yb":int(yb) if yb and yb>1600 else None,"lot":int(lot) if lot else None,"zone":str(g(a,"zone") or ""),"mkt":int(mkt) if mkt else None,"sold":sold,"price":int(price) if price else None,"book":g(a,"book"),"page":g(a,"page")}
    props[area].append(p)
    if sold and sold>="2020-09-01" and sold<="2026-12-31" and price and price>0:
        conf=("Owner of record ("+cfg["source"]+")")+(" - LLC, research" if p["llc"] else "")
        deals.append([sold,area+(" County" if cfg.get("area_is_county") else ""),town,p["addr"],t,p["uc"],p["units"],p["sf"],int(price),1,p["lat"],p["lng"],own[:150],own[:150],conf,"",mail[:120],"",own[:80],p["yb"],p["zone"],p["lot"],p["id"],None,None,None,ST,None,None,None,None,p["mkt"]][:ncols])
os.makedirs("site/props",exist_ok=True)
for k,L in props.items(): json.dump(L,open(f"site/props/{ST}_{re.sub(r'[^A-Za-z0-9]+','_',k)}.json","w"),separators=(",",":"),allow_nan=False)
json.dump(sorted(props.keys()),open(f"site/props/{ST}_areas.json","w"))
json.dump({"cols":D["cols"],"rows":deals,"pulled":time.strftime("%Y-%m-%d")},open(f"site/data/{ST}.json","w"),separators=(",",":"))
# register in states.json for the picker
reg=json.load(open("site/props/states.json")) if os.path.exists("site/props/states.json") else {}
reg[ST]={"name":cfg["name"],"areaLabel":"County" if cfg.get("area_is_county") else cfg.get("area_label","Area"),"areas":sorted(props.keys()),"props":sum(len(v) for v in props.values()),"deals":len(deals),"note":cfg.get("note","")}
json.dump(reg,open("site/props/states.json","w"),indent=0)
print(ST,"props",sum(len(v) for v in props.values()),"areas",len(props),"deals",len(deals),flush=True)
