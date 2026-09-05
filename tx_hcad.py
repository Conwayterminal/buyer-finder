import pandas as pd, csv, sys
csv.field_size_limit(10**9)
use=["acct","mailto","mail_addr_1","mail_city","mail_state","mail_zip","site_addr_1","site_addr_2","site_addr_3","state_class","Neighborhood_Code","Market_Area_1_Dscr","yr_impr","bld_ar","land_ar","tot_mkt_val","tot_appr_val","new_own_dt","lgl_1","econ_bld_class"]
d=pd.read_csv("real_acct.txt",sep="\t",usecols=use,dtype=str,encoding="latin1",quoting=3,on_bad_lines="skip",engine="c")
print(len(d)); d["sc"]=d.state_class.str.strip()
print(d.sc.value_counts().head(25).to_dict())
d["dt"]=pd.to_datetime(d.new_own_dt,errors="coerce",format="%m/%d/%Y"); d["mkt"]=pd.to_numeric(d.tot_mkt_val,errors="coerce")
k=d[(d.dt>="2020-09-01")&(d.mkt>=500000)&d.sc.str[0].isin(list("BFCGJ"))]
print("candidates",len(k)); print(k.sc.value_counts().head(15).to_dict())
k.to_pickle("hcad_comm.pkl")
