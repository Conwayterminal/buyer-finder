#!/usr/bin/env python3
"""Actions job: every commercial parcel in Harris (Houston) and Dallas counties from the appraisal districts, with owner,
mailing, deed-transfer date, appraised value, SF, units; geocoded via Census (cached tx_geo.json). Texas is non-disclosure:
no sale prices. Writes site/props/TX_<county>.json and site/data/TX.json (transfers since 2020, appraised value shown)."""
import os, re, json, csv, io, zipfile, time, subprocess, collections, statistics
import requests, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
geo=json.load(open("tx_geo.json")) if os.path.exists("tx_geo.json") else {}
def geocode(items):
    for i in range(0,len(items),4000):
        body="\n".join(f'{k},"{a}","{c}",TX,{z}' for k,a,c,z in items[i:i+4000])
        for attempt in range(3):
            try:
                r=requests.post("https://geocoding.geo.census.gov/geocoder/locations/addressbatch",files={"addressFile":("a.csv",body)},data={"benchmark":"Public_AR_Current"},timeout=900)
                for line in r.text.splitlines():
                    p=next(csv.reader([line]))
                    if len(p)>=6 and p[2]=="Match": lon,lat=p[5].split(","); geo[p[0]]=[round(float(lat),5),round(float(lon),5)]
                break
            except Exception as e: print("geo err",e,flush=True); time.sleep(10)
        json.dump(geo,open("tx_geo.json","w")); print("geocoded",len(geo),flush=True)
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|CO\b|COMPANY|LLLP|LLP)\b",re.I)
D=json.load(open("data.json")); ncols=len(D["cols"])
deals=[]
def emit(county,P):
    json.dump(P,open(f"site/props/TX_{county.replace(' ','_')}.json","w"),separators=(",",":"),allow_nan=False); print(county,"props",len(P),flush=True)
    for p in P:
        if p["sold"] and p["sold"]>="2020-09-01":
            deals.append([p["sold"],county+" County",p["town"],p["addr"],p["type"],p["cls"],p["units"],p["sf"],None,1,p["lat"],p["lng"],p["owner"][:150],p["owner"][:150],("Owner of record ("+county+" CAD) - LLC, research" if p["llc"] else "Owner of record ("+county+" CAD)")+" - price not disclosed (TX)"+(" - location approximate" if p.get("approx") else ""),"",p["mail"],"",p.get("pname",""),p["yb"],"",p["lot"],p["id"],None,None,None,"TX",None,None,None,None,p["mkt"]][:ncols])
# ---------- Harris ----------
url="https://download.hcad.org/data/CAMA/2026/Real_acct_owner.zip"
subprocess.run(["curl","-sSL","-A","Mozilla/5.0","-o","/tmp/hcad.zip",url],check=True)
with zipfile.ZipFile("/tmp/hcad.zip") as z: z.extract("real_acct.txt","/tmp")
use=["acct","mailto","mail_addr_1","mail_city","mail_state","mail_zip","site_addr_1","site_addr_2","site_addr_3","state_class","Market_Area_1_Dscr","yr_impr","bld_ar","land_ar","tot_mkt_val","new_own_dt","econ_bld_class"]
d=pd.read_csv("/tmp/real_acct.txt",sep="\t",usecols=use,dtype=str,encoding="latin1",quoting=3,on_bad_lines="skip",engine="c")
d["sc"]=d.state_class.str.strip(); d=d[d.sc.str[0].isin(list("BFCG"))&~d.sc.isin(["C1"])|d.sc.isin(["C1"])]  # keep vacant too
d=d[d.sc.str[0].isin(list("BFCG"))]
print("Harris commercial parcels",len(d),flush=True)
d["key"]="H"+d.acct.str.strip()
todo=[(k,str(a).replace('"',''),str(c or ""),str(zp or "")[:5]) for k,a,c,zp in zip(d.key,d.site_addr_1,d.site_addr_2,d.site_addr_3) if k not in geo and isinstance(a,str) and a.strip() and not a.strip().startswith("0 ")]
geocode(todo)
SC={"F1":"Retail / commercial","F2":"Industrial","B1":"Multifamily 5+ units","B2":"Multifamily 2-4 units","B3":"Multifamily 5+ units","B4":"Multifamily 5+ units","C1":"Vacant land / development","C2":"Vacant land / development","C3":"Vacant land / development","G1":"Industrial"}
cc=collections.defaultdict(list)
for k,c in zip(d.key,d.Market_Area_1_Dscr):
    if k in geo: cc[str(c)].append(geo[k])
