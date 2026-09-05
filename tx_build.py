import pandas as pd, pickle, json, re
rows=[]
ent=lambda n: bool(re.search(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|COMPANY|LLLP|LLP|CO)\b",str(n).upper()))
# Harris
h=pd.read_pickle("hcad_comm.pkl"); g=pickle.load(open("hcad_geo.pkl","rb"))
SC={"F1":"Retail / commercial","F2":"Industrial","B1":"Multifamily 5+ units","B2":"Multifamily 2-4 units","B3":"Multifamily 5+ units","B4":"Multifamily 5+ units","C1":"Vacant land / development","C2":"Vacant land / development","C3":"Vacant land / development","G1":"Industrial","J2":"Utility","J3":"Utility","J4":"Utility"}
def owner_of(n):
    n=re.sub(r"\s+"," ",str(n or "")).strip().title(); return n
for r in h.itertuples():
    ll=g.get(r.acct); 
    if not ll: continue
    own=owner_of(r.mailto); sf=pd.to_numeric(r.bld_ar,errors="coerce"); land=pd.to_numeric(r.land_ar,errors="coerce")
    a=SC.get(r.sc,"Other"); 
    if r.sc=="F1":
        t=str(r.econ_bld_class or "")
    mail=", ".join(v for v in [str(r.mail_addr_1 or "").strip().title(),str(r.mail_city or "").strip().title(),str(r.mail_state or "").strip()] if v)
    conf=("Owner of record (Harris CAD) - LLC, research" if ent(own) else "Owner of record (Harris CAD)")+" - price not disclosed (TX)"
    rows.append([r.dt.strftime("%Y-%m-%d"),"Harris County",str(r.Market_Area_1_Dscr or "").strip().title() or "Houston",str(r.site_addr_1 or "").strip().title(),a,r.sc,None,int(sf) if pd.notna(sf) and sf>0 else None,None,1,ll[0],ll[1],own[:150],own[:150],conf,"",mail[:120],"",own[:80],int(r.yr_impr) if str(r.yr_impr).isdigit() and int(r.yr_impr)>1700 else None,"",int(land) if pd.notna(land) else None,"HCAD "+r.acct.strip(),None,None,None,"TX",None,None,None,None,int(r.mkt)])
nh=len(rows)
# Dallas
d=pd.read_pickle("dcad_comm.pkl"); g=pickle.load(open("dcad_geo.pkl","rb"))
def cls(c):
    c=str(c or "").upper()
    if "APARTMENT" in c or "MULTI" in c: return "Multifamily 5+ units"
    if "LAND" in c: return "Vacant land / development"
    if "WAREHOUSE" in c or "INDUSTRIAL" in c or "MANUFACT" in c: return "Industrial"
    if "OFFICE" in c: return "Office"
    if "HOTEL" in c or "MOTEL" in c: return "Hotel"
    if "GARAGE" in c or "PARKING" in c: return "Garage / parking"
    if c=="": return "Other"
    return "Retail / commercial"
for r in d.itertuples():
    ll=g.get(r.ACCOUNT_NUM)
    if not ll: continue
    own=owner_of(r.OWNER_NAME1)+(" & "+owner_of(r.OWNER_NAME2) if isinstance(r.OWNER_NAME2,str) and r.OWNER_NAME2.strip() else "")
    mail=", ".join(v for v in [str(r.OWNER_ADDRESS_LINE1 or "").strip().title(),str(r.OWNER_CITY or "").strip().title(),str(r.OWNER_STATE or "").strip()] if v and v!="Nan")
    conf=("Owner of record (Dallas CAD) - LLC, research" if ent(own) else "Owner of record (Dallas CAD)")+" - price not disclosed (TX)"
    rows.append([r.dt.strftime("%Y-%m-%d"),"Dallas County",str(r.PROPERTY_CITY or "").strip().title() or "Dallas",r.site.title(),cls(r.cls),str(r.cls or "")[:40],int(r.units) if pd.notna(r.units) and r.units>0 else None,int(r.sf) if pd.notna(r.sf) and r.sf>0 else None,None,1,ll[0],ll[1],own[:150],own[:150],conf,"",mail[:120],"",str(r.pname or "").title()[:80] if isinstance(r.pname,str) else "",int(float(r.yb)) if str(r.yb).replace(".","").isdigit() and float(r.yb)>1700 else None,"",None,"DCAD "+r.ACCOUNT_NUM,None,None,None,"TX",None,None,None,None,int(r.TOT_VAL)])
print("Harris",nh,"Dallas",len(rows)-nh)
json.dump(rows,open("rows.json","w"),separators=(",",":"))
