import pandas as pd, pickle, json, re
D=pd.read_pickle("nal_comm2.pkl"); geo=pickle.load(open("geo_part.pkl","rb"))
cmap={}
for l in open("nal_urls.txt"):
    n=l.strip().split("/")[-1]; m=re.match(r"(.+?) (\d+) Preliminary",n)
    if m: cmap[int(m.group(2))]=m.group(1)
UC={"003":"Multifamily 10+ units","008":"Multifamily under 10 units","010":"Vacant land / development","011":"Retail","012":"Mixed-use","013":"Retail","014":"Retail","015":"Retail","016":"Retail","017":"Office","018":"Office","019":"Office","020":"Marina / airport","021":"Retail","022":"Retail","023":"Office","024":"Office","025":"Retail","026":"Retail","027":"Retail","028":"Garage / parking","029":"Industrial","030":"Retail","031":"Retail","032":"Retail","033":"Retail","034":"Retail","035":"Hotel","036":"Hotel","037":"Retail","038":"Golf / recreation","039":"Hotel","040":"Vacant land / development","041":"Industrial","042":"Industrial","043":"Industrial","044":"Industrial","045":"Industrial","046":"Industrial","047":"Industrial","048":"Warehouse","049":"Industrial"}
D=D[D.DOR_UC.isin(UC)]
D["lat"]=D.key.map(lambda k:geo.get(k,(None,None))[0]); D["lng"]=D.key.map(lambda k:geo.get(k,(None,None))[1])
cc=D[D.lat.notna()].groupby(D.PHY_CITY.fillna("").str.upper()).agg(la=("lat","median"),ln=("lng","median"))
def shell(n): return bool(re.search(r"\b(LLC|L\.?L\.?C|LP|LTD|CORP|INC|TRUST|TR\b|ASSOC|PARTNERS|HOLDINGS|REALTY|PROPERTIES|GROUP|CO\b|COMPANY|LLLP|LLP)",str(n).upper()))
rows=[];approx=0
for r in D.itertuples():
    lat,lng=r.lat,r.lng; ap=False
    if pd.isna(lat):
        k=str(r.PHY_CITY or "").upper()
        if k not in cc.index: continue
        lat,lng=cc.loc[k,"la"],cc.loc[k,"ln"]; ap=True; approx+=1
    own=str(r.OWN_NAME or "").strip().title()
    mail=", ".join(v for v in [str(r.OWN_ADDR1 or "").strip().title(),str(r.OWN_CITY or "").strip().title(),str(r.OWN_STATE or "").strip(),str(r.OWN_ZIPCD or "")[:5]] if v and v.lower()!="nan")
    conf=("Owner of record (county appraiser) - LLC, research" if shell(own) else "Owner of record (county appraiser)")+(" - location approximate" if ap else "")
    q=str(r.QUAL_CD1 or "").strip(); conf+= "" if q in ("01","02","1","2","Q","") else f" - sale qualification code {q} (may not be arm's length)"
    dt=f"{int(r.SALE_YR1)}-{int(r.SALE_MO1):02d}-01"
    addr=str(r.PHY_ADDR1 or "").strip().title() or "Address not listed"
    sf=int(float(r.TOT_LVG_AREA)) if pd.notna(r.TOT_LVG_AREA) and str(r.TOT_LVG_AREA).replace(".","").isdigit() and float(r.TOT_LVG_AREA)>0 else None
    units=int(float(r.NO_RES_UNTS)) if pd.notna(r.NO_RES_UNTS) and str(r.NO_RES_UNTS).replace(".","").isdigit() and float(r.NO_RES_UNTS)>0 else None
    yb=int(float(r.ACT_YR_BLT)) if pd.notna(r.ACT_YR_BLT) and str(r.ACT_YR_BLT).replace(".","").isdigit() and float(r.ACT_YR_BLT)>1600 else None
    lot=int(float(r.LND_SQFOOT)) if pd.notna(r.LND_SQFOOT) and str(r.LND_SQFOOT).replace(".","").isdigit() else None
    nl=2 if str(r.MULTI_PAR_SAL1 or "").strip().upper() in ("Y","1") else 1
    doc=(f"OR {r.OR_BOOK1}/{r.OR_PAGE1}" if pd.notna(r.OR_BOOK1) and str(r.OR_BOOK1).strip() else "")+(f" clerk {r.CLERK_NO1}" if pd.notna(r.CLERK_NO1) and str(r.CLERK_NO1).strip() else "")
    rows.append([dt,cmap.get(int(r.CO_NO),str(r.CO_NO))+" County",str(r.PHY_CITY or "").strip().title() or cmap.get(int(r.CO_NO),""),addr,UC[r.DOR_UC],r.DOR_UC,units,sf,int(r.SALE_PRC1),nl,round(float(lat),5),round(float(lng),5),own[:150],own[:150],conf,"",mail[:120],"",own[:80],yb,"",lot,doc.strip(),None,None,None,"FL",str(r.PARCEL_ID),None,None])
json.dump(rows,open("rows.json","w"),separators=(",",":"))
import collections; print(len(rows),"approx loc",approx); print(collections.Counter(x[4] for x in rows).most_common())
