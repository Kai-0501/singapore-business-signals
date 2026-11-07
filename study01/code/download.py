import urllib.request,datetime,json,pathlib,hashlib,concurrent.futures
BASE=pathlib.Path(__file__).resolve().parents[1]/'raw'
SOURCES={
'fsi_current':'https://tablebuilder.singstat.gov.sg/api/table/tabledata/M602211',
'fsi_metadata':'https://tablebuilder.singstat.gov.sg/api/table/metadata/M602211',
'bes_revenue_current':'https://tablebuilder.singstat.gov.sg/api/table/tabledata/M250451',
'bes_revenue_metadata':'https://tablebuilder.singstat.gov.sg/api/table/metadata/M250451',
'bes_outlook_current':'https://tablebuilder.singstat.gov.sg/api/table/tabledata/M250431',
'visitors_current':'https://tablebuilder.singstat.gov.sg/api/table/tabledata/M550001',
'visitors_metadata':'https://tablebuilder.singstat.gov.sg/api/table/metadata/M550001',
}
def download(kv):
 k,u=kv
 try:
  req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'})
  r=urllib.request.urlopen(req,timeout=25);b=r.read();j=json.loads(b);(BASE/(k+'.json')).write_bytes(b)
  meta={'name':k,'url':u,'download_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'response_date':r.headers.get('date')};(BASE/(k+'_download.json')).write_text(json.dumps(meta,indent=2))
  d=j.get('Data',{});return {'name':k,'bytes':len(b),'keys':list(d),'metadata':{a:v for a,v in d.items() if a not in ['row','rows']},'first_row':str(d.get('row',[]))[:350]}
 except Exception as e:return {'name':k,'error':str(e)}
if __name__=='__main__':
 for x in concurrent.futures.ThreadPoolExecutor(max_workers=4).map(download,SOURCES.items()):print(json.dumps(x))
