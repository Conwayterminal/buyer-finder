#!/usr/bin/env python3
"""Actions job: every Florida commercial parcel, all 67 counties, from the DOR NAL rolls (owner of record + mailing,
use code, SF, units, year built, lot, just value, last two sales). Geocodes new addresses with the Census batch
geocoder (cached in fl_geo.json). Writes site/props/FL_<county>.json and site/data/FL.json (sales since 2020, any price).
Also applies Sunbiz officer resolution (fl_sunbiz.json) to LLC owners."""
import os, re, json, csv, io, glob, zipfile, time, urllib.parse, collections
import requests, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
B="https://floridarevenue.com/property/dataportal/_api/web/GetFolderByServerRelativeUrl('/property/dataportal/Documents/PTO%20Data%20Portal/Tax%20Roll%20Data%20Files/NAL')"
H={"User-Agent":"Mozilla/5.0","Accept":"application/json;odata=verbose"}
folders=[f["Name"] for f in requests.get(B+"/Folders?$select=Name",headers=H,timeout=60).json()["d"]["results"]]
folder=sorted(folders)[-1]; print("using roll",folder,flush=True)
files=requests.get(B.replace("/NAL')",f"/NAL/{folder}')")+"/Files?$select=Name,ServerRelativeUrl&$top=300",headers=H,timeout=60).json()["d"]["results"]
KEEP=set(["003","008"]+["%03d"%i for i in range(10,50)])
UC={"003":"Multifamily 10+ units","008":"Multifamily under 10 units","010":"Vacant land / development","011":"Retail","012":"Mixed-use","013":"Retail","014":"Retail","015":"Retail","016":"Retail","017":"Office","018":"Office","019":"Office","020":"Marina / airport","021":"Retail","022":"Retail","023":"Office","024":"Office","025":"Retail","026":"Retail","027":"Retail","028":"Garage / parking","029":"Industrial","030":"Retail","031":"Retail","032":"Retail","033":"Retail","034":"Retail","035":"Hotel","036":"Hotel","037":"Retail","038":"Golf / recreation","039":"Hotel","040":"Vacant land / development","041":"Industrial","042":"Industrial","043":"Industrial","044":"Industrial","045":"Industrial","046":"Industrial","047":"Industrial","048":"Warehouse","049":"Industrial"}
COLS=["CO_NO","PARCEL_ID","DOR_UC","JV","LND_SQFOOT","ACT_YR_BLT","TOT_LVG_AREA","NO_BULDNG","NO_RES_UNTS","QUAL_CD1","SALE_PRC1","SALE_YR1","SALE_MO1","OR_BOOK1","OR_PAGE1","CLERK_NO1","MULTI_PAR_SAL1","SALE_PRC2","SALE_YR2","SALE_MO2","QUAL_CD2","OWN_NAME","OWN_ADDR1","OWN_CITY","OWN_STATE","OWN_ZIPCD","PHY_ADDR1","PHY_CITY","PHY_ZIPCD","NBRHD_CD"]
geo=json.load(open("fl_geo.json")) if os.path.exists("fl_geo.json") else {}
sunbiz=json.load(open("fl_sunbiz.json")) if os.path.exists("fl_sunbiz.json") else {}
def norm(n):
    n=n.upper().replace("&"," AND "); n=re.sub(r"[^A-Z0-9 ]"," ",n); n=re.sub(r"\b(THE)\b","",n)
    n=re.sub(r"\bL L C\b|\bLLC\b|\bLIMITED LIABILITY (COMPANY|CO)\b","LLC",n); n=re.sub(r"\bINCORPORATED\b","INC",n); n=re.sub(r"\bCORPORATION\b","CORP",n)
    return re.sub(r"\s+"," ",n).strip()
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|CO\b|COMPANY|LLLP|LLP)\b",re.I)
def geocode_batch(items):
    body="\n".join(f'{k},"{a}","{c}",FL,{z}' for k,a,c,z in items)
    for attempt in range(3):
        try:
            r=requests.post("https://geocoding.geo.census.gov/geocoder/locations/addressbatch",files={"addressFile":("a.csv",body)},data={"benchmark":"Public_AR_Current"},timeout=900)
            for line in r.text.splitlines():
                p=next(csv.reader([line]))
                if len(p)>=6 and p[2]=="Match": lon,lat=p[5].split(","); geo[p[0]]=[round(float(lat),5),round(float(lon),5)]
            return
        except Exception as e: print("geo err",e,flush=True); time.sleep(10)
