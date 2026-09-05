#!/usr/bin/env python3
"""Daily: read PincusCo's public transfers feed and add today's reported sales (with PincusCo's true-owner names)
to data.json, tagged 'PincusCo report'. ACRIS backfill (update.py) replaces them once the deed is in Open Data."""
import requests, re, json, html, time, os, sys
from datetime import date
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
UA={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15","Accept":"text/html"}
D=json.load(open("data.json")); C={k:i for i,k in enumerate(D["cols"])}
seen=set(r[C["doc"]] for r in D["rows"]); seen_addr=set((r[C["addr"]].upper(),r[C["price"]]) for r in D["rows"])
BORO={"Manhattan":"Manhattan","Brooklyn":"Brooklyn","Queens":"Queens","Bronx":"Bronx"}
AC={"C":"Walkup multifamily","D":"Elevator multifamily","S":"Mixed-use","K":"Retail","O":"Office","E":"Warehouse","F":"Industrial","G":"Garage / parking","V":"Vacant land / development","H":"Hotel","L":"Loft","M":"Religious","I":"Health / institutional","W":"Education","Z":"Misc","B":"Small residential (1-3 family)","A":"Small residential (1-3 family)"}
def money(s):
    m=re.search(r"\$([\d.,]+)\s*(million|billion|M|B)?",s,re.I)
    if not m: return None
    v=float(m.group(1).replace(",","")); u=(m.group(2) or "").lower()
    return int(v*1e9) if u.startswith("b") else int(v*1e6) if u.startswith("m") else int(v)
def geocode(addr,boro):
    try:
        r=requests.get("https://nominatim.openstreetmap.org/search",params={"format":"jsonv2","limit":1,"q":f"{addr}, {boro}, New York, NY"},headers={"User-Agent":"ConwayBuyerFinder/1.0 (justin@conwaypropertyadvisors.com)"},timeout=30).json()
        time.sleep(1.1)
        if r: return round(float(r[0]["lat"]),5),round(float(r[0]["lon"]),5)
    except Exception: pass
    return None,None
pages=int(sys.argv[1]) if len(sys.argv)>1 else 1
added=0
for p in range(1,pages+1):
    url="https://www.pincusco.com/transfers/"+(f"page/{p}/" if p>1 else "")
    t=requests.get(url,headers=UA,timeout=60).text
    items=re.findall(r'<h3[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>\s*</h3>(.*?)(?=<h3|PREVIOUS|$)',t,re.S)
    for link,title,body in items:
        title=html.unescape(re.sub("<.*?>","",title)).strip(); body=html.unescape(re.sub("<.*?>"," ",body))
        if "Sale" not in body[:200] or link in seen: continue
        ex=re.search(r"(?:\d{1,2}/\d{1,2}/\d{4}[^\n]*?)\s+(.*?)(?:Continue reading|$)",body,re.S)
        text=(ex.group(1) if ex else "")+" "+title
        if any(k in title for k in ["takes title","Fannie Mae","foreclosure auction"]): continue
        buyer=re.split(r"\s+(?:pays|paid|through the entity|, partners|acquires|buys)\b",title)[0].strip()
        if re.search(r"\b(sells|sold|sale of)\b",buyer,re.I) or " for $" in buyer:
            mb=re.search(r"^\s*(?:UPDATED[^:]*:\s*)?(.*?)\s+(?:through the entity|paid)\b",ex.group(1) if ex else "",re.S)
            buyer=mb.group(1).strip() if mb and len(mb.group(1))<80 else ""
            if not buyer: continue
        if not buyer or buyer.lower().startswith(("$","nyc pre")): continue
        price=money(title) or money(text)
        if not price or price<500000: continue
        m=re.search(r"\bat\s+([\d][\w\-]*\s+[A-Z][^,]*?)\s+in\s+([A-Z][\w\s.'-]+?),\s+(Manhattan|Brooklyn|Queens|Bronx)\b",text)
        if m: addr,nbhd,boro=m.group(1).strip(),m.group(2).strip(),m.group(3)
        else:
            m2=re.search(r"\bin\s+([A-Z][\w\s.'-]+?)(?:,\s*(Manhattan|Brooklyn|Queens|Bronx))?\s*$",title)
            if not m2: continue
            nbhd=m2.group(1).strip(); boro=m2.group(2) or ""
            addr=""
        if boro not in BORO: continue
        if (addr.upper(),price) in seen_addr and addr: continue
        units=re.search(r"(\d+)-unit",text); sf=re.search(r"([\d,]+)\s+square feet of built space",text) or re.search(r"([\d,]+)\s+square-foot",text)
        bc=re.search(r"\(([A-Z]\d)\)",text); bc=bc.group(1) if bc else ""
        asset=AC.get(bc[:1],"") or ("Vacant land / development" if "dev site" in title else "Mixed-use" if "mixed-use" in title else "Walkup multifamily" if "walkup" in title else "Retail" if "retail" in title else "Industrial" if "industrial" in title else "Elevator multifamily" if "rental" in title else "Other")
        seller=re.search(r"paid \$[\d.,]+ (?:million|billion)? ?to (.*?)(?: through| for)",text); seller=seller.group(1).strip() if seller else ""
        use=re.search(r"expected use is ([^.]+)\.",text); note=("Expected use: "+use.group(1)+". " if use else "")+"Reported by PincusCo; deed not yet in Open Data."
        lat,lng=geocode(addr,boro) if addr else (None,None)
        if lat is None:
            # neighborhood centroid from existing rows
            pts=[(r[C["lat"]],r[C["lng"]]) for r in D["rows"] if r[C["nbhd"]].lower()==nbhd.lower() and r[C["boro"]]==boro]
            if not pts: continue
            lat=round(sorted(p[0] for p in pts)[len(pts)//2],5); lng=round(sorted(p[1] for p in pts)[len(pts)//2],5)
        d=re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})",body); dt=f"{d.group(3)}-{int(d.group(1)):02d}-{int(d.group(2)):02d}" if d else date.today().isoformat()
        cl=re.search(r"deal closed on ([A-Z][a-z]+ \d{1,2}, \d{4})",text)
        if cl:
            from datetime import datetime
            try: dt=datetime.strptime(cl.group(1),"%B %d, %Y").strftime("%Y-%m-%d")
            except Exception: pass
        D["rows"].append([dt,boro,nbhd,addr or nbhd+" (address pending)",asset,bc,int(units.group(1)) if units else None,int(sf.group(1).replace(",","")) if sf else None,price,1,lat,lng,"",buyer,"PincusCo report (true owner as reported)",seller,"","","",None,"",None,link,None,None,None,"NY"])
        seen.add(link); added+=1
        print("+",dt,buyer,"|",addr or nbhd,"|",price)
D["pulled"]=date.today().isoformat()
json.dump(D,open("data.json","w"),separators=(",",":"))
h=open("template.html").read().replace("__COLS__",json.dumps(D["cols"]))
os.makedirs("site",exist_ok=True); open("site/index.html","w").write(h); open("Conway_Buyer_Finder.html","w").write(h)
print("added",added,"rows",len(D["rows"]))
for st in sorted(set(r[-1] for r in D["rows"])):
    json.dump({"cols":D["cols"],"rows":[r for r in D["rows"] if r[-1]==st],"pulled":D["pulled"]},open(f"site/data/{st}.json","w"),separators=(",",":"))
