import json, re, requests, pandas as pd, time
d=json.load(open("site/data/CT.json")); C={k:i for i,k in enumerate(d["cols"])}
names=sorted(set(r[C["owner"]].upper() for r in d["rows"] if re.search(r"\b(LLC|L\.L\.C|LP|CORP|INC|TRUST|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|COMPANY|CO\b)",r[C["owner"]].upper())))
print("LLC-ish owners",len(names))
def norm(n): return re.sub(r"[^A-Z0-9 ]","",n.upper().replace("&","AND")).replace("  "," ").strip()
res={}
for i in range(0,len(names),80):
    ch=names[i:i+80]
    w="upper(name) in("+",".join("'%s'"%n.replace("'","''") for n in ch)+")"
    for a in range(4):
        try:
            r=requests.get("https://data.ct.gov/resource/n7gp-d28j.json",params={"$where":w,"$select":"id,name,status,mailing_address,date_registration","$limit":5000},timeout=90)
            if r.status_code==200:
                for x in r.json(): res.setdefault(x["name"].upper(),[]).append(x)
                break
        except Exception: time.sleep(2)
print("matched names",len(res))
json.dump(res,open("ct_reg_biz.json","w"))
