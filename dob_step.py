#!/usr/bin/env python3
"""Resumable: pull NYC DOB job filings (owner name/business/mailing) for every NYC lot in the database.
Runs ~45 min per invocation (daily job), checkpoints to dob_state.json, merges into data.json when done."""
import requests, json, time, os, sys
from collections import defaultdict
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
BUDGET=int(sys.argv[1]) if len(sys.argv)>1 else 2700
bbls=json.load(open("nyc_bbls.json"))
st=json.load(open("dob_state.json")) if os.path.exists("dob_state.json") else {"idx":0,"idx_now":0,"f":{}}
def q(ds,params):
    for a in range(4):
        try:
            r=requests.get("https://data.cityofnewyork.us/resource/"+ds+".json",params=params,timeout=90)
            if r.status_code==200: return r.json()
        except Exception: pass
        time.sleep(2)
    return None
t0=time.time()
# BIS filings (has bbl)
while st["idx"]<len(bbls) and time.time()-t0<BUDGET:
    ch=bbls[st["idx"]:st["idx"]+100]
    j=q("ic3t-wcy2",{"$where":"bbl in("+",".join("'%d'"%b for b in ch)+")","$select":"bbl,owner_type,owner_s_first_name,owner_s_last_name,owner_s_business_name,owner_s_house_number,owner_shouse_street_name,city_,state,zip,pre__filing_date","$limit":50000})
    if j is None: continue
    for x in j:
        nm=(" ".join(v for v in [x.get("owner_s_first_name",""),x.get("owner_s_last_name","")] if v)).strip().title()
        biz=(x.get("owner_s_business_name") or "").strip().title(); 
        if biz.upper() in ("N-A","NA","N/A","NONE",""): biz=""
        mail=" ".join(v for v in [x.get("owner_s_house_number",""),x.get("owner_shouse_street_name","")] if v).strip().title()
        mail=", ".join(v for v in [mail,(x.get("city_") or "").title(),x.get("state",""),x.get("zip","")] if v)
        dt=x.get("pre__filing_date","");
        try: iso=dt[6:10]+"-"+dt[0:2]+"-"+dt[3:5]
        except Exception: iso=""
        if iso<"2018-01-01": continue
        st["f"].setdefault(x["bbl"],[]).append([iso,nm,biz,mail,x.get("owner_type","")])
    st["idx"]+=100
# DOB NOW filings (borough/block/lot)
if st["idx"]>=len(bbls):
    BN={1:"MANHATTAN",2:"BRONX",3:"BROOKLYN",4:"QUEENS"}
    while st["idx_now"]<len(bbls) and time.time()-t0<BUDGET:
        ch=bbls[st["idx_now"]:st["idx_now"]+60]
        ch=bbls[st["idx_now"]:st["idx_now"]+100]
        w="bbl in("+",".join("'%d'"%b for b in ch)+")"
        j=q("w9ak-ipjd",{"$where":w,"$select":"bbl,owner_s_business_name,owner_first_name,owner_last_name,owner_type,filing_date","$limit":50000})
        if j is None: continue
        for x in j:
            bbl=str(int(float(x["bbl"])))
            nm=(" ".join(v for v in [x.get("owner_first_name",""),x.get("owner_last_name","")] if v)).strip().title()
            biz=(x.get("owner_s_business_name") or "").strip().title()
            mail=""
            iso=(x.get("filing_date") or "")[:10]
            if iso<"2018-01-01": continue
            st["f"].setdefault(bbl,[]).append([iso,nm,biz,mail,x.get("owner_type","")])
        st["idx_now"]+=100
json.dump(st,open("dob_state.json","w"),separators=(",",":"))
print("BIS",st["idx"],"/",len(bbls),"NOW",st["idx_now"],"/",len(bbls),"lots with filings",len(st["f"]))
# merge whatever we have into data.json (idempotent)
D=json.load(open("data.json")); C={k:i for i,k in enumerate(D["cols"])}
if "dob" not in D["cols"]:
    D["cols"].append("dob"); [r.append(None) for r in D["rows"]]
    C["dob"]=len(D["cols"])-1
hit=0
for r in D["rows"]:
    b=r[C["bbl"]]
    if not b or str(b) not in st["f"]: continue
    fs=[f for f in st["f"][str(b)] if f[0]>=r[C["date"]]] or st["f"][str(b)]
    fs.sort(reverse=True)
    seen=[];out=[]
    for f in fs:
        key=(f[1],f[2])
        if key in seen or not (f[1] or f[2]): continue
        seen.append(key); out.append(f)
        if len(out)>=3: break
    if out: r[C["dob"]]=out; hit+=1
print("rows with DOB contacts",hit)
json.dump(D,open("data.json","w"),separators=(",",":"))
os.makedirs("site/data",exist_ok=True)
for s2 in sorted(set(r[C["st"]] for r in D["rows"])):
    json.dump({"cols":D["cols"],"rows":[r for r in D["rows"] if r[C["st"]]==s2],"pulled":D.get("pulled")},open(f"site/data/{s2}.json","w"),separators=(",",":"))
