import json, re, collections
P=json.load(open("pd/persons_all.json"))
d=json.load(open("repo/data.json")); C={k:i for i,k in enumerate(d["cols"])}
def toks(n):
    n=re.sub(r"[^A-Za-z ]"," ",str(n or "")).upper()
    n=re.sub(r"\b(MR|MRS|MS|DR|JR|SR|II|III|IV|ESQ|TRUSTEE|TR|ETAL|ET AL|AND|THE)\b","",n)
    return [t for t in n.split() if len(t)>1]
# index persons by frozenset of first+last tokens (skip junk names)
idx=collections.defaultdict(list); byphone={}; byemail={}
for p in P:
    fn,ln=str(p.get("first_name") or "").strip(),str(p.get("last_name") or "").strip()
    if fn.lower()=="aloware" or len(ln)<2 or len(fn)<2 or re.search(r"contact|unknown|test",p["name"],re.I): 
        pass
    else:
        idx[frozenset(toks(fn)[:1]+toks(ln)[-1:])].append(p)
    for ph in p.get("phones") or []:
        v=re.sub(r"\D","",ph.get("value",""))[-10:]
        if len(v)==10: byphone.setdefault(v,p)
    for em in p.get("emails") or []:
        if em.get("value"): byemail.setdefault(em["value"].lower(),p)
print("indexed names",len(idx),"phones",len(byphone),"emails",len(byemail))
def cands(name):
    # name may be "First Last", "Last First", "First Last, First2 Last2", "Last, First"
    out=[]
    for part in re.split(r"[,;&/]| and ",str(name or "")):
        t=toks(part)
        if len(t)<2 or len(t)>4: continue
        for a,b in [(t[0],t[-1]),(t[-1],t[0]),(t[0],t[1]),(t[1],t[0])]:
            for p in idx.get(frozenset([a,b]),[]):
                # confirm order sanity: person's first token must be one of them
                out.append(p)
    return out
def rec(p): return {"id":p["id"],"name":p["name"],"owner":p.get("owner_id"),"al":(p.get("custom_fields") or {}).get("cdcc4762eca5901f42e50f12e9cb8863e16cc1ea") or "","org":p.get("org_id")}
if "pd" not in d["cols"]:
    d["cols"].append("pd"); [r.append(None) for r in d["rows"]]; C["pd"]=len(d["cols"])-1
hits=0; by_state=collections.Counter(); by_src=collections.Counter()
for r in d["rows"]:
    found={}
    names=[]
    o=r[C["owner"]]
    if not re.search(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|COMPANY|UNDISCLOSED)\b",o.upper()): names.append(("owner",re.sub(r"\(.*?\)","",o)))
    reg=r[C["reg"]] if "reg" in C else None
    if reg:
        for pr in reg.get("principals") or []: names.append(("registry",re.sub(r"\(.*?\)","",pr)))
        ag=reg.get("agent") or {}
        if ag.get("name"): names.append(("agent",ag["name"]))
        if ag.get("phone"):
            v=re.sub(r"\D","",ag["phone"])[-10:]
            if v in byphone: found[byphone[v]["id"]]=dict(rec(byphone[v]),via="agent phone")
        if ag.get("email") and ag["email"].lower() in byemail: p=byemail[ag["email"].lower()]; found[p["id"]]=dict(rec(p),via="agent email")
    for f in (r[C["dob"]] or []) if "dob" in C else []:
        if f[1]: names.append(("permit signer",f[1]))
    for src,nm in names:
        for p in cands(nm):
            if p["id"] not in found: found[p["id"]]=dict(rec(p),via=src+": "+nm.strip()[:40])
    if found:
        r[C["pd"]]=list(found.values())[:5]; hits+=1; by_state[r[C["st"]]]+=1
        for v in found.values(): by_src[v["via"].split(":")[0]]+=1
print("rows with Pipedrive match",hits,dict(by_state)); print(by_src)
json.dump(d,open("repo/data.json","w"),separators=(",",":"))
for st in sorted(set(r[C["st"]] for r in d["rows"])):
    json.dump({"cols":d["cols"],"rows":[r for r in d["rows"] if r[C["st"]]==st],"pulled":d.get("pulled")},open(f"repo/site/data/{st}.json","w"),separators=(",",":"))
