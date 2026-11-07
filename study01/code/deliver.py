"""Build chart and workbook inputs from the frozen analysis outputs."""
from pathlib import Path
import json, re, datetime, importlib.metadata
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output';RAW=ROOT/'raw'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#384657','text.color':'#182331','xtick.color':'#526173','ytick.color':'#526173','figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})
COLORS={'A':'#235789','B':'#cf6a32','C':'#168579'}
monthly=pd.read_csv(OUT/'monthly_data.csv');monthly['date']=pd.to_datetime(monthly.month)
q=pd.read_csv(OUT/'quarterly_data.csv');q['date']=pd.PeriodIndex(q.database_quarter,freq='Q').to_timestamp(how='end')
test=pd.read_csv(OUT/'test_predictions.csv');rob=pd.read_csv(OUT/'robustness_metrics.csv');ci=pd.read_csv(OUT/'uncertainty.csv')
primary=rob[rob.variant=='primary'].set_index('model')

# Chart 1: separate panels, no spurious dual-axis equivalence.
fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True,gridspec_kw={'hspace':.25})
sel=monthly[monthly.date>='2008-01-01']
axes[0].plot(sel.date,sel.fsi_volume_2025base,color=COLORS['A'],lw=1.7)
axes[0].set_ylabel('F&B volume index\n2025 = 100');axes[0].set_title('F&B activity and visitor arrivals share the pandemic shock',loc='left',fontsize=16,pad=14)
axes[1].plot(sel.date,sel.arrivals_nsa/1e6,color=COLORS['C'],lw=1.7);axes[1].set_ylabel('Visitor arrivals\nmillions per month')
sq=q[q.date>='2008-01-01'];axes[2].step(sq.date,sq.bes_revenue_pp,where='post',color=COLORS['B'],lw=1.7);axes[2].axhline(0,color='#8391a1',lw=.7);axes[2].set_ylabel('F&B revenue expectations\nnet balance, pp')
for ax in axes:
    ax.axvspan(pd.Timestamp('2020-01-01'),pd.Timestamp('2023-12-31'),color='#cfd6df',alpha=.25,zorder=0)
    ax.grid(axis='y',color='#e4e8ed',lw=.7)
axes[2].xaxis.set_major_locator(mdates.YearLocator(2));axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
fig.text(.11,.035,'Monthly observations through September 2026. Expectations plotted by database quarter, not release date.\nShading: 2020–2023 shock, reopening and annual base effects. Sources: SingStat / STB, downloaded 6 Nov 2026.',fontsize=9,color='#526173')
fig.subplots_adjust(left=.15,bottom=.12,right=.96,top=.94)
fig.savefig(OUT/'chart_01_history.png',dpi=200);plt.close(fig)

# Chart 2: pre-specified primary models plus simple diagnostic benchmark.
fig,ax=plt.subplots(figsize=(10,5.5));labs=['A: Sales history','B: + Expectations','C: + Tourism','Zero-growth benchmark']
mae=[primary.loc[m,'MAE_pp'] for m in 'ABC']+[float(pd.read_csv(OUT/'benchmark_metrics.csv').iloc[0].MAE_pp)]
ax.barh(labs,mae,color=[COLORS[m] for m in 'ABC']+['#8b949e'],height=.58)
for i,v in enumerate(mae):ax.text(v+.04,i,f'{v:.2f} pp',va='center',fontweight='bold')
ax.invert_yaxis();ax.set_xlim(0,2.3);ax.set_xlabel('Mean absolute error (percentage points); lower is better')
ax.set_title('Neither added indicator beats the sales-history model',loc='left',fontsize=16,pad=18)
ax.grid(axis='x',color='#e4e8ed',lw=.7);ax.set_axisbelow(True)
fig.text(.04,.04,'24 held-out issue months: July 2024–June 2026. Target: average annual volume growth in the next three months.\nRetrospective evaluation using revised data and assumed release lags; not a real-time backtest.',fontsize=9,color='#526173')
fig.subplots_adjust(left=.27,right=.94,top=.86,bottom=.20);fig.savefig(OUT/'chart_02_forecast_accuracy.png',dpi=200);plt.close(fig)