cent={c:(statistics.median(x[0] for x in v),statistics.median(x[1] for x in v)) for c,v in cc.items() if len(v)>=5}
P=[]
for r in d.itertuples():
    ll=geo.get(r.key); ap=False
    if not ll: ll=cent.get(str(r.Market_Area_1_Dscr)); ap=True
    if not ll: continue
    def num(x):
        try: v=float(x); return None if v!=v else v
        except Exception: return None
    dt=None
    if isinstance(r.new_own_dt,str) and re.match(r"\d{2}/\d{2}/\d{4}",r.new_own_dt.strip()): m,dd,y=r.new_own_dt.strip().split("/"); dt=f"{y}-{m}-{dd}"
    own=re.sub(r"\s+"," ",str(r.mailto or "")).strip().title()
    P.append({"id":"HCAD "+r.acct.strip(),"county":"Harris","town":str(r.Market_Area_1_Dscr or "").strip().title() or "Houston","addr":str(r.site_addr_1 or "").strip().title(),"zip":str(r.site_addr_3 or "")[:5],"lat":ll[0],"lng":ll[1],"approx":ap,"type":SC.get(r.sc,"Retail / commercial"),"cls":r.sc,"owner":own[:100],"llc":bool(ent.search(own)),
       "mail":", ".join(v for v in [str(r.mail_addr_1 or "").strip().title(),str(r.mail_city or "").strip().title(),str(r.mail_state or "").strip()] if v and v!="Nan")[:120],"units":None,"sf":int(num(r.bld_ar)) if num(r.bld_ar) else None,"lot":int(num(r.land_ar)) if num(r.land_ar) else None,"yb":int(num(r.yr_impr)) if num(r.yr_impr) and num(r.yr_impr)>1700 else None,"mkt":int(num(r.tot_mkt_val)) if num(r.tot_mkt_val) else None,"sold":dt,"price":None})
emit("Harris",P); del d,P
# ---------- Dallas ----------
subprocess.run(["curl","-sSL","-A","Mozilla/5.0","-o","/tmp/dcad.zip","https://www.dallascad.org/ViewPDFs.aspx?type=3&id=%5C%5CDCAD.ORG%5CWEB%5CWEBDATA%5CWEBFORMS%5CDATA%20PRODUCTS%5CDCAD2026_CURRENT.ZIP"],check=True)
with zipfile.ZipFile("/tmp/dcad.zip") as z:
    for n in ["ACCOUNT_INFO.CSV","ACCOUNT_APPRL_YEAR.CSV","COM_DETAIL.CSV"]: z.extract(n,"/tmp")
