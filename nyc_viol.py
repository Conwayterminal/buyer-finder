import requests, pandas as pd, time
def grp(ds,sel,where,group,name):
    rows=[];off=0
    while True:
        for a in range(4):
            try:
                r=requests.get(f"https://data.cityofnewyork.us/resource/{ds}.json",params={"$select":sel,"$where":where,"$group":group,"$limit":50000,"$offset":off,"$order":group.split(",")[0]},timeout=300)
                if r.status_code==200: break
                print(name,r.status_code,r.text[:200]); time.sleep(3)
            except Exception as e: print("err",e); time.sleep(3)
        j=r.json(); rows+=j; off+=len(j); print(name,off,flush=True)
        if len(j)<50000: break
    df=pd.DataFrame(rows); df.to_pickle(f"{name}.pkl"); return df
grp("wvxf-dwi5","bbl,count(*) as n,max(inspectiondate) as last","violationstatus='Open'","bbl","hpd_open")
grp("3h2n-5cm9","boro,block,lot,count(*) as n","violation_category like '%ACTIVE%'","boro,block,lot","dob_active")
grp("6bgk-3dad","boro,block,lot,count(*) as n,sum(balance_due) as due","ecb_violation_status='ACTIVE'","boro,block,lot","ecb_active")