# Chart 3: report every prespecified current-vintage specification, including failures.
variants=['primary','no_season','stricter_lags','stale_survey','exclude_pandemic','rolling60','general_outlook']
labels=['Primary model','No month indicators','One extra month of delay','Survey one quarter older','Exclude 2020–2023 training targets','Latest 60 training origins','Six-month outlook survey']
fig,ax=plt.subplots(figsize=(11,6.5))
for i,(var,label) in enumerate(zip(variants,labels)):
    d=rob[rob.variant==var].set_index('model');values=[d.loc[m,'MAE_pp'] for m in 'ABC']
    ax.plot([min(values),max(values)],[i,i],color='#b9c2ce',lw=2,zorder=1)
    for m,off in zip('ABC',[-.12,0,.12]):ax.scatter(d.loc[m,'MAE_pp'],i+off,s=55,color=COLORS[m],zorder=3,label=m if i==0 else None)
ax.set_yticks(range(len(labels)),labels);ax.invert_yaxis();ax.set_xlabel('Mean absolute error (percentage points); lower is better')
ax.set_title('The apparent gain changes with the specification',loc='left',fontsize=16,pad=18)
ax.legend(title='Model',ncol=3,loc='lower right',frameon=False);ax.grid(axis='x',color='#e4e8ed');ax.set_xlim(1.1,4.3)
fig.text(.035,.04,'All checks use the same 24 held-out forecasts and fixed penalties. A = sales history; B = + expectations; C = + tourism.\nThe recent-window models show relative gains but substantially larger absolute errors. None was selected after testing.',fontsize=9,color='#526173')
fig.subplots_adjust(left=.35,right=.96,top=.87,bottom=.18);fig.savefig(OUT/'chart_03_robustness.png',dpi=200);plt.close(fig)

inventory=[]
names=[('fsi_current','M602211','Primary outcome','Monthly','1985-01','2026-09','2026-11-05','5th of second following month / following working day, current schedule','Chained volume; 2025=100; NSA. Excludes individual hawker/food-court/coffee-shop/canteen stalls. 2026 rebasing changed weights and coverage.'),
('bes_revenue_current','M250451','H1 predictor','Quarterly','1995-Q1','2026-Q3','2026-11-02','Around end of first month of reference quarter; actual history incomplete','F&B operating-revenue forecast: weighted up minus down, pp; database quarter precedes forecast quarter. Nominal quarter-on-quarter expectations versus real annual target.'),
('bes_outlook_current','M250431','Robustness predictor','Quarterly','1995-Q1','2026-Q3','2026-11-02','Quarterly; actual history incomplete','Six-month general business outlook, F&B net weighted balance, pp.'),
('visitors_current','M550001','H2 predictor','Monthly','2008-01','2026-09','','Monthly; historical first-release dates not reconstructed','STB arrival counts. NSA identified by mirror agreement and comparison to M550002; API adjustmentType is inconsistent. Arrivals do not measure visitor F&B expenditure.'),
('visitors_sa_current','M550002','Metadata verification only','Monthly','2008-01','2026-09','','Monthly; not used as predictor','Separate explicitly seasonally adjusted arrivals series; numeric comparison distinguishes M550001.'),
('registry_cessation_page6','M085841','Exploratory data audit only','Monthly','1990-01','2026-10','','Monthly; table updated on cutoff date','F&B entity cessations, not outlet failures. Publication-vintage history incomplete; registry processing interventions. Not modelled.'),
('registry_formation_page6','M085831','Exploratory data audit only','Monthly','1990-01','2026-10','','Monthly; table updated on cutoff date','F&B entity registrations, not openings or realised sales. December 2024 system migration. Not modelled.')]
for name,id,role,freq,start,end,release,schedule,limits in names:
    p=RAW/(name+'.json')
    if not p.exists():continue
    data=json.loads(p.read_text())['Data'];meta=json.loads((RAW/(name+'_download.json')).read_text())
    inventory.append({'dataset':data['title'],'table_id':id,'role':role,'official_url':'https://tablebuilder.singstat.gov.sg/table/TS/'+id,
                      'frequency':freq,'coverage_start':start,'coverage_end':end,'verified_latest_release_date':release,
                      'table_updated':data['dataLastUpdated'],'download_utc':meta['download_utc'],'publication_schedule':schedule,
                      'revision_status':'Single downloaded vintage; complete historical first releases unavailable','limitations':limits,
                      'sha256':meta['sha256'],'raw_file':'raw/'+name+'.json'})
