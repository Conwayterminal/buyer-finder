import requests, pandas as pd, time, pickle, os
U="https://services2.arcgis.com/XVOqAjTOJ5P6ngMu/arcgis/rest/services/Parcels_Composite_NJ_WM/FeatureServer/0/query"
F="PAMS_PIN,PCL_MUN,PCLBLOCK,PCLLOT,PCLQCODE,PROP_CLASS,COUNTY,MUN_NAME,PROP_LOC,ST_ADDRESS,CITY_STATE,BLDG_DESC,LAND_DESC,CALC_ACRE,PROP_USE,BLDG_CLASS,DEED_DATE,YR_CONSTR,SALES_CODE,SALE_PRICE,DWELL,COMM_DWELL,NET_VALUE,FAC_NAME"
rows=pickle.load(open("comp_part.pkl","rb")) if os.path.exists("comp_part.pkl") else []; off=len(rows); t0=time.time()
while time.time()-t0<240:
    try:
        r=requests.get(U,params={"where":"SALE_PRICE>=500000 AND PROP_CLASS IN ('4A','4B','4C','1','3A','15C')","outFields":F,"f":"json","returnGeometry":"false","returnCentroid":"true","outSR":"4326","resultOffset":off,"resultRecordCount":2000,"orderByFields":"OBJECTID"},timeout=120).json()
    except Exception: time.sleep(3); continue
    fs=r.get("features",[])
    for f in fs:
        a=f["attributes"]; c=f.get("centroid") or {}; a["lat"]=c.get("y"); a["lng"]=c.get("x"); rows.append(a)
    off+=len(fs)
    if len(fs)<2000: pickle.dump(rows,open("comp_part.pkl","wb")); pd.DataFrame(rows).to_pickle("comp.pkl"); print("done",len(rows)); raise SystemExit
pickle.dump(rows,open("comp_part.pkl","wb")); print("checkpoint",len(rows))
