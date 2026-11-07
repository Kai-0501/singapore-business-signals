"""Study 01. Reproduce the frozen-vintage experiment, not a real-time vintage backtest.

Run --stage validate BEFORE --stage final. The latter consumes locked penalties.
All modelling is local computation in the hosted runtime; no private data are used.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / 'raw', ROOT / 'output'
TRAIN_START = pd.Period('2010-01', 'M')
VALID = pd.period_range('2016-01', '2024-02', freq='M')
TEST = pd.period_range('2024-07', '2026-06', freq='M')
ALPHAS = [0.1, 1., 10., 100.]
MODELS = ['A', 'B', 'C']
SEED = 20261106

def save_json(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False, default=str))

def read_series(name, row_name, quarterly=False):
    data = json.loads((RAW / (name + '.json')).read_text())['Data']
    row = next(r for r in data['row'] if r['rowText'] == row_name)
    dates, vals = [], []
    for c in row['columns']:
        if quarterly:
            year, quarter = re.fullmatch(r'(\d{4}) (\d)Q', c['key']).groups()
            date = pd.Period(f'{year}Q{quarter}', 'Q-DEC')
        else:
            date = pd.Period(pd.to_datetime(c['key'], format='%Y %b'), 'M')
        dates.append(date)
        vals.append(pd.to_numeric(c['value'], errors='coerce'))
    s = pd.Series(vals, index=pd.PeriodIndex(dates), name=name).sort_index()
    assert s.index.is_unique and not s.isna().any()
    assert len(s) == len(pd.period_range(s.index.min(), s.index.max(), freq=s.index.freq))
    return s.astype(float), data, row

def old_fsi():
    result = json.loads((RAW / 'fsi_2017.json').read_text())['result']
    row = next(r for r in result['records'] if r['DataSeries'] == 'Total')
    d = {pd.Period(pd.to_datetime(k, format='%Y%b'), 'M'): float(v)
         for k,v in row.items() if re.fullmatch(r'\d{4}[A-Za-z]{3}', k)}
    return pd.Series(d).sort_index()

def prepare():
    v, vm, vr = read_series('fsi_current', 'Total')
    r, rm, rr = read_series('bes_revenue_current', 'Food & Beverage Services', True)
    b, bm, br = read_series('bes_outlook_current', 'Food & Beverage Services', True)
    a, am, ar = read_series('visitors_current', 'Total International Visitor Arrivals By Place Of Residence')
    sa, sam, sar = read_series('visitors_sa_current', 'Total International Visitor Arrivals By Place Of Residence')
    assert (v > 0).all() and (a >= 0).all()
    mirror = json.loads((RAW / 'visitors.json').read_text())['result']['records'][0]
    mirror = pd.Series({pd.Period(pd.to_datetime(k, format='%Y%b'), 'M'): float(val)
                       for k,val in mirror.items() if re.fullmatch(r'\d{4}[A-Za-z]{3}', k)})
    delta = a.reindex(mirror.index)-mirror
    # Require near identity to the NSA mirror, and distinctness from the explicit SA table.
    assert (delta.abs() <= 50).all() and (delta == 0).mean() > .95
    assert not np.allclose(a, sa)
    quality = {'volume_n':len(v),'expectations_n':len(r),'visitor_n':len(a),
               'missing_selected_series':0,'visitor_mirror_common_months':len(delta),
               'visitor_mirror_exact_matches':int((delta==0).sum()),
               'visitor_mirror_max_abs_difference':float(delta.abs().max()),
               'visitor_mirror_differences':{str(k):float(val) for k,val in delta[delta!=0].items()},
               'visitor_adjustment_resolution':'M550001 matches unadjusted official mirror except small vintage revisions; differs from separate SA M550002. Retain original inconsistent adjustmentType metadata.',
               'api_total_row_complete':True}
    save_json('data_quality.json',quality)
    raw_monthly = pd.DataFrame({'fsi_volume_2025base':v,'arrivals_nsa':a,'fsi_volume_2017base':old_fsi()})
    raw_monthly.index.name='month'
    raw_monthly.to_csv(OUT/'monthly_data.csv')
    quarters = pd.DataFrame({'bes_revenue_pp':r,'bes_outlook_pp':b})
    quarters.index.name='database_quarter'
    quarters['forecast_quarter']=[str(q+1) for q in quarters.index]
    quarters['assumed_eligible_date']=[str((q.asfreq('M','end')+2).start_time.date().replace(day=15)) for q in quarters.index]
    quarters['actual_release_date']=''
    quarters.loc[pd.Period('2026Q2'),'actual_release_date']='2026-07-31'
    quarters.loc[pd.Period('2026Q3'),'actual_release_date']='2026-11-02'
    quarters.to_csv(OUT/'quarterly_data.csv')
    return v,r,b,a

def make_frame(v,r,b,a,variant='primary'):
    sales_lag=3 if variant=='stricter_lags' else 2
    tourism_lag=4 if variant=='stricter_lags' else 3
    survey_extra=1 if variant=='stricter_lags' else (3 if variant=='stale_survey' else 0)
    survey = b if variant=='general_outlook' else r
    g = 100*(v/v.shift(12)-1)
    target = (g.shift(-1)+g.shift(-2)+g.shift(-3))/3
    visitor_log = 100*(np.log1p(a)-np.log1p(a.shift(12)))
    dates=pd.period_range(TRAIN_START, min(v.index.max()-3, TEST[-1]), freq='M')
    records=[]
    for t in dates:
        eligible=[q for q in survey.index if q.asfreq('M','end')+2+survey_extra <= t]
        q=eligible[-1] if eligible else None
        tm=t-sales_lag
        row={'issue_month':t,'issue_date':t.start_time.date().replace(day=20),
             'target_start':str(t+1),'target_end':str(t+3),'actual':target.get(t,np.nan),
             'latest_growth':g.get(tm,np.nan),'trailing_growth':np.mean([g.get(tm-j,np.nan) for j in range(3)]),
             'seasonal_target':target.get(t-12,np.nan),'survey':survey.get(q,np.nan),
             'tourism':visitor_log.get(t-tourism_lag,np.nan),
             'sales_last_month':str(tm),'tourism_last_month':str(t-tourism_lag),
             'survey_database_quarter':str(q),'survey_target_quarter':str(q+1) if q is not None else '',
             'survey_eligible_date':str((q.asfreq('M','end')+2+survey_extra).start_time.date().replace(day=15)) if q else '',
             'sales_release_date_verified':False,'tourism_release_date_verified':False,'survey_release_date_verified':False,
             'sales_lag':sales_lag}
        for m in range(2,13):row[f'month_{m:02}']=float(t.month==m)
        records.append(row)
    frame=pd.DataFrame(records).set_index('issue_month')
    assert frame[['actual','latest_growth','trailing_growth','seasonal_target','survey','tourism']].notna().all().all()
    return frame

def features(model,variant):
    cols=['latest_growth','trailing_growth','seasonal_target']
    if variant!='no_season':cols += [f'month_{m:02}' for m in range(2,13)]
    if model in ['B','C']:cols+=['survey']
    if model=='C':cols+=['tourism']
    return cols

def fit_predict(frame,t,model,alpha,variant='primary',detail=False):
    lag=int(frame.loc[t,'sales_lag'])
    train=frame.loc[(frame.index>=TRAIN_START)&(frame.index<=t-3-lag)].copy()
    if variant=='exclude_pandemic':
        keep=[not(s+1<=pd.Period('2023-12','M') and s+3>=pd.Period('2020-01','M')) for s in train.index]
        train=train.loc[keep]
    if variant=='rolling60':train=train.tail(60)
    assert len(train)>=30 and train.index.max()+3 <= t-lag
    cols=features(model,variant)
    X=train[cols].to_numpy(float);y=train.actual.to_numpy(float)
    mu=X.mean(axis=0);sd=X.std(axis=0);sd[sd==0]=1
    Z=(X-mu)/sd; ym=y.mean()
    beta=np.linalg.solve(Z.T@Z+alpha*np.eye(len(cols)),Z.T@(y-ym))
    xp=frame.loc[t,cols].to_numpy(float)
    forecast=float(ym+((xp-mu)/sd)@beta)
    result={'model':model,'variant':variant,'alpha':alpha,'issue_month':str(t),
            'issue_date':str(frame.loc[t,'issue_date']),'actual':float(frame.loc[t,'actual']),
            'prediction':forecast,'train_n':len(train),'train_last_issue':str(train.index.max()),
            'last_training_target_month':str(train.index.max()+3),
            'sales_last_month':frame.loc[t,'sales_last_month'],'tourism_last_month':frame.loc[t,'tourism_last_month'],
            'survey_database_quarter':frame.loc[t,'survey_database_quarter'],
            'survey_target_quarter':frame.loc[t,'survey_target_quarter'],'target_start':str(t+1),'target_end':str(t+3)}
    if detail:
        result['coef']=[{'feature':c,'beta_standardized':float(be),'mean':float(m),'sd':float(d)} for c,be,m,d in zip(cols,beta,mu,sd)]
        result['intercept_at_training_means']=float(ym)
    return result

def predict(frame,issues,alphas,variant='primary'):
    return pd.DataFrame([fit_predict(frame,t,model,alphas[model],variant) for t in issues for model in MODELS])

def score(df):
    y=df.actual.to_numpy();p=df.prediction.to_numpy();e=p-y
    true=y<=0;warning=p<=0
    tp=int((true&warning).sum());fp=int((~true&warning).sum());tn=int((~true&~warning).sum());fn=int((true&~warning).sum())
    div=lambda n,d:float(n/d) if d else None
    recall=div(tp,tp+fn);specificity=div(tn,tn+fp)
    return {'n':len(y),'MAE_pp':float(np.abs(e).mean()),'RMSE_pp':float(np.sqrt(np.mean(e**2))),
            'bias_pp':float(e.mean()),'direction_accuracy':float((true==warning).mean()),
            'TP':tp,'FP':fp,'TN':tn,'FN':fn,'precision':div(tp,tp+fp),'recall':recall,
            'false_positive_rate':div(fp,fp+tn),'balanced_accuracy':(recall+specificity)/2 if recall is not None and specificity is not None else None}

def metrics(df,group=('variant','model')):
    return pd.DataFrame([{**dict(zip(group,keys if isinstance(keys,tuple) else (keys,))),**score(d)} for keys,d in df.groupby(list(group),sort=False)])

def errors(df):
    df=df.copy();df['error_pp']=df.prediction-df.actual;df['absolute_error_pp']=df.error_pp.abs();df['squared_error']=df.error_pp**2
    df['actual_weak']=df.actual<=0;df['warning']=df.prediction<=0
    return df

def bootstrap(df):
    rows=[];rng=np.random.default_rng(SEED)
    loss=df.pivot(index='issue_month',columns='model',values='absolute_error_pp').sort_index()
    n=len(loss);starts=rng.integers(0,n,(5000,int(np.ceil(n/6))))
    idx=((starts[:,:,None]+np.arange(6))%n).reshape(5000,-1)[:,:n]
    for base,chall in [('A','B'),('B','C'),('A','C')]:
        d=(loss[base]-loss[chall]).to_numpy();boot=d[idx].mean(axis=1)
        rows.append({'comparison':chall+' versus '+base,'mean_MAE_gain_pp':float(d.mean()),'ci95_low':float(np.quantile(boot,.025)),
                     'ci95_high':float(np.quantile(boot,.975)),'ci97_5_low':float(np.quantile(boot,.0125)),
                     'ci97_5_high':float(np.quantile(boot,.9875)),'bootstrap_block_months':6,'replications':5000})
    return pd.DataFrame(rows)

def validate(v,r,b,a):
    frame=make_frame(v,r,b,a)
    # Enforce the initial-test information boundary, including label publication lag.
    assert VALID[-1]+3<=TEST[0]-2
    assert set(VALID).isdisjoint(TEST)
    pred=[]
    for alpha in ALPHAS:
        pred.append(predict(frame,VALID,{m:alpha for m in MODELS}))
    p=errors(pd.concat(pred,ignore_index=True));p.to_csv(OUT/'validation_predictions.csv',index=False)
    stats=metrics(p,('model','alpha'));stats.to_csv(OUT/'validation_tuning.csv',index=False)
    chosen={m:float(stats[stats.model==m].sort_values(['MAE_pp','alpha'],ascending=[True,False]).iloc[0].alpha) for m in MODELS}
    lock={'selected_alpha':chosen,'locked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'test_performance_examined':False,'validation_first':str(VALID[0]),'validation_last':str(VALID[-1]),
          'preregistration_sha256':hashlib.sha256((OUT/'preregistration_v1.txt').read_bytes()).hexdigest()}
    save_json('model_lock.json',lock)
    frame.to_csv(OUT/'aligned_features.csv')
    print('VALIDATION ONLY. Fixed penalties:',chosen)
    print(stats.to_string(index=False))

def final(v,r,b,a):
    lock=json.loads((OUT/'model_lock.json').read_text());alphas=lock['selected_alpha']
    assert lock['preregistration_sha256']==hashlib.sha256((OUT/'preregistration_v1.txt').read_bytes()).hexdigest()
    frame=make_frame(v,r,b,a)
    primary=errors(predict(frame,TEST,alphas));primary.to_csv(OUT/'test_predictions.csv',index=False)
    allp=[primary]
    for variant in ['no_season','stricter_lags','stale_survey','exclude_pandemic','rolling60','general_outlook']:
        f=make_frame(v,r,b,a,variant);allp.append(errors(predict(f,TEST,alphas,variant)))
    # Matched vintage comparison: no change of test dates between vintages.
    common=TEST[TEST<=pd.Period('2025-09','M')]
    oldframe=make_frame(old_fsi(),r,b,a)
    legacy=errors(predict(oldframe,common,alphas));legacy['variant']='legacy_2017_basis';allp.append(legacy)
    current=primary[primary.issue_month.isin([str(x) for x in common])].copy();current['variant']='current_matched_legacy';allp.append(current)
    allp=pd.concat(allp,ignore_index=True);allp.to_csv(OUT/'robustness_predictions.csv',index=False)
    summary=metrics(allp);summary.to_csv(OUT/'robustness_metrics.csv',index=False)
    rows=[]
    for label,sub in [('test_year_1',primary[primary.issue_month<'2025-07']),('test_year_2',primary[primary.issue_month>='2025-07'])]:
        d=metrics(sub);d['period']=label;rows.append(d)
    for cohort in range(3):
        sub=primary[primary.issue_month.isin([str(t) for t in TEST[cohort::3]])]
        d=metrics(sub);d['period']='nonoverlap_cohort_'+str(cohort+1);rows.append(d)
    val=errors(predict(frame,VALID,alphas));val.to_csv(OUT/'selected_validation_predictions.csv',index=False)
    sub=val[val.issue_month<='2019-09'];d=metrics(sub);d['period']='pre_COVID_validation';rows.append(d)
    period=pd.concat(rows,ignore_index=True);period.to_csv(OUT/'period_metrics.csv',index=False)
    benchmarks=[]
    for name,col in [('Zero growth',None),('Latest growth persistence','latest_growth'),('Seasonal persistence','seasonal_target')]:
        d=primary[primary.model=='A'].copy();d['model']=name;d['prediction']=[float(frame.loc[t,col]) if col else 0. for t in TEST]
        benchmarks.append(errors(d))
    bench=pd.concat(benchmarks,ignore_index=True);bench.to_csv(OUT/'benchmark_predictions.csv',index=False)
    metrics(bench).to_csv(OUT/'benchmark_metrics.csv',index=False)
    ci=bootstrap(primary);ci.to_csv(OUT/'uncertainty.csv',index=False)
    params=[fit_predict(frame,t,m,alphas[m],detail=True) for t in TEST for m in MODELS]
    save_json('test_fitted_parameters.json',params)
    sm=summary[summary.variant=='primary'].set_index('model')
    criteria=[]
    for hyp,base,chall in [('H1','A','B'),('H2','B','C')]:
        gain=float(sm.loc[base,'MAE_pp']-sm.loc[chall,'MAE_pp']);relative=gain/sm.loc[base,'MAE_pp']
        halves=all(period[(period.period==p)&(period.model==chall)].iloc[0].MAE_pp < period[(period.period==p)&(period.model==base)].iloc[0].MAE_pp for p in ['test_year_1','test_year_2'])
        robust=all(summary[(summary.variant==z)&(summary.model==chall)].iloc[0].MAE_pp < summary[(summary.variant==z)&(summary.model==base)].iloc[0].MAE_pp for z in ['stricter_lags','exclude_pandemic'])
        lower=float(ci[ci.comparison==chall+' versus '+base].iloc[0].ci97_5_low)
        size_vs_A=bool((sm.loc['A','MAE_pp']-sm.loc[chall,'MAE_pp']>=.25) and (sm.loc['A','MAE_pp']-sm.loc[chall,'MAE_pp'])/sm.loc['A','MAE_pp']>=.10)
        tests={'at_least_10pct':bool(relative>=.10),'at_least_025pp':bool(gain>=.25),
               'RMSE_not_over_5pct_worse':bool(sm.loc[chall,'RMSE_pp']<=1.05*sm.loc[base,'RMSE_pp']),
               'both_test_halves_improve':bool(halves),'lag_and_pandemic_sensitivity_improve':bool(robust),
               'adjusted_interval_lower_positive':bool(lower>0),'size_criteria_also_vs_A':size_vs_A}
        criteria.append({'hypothesis':hyp,'MAE_gain_pp':gain,'MAE_improvement_pct':float(relative*100),**tests,'all_pass':all(tests.values())})
    save_json('decision_criteria.json',criteria)
    print('FINAL TEST')
    print(sm.to_string());print('UNCERTAINTY');print(ci.to_string(index=False))
    print('BENCHMARKS');print(metrics(bench).to_string(index=False))
    print('ROBUSTNESS');print(summary[['variant','model','n','MAE_pp','RMSE_pp']].to_string(index=False))
    print('DECISIONS');print(json.dumps(criteria,indent=2))

if __name__=='__main__':
    args=argparse.ArgumentParser();args.add_argument('--stage',choices=['prepare','validate','final'],required=True);stage=args.parse_args().stage
    v,r,b,a=prepare()
    if stage=='validate':validate(v,r,b,a)
    elif stage=='final':final(v,r,b,a)
    else:print((OUT/'data_quality.json').read_text())