meta=json.loads((RAW/'fsi_2017_download.json').read_text())
inventory.append({'dataset':'Food & Beverage Services Index (2017=100), chained volume, monthly','table_id':'M601881','role':'Vintage/basis sensitivity','official_url':'https://data.gov.sg/datasets/d_42cb05dd61cddf473a8ba82cd10c7e34/view','frequency':'Monthly','coverage_start':'1985-01','coverage_end':'2025-12','verified_latest_release_date':'','table_updated':'2026-02-05 (portal metadata)','download_utc':meta['download_utc'],'publication_schedule':'Archived discontinued basis','revision_status':'Different vintage/basis; not a complete real-time archive','limitations':'Comparisons mix rebasing and other revisions; do not interpret differences as pure revision error.','sha256':meta['sha256'],'raw_file':'raw/fsi_2017.json'})
pd.DataFrame(inventory).to_csv(OUT/'dataset_inventory.csv',index=False)

dictionary=[
['fsi_volume_2025base','Total F&B chained-volume index','Index, 2025=100','M602211','Use published NSA total; no further CPI deflation.'],
['fsi_volume_2017base','Archived total F&B chained-volume index','Index, 2017=100','M601881','Sensitivity only; never splice levels.'],
['g_m','Annual volume growth','Percent / percentage-point scale','100*(V_m/V_(m-12)-1)','Calculated from source-precision levels.'],
['Y_t','Average annual growth in following three months','Percent / percentage-point scale','(g_(t+1)+g_(t+2)+g_(t+3))/3','Primary target; not growth of quarterly sum.'],
['latest_growth','Latest available annual volume growth','Percentage points','g_(t-2)','Primary lag assumption, not an actual release date.'],
['trailing_growth','Mean annual growth in latest three available months','Percentage points','mean(g_(t-4),g_(t-3),g_(t-2))','Training-only scaling.'],
['seasonal_target','Same three-month annual-growth target one year earlier','Percentage points','Y_(t-12)','Uses only months t-11 through t-9.'],
['bes_revenue_pp','F&B revenue expectations balance','Percentage points','M250451','Latest eligible release; no interpolation.'],
['bes_outlook_pp','F&B six-month general outlook','Percentage points','M250431','Replacement in fixed robustness check.'],
['arrivals_nsa','International visitor arrivals','Persons / arrival events','M550001','Not distinct persons or spending.'],
['tourism','Annual log change in arrivals','100 log points','100*(log(1+A_(t-3))-log(1+A_(t-15)))','Log transform handles near-zero pandemic arrivals.'],
['month_02…month_12','Issue-month fixed effects','0/1','Calendar known at issue','January omitted; ridge penalised after training-only standardisation.'],
['prediction','Direct three-month target prediction','Percentage points','Frozen alpha; expanding-window regression','Generated in Python; rerun code to refit.'],
['error_pp','Prediction minus observed outcome','Percentage points','prediction - actual','Positive means too optimistic.'],
['warning','Predicted weak demand','0/1','prediction <= 0','Threshold locked before test.'],
['actual_release_date','Verified first-publication date','Calendar date or blank','Official release when recovered','Blank means unknown; never substitute download date.'],
['assumed_eligible_date','Imposed information-availability date','Calendar date','Protocol lag rule','An assumption, not a verified release date.']]

transform=[
['T01','Parse official JSON','Retain originals, source precision, hashes and download timestamps.'],
['T02','Select aggregate F&B and arrivals','No subindustry aggregation; source series directly selected.'],
['T03','Check coverage','Unique consecutive dates; nonnegative arrivals; positive volume; selected series have zero missing.'],
['T04','Resolve visitor metadata','221/224 mirror months identical; three latest differences <=43 arrivals; separate adjusted series differs.'],
['T05','Construct annual and forward growth','Exact protocol formulas. No extra deflation or interpolation.'],
['T06','Align public information','Sales lag2, tourism lag3, survey quarter end +2 months; actual release history incomplete.'],
['T07','Fit and select','Training-only standardisation; labels mature at s<=t-5; validation chooses alpha100 for A/B/C.'],
['T08','Unseal final test','24 issues Jul2024–Jun2026; no test tuning.'],
['T09','Run locked checks','All prespecified variants reported; no post-test substitution.'],
['T10','Audit computation','Nine independent sklearn comparisons and unavailable-data perturbation passed.'],
['T11','No methodological deviation','Registry model gate failed; all primary models and fixed checks executed. Exact real-time validation remains incomplete.']]

