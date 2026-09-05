import requests, pandas as pd, time, pickle, os
U="https://services1.arcgis.com/hGdibHYSPO59RG1h/arcgis/rest/services/Massachusetts_Property_Tax_Parcels/FeatureServer/0/query"
F="OBJECTID,LOC_ID,TOWN_ID,PROP_ID,BLDG_VAL,LAND_VAL,TOTAL_VAL,FY,LOT_SIZE,LS_DATE,LS_PRICE,USE_CODE,USE_DESC,SITE_ADDR,CITY,ZIP,OWNER1,OWN_ADDR,OWN_CITY,OWN_STATE,OWN_ZIP,OWN_CO,LS_BOOK,LS_PAGE,ZONING,YEAR_BUILT,BLD_AREA,UNITS,RES_AREA,STYLE,STORIES"
W="USE_CODE LIKE '3%' OR USE_CODE LIKE '4%' OR USE_CODE IN ('111','112','013','031','109','130','131','132')"
st=pickle.load(open("part.pkl","rb")) if os.path.exists("part.pkl") else {"off":0,"rows":[]}
st["last"]=max([r.get("OBJECTID",0) for r in st["rows"]] or [0]) if st["rows"] else st.get("last",0)
print("resuming from OBJECTID",st["last"],"rows",len(st["rows"]))
t0=time.time()
while time.time()-t0<240:
    try: r=requests.post(U,data={"where":"("+W+") AND OBJECTID>"+str(st["last"]),"outFields":F,"returnGeometry":"false","returnCentroid":"true","outSR":"4326","resultRecordCount":2000,"orderByFields":"OBJECTID","f":"json"},timeout=120).json()
    except Exception as e: print("err",e); time.sleep(3); continue
    if "error" in r: print(r["error"]); time.sleep(3); continue
    fs=r.get("features",[])
    for f in fs:
        a=f["attributes"]; c=f.get("centroid") or {}; a["lat"]=c.get("y"); a["lng"]=c.get("x"); st["rows"].append(a)
    st["off"]+=len(fs)
    if fs: st["last"]=max(f["attributes"]["OBJECTID"] for f in fs)
    if len(fs)<2000: pickle.dump(st,open("part.pkl","wb")); pd.DataFrame(st["rows"]).to_pickle("ma.pkl"); print("DONE",len(st["rows"])); raise SystemExit
pickle.dump(st,open("part.pkl","wb")); print("checkpoint",len(st["rows"]))
