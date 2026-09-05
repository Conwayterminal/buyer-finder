#!/usr/bin/env python3
"""Add any-price NYC sales (from the ACRIS full-history layer on the property cards) into data.json / site/data/NY.json."""
import json,glob,os
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
D=json.load(open("data.json")); C={k:i for i,k in enumerate(D["cols"])}; n=len(D["cols"])
have={(r[C["bbl"]],r[C["date"]]) for r in D["rows"] if r[C["st"]]=="NY" and r[C["bbl"]]}
have_addr={(r[C["addr"]],r[C["date"]]) for r in D["rows"] if r[C["st"]]=="NY"}
AC=lambda t:t
added=0
for f in glob.glob("site/props/NY_*.json"):
    for p in json.load(open(f)):
        if not p.get("sold") or p["sold"]<"2020-09-01": continue
        if (p["bbl"],p["sold"]) in have or (p["addr"],p["sold"]) in have_addr: continue
        row=[None]*n
        row[C["date"]]=p["sold"]; row[C["boro"]]=p["boro"]; row[C["nbhd"]]=p.get("cd") and ("CD "+str(p["cd"])) or p["boro"]; row[C["addr"]]=p["addr"]; row[C["asset"]]=p["type"]; row[C["bc"]]=p["bc"]
        row[C["units"]]=p.get("units"); row[C["sf"]]=p.get("sf"); row[C["price"]]=p.get("price") or 0; row[C["nlots"]]=1; row[C["lat"]]=p["lat"]; row[C["lng"]]=p["lng"]
        row[C["grantee"]]=p.get("buyer") or ""; row[C["owner"]]=p.get("buyer") or p.get("owner") or "Unknown"; row[C["conf"]]=(p.get("conf") or "Deed grantee (ACRIS)")+(" - price under $500k or nominal" if (p.get("price") or 0)<500000 else "")
        row[C["seller"]]=""; row[C["mail"]]=(p.get("hpdc") or {}).get("addr","") ; row[C["hpdaddr"]]=""; row[C["pluto_owner"]]=p.get("owner",""); row[C["yb"]]=p.get("yb"); row[C["zone"]]=p.get("zone",""); row[C["lot"]]=p.get("lot"); row[C["doc"]]=""
        row[C["acq"]]=p.get("acq"); row[C["refi"]]=p.get("refi"); row[C["st"]]="NY"; row[C["bbl"]]=p["bbl"]; row[C["dob"]]=p.get("dobc"); row[C["pd"]]=p.get("pd"); row[C["appr"]]=p.get("mkt")
        if p.get("hpdc") and p["hpdc"].get("p"): row[C["owner"]]=", ".join(p["hpdc"]["p"][:3]); row[C["conf"]]="HPD registration (principal)"
        D["rows"].append(row); added+=1
json.dump(D,open("data.json","w"),separators=(",",":"))
json.dump({"cols":D["cols"],"rows":[r for r in D["rows"] if r[C["st"]]=="NY"],"pulled":D.get("pulled")},open("site/data/NY.json","w"),separators=(",",":"))
print("added NYC any-price sales",added,"NY rows now",sum(1 for r in D["rows"] if r[C["st"]]=="NY"))
