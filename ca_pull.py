import requests, json, time, pickle, os
U="https://public.gis.lacounty.gov/public/rest/services/LACounty_Cache/LACounty_Parcel/MapServer/0/query"
F="AIN,SitusFullAddress,SitusCity,SitusZIP,UseType,UseDescription,YearBuilt1,Units1,SQFTmain1,Units2,SQFTmain2,Roll_LandValue,Roll_ImpValue,Roll_LandBaseYear,Roll_ImpBaseYear,CENTER_LAT,CENTER_LON"
W=["Roll_LandBaseYear IN ('2020','2021','2022','2023','2024','2025','2026') AND UseType IN ('Commercial','Industrial') AND Roll_LandValue+Roll_ImpValue>=500000","Roll_LandBaseYear IN ('2020','2021','2022','2023','2024','2025','2026') AND UseType='Residential' AND Units1>=5 AND Roll_LandValue+Roll_ImpValue>=500000"]
st=pickle.load(open("la_part.pkl","rb")) if os.path.exists("la_part.pkl") else {"i":0,"off":0,"rows":[]}
t0=time.time()
while st["i"]<len(W) and time.time()-t0<230:
    try:
        r=requests.post(U,data={"where":W[st["i"]],"outFields":F,"returnGeometry":"false","resultOffset":st["off"],"resultRecordCount":1000,"orderByFields":"OBJECTID","f":"json"},timeout=120).json()
    except Exception as e: print("err",e); time.sleep(3); continue
    fs=r.get("features",[])
    if "error" in r: print(r["error"]); time.sleep(3); continue
    st["rows"]+=[f["attributes"] for f in fs]; st["off"]+=len(fs)
    if len(fs)<1000: st["i"]+=1; st["off"]=0
pickle.dump(st,open("la_part.pkl","wb")); print("query",st["i"],"offset",st["off"],"rows",len(st["rows"]))
