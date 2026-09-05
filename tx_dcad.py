import pandas as pd
a=pd.read_csv("ACCOUNT_INFO.CSV",dtype=str,usecols=["ACCOUNT_NUM","DIVISION_CD","BIZ_NAME","OWNER_NAME1","OWNER_NAME2","OWNER_ADDRESS_LINE1","OWNER_CITY","OWNER_STATE","OWNER_ZIPCODE","STREET_NUM","FULL_STREET_NAME","PROPERTY_CITY","PROPERTY_ZIPCODE","NBHD_CD","DEED_TXFR_DATE","PHONE_NUM"],encoding="latin1",on_bad_lines="skip")
print(len(a), a.DIVISION_CD.value_counts().to_dict())
a["dt"]=pd.to_datetime(a.DEED_TXFR_DATE,errors="coerce")
a=a[(a.DIVISION_CD=="COM")&(a.dt>="2020-09-01")]
v=pd.read_csv("ACCOUNT_APPRL_YEAR.CSV",dtype=str,usecols=["ACCOUNT_NUM","TOT_VAL","IMPR_VAL","LAND_VAL"],encoding="latin1",on_bad_lines="skip"); v["TOT_VAL"]=pd.to_numeric(v.TOT_VAL,errors="coerce")
c=pd.read_csv("COM_DETAIL.CSV",dtype=str,usecols=["ACCOUNT_NUM","BLDG_CLASS_DESC","YEAR_BUILT","GROSS_BLDG_AREA","NUM_UNITS","PROPERTY_NAME","MKT_VAL"],encoding="latin1",on_bad_lines="skip")
c["GROSS_BLDG_AREA"]=pd.to_numeric(c.GROSS_BLDG_AREA,errors="coerce"); c["NUM_UNITS"]=pd.to_numeric(c.NUM_UNITS,errors="coerce")
cg=c.groupby("ACCOUNT_NUM").agg(cls=("BLDG_CLASS_DESC","first"),yb=("YEAR_BUILT","first"),sf=("GROSS_BLDG_AREA","sum"),units=("NUM_UNITS","sum"),pname=("PROPERTY_NAME","first")).reset_index()
d=a.merge(v.drop_duplicates("ACCOUNT_NUM"),on="ACCOUNT_NUM",how="left").merge(cg,on="ACCOUNT_NUM",how="left")
d=d[d.TOT_VAL>=500000]; print("candidates",len(d)); print(d.cls.value_counts().head(20).to_dict()); print("with phone",d.PHONE_NUM.notna().sum())
d["site"]=(d.STREET_NUM.fillna("")+" "+d.FULL_STREET_NAME.fillna("")).str.strip()
d.to_pickle("dcad_comm.pkl")
