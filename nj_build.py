import pandas as pd, pickle, json, re, numpy as np
s=pd.read_pickle("sr1a2.pkl"); c=pd.concat([pd.read_pickle("comp.pkl"),pd.DataFrame(pickle.load(open("pins_part.pkl","rb")))],ignore_index=True).drop_duplicates("PAMS_PIN")
have=set(c.PAMS_PIN); s["mpin"]=s.pins.map(lambda L: next((p for p in L if p in have),None))
s=s.merge(c,left_on="mpin",right_on="PAMS_PIN",how="left")
def d6(x):
    x=str(x or "").strip()
    if len(x)!=6 or not x.isdigit(): return None
    y=int(x[:2]); y=2000+y if y<50 else 1900+y
    try: return pd.Timestamp(year=y,month=int(x[2:4]),day=int(x[4:6]))
    except: return None
s["dt"]=s.deed.map(d6); s.loc[s.dt.isna(),"dt"]=s.rec.map(d6)
s=s[s.dt>="2020-09-01"]
s=s[~s.nu.isin(["01","02","03","04","05","06","09","10","11","12","13","14","15","17","18","19","20","21","22","23","24","25","26","27","28","29","30","31","33"]) | True]  # keep all, flag non-usable below
# municipality centroid fallback
mc=s[s.lat.notna()].groupby(s.cty+s.dist).agg(la=("lat","median"),ln=("lng","median"),mun=("MUN_NAME","first"),cnt=("COUNTY","first"))
def asset(r):
    txt=(str(r.BLDG_DESC or "")+" "+str(r.PROP_USE or "")+" "+str(r.FAC_NAME or "")+" "+str(r.addr or "")).upper()
    if r.pc=="4C": return "Walkup multifamily" if not re.search(r"HI.?RISE|ELEV|TOWER",txt) else "Elevator multifamily"
    if r.pc=="4B": return "Industrial"
    if r.pc=="1": return "Vacant land / development"
    if r.pc=="4A":
        if re.search(r"MIX|APT|RES",txt): return "Mixed-use"
        if re.search(r"HOTEL|MOTEL|INN\b",txt): return "Hotel"
        if re.search(r"OFF|MED|PROF",txt): return "Office"
        if re.search(r"WHSE|WAREHOUSE|INDUST|MFG",txt): return "Industrial"
        return "Retail"
    return None
rows=[]
for r in s.itertuples():
    a=asset(r)
    if not a: continue
    lat,lng=r.lat,r.lng; approx=False
    if pd.isna(lat):
        k=r.cty+r.dist
        if k not in mc.index: continue
        lat,lng=mc.loc[k,"la"],mc.loc[k,"ln"]; approx=True
    mun=str(r.MUN_NAME if isinstance(r.MUN_NAME,str) else (mc.loc[r.cty+r.dist,"mun"] if r.cty+r.dist in mc.index else "")).title()
    cty=str(r.COUNTY if isinstance(r.COUNTY,str) else (mc.loc[r.cty+r.dist,"cnt"] if r.cty+r.dist in mc.index else "")).title()
    same_sale = (str(r.DEED_DATE or "").strip()==r.deed) or (pd.notna(r.SALE_PRICE) and int(r.SALE_PRICE or 0)==r.price)
    mail=(str(r.ST_ADDRESS or "").strip()+", "+str(r.CITY_STATE or "").strip()).strip(", ").title() if same_sale and isinstance(r.ST_ADDRESS,str) else ""
    owner=("Undisclosed - mail to "+mail) if mail else "Undisclosed (NJ)"
    conf="NJ withholds names (Daniel's Law)"+(" - buyer mailing address from tax roll" if mail else "")+("" if not approx else " - location approximate")
    nuflag=" Non-usable sale code "+r.nu+"." if r.nu and r.nu!="00" else ""
    units=int(r.DWELL) if pd.notna(r.DWELL) and r.DWELL>0 and same_sale else None
    rows.append([r.dt.strftime("%Y-%m-%d"),cty+" County",mun,str(r.addr or "").title() or "Address not listed",a,r.pc,units,None,int(r.price),1+sum(1 for x in [r.etc] if x=="X"),round(float(lat),5),round(float(lng),5),"",owner[:150],conf+nuflag,"",mail[:120],"","",int(r.yb) if r.yb.isdigit() and int(r.yb)>1600 else None,"",int(float(r.CALC_ACRE)*43560) if pd.notna(r.CALC_ACRE) and r.CALC_ACRE>0 else None,r.pins[0].split("_")[0]+"/"+"/".join(r.pins[0].split("_")[1:3]),"","","","NJ"])
json.dump(rows,open("rows.json","w"),separators=(",",":"))
import collections; print(len(rows), collections.Counter(x[4] for x in rows).most_common(), "with mailing addr:",sum(1 for x in rows if x[16]))
