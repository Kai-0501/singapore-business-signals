"""Independent numerical and information-boundary verification of frozen outputs."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import analyse as a
v,_,_=a.read_series('fsi_current','Total')
r,_,_=a.read_series('bes_revenue_current','Food & Beverage Services',True)
b,_,_=a.read_series('bes_outlook_current','Food & Beverage Services',True)
vis,_,_=a.read_series('visitors_current','Total International Visitor Arrivals By Place Of Residence')
f=a.make_frame(v,r,b,vis); comparisons=[]
for t in map(lambda s:pd.Period(s,'M'),['2016-01','2024-07','2026-06']):
 for m in a.MODELS:
  tr=f.loc[:t-5];cols=a.features(m,'primary')
  scaler=StandardScaler();X=scaler.fit_transform(tr[cols].to_numpy());model=Ridge(alpha=100).fit(X,tr.actual)
  independent=float(model.predict(scaler.transform(f.loc[[t],cols].to_numpy()))[0]);pred=a.fit_predict(f,t,m,100)['prediction']
  delta=abs(pred-independent);assert delta<1e-10
  comparisons.append({'issue':str(t),'model':m,'absolute_difference':delta})
t=pd.Period('2024-07','M');v2=v.copy();vis2=vis.copy();r2=r.copy();b2=b.copy()
v2.loc[v2.index>t-2]*=1.7;vis2.loc[vis2.index>t-3]+=123456
for q in r2.index:
 if q.asfreq('M','end')+2>t:r2.loc[q]+=50;b2.loc[q]-=50
f2=a.make_frame(v2,r2,b2,vis2)
for m in a.MODELS:assert abs(a.fit_predict(f,t,m,100)['prediction']-a.fit_predict(f2,t,m,100)['prediction'])<1e-10
p=pd.read_csv(a.OUT/'test_predictions.csv');assert p.groupby('model').size().eq(24).all()
assert len({tuple(g.issue_month) for _,g in p.groupby('model')})==1
assert not f[a.features('C','primary')+['actual']].isna().any().any()
for _,row in p.iterrows():
 issue=pd.Period(row.issue_month,'M');last=pd.Period(row.train_last_issue,'M')
 assert last+3<=issue-2
 expected=sum(100*(v[issue+j]/v[issue+j-12]-1) for j in (1,2,3))/3
 assert abs(expected-row.actual)<1e-10
 raw=a.fit_predict(f,issue,row.model,100);assert abs(raw['prediction']-row.prediction)<1e-10
hashes=[]
for meta in sorted(a.RAW.glob('*_download.json')):
 d=json.loads(meta.read_text());raw=meta.with_name(meta.name.replace('_download.json','.json'))
 if raw.exists() and d.get('sha256'):
  assert hashlib.sha256(raw.read_bytes()).hexdigest()==d['sha256'],str(raw)
  hashes.append(raw.name)
result={'sklearn_comparisons':comparisons,'future_data_perturbation_passed':True,'identical_test_origins':True,'target_and_feature_missing_count':0,'all_72_primary_predictions_reproduced':True,'raw_hashes_verified':len(hashes),'limitations':'Checks establish computation and imposed lag discipline, not historical release-date or vintage authenticity.'}
(a.OUT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
