import pandas as pd, requests, io, time, os, pickle
D=pd.read_pickle("nal_comm.pkl")
D["SALE_MO1"]=pd.to_numeric(D.SALE_MO1,errors="coerce").fillna(6)
D=D[~((D.SALE_YR1==2020)&(D.SALE_MO1<9))].copy()
D["key"]=D.CO_NO.astype(str)+"_"+D.PARCEL_ID.astype(str)
D.to_pickle("nal_comm2.pkl"); print(len(D))
have=pickle.load(open("geo_part.pkl","rb")) if os.path.exists("geo_part.pkl") else {}
todo=D[~D.key.isin(have)&D.PHY_ADDR1.notna()&(D.PHY_ADDR1.str.strip()!="")]
print("to geocode",len(todo))
t0=time.time()
for i in range(0,len(todo),5000):
    if time.time()-t0>200: break
    ch=todo.iloc[i:i+5000]
    csv="\n".join(f'{k},"{a}","{c}",FL,{z}' for k,a,c,z in zip(ch.key,ch.PHY_ADDR1.str.replace('"',''),ch.PHY_CITY.fillna(""),ch.PHY_ZIPCD.fillna("").astype(str).str[:5]))
    try:
        r=requests.post("https://geocoding.geo.census.gov/geocoder/locations/addressbatch",files={"addressFile":("a.csv",csv)},data={"benchmark":"Public_AR_Current"},timeout=600)
        n=0
        for line in r.text.splitlines():
            p=next(__import__("csv").reader([line]))
            if len(p)>=6 and p[2]=="Match":
                lon,lat=p[5].split(","); have[p[0]]=(round(float(lat),5),round(float(lon),5)); n+=1
        print("batch",i,"matched",n,flush=True)
    except Exception as e: print("err",e)
    pickle.dump(have,open("geo_part.pkl","wb"))
print("geocoded",len(have))
