#!/usr/bin/env python3
"""King County (Seattle): every commercial parcel (assessor PropType C) from the assessor extracts — mailing/attn (names
withheld in the bulk file), present use, zoning, lot SF, commercial building SF/year, apartment units — plus every sale since
2020 with buyer and seller names and price. Coordinates from the county GIS parcel-address service."""
import os, io, csv, re, json, zipfile, time, collections, subprocess, requests
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
B="https://aqua.kingcounty.gov/extranet/assessor/"
def get(name):
    p="/tmp/"+name.replace(" ","_")
    if not os.path.exists(p): subprocess.run(["curl","-sSL","-A","Mozilla/5.0","-o",p,B+name.replace(" ","%20")],check=True)
    z=zipfile.ZipFile(p); n=[x for x in z.namelist() if x.lower().endswith(".csv")][0]
    return csv.DictReader(io.TextIOWrapper(z.open(n),encoding="latin1"))
acct={}
for r in get("Real Property Account.zip"):
    k=r["Major"].strip()+r["Minor"].strip()
    acct[k]={"mail":", ".join(v for v in [r["AttnLine"].strip().title(),r["AddrLine"].strip().title(),r["CityState"].strip().title()] if v),"attn":r["AttnLine"].strip().title(),"val":int(float(r["ApprLandVal"] or 0)+float(r["ApprImpsVal"] or 0))}
print("accounts",len(acct),flush=True)
com=collections.defaultdict(lambda:{"sf":0,"yb":None,"stories":None,"units":0,"name":""})
for r in get("Commercial Building.zip"):
    k=r["Major"].strip()+r["Minor"].strip(); c=com[k]; c["sf"]+=int(float(r.get("BldgGrossSqFt") or 0)); c["yb"]=c["yb"] or int(r.get("YrBuilt") or 0) or None; c["stories"]=r.get("NbrStories") or c["stories"]; c["name"]=c["name"] or r.get("BldgDescr","").strip().title()
for r in get("Apartment Complex.zip"):
    k=r["Major"].strip()+r["Minor"].strip(); c=com[k]; c["units"]+=int(float(r.get("NbrUnits") or 0)); c["yb"]=c["yb"] or int(r.get("YrBuilt") or 0) or None; c["stories"]=r.get("NbrStories") or c["stories"]; c["name"]=c["name"] or r.get("ComplexDescr","").strip().title()
print("buildings",len(com),flush=True)
# coordinates
geo={}; off=0
U="https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/PARCEL_ADDRESS_PUB_AREA_3069/FeatureServer/0/query"
while True:
    try: j=requests.post(U,data={"where":"1=1","outFields":"PIN,LAT,LON,ADDR_FULL,CTYNAME,ZIP5","returnGeometry":"false","resultOffset":off,"resultRecordCount":2000,"orderByFields":"OBJECTID","f":"json"},timeout=180).json()
    except Exception as e: print("err",e,flush=True); time.sleep(5); continue
    if "error" in j: print(j["error"],flush=True); time.sleep(5); continue
    fs=j.get("features",[])
    for f in fs:
        a=f["attributes"]
        if a.get("LAT") and a.get("PIN"): geo[a["PIN"]]=(a["LAT"],a["LON"],a.get("ADDR_FULL") or "",a.get("CTYNAME") or "",a.get("ZIP5") or "")
    off+=len(fs)
    if off%50000<2000: print("geo",off,flush=True)
    if len(fs)<2000: break
