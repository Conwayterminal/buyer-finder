import json, requests, time, re
biz=json.load(open("ct_reg_biz.json")); ids=sorted(set(x["id"] for L in biz.values() for x in L))
ag={}
for i in range(0,len(ids),150):
    w="business_key in("+",".join("'%s'"%x for x in ids[i:i+150])+")"
    for a in range(4):
        try:
            r=requests.get("https://data.ct.gov/resource/qh2m-n44y.json",params={"$where":w,"$select":"business_key,type,name__c,agent_phone,email,business_address,mailing_address","$limit":50000},timeout=90)
            if r.status_code==200:
                for x in r.json(): ag.setdefault(x["business_key"],[]).append(x)
                break
        except Exception: time.sleep(2)
print("businesses with agent",len(ag),"with phone",sum(1 for L in ag.values() if any(x.get("agent_phone") for x in L)),"with email",sum(1 for L in ag.values() if any(x.get("email") for x in L)))
json.dump(ag,open("ct_reg_agents.json","w"))
d=json.load(open("data.json")); C={k:i for i,k in enumerate(d["cols"])}
n=0
for r in d["rows"]:
    if r[C["st"]]!="CT" or not r[C["reg"]]: continue
    k=r[C["owner"]].upper(); m=re.search(r"\(([^()]+)\)$",r[C["owner"]]); key=(m.group(1) if m else r[C["owner"]]).upper()
    L=biz.get(key) or biz.get(k); 
    if not L: continue
    b=sorted(L,key=lambda x:x.get("status")!="Active")[0]
    A=ag.get(b["id"],[])
    if A:
        a=A[0]; r[C["reg"]]["agent"]={"name":(a.get("name__c") or "").title(),"type":a.get("type",""),"phone":a.get("agent_phone",""),"email":a.get("email",""),"addr":re.sub(r"\s*,\s*",", ",a.get("business_address") or a.get("mailing_address") or "").strip(", ")}; n+=1
print("CT rows with agent contact",n)
json.dump(d,open("data.json","w"),separators=(",",":"))
for st in sorted(set(r[C["st"]] for r in d["rows"])):
    json.dump({"cols":d["cols"],"rows":[r for r in d["rows"] if r[C["st"]]==st],"pulled":d.get("pulled")},open(f"site/data/{st}.json","w"),separators=(",",":"))
