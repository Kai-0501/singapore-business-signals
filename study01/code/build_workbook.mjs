import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const studyRoot=process.env.SBS_STUDY_ROOT??path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const d=JSON.parse(await fs.readFile(studyRoot+'/output/workbook_inputs.json','utf8'));
const out=process.env.SBS_WORKBOOK_OUT??studyRoot+'/workbook_export';await fs.mkdir(out+'/qa',{recursive:true});
const wb=Workbook.create();
const names=['Results','Predictions','Robustness','Period Checks','Uncertainty','Monthly Data','Quarterly Data','Forecast Inputs','Sources','Dictionary','Protocol','Tuning','Robust Predictions','Registry Audit'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const dims={};
function col(n){let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;}
function grid(name,headers,rows,widths={}){
 const s=sheets[name],nr=rows.length+1,nc=headers.length;
 s.getRange(`A1:${col(nc)}${nr}`).values=[headers,...rows];
 const all=s.getRange(`A1:${col(nc)}${nr}`);all.format.font={name:'Arial',size:10,color:'#000000'};all.format.rowHeight=22;all.format.columnWidth=19;all.format.verticalAlignment='center';
 const h=s.getRange(`A1:${col(nc)}1`);h.format.fill='#eeeeee';h.format.font.bold=true;h.format.wrapText=true;h.format.rowHeight=38;
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(1);s.showGridLines=true;
 for(const [c,w]of Object.entries(widths))s.getRange(`${c}1:${c}${nr}`).format.columnWidth=w;
 dims[name]={rows:nr,columns:nc};return s;
}
const resultModels=['A','B','C','Zero growth','Latest growth persistence','Seasonal persistence'];
grid('Results',['Model','Forecasts','MAE (pp)','RMSE (pp)','Bias (pp)','Direction accuracy','MAE change vs A','Weak-demand recall','False-positive rate'],resultModels.map(m=>[m,...Array(8).fill(null)]),{A:30});
const pred=d.predictions.map(r=>[(Date.parse(r.issue_date+'T00:00:00Z')/86400000+25569),r.model,r.phase,r.actual,r.prediction,...Array(10).fill(null),r.train_n,r.train_last_issue,r.target_start,r.target_end]);
const ps=grid('Predictions',['Issue date','Model','Evaluation period','Actual growth (%)','Forecast growth (%)','Error (pp)','Absolute error (pp)','Squared error','Actual weak (0/1)','Warning (0/1)','Direction correct','True positive','False positive','True negative','False negative','Training origins','Last training issue','Target start','Target end'],pred,{B:30});
ps.getRange(`A2:A${pred.length+1}`).setNumberFormat('yyyy-mm-dd');ps.getRange(`D2:H${pred.length+1}`).setNumberFormat('0.0000');
ps.getRange(`F2:O${pred.length+1}`).formulas=pred.map((_,i)=>{const r=i+2;return [`=E${r}-D${r}`,`=ABS(F${r})`,`=F${r}^2`,`=IF(D${r}<=0,1,0)`,`=IF(E${r}<=0,1,0)`,`=IF(I${r}=J${r},1,0)`,`=I${r}*J${r}`,`=(1-I${r})*J${r}`,`=(1-I${r})*(1-J${r})`,`=I${r}*(1-J${r})`];});
const last=pred.length+1;const pcol=c=>`Predictions!$${c}$2:$${c}$${last}`;const sums=(c,r)=>`SUMIFS(${pcol(c)},${pcol('B')},A${r},${pcol('C')},"Test")`;
sheets.Results.getRange('B2:I7').formulas=resultModels.map((m,i)=>{const r=i+2;return [`=COUNTIFS(${pcol('B')},A${r},${pcol('C')},"Test")`,`=${sums('G',r)}/B${r}`,`=SQRT(${sums('H',r)}/B${r})`,`=${sums('F',r)}/B${r}`,`=${sums('K',r)}/B${r}`,`=C${r}/$C$2-1`,`=${sums('L',r)}/(${sums('L',r)}+${sums('O',r)})`,`=${sums('M',r)}/(${sums('M',r)}+${sums('N',r)})`];});
sheets.Results.getRange('C2:E7').setNumberFormat('0.0000');sheets.Results.getRange('F2:I7').setNumberFormat('0.0%');
const notes=['STUDY 01 • Research cutoff: 6 November 2026','Finding: neither added indicator passed the locked standard for meaningful improvement.','24 test issue months: July 2024–June 2026; all models forecast identical targets.','Target: arithmetic mean of monthly year-on-year F&B volume growth over the next 3 months.','A = sales history; B adds F&B revenue expectations; C adds visitor arrivals.','Positive MAE change means deterioration. Lower MAE and RMSE are better.','Warning threshold: forecast <= 0. Twenty of 24 actual targets meet this threshold.','Retrospective pseudo-out-of-sample: revised data and assumed publication lags.','Historical release dates and first-release vintages are not fully reconstructed.','Edit predictions to recompute error summaries. Refit models with the bundled Python code.','Other tabs preserve validation, all fixed robustness checks, source dates and transformations.'];
notes.forEach((n,i)=>{const r=i+10;sheets.Results.getRange(`A${r}:I${r}`).merge();sheets.Results.getRange(`A${r}`).values=[[n]];sheets.Results.getRange(`A${r}:I${r}`).format.rowHeight=27;});dims.Results.rows=20;
function objects(name,rows,keys,widths={}){const s=grid(name,keys,rows.map(r=>keys.map(k=>typeof r[k]==='number'?r[k]:r[k]??null)),widths);for(let c=0;c<keys.length;c++)if(rows.some(r=>typeof r[keys[c]]==='number'))s.getRange(`${col(c+1)}2:${col(c+1)}${rows.length+1}`).setNumberFormat('0.0000');return s;}
const metrics=['variant','model','n','MAE_pp','RMSE_pp','bias_pp','direction_accuracy','TP','FP','TN','FN','precision','recall','false_positive_rate','balanced_accuracy'];
objects('Robustness',d.robustness,metrics,{A:30});objects('Period Checks',d.period_metrics,['period',...metrics],{A:30});objects('Uncertainty',d.uncertainty,Object.keys(d.uncertainty[0]),{A:25});
const ms=grid('Monthly Data',['Observation month','F&B volume (2025=100)','Visitor arrivals (NSA)','Legacy F&B (2017=100)','Annual growth (%)','Next-3-month mean (%)'],d.monthly.map(r=>[(Date.parse(r.month+'-01T00:00:00Z')/86400000+25569),r.fsi_volume_2025base,r.arrivals_nsa,r.fsi_volume_2017base,null,null]),{A:22,B:24,C:25,D:25,E:23,F:28});
ms.getRange(`A2:A${d.monthly.length+1}`).setNumberFormat('yyyy-mm');ms.getRange(`B2:F${d.monthly.length+1}`).setNumberFormat('0.0000');ms.getRange(`C2:C${d.monthly.length+1}`).setNumberFormat('#,##0');
ms.getRange(`E14:E${d.monthly.length+1}`).formulas=d.monthly.slice(12).map((_,i)=>[`=100*(B${i+14}/B${i+2}-1)`]);
ms.getRange(`F13:F${d.monthly.length-2}`).formulas=d.monthly.slice(11,-3).map((_,i)=>[`=(E${i+14}+E${i+15}+E${i+16})/3`]);
objects('Quarterly Data',d.quarterly,Object.keys(d.quarterly[0]),{A:23,D:23,E:26,F:26});
objects('Forecast Inputs',d.features,Object.keys(d.features[0]),{A:20,B:22,M:27,N:26,O:28,P:27,Q:28,R:28});
const sources=objects('Sources',d.inventory,Object.keys(d.inventory[0]),{A:52,C:30,D:68,K:55,L:50,M:80,N:70,O:50});sources.getRange(`A2:O${d.inventory.length+1}`).format.wrapText=true;sources.getRange(`A2:O${d.inventory.length+1}`).format.rowHeight=90;
const ds=grid('Dictionary',['Variable','Definition','Units','Source / formula','Treatment / limitation'],d.dictionary,{A:30,B:55,C:35,D:65,E:80});ds.getRange('A2:E18').format.wrapText=true;ds.getRange('A2:E18').format.rowHeight=42;
const protocol=grid('Protocol',['Item','Locked rule / transformation'],[...d.models,['TRANSFORMATION LOG',''],...d.transforms.map(x=>[x[0]+' '+x[1],x[2]])],{A:42,B:120});protocol.getRange(`A2:B${dims.Protocol.rows}`).format.wrapText=true;protocol.getRange(`A2:B${dims.Protocol.rows}`).format.rowHeight=38;
objects('Tuning',d.tuning,Object.keys(d.tuning[0]),{A:20});
objects('Robust Predictions',d.robustness_predictions,Object.keys(d.robustness_predictions[0]),{B:30,I:25,J:28,K:25,L:27,M:29,N:29});
objects('Registry Audit',d.registry.map(r=>({...r,count:Number(r.count)})),Object.keys(d.registry[0]),{D:42,E:60});
wb.recalculate();
const inspect=await wb.inspect({kind:'region',sheetId:'Results',range:'A1:I7',maxChars:5000,tableMaxRows:7,tableMaxCols:9});console.log(inspect.ndjson??JSON.stringify(inspect));
await fs.writeFile(out+'/workbook_layout.json',JSON.stringify(dims,null,2));
for(const name of (process.env.SBS_SKIP_RENDER?[]:names)){let end=name==='Results'?'I20':(name==='Protocol'?'B7':name==='Sources'?'E5':name==='Dictionary'?'E5':'F8');const img=await wb.render({sheetName:name,range:'A1:'+end,scale:1.2,format:'png'});await fs.writeFile(out+'/qa/'+name.replaceAll(' ','_')+'.png',new Uint8Array(await img.arrayBuffer()));}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(out+'/Singapore_Business_Signals_Study01_Evidence.xlsx');
console.log('Workbook exported; tabs:',names.length);
