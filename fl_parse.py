import pandas as pd, zipfile, glob, io, re
COLS=["CO_NO","PARCEL_ID","DOR_UC","JV","LND_SQFOOT","ACT_YR_BLT","TOT_LVG_AREA","NO_BULDNG","NO_RES_UNTS","QUAL_CD1","SALE_PRC1","SALE_YR1","SALE_MO1","OR_BOOK1","OR_PAGE1","CLERK_NO1","MULTI_PAR_SAL1","SALE_PRC2","SALE_YR2","SALE_MO2","QUAL_CD2","OWN_NAME","OWN_ADDR1","OWN_ADDR2","OWN_CITY","OWN_STATE","OWN_ZIPCD","PHY_ADDR1","PHY_ADDR2","PHY_CITY","PHY_ZIPCD","NBRHD_CD","MKT_AR"]
KEEP=set(["003","008"]+["%03d"%i for i in range(10,50)]+["070","071","072","073","074","075","076","077","078","079"]+["080","081","082","083","084","085","086","087","088","089","090","091"])
# 003 multifam 10+, 008 multifam <10, 010-039 commercial, 040-049 industrial, 070-079 institutional, 080s government (drop), 090 leasehold
KEEP-= set(["080","081","082","083","084","085","086","087","088","089","090","091"])
out=[]
for z in sorted(glob.glob("nal/*.zip")):
    with zipfile.ZipFile(z) as zf:
        name=[n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        df=pd.read_csv(zf.open(name),usecols=lambda c:c in COLS,dtype=str,encoding="latin1",low_memory=False)
    df["SALE_PRC1"]=pd.to_numeric(df.SALE_PRC1,errors="coerce"); df["SALE_YR1"]=pd.to_numeric(df.SALE_YR1,errors="coerce")
    df["DOR_UC"]=df.DOR_UC.astype(str).str.zfill(3)
    d=df[(df.SALE_PRC1>=500000)&(df.SALE_YR1>=2020)&df.DOR_UC.isin(KEEP)]
    out.append(d); print(z.split("/")[1].split(" ")[0],len(df),"->",len(d),flush=True)
D=pd.concat(out,ignore_index=True); D.to_pickle("nal_comm.pkl"); print("TOTAL",len(D))
