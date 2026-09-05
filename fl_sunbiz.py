#!/usr/bin/env python3
"""Runs in GitHub Actions (needs SFTP egress). Downloads Sunbiz quarterly corporate data (public creds),
parses fixed-width records using the field definitions page, and attaches officers/registered agent to
every Florida LLC/corporate owner in data.json."""
import os, re, json, io, sys, socket, html
import paramiko, requests
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
D=json.load(open("data.json")); C={k:i for i,k in enumerate(D["cols"])}
def norm(n): 
    n=n.upper().replace("&"," AND "); n=re.sub(r"[^A-Z0-9 ]"," ",n); n=re.sub(r"\b(THE)\b","",n)
    n=re.sub(r"\bL L C\b|\bLLC\b|\bLIMITED LIABILITY (COMPANY|CO)\b","LLC",n); n=re.sub(r"\bINCORPORATED\b","INC",n); n=re.sub(r"\bCORPORATION\b","CORP",n)
    return re.sub(r"\s+"," ",n).strip()
fl=[r for r in D["rows"] if r[C["st"]]=="FL"]
targets={}
for r in fl:
    o=r[C["owner"]]
    if re.search(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|COMPANY|LLLP|LLP)\b",o.upper()): targets.setdefault(norm(o),[]).append(r)