all_props={}; deals=[]; processed=set()
D=json.load(open("data.json")); ncols=len(D["cols"])
for f in files:
    name=f["Name"]; m=re.match(r"(.+?)(?: \d+)? Preliminary",name)
    if not m: continue
    county=m.group(1).strip()
    if os.path.exists(f"site/props/FL_{county.replace(' ','_')}.json") and os.environ.get("FL_FORCE")!="1":
        # already built this cycle; reuse its deals for the market file
        for p in json.load(open(f"site/props/FL_{county.replace(' ','_')}.json")):
            pass
        print("skip (exists)",county,flush=True); continue
    url="https://floridarevenue.com"+urllib.parse.quote(f["ServerRelativeUrl"])
    try: z=zipfile.ZipFile(io.BytesIO(requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=600).content))
    except Exception as e: print("skip",name,e,flush=True); continue
    csvn=[n for n in z.namelist() if n.lower().endswith(".csv")][0]
    df=pd.read_csv(z.open(csvn),usecols=lambda c:c in COLS,dtype=str,encoding="latin1",low_memory=False)
    df["DOR_UC"]=df.DOR_UC.astype(str).str.zfill(3); df=df[df.DOR_UC.isin(KEEP)]
    df["key"]=df.CO_NO.astype(str)+"_"+df.PARCEL_ID.astype(str)
    todo=[(k,str(a).replace('"',''),str(c or ""),str(zp or "")[:5]) for k,a,c,zp in zip(df.key,df.PHY_ADDR1,df.PHY_CITY,df.PHY_ZIPCD) if k not in geo and isinstance(a,str) and a.strip()]
    for i in range(0,len(todo),4000): geocode_batch(todo[i:i+4000])
    json.dump(geo,open("fl_geo.json","w"))
    cc=collections.defaultdict(list)
    for k,c in zip(df.key,df.PHY_CITY):
        if k in geo: cc[str(c or "").upper()].append(geo[k])
    import statistics
    cent={c:(statistics.median(x[0] for x in v),statistics.median(x[1] for x in v)) for c,v in cc.items() if v}
    P=[]
    for r in df.itertuples():
        ll=geo.get(r.key); ap=False
        if not ll:
            ll=cent.get(str(r.PHY_CITY or "").upper()); ap=True
            if not ll: continue
        own=str(r.OWN_NAME or "").strip().title(); k=norm(own); sb=sunbiz.get(k)
        people=[o["name"] for o in sb["officers"] if o["name"] and not re.search(r"\b(LLC|INC|CORP|TRUST|COMPANY|LP)\b",o["name"].upper())] if sb else []
        def num(x):
            try:
                v=float(x)
                return None if v!=v else v
            except Exception: return None
        sf=num(r.TOT_LVG_AREA); units=num(r.NO_RES_UNTS); yb=num(r.ACT_YR_BLT); lot=num(r.LND_SQFOOT); jv=num(r.JV)
        s1=(int(num(r.SALE_YR1) or 0),int(num(r.SALE_MO1) or 0),num(r.SALE_PRC1)); s2=(int(num(r.SALE_YR2) or 0),int(num(r.SALE_MO2) or 0),num(r.SALE_PRC2))
        sold=f"{s1[0]}-{max(1,s1[1]):02d}-01" if s1[0]>1900 else None
        mail=", ".join(v for v in [str(r.OWN_ADDR1 or "").strip().title(),str(r.OWN_CITY or "").strip().title(),str(r.OWN_STATE or "").strip()] if v and v.lower()!="nan")
        p={"id":r.key,"county":county,"town":str(r.PHY_CITY or "").strip().title() or county,"addr":str(r.PHY_ADDR1 or "").strip().title() or "Address not listed","zip":str(r.PHY_ZIPCD or "")[:5],"lat":ll[0],"lng":ll[1],"approx":ap,"type":UC[r.DOR_UC],"uc":r.DOR_UC,
           "owner":own[:100],"principals":people[:4],"mail":mail[:120],"llc":bool(ent.search(own)),"units":int(units) if units else None,"sf":int(sf) if sf else None,"yb":int(yb) if yb and yb>1600 else None,"lot":int(lot) if lot else None,"mkt":int(jv) if jv else None,
           "sold":sold,"price":int(s1[2]) if s1[2] else None,"q":(r.QUAL_CD1 if isinstance(r.QUAL_CD1,str) else ""),"prior":f"{s2[0]}-{max(1,s2[1]):02d}-01" if s2[0]>1900 else None,"priorP":int(s2[2]) if s2[2] else None,"doc":(f"OR {r.OR_BOOK1}/{r.OR_PAGE1}" if isinstance(r.OR_BOOK1,str) and r.OR_BOOK1.strip() else "")}
        P.append(p)
        for (yy,mm,pr) in (s1,s2):
            if yy>=2020 and pr and pr>0:
                dt=f"{yy}-{max(1,mm):02d}-01"
                if dt<"2020-09-01": continue
                disp=(", ".join(people[:3])+" ("+own+")")[:150] if people and p["llc"] else own[:150]
                conf=("FL Sunbiz officer(s)/manager(s) of the owner entity" if people and p["llc"] else ("Owner of record (county appraiser) - LLC, research" if p["llc"] else "Owner of record (county appraiser)"))+(" - location approximate" if ap else "")+(" - later resold; this is the prior sale" if (yy,mm,pr)==s2 else "")
                deals.append([dt,county+" County",p["town"],p["addr"],p["type"],r.DOR_UC,p["units"],p["sf"],int(pr),2 if str(r.MULTI_PAR_SAL1 or "").upper() in ("Y","1") else 1,ll[0],ll[1],own[:150],disp,conf,"",mail[:120],"",own[:80],p["yb"],"",p["lot"],p["doc"],None,None,None,"FL",str(r.PARCEL_ID),None,({"biz":sb["biz"],"status":sb["status"],"mail":sb["mail"],"reg":sb["filed"],"principals":[f"{o['name']} ({o['title']})" if o["title"] else o["name"] for o in sb["officers"]][:6],"where":[],"agent":{"name":sb["ra"]["name"],"type":"","phone":"","email":"","addr":sb["ra"]["addr"]}} if sb else None),None,p["mkt"]][:ncols])
    def clean(o):
        if isinstance(o,float) and o!=o: return None
        if isinstance(o,dict): return {k:clean(v) for k,v in o.items()}
        if isinstance(o,list): return [clean(v) for v in o]
        return o
    P=clean(P); deals[:]=clean(deals)
    json.dump(P,open(f"site/props/FL_{county.replace(' ','_')}.json","w"),separators=(",",":"),allow_nan=False); processed.add(county+" County")
    print(county,"parcels",len(P),"deals total",len(deals),flush=True)
try:
    old=json.load(open("site/data/FL.json"))["rows"]; ci=D["cols"].index("boro")
    deals=[r for r in old if r[ci] not in processed]+deals
except Exception: pass
json.dump({"cols":D["cols"],"rows":deals,"pulled":D.get("pulled")},open("site/data/FL.json","w"),separators=(",",":"))
json.dump(sorted({(p["county"],) for f in glob.glob("site/props/FL_*.json") if "counties" not in f for p in json.load(open(f))}),open("site/props/FL_counties.json","w"))
print("FL deals since 2020 (any price)",len(deals),flush=True)
