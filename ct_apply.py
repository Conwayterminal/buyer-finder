import json, re
d=json.load(open("data.json")); C={k:i for i,k in enumerate(d["cols"])}
biz=json.load(open("ct_reg_biz.json")); people=json.load(open("ct_reg_people.json"))["principals"]
if "reg" not in d["cols"]:
    d["cols"].append("reg"); [r.append(None) for r in d["rows"]]; C["reg"]=len(d["cols"])-1
n=0;up=0
for r in d["rows"]:
    if r[C["st"]]!="CT": continue
    k=r[C["owner"]].upper()
    if k not in biz: continue
    b=sorted(biz[k],key=lambda x:x.get("status")!="Active")[0]
    pp=people.get(b["id"],[])
    names=sorted(set((p.get("name__c") or "").strip().title() for p in pp if p.get("name__c")))
    addr=sorted(set(", ".join(v for v in [p.get("residence_city",""),p.get("residence_state","")] if v) for p in pp if p.get("residence_city")))
    r[C["reg"]]={"biz":b["name"].title(),"status":b.get("status",""),"mail":re.sub(r"\s*,\s*",", ",b.get("mailing_address","") or "").strip(", "),"reg":(b.get("date_registration") or "")[:10],"principals":names[:6],"where":addr[:3]}
    n+=1
    if names and "LLC" in r[C["conf"]]:
        r[C["owner"]]=(", ".join(names[:3])+" ("+r[C["owner"]]+")")[:150]; r[C["conf"]]="CT business registry principal(s) of the owner LLC"; up+=1
print("CT rows with registry",n,"owner upgraded to principals",up)
json.dump(d,open("data.json","w"),separators=(",",":"))
for st in sorted(set(r[C["st"]] for r in d["rows"])):
    json.dump({"cols":d["cols"],"rows":[r for r in d["rows"] if r[C["st"]]==st],"pulled":d.get("pulled")},open(f"site/data/{st}.json","w"),separators=(",",":"))