model_specs=[
['Outcome','Arithmetic mean of annual F&B volume growth for the next three months'],
['Issue date','20th calendar day, 23:59 Asia/Singapore'],
['Training origins','January 2010 onwards; only matured labels'],
['Validation origins','January 2016–February 2024 (98)'],
['Embargo','March–June 2024 excluded from tuning'],
['Final test origins','July 2024–June 2026 (24)'],
['A','Intercept; latest sales growth; trailing mean; prior-year target; 11 month indicators'],
['B','A plus latest eligible F&B operating-revenue expectations'],
['C','B plus annual visitor log change, lagged 3 months'],
['D','Not fitted. Registry timing and comparability gate not met.'],
['Ridge grid','0.1, 1, 10, 100; training-only StandardScaler; unpenalised intercept'],
['Selected penalties','A=100, B=100, C=100; locked before test'],
['Primary accuracy metric','Mean absolute error, percentage points'],
['Weak demand','Actual Y<=0; warning predicted Y<=0'],
['Success rule','>=10% and >=0.25pp MAE gain; RMSE not >5% worse; both test halves; robustness; adjusted CI lower>0'],
['Uncertainty','Paired circular moving-block bootstrap; block6; 5000; seed20261106'],
['Vintage status','Retrospective pseudo-out-of-sample; revised snapshots and assumed timing'],
['Preregistered protocol','output/preregistration_v1.txt (SHA-256 fd528e90...aaa0)'],
['Refitting','Python code is authoritative. Spreadsheet formulas recompute errors and growth, not fitted coefficients.']]

val=pd.read_csv(OUT/'selected_validation_predictions.csv');val['phase']='Validation'
test['phase']='Test';bench=pd.read_csv(OUT/'benchmark_predictions.csv');bench['phase']='Test'
pred=pd.concat([test,bench,val],ignore_index=True).sort_values(['phase','issue_month','model'])
pred=pred.replace({np.nan:None})

registry=[]
for label,name in [('cessations','registry_cessation_page6'),('formations','registry_formation_page6')]:
    p=RAW/(name+'.json')
    if p.exists():
        data=json.loads(p.read_text())['Data']
        for row in data['row']:
            if row['rowText'] == 'SSIC 56 - Food & Beverage':
                for c in row['columns']:
                    registry.append({'month':pd.to_datetime(c['key'],format='%Y %b').strftime('%Y-%m'),'measure':label,'count':pd.to_numeric(c['value'],errors='coerce'),'series_label':row['rowText'],'use':'Descriptive only; excluded from prediction'})
reg=pd.DataFrame(registry)
if len(reg):reg.to_csv(OUT/'registry_audit.csv',index=False)

def records(file):return pd.read_csv(OUT/file).replace({np.nan:None}).to_dict(orient='records')
payload={'inventory':inventory,'dictionary':dictionary,'transforms':transform,'models':model_specs,
         'predictions':pred.to_dict(orient='records'),'monthly':records('monthly_data.csv'),'quarterly':records('quarterly_data.csv'),
         'features':records('aligned_features.csv'),'robustness':records('robustness_metrics.csv'),
         'robustness_predictions':records('robustness_predictions.csv'),'period_metrics':records('period_metrics.csv'),
         'uncertainty':records('uncertainty.csv'),'tuning':records('validation_tuning.csv'),'registry':registry}
(OUT/'workbook_inputs.json').write_text(json.dumps(payload,allow_nan=False,default=str))
versions={name:importlib.metadata.version(name) for name in ['numpy','pandas','matplotlib','scikit-learn','scipy']}
(OUT/'environment.json').write_text(json.dumps(versions,indent=2))
print('Created three charts and workbook inputs. Registry records:',len(registry))