a=pd.read_csv("/tmp/ACCOUNT_INFO.CSV",dtype=str,usecols=["ACCOUNT_NUM","DIVISION_CD","OWNER_NAME1","OWNER_NAME2","OWNER_ADDRESS_LINE1","OWNER_CITY","OWNER_STATE","STREET_NUM","FULL_STREET_NAME","PROPERTY_CITY","PROPERTY_ZIPCODE","DEED_TXFR_DATE"],encoding="latin1",on_bad_lines="skip")
a=a[a.DIVISION_CD=="COM"]
v=pd.read_csv("/tmp/ACCOUNT_APPRL_YEAR.CSV",dtype=str,usecols=["ACCOUNT_NUM","TOT_VAL"],encoding="latin1",on_bad_lines="skip").drop_duplicates("ACCOUNT_NUM")
c=pd.read_csv("/tmp/COM_DETAIL.CSV",dtype=str,usecols=["ACCOUNT_NUM","BLDG_CLASS_DESC","YEAR_BUILT","GROSS_BLDG_AREA","NUM_UNITS","PROPERTY_NAME"],encoding="latin1",on_bad_lines="skip")
c["GROSS_BLDG_AREA"]=pd.to_numeric(c.GROSS_BLDG_AREA,errors="coerce"); c["NUM_UNITS"]=pd.to_numeric(c.NUM_UNITS,errors="coerce")
cg=c.groupby("ACCOUNT_NUM").agg(cls=("BLDG_CLASS_DESC","first"),yb=("YEAR_BUILT","first"),sf=("GROSS_BLDG_AREA","sum"),units=("NUM_UNITS","sum"),pname=("PROPERTY_NAME","first")).reset_index()
d=a.merge(v,on="ACCOUNT_NUM",how="left").merge(cg,on="ACCOUNT_NUM",how="left"); print("Dallas commercial accounts",len(d),flush=True)
d["site"]=(d.STREET_NUM.fillna("")+" "+d.FULL_STREET_NAME.fillna("")).str.strip(); d["key"]="D"+d.ACCOUNT_NUM.str.strip()
geocode([(k,str(s).replace('"',''),str(ci or ""),str(zp or "")[:5]) for k,s,ci,zp in zip(d.key,d.site,d.PROPERTY_CITY,d.PROPERTY_ZIPCODE) if k not in geo and isinstance(s,str) and s.strip()])
def dcls(x):
    x=str(x or "").upper()
    if "APARTMENT" in x or "MULTI" in x: return "Multifamily 5+ units"
    if "LAND" in x: return "Vacant land / development"
    if "WAREHOUSE" in x or "INDUSTRIAL" in x or "MANUFACT" in x: return "Industrial"
    if "OFFICE" in x: return "Office"
    if "HOTEL" in x or "MOTEL" in x: return "Hotel"
    if "GARAGE" in x or "PARKING" in x: return "Garage / parking"
    return "Retail / commercial" if x else "Other"
cc=collections.defaultdict(list)
for k,ci in zip(d.key,d.PROPERTY_CITY):
    if k in geo: cc[str(ci)].append(geo[k])
cent={c2:(statistics.median(x[0] for x in vv),statistics.median(x[1] for x in vv)) for c2,vv in cc.items() if len(vv)>=5}
P=[]
for r in d.itertuples():
    ll=geo.get(r.key); ap=False
    if not ll: ll=cent.get(str(r.PROPERTY_CITY)); ap=True
    if not ll: continue
    own=(str(r.OWNER_NAME1 or "").strip()+((" & "+str(r.OWNER_NAME2).strip()) if isinstance(r.OWNER_NAME2,str) and r.OWNER_NAME2.strip() else "")).title()
    dt=str(r.DEED_TXFR_DATE or "")[:10] if isinstance(r.DEED_TXFR_DATE,str) and re.match(r"\d{4}-\d{2}-\d{2}",str(r.DEED_TXFR_DATE)) else None
    tv=pd.to_numeric(r.TOT_VAL,errors="coerce")
    P.append({"id":"DCAD "+r.ACCOUNT_NUM.strip(),"county":"Dallas","town":str(r.PROPERTY_CITY or "").strip().title() or "Dallas","addr":r.site.title(),"zip":str(r.PROPERTY_ZIPCODE or "")[:5],"lat":ll[0],"lng":ll[1],"approx":ap,"type":dcls(r.cls),"cls":str(r.cls or "")[:40],"owner":own[:100],"llc":bool(ent.search(own)),
       "mail":", ".join(v2 for v2 in [str(r.OWNER_ADDRESS_LINE1 or "").strip().title(),str(r.OWNER_CITY or "").strip().title(),str(r.OWNER_STATE or "").strip()] if v2 and v2!="Nan")[:120],"units":int(r.units) if pd.notna(r.units) and r.units>0 else None,"sf":int(r.sf) if pd.notna(r.sf) and r.sf>0 else None,"lot":None,"yb":int(float(r.yb)) if isinstance(r.yb,str) and r.yb.replace(".","").isdigit() and float(r.yb)>1700 else None,"pname":str(r.pname or "").title() if isinstance(r.pname,str) else "","mkt":int(tv) if pd.notna(tv) else None,"sold":dt,"price":None})
emit("Dallas",P)
json.dump({"cols":D["cols"],"rows":deals,"pulled":D.get("pulled")},open("site/data/TX.json","w"),separators=(",",":"))
print("TX transfers since 2020",len(deals),flush=True)
