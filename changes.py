#!/usr/bin/env python3
"""Weekly change feed: compares each market file to the last committed version and writes site/changes/<ST>.json
(new transactions, new/changed owners) so agents get a prospecting feed instead of re-reading the whole database."""
import json,os,subprocess,sys,glob,time
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
os.makedirs("site/changes",exist_ok=True)
sts=sys.argv[1:] or [os.path.basename(f)[:-5] for f in glob.glob("site/data/*.json")]
for st in sts:
    p=f"site/data/{st}.json"
    if not os.path.exists(p): continue
    new=json.load(open(p)); C={k:i for i,k in enumerate(new["cols"])}
    try: old=json.loads(subprocess.check_output(["git","show",f"HEAD:{p}"],text=True))
    except Exception: old={"rows":[]}
    key=lambda r:(r[C["addr"]],r[C["date"]],r[C["price"]])
    seen={key(r) for r in old["rows"]}
    added=[r for r in new["rows"] if key(r) not in seen]
    added.sort(key=lambda r:r[C["date"]],reverse=True)
    out={"market":st,"generated":time.strftime("%Y-%m-%d"),"new_transactions":len(added),"rows":[{"date":r[C["date"]],"addr":r[C["addr"]],"area":r[C["boro"]],"town":r[C["nbhd"]],"type":r[C["asset"]],"price":r[C["price"]],"buyer":r[C["owner"]],"conf":r[C["conf"]]} for r in added[:2000]]}
    json.dump(out,open(f"site/changes/{st}.json","w"),separators=(",",":"))
    print(st,"new transactions this refresh:",len(added),flush=True)
