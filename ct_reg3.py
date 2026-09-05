import json, requests, time
res=json.load(open("ct_reg_biz.json"))
ids=sorted(set(x["id"] for L in res.values() for x in L)); print("business ids",len(ids))
pr={}; ag={}
for ds,store,sel in [("ka36-64k6",pr,"business_id,name__c,residence_address,residence_city,residence_state"),("qh2m-n44y",ag,None)]:
    if sel is None:
        r=requests.get("https://data.ct.gov/resource/qh2m-n44y.json",params={"$limit":1},timeout=60); sel=",".join(k for k in r.json()[0].keys() if k in("business_id","name__c","agent_name","name","business_address","mailing_address","agent_business_address","residence_address","agent_type","agent_type__c","agent_business_street_address_1","agent_residence_address"))
        print("agent fields",sel)
    for i in range(0,len(ids),150):
        w="business_id in("+",".join("'%s'"%x for x in ids[i:i+150])+")"
        for a in range(4):
            try:
                r=requests.get("https://data.ct.gov/resource/"+ds+".json",params={"$where":w,"$select":sel,"$limit":50000},timeout=90)
                if r.status_code==200:
                    for x in r.json(): store.setdefault(x["business_id"],[]).append(x)
                    break
            except Exception: time.sleep(2)
print("with principals",len(pr),"with agents",len(ag))
json.dump({"principals":pr,"agents":ag},open("ct_reg_people.json","w"))
