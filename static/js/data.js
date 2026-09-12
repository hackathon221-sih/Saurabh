function moneyData(v){return '₹'+Number(v||0).toLocaleString('en-IN',{maximumFractionDigits:0});}
function showDataset(d){
 const el=document.getElementById('datasetInfo');
 el.innerHTML=`<div><span>File</span><b>${d.filename||'—'}</b></div><div><span>Records</span><b>${Number(d.rows||0).toLocaleString('en-IN')}</b></div><div><span>Coverage</span><b>${d.start_date||'—'} → ${d.end_date||'—'}</b></div><div><span>Sectors</span><b>${(d.sectors||[]).join(', ')||'—'}</b></div>`;
}
async function loadDatasetInfo(){try{const r=await fetch('/api/data/info',{cache:'no-store'});showDataset(await r.json())}catch(e){document.getElementById('datasetInfo').innerHTML='<div><span>Status</span><b>Unable to read dataset</b></div>'}}
function renderForecast(rows){
 const cards=document.getElementById('forecastCards'); const table=document.getElementById('forecastRows');
 if(!rows.length){cards.innerHTML='<div class="empty-state">No forecast can be generated yet.</div>';table.innerHTML='';return;}
 const first=rows[0];
 cards.innerHTML=[['🏨','Hospitality',first.hospitality,'customers/day'],['🛒','Retail',first.retail,'customers/day'],['🏦','Financial',first.financial,`customers/day`],['🎬','Entertainment',first.entertainment,'customers/day']].map(x=>`<article class="forecast-card"><span>${x[0]}</span><b>${x[1]}</b><strong>${Number(x[2]).toFixed(1)}</strong><small>Predicted ${x[3]} · ${first.month_name} ${first.year}</small></article>`).join('');
 table.innerHTML=rows.map(r=>`<tr><td><b>${r.month_name} ${r.year}</b><em>Predicted</em></td><td>${Number(r.all).toFixed(1)}</td><td>${Number(r.hospitality).toFixed(1)}</td><td>${Number(r.retail).toFixed(1)}</td><td>${Number(r.financial).toFixed(1)}</td><td>${Number(r.entertainment).toFixed(1)}</td><td>${moneyData(r.financial_revenue)}</td></tr>`).join('');
}
async function loadForecast(){
 const months=document.getElementById('forecastMonths').value;
 try{const r=await fetch('/api/forecast/monthly?months='+months,{cache:'no-store'});const d=await r.json();if(d.error)throw new Error(d.error);renderForecast(d.forecast||[])}catch(e){document.getElementById('forecastCards').innerHTML=`<div class="empty-state">${e.message}</div>`;document.getElementById('forecastRows').innerHTML=''}
}
document.addEventListener('DOMContentLoaded',()=>{
 const input=document.getElementById('datasetFile'), zone=document.getElementById('dropZone'), form=document.getElementById('uploadForm'), name=document.getElementById('fileName'), msg=document.getElementById('uploadMessage');
 input?.addEventListener('change',()=>{name.textContent=input.files[0]?.name||'Choose an Excel file'});
 ['dragenter','dragover'].forEach(ev=>zone?.addEventListener(ev,e=>{e.preventDefault();zone.classList.add('dragging')}));
 ['dragleave','drop'].forEach(ev=>zone?.addEventListener(ev,e=>{e.preventDefault();zone.classList.remove('dragging')}));
 zone?.addEventListener('drop',e=>{const f=e.dataTransfer.files[0];if(f){const dt=new DataTransfer();dt.items.add(f);input.files=dt.files;name.textContent=f.name}});
 form?.addEventListener('submit',async e=>{e.preventDefault();if(!input.files[0]){msg.textContent='Please choose an Excel file.';msg.className='upload-message error';return;}msg.textContent='Reading data and updating the forecasting engine…';msg.className='upload-message';const fd=new FormData();fd.append('file',input.files[0]);try{const r=await fetch('/api/data/upload',{method:'POST',body:fd});const d=await r.json();if(!r.ok)throw new Error(d.error||'Upload failed');showDataset(d.dataset);renderForecast(d.forecast||[]);msg.textContent='Dataset loaded successfully. Future predictions are now based on the new data.';msg.className='upload-message success';}catch(err){msg.textContent=err.message;msg.className='upload-message error'}});
 document.getElementById('forecastMonths')?.addEventListener('change',loadForecast);loadDatasetInfo();loadForecast();
});
