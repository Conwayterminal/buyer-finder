import requests, pandas as pd, time, pickle, os
S="parid,boro,block,lot,owner,bldg_class,curtaxclass,fintaxclass,units,bld_story,lot_frt,lot_dep,bld_frt,bld_dep,land_area,gross_sqft,residential_area_gross,retail_area_gross,office_area_gross,curmkttot,curmktland,curacttot,curactland,curtxbtot,curactextot,finmkttot,finacttot,fintxbtot,yrbuilt,yralt1,zoning,zip_code,housenum_lo,street_name,coop_apts,num_bldgs"
rows=pickle.load(open("dof_part.pkl","rb")) if os.path.exists("dof_part.pkl") else []; off=len(rows); t0=time.time()
W="year='2027' AND period='3' AND curtaxclass in('2','2A','2B','2C','4','1D','3')"
while time.time()-t0<240:
    try: r=requests.get("https://data.cityofnewyork.us/resource/8y4t-faws.json",params={"$where":W,"$select":S,"$limit":50000,"$offset":off,"$order":"parid"},timeout=180)
    except Exception as e: print("err",e); time.sleep(3); continue
    if r.status_code!=200: print(r.status_code,r.text[:300]); time.sleep(3); continue
    j=r.json(); rows+=j; off+=len(j); print(off,flush=True)
    if len(j)<50000: pd.DataFrame(rows).to_pickle("dof_roll.pkl"); print("DONE",len(rows)); break
pickle.dump(rows,open("dof_part.pkl","wb"))
