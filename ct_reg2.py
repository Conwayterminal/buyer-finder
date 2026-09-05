import json, re, requests, time
d=json.load(open("site/data/CT.json")); C={k:i for i,k in enumerate(d["cols"])}
res=json.load(open("ct_reg_biz.json"))
names=sorted(set(r[C["owner"]].upper() for r in d["rows"] if re.search(r"\b(LLC|L\.L\.C|LP|CORP|INC|TRUST|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|COMPANY|CO\b)",r[C["owner"]].upper())))
un=[n for n in names if n not in res]
def variants(n):
    v=set(); base=re.sub(r"\s+"," ",n).strip()
    for b in [base,base.replace(", LLC"," LLC").replace(",LLC"," LLC"),re.sub(r"\bL\.L\.C\.?","LLC",base),re.sub(r"\bLLC\b","LLC.",base),re.sub(r"\bLLC\b","L.L.C.",base),re.sub(r"\bLLC\b",", LLC",base).replace(" , ",", "),base.replace("&","AND"),base.replace(" AND ","& "),re.sub(r"[.,]","",base),re.sub(r"\bINC\b","INC.",base),re.sub(r"\bCORP\b","CORPORATION",base)]:
        v.add(re.sub(r"\s+"," ",b).strip())
    return list(v-{n})
vm={}
for n in un:
    for v in variants(n): vm.setdefault(v,n)
keys=sorted(vm); print("variants to try",len(keys))
for i in range(0,len(keys),80):
    ch=keys[i:i+80]; w="upper(name) in("+",".join("'%s'"%k.replace("'","''") for k in ch)+")"
    for a in range(4):
        try:
            r=requests.get("https://data.ct.gov/resource/n7gp-d28j.json",params={"$where":w,"$select":"id,name,status,mailing_address,date_registration","$limit":5000},timeout=90)
            if r.status_code==200:
                for x in r.json(): res.setdefault(vm.get(x["name"].upper(),x["name"].upper()),[]).append(x)
                break
        except Exception: time.sleep(2)
print("matched names now",len([n for n in names if n in res]),"of",len(names))
json.dump(res,open("ct_reg_biz.json","w"))