print("FL entity owners to resolve",len(targets))
# --- field definitions
defs=None
for u in ["https://dos.fl.gov/sunbiz/other-services/data-downloads/corporate-file-definitions/","https://dos.myflorida.com/sunbiz/other-services/data-downloads/corporate-file-definitions/"]:
    try:
        t=requests.get(u,headers={"User-Agent":"Mozilla/5.0"},timeout=60).text
        rows=re.findall(r"<tr[^>]*>(.*?)</tr>",t,re.S); fields=[]
        for tr in rows:
            cells=[html.unescape(re.sub("<.*?>","",c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>",tr,re.S)]
            nums=[c for c in cells if re.fullmatch(r"\d+",c)]
            if len(cells)>=3 and len(nums)>=2: fields.append((cells[0],int(nums[-2]),int(nums[-1])))
        if len(fields)>30: defs=fields; print("definitions fields",len(fields)); break
    except Exception as e: print("defs err",e)
if not defs:
    # documented layout fallback (record length 1440)
    defs=[("COR_NUMBER",1,12),("COR_NAME",13,192),("COR_STATUS",205,1),("COR_FILING_TYPE",206,15),("COR_PRINC_ADD_1",221,42),("COR_PRINC_ADD_2",263,42),("COR_PRINC_CITY",305,28),("COR_PRINC_STATE",333,2),("COR_PRINC_ZIP",335,10),("COR_PRINC_COUNTRY",345,2),("COR_MAIL_ADD_1",347,42),("COR_MAIL_ADD_2",389,42),("COR_MAIL_CITY",431,28),("COR_MAIL_STATE",459,2),("COR_MAIL_ZIP",461,10),("COR_MAIL_COUNTRY",471,2),("COR_FILE_DATE",473,8),("COR_FEI_NUMBER",481,14),("MORE_THAN_SIX_OFF_FLAG",495,1),("COR_LAST_TRX_DATE",496,8),("COR_STATE_COUNTRY",504,2),("COR_REPORT_YEAR_1",506,4),("COR_REPORT_DATE_1",510,8),("COR_REPORT_YEAR_2",518,4),("COR_REPORT_DATE_2",522,8),("COR_REPORT_YEAR_3",530,4),("COR_REPORT_DATE_3",534,8),("RA_NAME",542,42),("RA_NAME_TYPE",584,1),("RA_ADD_1",585,42),("RA_CITY",627,28),("RA_STATE",655,2),("RA_ZIP5",657,5),("RA_ZIP4",662,4)]
    p=666
    for i in range(1,7):
        for nm,ln in [("TITLE",4),("NAME_TYPE",1),("NAME",42),("ADD_1",42),("CITY",28),("STATE",2),("ZIP5",5),("ZIP4",4)]:
            defs.append((f"OFF{i}_{nm}",p,ln)); p+=ln
    print("using fallback layout, officers end at",p)
F={n:(s-1,s-1+l) for n,s,l in defs}
def fld(rec,n):
    a,b=F[n]; return rec[a:b].strip()
name_key=next((n for n in F if "COR_NAME" in n.upper() or n.upper()=="NAME"),None)
print("name field",name_key)
# --- SFTP
ip=socket.getaddrinfo("sftp.floridados.gov",22,socket.AF_INET,socket.SOCK_STREAM)[0][4]
sock=socket.create_connection(ip,timeout=60); tr=paramiko.Transport(sock); tr.connect(username="Public",password="PubAccess1845!")
sf=paramiko.SFTPClient.from_transport(tr)
def find(d,depth=0):
    out=[]
    for a in sf.listdir_attr(d):
        p=d.rstrip("/")+"/"+a.filename
        if a.st_mode & 0o40000:
            if depth<3: out+=find(p,depth+1)
        else: out.append((p,a.st_size))
    return out
files=find("/doc")
q=[f for f in files if re.search(r"/cor/.*(quarterly|Quarterly|qtr).*",f[0]) or re.search(r"cordata.*\d\.txt$",f[0],re.I)]
if not q: q=[f for f in files if "/cor" in f[0] and f[1]>50_000_000]
print("candidate files",len(q)); [print(" ",p,s) for p,s in q[:12]]
found={}
for p,size in q:
    print("reading",p,size,flush=True)
    with sf.open(p,"rb") as fh:
        fh.prefetch(size); buf=b""
        while True:
            chunk=fh.read(4*1024*1024)
            if not chunk: break
            buf+=chunk; recs=buf.split(b"\n"); buf=recs.pop()
            for rec in recs:
                rec=rec.decode("latin1")
                if len(rec)<600: continue
                k=norm(fld(rec,name_key))
                if k in targets and k not in found:
                    offs=[]
                    for i in range(1,7):
                        nm=fld(rec,f"OFF{i}_NAME") if f"OFF{i}_NAME" in F else ""
                        if nm: offs.append({"title":fld(rec,f"OFF{i}_TITLE") if f"OFF{i}_TITLE" in F else "","name":nm.title(),"addr":", ".join(v for v in [fld(rec,f"OFF{i}_ADD_1").title(),fld(rec,f"OFF{i}_CITY").title(),fld(rec,f"OFF{i}_STATE")] if f"OFF{i}_ADD_1" in F and v)})
                    found[k]={"biz":fld(rec,name_key).title(),"docnum":fld(rec,"COR_NUMBER") if "COR_NUMBER" in F else "","status":fld(rec,"COR_STATUS") if "COR_STATUS" in F else "","mail":", ".join(v for v in [fld(rec,x).title() for x in ("COR_MAIL_ADD_1","COR_MAIL_CITY","COR_MAIL_STATE") if x in F] if v),"filed":fld(rec,"COR_FILE_DATE") if "COR_FILE_DATE" in F else "","ra":{"name":fld(rec,"RA_NAME").title() if "RA_NAME" in F else "","addr":", ".join(v for v in [fld(rec,x).title() for x in ("RA_ADD_1","RA_CITY","RA_STATE") if x in F] if v)},"officers":offs}
    print("matched so far",len(found),flush=True)
json.dump(found,open("fl_sunbiz.json","w"))
# --- apply
up=0
for k,rs in targets.items():
    if k not in found: continue
    f=found[k]; people=[o["name"] for o in f["officers"] if o["name"] and not re.search(r"\b(LLC|INC|CORP|TRUST|COMPANY|LP)\b",o["name"].upper())]
    for r in rs:
        r[C["reg"]]={"biz":f["biz"],"status":f["status"],"mail":f["mail"],"reg":f["filed"],"principals":[f"{o['name']} ({o['title']})" if o["title"] else o["name"] for o in f["officers"]][:6],"where":[],"agent":{"name":f["ra"]["name"],"type":"","phone":"","email":"","addr":f["ra"]["addr"]},"docnum":f["docnum"]}
        if people and "LLC" in r[C["conf"]]:
            r[C["owner"]]=(", ".join(people[:3])+" ("+r[C["grantee"]]+")")[:150]; r[C["conf"]]="FL Sunbiz officer(s)/manager(s) of the owner entity"; up+=1
print("FL rows upgraded",up)
json.dump(D,open("data.json","w"),separators=(",",":"))
json.dump({"cols":D["cols"],"rows":[r for r in D["rows"] if r[C["st"]]=="FL"],"pulled":D.get("pulled")},open("site/data/FL.json","w"),separators=(",",":"))
