import pandas as pd, requests, csv, pickle, os, time, sys
src,keycol,addrcol,citycol,zipcol,out=sys.argv[1:7]
D=pd.read_pickle(src); have=pickle.load(open(out,"rb")) if os.path.exists(out) else {}
todo=D[~D[keycol].isin(have)&D[addrcol].notna()&(D[addrcol].str.strip()!="")]
print("to geocode",len(todo)); t0=time.time()
for i in range(0,len(todo),2000):
    if time.time()-t0>200: break
    ch=todo.iloc[i:i+2000]
    body="\n".join(f'{k},"{a}","{c}",TX,{z}' for k,a,c,z in zip(ch[keycol],ch[addrcol].str.replace('"',''),ch[citycol].fillna("").astype(str),ch[zipcol].fillna("").astype(str).str[:5]))
    try:
        r=requests.post("https://geocoding.geo.census.gov/geocoder/locations/addressbatch",files={"addressFile":("a.csv",body)},data={"benchmark":"Public_AR_Current"},timeout=600)
        n=0
        for line in r.text.splitlines():
            p=next(csv.reader([line]))
            if len(p)>=6 and p[2]=="Match": lon,lat=p[5].split(","); have[p[0]]=(round(float(lat),5),round(float(lon),5)); n+=1
        print("batch",i,"matched",n,flush=True)
    except Exception as e: print("err",e)
    pickle.dump(have,open(out,"wb"))
print("geocoded",len(have))
