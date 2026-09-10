#!/usr/bin/env python3
"""Writes site/status.json: per-market row counts and last successful refresh (from git history)."""
import json,glob,os,subprocess,time,collections
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
def last(path):
    try: return subprocess.check_output(["git","log","-1","--format=%cs","--",path],text=True).strip()
    except Exception: return ""
props=collections.Counter(); pfiles=collections.defaultdict(list)
for f in glob.glob("site/props/*.json"):
    n=os.path.basename(f)
    if any(k in n for k in ("towns","counties","index","areas","states")) or n=="MA.json": continue
    st=n.split("_")[0]; props[st]+=len(json.load(open(f))); pfiles[st].append(f)
out={}
for st in sorted(set(list(props)+[os.path.basename(f)[:-5] for f in glob.glob("site/data/*.json")])):
    d=f"site/data/{st}.json"; deals=len(json.load(open(d))["rows"]) if os.path.exists(d) else 0
    lp=max((last(f) for f in pfiles.get(st,[])),default=""); ld=last(d) if os.path.exists(d) else ""
    ref=max(lp,ld); age=(time.time()-time.mktime(time.strptime(ref,"%Y-%m-%d")))/86400 if ref else None
    out[st]={"props":props.get(st,0),"deals":deals,"refreshed":ref,"stale":bool(age is not None and age>8)}
json.dump({"generated":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime()),"markets":out,"totals":{"props":sum(props.values()),"deals":sum(v["deals"] for v in out.values())}},open("site/status.json","w"),indent=0)
print(json.dumps(out)[:400])