print("coordinates",len(geo),flush=True)
USE={"1":"Vacant land / development","118":"Vacant land / development","102":"Retail / commercial","104":"Office","105":"Office","106":"Office","108":"Retail / commercial","110":"Retail / commercial","111":"Retail / commercial","114":"Retail / commercial","118":"Vacant land / development","119":"Vacant land / development","120":"Multifamily 5+ units","121":"Multifamily 5+ units","122":"Multifamily 5+ units","123":"Multifamily 5+ units","124":"Multifamily 5+ units","125":"Multifamily 5+ units","126":"Multifamily 5+ units","127":"Multifamily 5+ units","128":"Hotel","129":"Hotel","130":"Industrial","131":"Industrial","132":"Industrial","133":"Industrial","134":"Industrial","136":"Industrial","137":"Industrial","138":"Industrial","139":"Industrial","140":"Retail / commercial","141":"Retail / commercial","142":"Retail / commercial","143":"Retail / commercial","144":"Retail / commercial","145":"Retail / commercial","146":"Retail / commercial","147":"Retail / commercial","148":"Retail / commercial","149":"Retail / commercial","150":"Garage / parking","151":"Garage / parking","152":"Garage / parking","153":"Garage / parking","154":"Retail / commercial","155":"Retail / commercial","156":"Retail / commercial","157":"Retail / commercial","158":"Retail / commercial","159":"Retail / commercial","160":"Retail / commercial","161":"Retail / commercial","162":"Retail / commercial","163":"Retail / commercial","164":"Retail / commercial","165":"Retail / commercial","166":"Retail / commercial","167":"Retail / commercial","168":"Retail / commercial","170":"Retail / commercial","171":"Retail / commercial","172":"Retail / commercial","173":"Retail / commercial","174":"Retail / commercial","175":"Retail / commercial","176":"Retail / commercial","177":"Retail / commercial","178":"Retail / commercial","179":"Retail / commercial","180":"Retail / commercial","183":"Retail / commercial","184":"Retail / commercial","185":"Retail / commercial","186":"Retail / commercial","187":"Retail / commercial","188":"Retail / commercial","189":"Retail / commercial","190":"Retail / commercial","191":"Retail / commercial","192":"Retail / commercial","193":"Retail / commercial","194":"Retail / commercial","195":"Retail / commercial","196":"Retail / commercial","197":"Retail / commercial","198":"Retail / commercial","199":"Retail / commercial"}
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|CO\b|COMPANY|LLP|BANK)\b",re.I)
props=[]; bypin={}
for r in get("Parcel.zip"):
    if r["PropType"].strip()!="C": continue
    k=r["Major"].strip()+r["Minor"].strip(); g=geo.get(k)
    if not g: continue
    a=acct.get(k,{}); c=com.get(k,{})
    p={"id":k,"county":"King","town":(g[3] or "Seattle").title(),"addr":(g[2] or "").title() or "Address not listed","zip":str(g[4] or "")[:5],"lat":round(g[0],5),"lng":round(g[1],5),"type":USE.get(r["PresentUse"].strip(),"Retail / commercial"),"uc":r["PresentUse"].strip(),"ucd":"",
       "owner":a.get("attn") or "Taxpayer name withheld in bulk file","mail":a.get("mail",""),"llc":True,"units":c.get("units") or None,"sf":c.get("sf") or None,"stories":c.get("stories"),"yb":c.get("yb"),"lot":int(float(r["SqFtLot"] or 0)) or None,"zone":r["CurrentZoning"].strip(),"mkt":a.get("val"),"pname":c.get("name",""),"sold":None,"price":None}
    props.append(p); bypin[k]=p
print("props",len(props),flush=True)
D=json.load(open("data.json")); n=len(D["cols"]); deals=[]
for r in get("Real Property Sales.zip"):
    k=r["Major"].strip()+r["Minor"].strip(); p=bypin.get(k)
    if not p: continue
    try: price=int(float(r["SalePrice"] or 0))
    except Exception: price=0
    d=r["DocumentDate"].strip()
    try: m,dd,y=d.split("/"); dt=f"{y}-{int(m):02d}-{int(dd):02d}"
    except Exception: continue
    if dt<"2020-09-01" or dt>"2026-12-31" or price<=0: continue
    buyer=r["BuyerName"].strip().title(); seller=r["SellerName"].strip().title()
    if not p["sold"] or dt>p["sold"]: p["sold"]=dt; p["price"]=price; p["buyer"]=buyer; p["owner"]=buyer or p["owner"]; p["llc"]=bool(ent.search(buyer))
    deals.append([dt,"King County",p["town"],p["addr"],p["type"],p["uc"],p["units"],p["sf"],price,1,p["lat"],p["lng"],buyer[:150],buyer[:150],"Deed buyer (King County excise affidavit)"+(" - LLC, research" if ent.search(buyer) else ""),seller[:120],p["mail"],"","",p["yb"],p["zone"],p["lot"],"Excise "+r["ExciseTaxNbr"],None,None,None,"WA",None,None,None,None,p["mkt"]][:n])
os.makedirs("site/props",exist_ok=True)
json.dump(props,open("site/props/WA_King.json","w"),separators=(",",":"),allow_nan=False)
json.dump({"cols":D["cols"],"rows":deals,"pulled":time.strftime("%Y-%m-%d")},open("site/data/WA.json","w"),separators=(",",":"))
reg=json.load(open("site/props/states.json")); reg["WA"]={"name":"Washington (King County)","areaLabel":"County","areas":["King"],"props":len(props),"deals":len(deals),"note":"King County (Seattle): use, zoning, lot, building SF/units/year, values, taxpayer mailing (names withheld in the bulk file), and every sale since 2020 with buyer and seller names and price."}
json.dump(reg,open("site/props/states.json","w"),indent=0)
print("WA props",len(props),"deals",len(deals),flush=True)
