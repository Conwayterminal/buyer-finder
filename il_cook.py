#!/usr/bin/env python3
"""Cook County (Chicago) from the Assessor's open data: every commercial/industrial/7+ unit/vacant parcel (taxpayer mailing
name as owner of record, class, lat/lon, mailing) + every sale since 2020 with buyer and seller names and price."""
import requests, json, os, re, time, collections
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
W="(starts_with(class,'3') OR starts_with(class,'5') OR starts_with(class,'6') OR starts_with(class,'7') OR starts_with(class,'8') OR starts_with(class,'9') OR starts_with(class,'1'))"
def soda(ds,params):
    rows=[];off=0
    while True:
        p=dict(params); p.update({"$limit":50000,"$offset":off})
        for a in range(5):
            try:
                r=requests.get(f"https://datacatalog.cookcountyil.gov/resource/{ds}.json",params=p,timeout=300); j=r.json()
                if isinstance(j,list): break
                print(j,flush=True)
            except Exception as e: print("err",e,flush=True)
            time.sleep(5)
        rows+=j; off+=len(j); print(ds,off,flush=True)
        if len(j)<50000: break
    return rows
yr=soda("tx2p-k2g9",{"$select":"max(year)"})[0]["max_year"]
P=soda("tx2p-k2g9",{"$select":"pin,class,lat,lon,prop_address_full,prop_address_city_name,mail_address_name,mail_address_full,mail_address_city_name,mail_address_state,township_name,cook_municipality_name,nbhd_code","$where":f"year='{yr}' AND {W}","$order":"pin"})
G={r["pin"]:(r["lat"],r["lon"]) for r in soda("pabr-t5kh",{"$select":"pin,lat,lon","$where":f"lat IS NOT NULL AND {W}","$order":"pin"}) if r.get("lat")}
print("coordinates",len(G),flush=True)
for r in P:
    if not r.get("lat") and r["pin"] in G: r["lat"],r["lon"]=G[r["pin"]]
S=soda("wvhk-k5uv",{"$select":"pin,class,sale_date,sale_price,buyer_name,seller_name,deed_type,is_multisale,num_parcels_sale","$where":f"sale_date>='2020-09-01' AND {W}","$order":"sale_date"})
CL={"1":"Vacant land / development","3":"Multifamily 7+ units","5":"Retail / commercial","6":"Industrial","7":"Retail / commercial","8":"Industrial","9":"Multifamily 7+ units"}
def cl(c):
    c=str(c or "")
    if c.startswith("5"):
        if c in ("517","518","519","520","521","522","523","524","525","526","527","528","529","530","531","532","533","534","535","536","537","538","539","540","541","542","543","544","545","546","547","548","549","550","551","552","553","554","555","556","557","558","559","560","561","562","563","564","565","566","567","568","569","570","571","572","573","574","575","576","577","578","579","580","581","582","583","584","585","586","587","588","589","590","591","592","593","594","595","596","597","598","599"): pass
    return CL.get(c[:1],"Retail / commercial")
ent=re.compile(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|CO\b|COMPANY|LLP|BANK)\b",re.I)
props=[]; bypin={}
for r in P:
    if not r.get("lat"): continue
    own=str(r.get("mail_address_name") or "").strip().title()
    p={"id":r["pin"],"county":"Cook","town":str(r.get("cook_municipality_name") or r.get("prop_address_city_name") or "Chicago").title(),"addr":str(r.get("prop_address_full") or "").title() or "Address not listed","zip":"","lat":round(float(r["lat"]),5),"lng":round(float(r["lon"]),5),"type":cl(r["class"]),"uc":r["class"],"ucd":"Class "+str(r["class"]),
       "owner":own[:100] or "Taxpayer name not listed","mail":", ".join(v for v in [str(r.get("mail_address_full") or "").title(),str(r.get("mail_address_city_name") or "").title(),str(r.get("mail_address_state") or "")] if v)[:120],"llc":bool(ent.search(own)),"nbhd":r.get("nbhd_code"),"sold":None,"price":None}
    props.append(p); bypin[r["pin"]]=p
D=json.load(open("data.json")); n=len(D["cols"]); deals=[]
for s in S:
    p=bypin.get(s["pin"])
    if not p: continue
    try: price=int(float(s.get("sale_price") or 0))
    except Exception: price=0
    if price<=0: continue
    dt=s["sale_date"][:10]; buyer=str(s.get("buyer_name") or "").strip().title(); seller=str(s.get("seller_name") or "").strip().title()
    if not p["sold"] or dt>p["sold"]: p["sold"]=dt; p["price"]=price; p["buyer"]=buyer
    conf="Deed buyer (Cook County Assessor sales)"+(" - LLC, research" if ent.search(buyer) else "")+(" - multi-parcel sale" if str(s.get("is_multisale"))=="true" else "")
    deals.append([dt,"Cook County",p["town"],p["addr"],p["type"],p["uc"],None,None,price,int(float(s.get("num_parcels_sale") or 1)),p["lat"],p["lng"],buyer[:150],buyer[:150] or p["owner"],conf,seller[:120],p["mail"],"",p["owner"][:80],None,"",None,"Doc "+str(s.get("doc_no") or ""),None,None,None,"IL",None,None,None,None,None][:n])
os.makedirs("site/props",exist_ok=True)
json.dump(props,open("site/props/IL_Cook.json","w"),separators=(",",":"),allow_nan=False)
json.dump({"cols":D["cols"],"rows":deals,"pulled":time.strftime("%Y-%m-%d")},open("site/data/IL.json","w"),separators=(",",":"))
reg=json.load(open("site/props/states.json")); reg["IL"]={"name":"Illinois (Cook County)","areaLabel":"County","areas":["Cook"],"props":len(props),"deals":len(deals),"note":"Cook County (Chicago): taxpayer of record, mailing, class, and every deed since 2020 with buyer and seller names and price."}
json.dump(reg,open("site/props/states.json","w"),indent=0)
print("IL props",len(props),"deals",len(deals),flush=True)
