import requests, json, time, pandas as pd
U="https://services3.arcgis.com/3FL1kr7L4LvwA2Kb/arcgis/rest/services/Connecticut_CAMA_and_Parcel_Layer/FeatureServer/0/query"
F="Town_Name,Location,Property_City,ZIP_CODE,Owner,Co_Owner,Mailing_Address,Mailing_City,Mailing_State,Mailing_Zip,Sale_Price,Sale_Date,Prior_Sale_Date,Prior_Sale_Price,State_Use,State_Use_Description,Model,Living_Area,Effective_Area,Land_Acres,Zone,AYB,Assessed_Total,Appraised_Building,Appraised_Land,Occupancy,Parcel_ID,Link"
import os,pickle
rows=pickle.load(open("ct_cama_part.pkl","rb")) if os.path.exists("ct_cama_part.pkl") else [];off=len(rows);t0=time.time()
while True:
    for a in range(5):
        try:
            r=requests.get(U,params={"where":"Sale_Price>=500000","outFields":F,"f":"json","returnGeometry":"false","returnCentroid":"true","outSR":"4326","resultOffset":off,"resultRecordCount":2000,"orderByFields":"OBJECTID"},timeout=120).json()
            if "features" in r: break
        except Exception: time.sleep(3)
    fs=r.get("features",[])
    for f in fs:
        a=f["attributes"]; c=f.get("centroid") or {}; a["lat"]=c.get("y"); a["lng"]=c.get("x"); rows.append(a)
    off+=len(fs); print(off,flush=True)
    if time.time()-t0>240: pickle.dump(rows,open("ct_cama_part.pkl","wb")); print("checkpoint"); raise SystemExit
    if len(fs)<2000 or not r.get("exceededTransferLimit",True): break
pd.DataFrame(rows).to_pickle("ct_cama.pkl"); print("done",len(rows))
