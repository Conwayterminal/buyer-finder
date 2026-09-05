import requests, pandas as pd, time, pickle, os
W="starts_with(bldgclass,'C') OR starts_with(bldgclass,'D') OR starts_with(bldgclass,'S') OR starts_with(bldgclass,'K') OR starts_with(bldgclass,'O') OR starts_with(bldgclass,'E') OR starts_with(bldgclass,'F') OR starts_with(bldgclass,'G') OR starts_with(bldgclass,'H') OR starts_with(bldgclass,'L') OR starts_with(bldgclass,'V') OR starts_with(bldgclass,'I') OR starts_with(bldgclass,'M') OR starts_with(bldgclass,'W') OR starts_with(bldgclass,'Z')"
S="bbl,borough,block,lot,address,zipcode,cd,council,latitude,longitude,bldgclass,landuse,ownertype,ownername,lotarea,bldgarea,comarea,resarea,officearea,retailarea,garagearea,strgearea,factryarea,otherarea,numbldgs,numfloors,unitsres,unitstotal,lotfront,lotdepth,bldgfront,bldgdepth,assessland,assesstot,exempttot,yearbuilt,yearalter1,yearalter2,zonedist1,zonedist2,overlay1,spdist1,ltdheight,builtfar,residfar,commfar,facilfar,histdist,landmark,condono,sanitboro,zonemap,plutomapid,appbbl,appdate"
rows=pickle.load(open("pluto_part.pkl","rb")) if os.path.exists("pluto_part.pkl") else []; off=len(rows); t0=time.time()
while time.time()-t0<240:
    try: r=requests.get("https://data.cityofnewyork.us/resource/64uk-42ks.json",params={"$where":W,"$select":S,"$limit":50000,"$offset":off,"$order":"bbl"},timeout=180)
    except Exception as e: print("err",e); time.sleep(3); continue
    if r.status_code!=200: print(r.status_code,r.text[:200]); time.sleep(3); continue
    j=r.json(); rows+=j; off+=len(j); print(off,flush=True)
    if len(j)<50000: pd.DataFrame(rows).to_pickle("pluto_all.pkl"); print("DONE",len(rows)); break
pickle.dump(rows,open("pluto_part.pkl","wb"))
