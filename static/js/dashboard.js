let dashboardDateValue = localISODate();
let calendarYear = Number(dashboardDateValue.slice(0,4));
let calendarMonth = Number(dashboardDateValue.slice(5,7));

function localISODate(){const d=new Date();const off=d.getTimezoneOffset();return new Date(d.getTime()-off*60000).toISOString().slice(0,10)}
function money(v){return '₹'+Number(v||0).toLocaleString('en-IN',{maximumFractionDigits:0});}
function fmtDate(s){return new Date(s+'T00:00:00').toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short',year:'numeric'});}
function goHospitality(){location.href='/hospitality?date='+dashboardDateValue;}
function applyDashboardDate(){dashboardDateValue=document.getElementById('dashboardDate').value||localISODate();calendarYear=+dashboardDateValue.slice(0,4);calendarMonth=+dashboardDateValue.slice(5,7);loadDashboard(dashboardDateValue)}

async function loadDashboard(dateValue){
 dashboardDateValue=dateValue; document.getElementById('dashboardDate').value=dateValue;
 const d=await (await fetch('/api/dashboard?date='+dateValue,{cache:'no-store'})).json();
 const historical=dateValue<localISODate(); const s=d.sectors,h=d.detail.hospitality,r=d.detail.retail,fin=d.detail.finance,e=d.detail.entertainment;
 const f=d.upcoming_festival;
 document.getElementById('festivalName').textContent=f?f.name:'No upcoming festival found';
 document.getElementById('festivalMeta').textContent=f?`${fmtDate(f.date)} · ${f.category}`:'';
 document.getElementById('selectedDateLabel').textContent=fmtDate(d.date);
 const cards=[
  ['hospitality','🏨','Hospitality',historical?`${h.customers} guests`:`${h.predicted_occupancy}%`,historical?'Actual customers':'Predicted occupancy',historical?h.prediction_accuracy:h.staff_increase],
  ['retail','🛒','Retail',historical?`${r.customers} customers`:`${r.recommended_total_units} units`,historical?'Actual customers':'Recommended stock',historical?r.prediction_accuracy:r.staff_increase],
  ['finance','🏦','Financial Services',historical?money(fin.revenue):`${fin.revenue_change_amount>=0?'+':'-'}${money(Math.abs(fin.revenue_change_amount))}`,historical?'Actual revenue':'Expected revenue change',historical?fin.prediction_accuracy:fin.revenue_change_pct],
  ['entertainment','🎬','Entertainment',`${e.expected_attendance}`,historical?'Actual attendance':'Expected attendance',historical?e.prediction_accuracy:e.staff_increase]
 ];
 document.getElementById('dashboardSectors').innerHTML=cards.map(c=>{
   const ch=Number(c[5]??0); const arrow=ch>=0?'↗':'↘'; const cls=ch<0?'negative':'';
   const tag=historical?'Prediction match':'Change';
   return `<article class="sector-card ${c[0]}"><div class="sector-icon">${c[1]}</div><h2>${c[2]}</h2><span class="growth ${cls}">${arrow} ${ch>=0?'+':''}${ch.toFixed(1)}%<small>${tag}</small></span><p>${historical?'Historical performance':'Planning analysis'}</p><strong>${c[3]}</strong><small>${c[4]}</small><a href="/sectors?sector=${c[0]}&date=${dateValue}">View Details →</a></article>`
 }).join('');
 document.getElementById('dateOverview').innerHTML=`<div><span>Mode</span><b>${historical?'Historical':'Planning'}</b></div><div><span>All-sector customers</span><b>${h.customers+r.customers+fin.customers+e.expected_attendance}</b></div><div><span>Combined revenue</span><b>${money(h.revenue+r.revenue+fin.revenue+e.ticket_revenue)}</b></div><div><span>Festival</span><b>${d.detail.festival?.name||'No festival'}</b></div>`;
 document.getElementById('snapshotInsight').textContent=historical?`The selected date has already occurred. Forecast values are compared with the recorded result to show how closely demand matched.`:`Planning view for ${fmtDate(dateValue)}. Demand patterns are used to estimate operational requirements.`;
 const impact=Math.max(0,Math.min(100,Math.round((h.predicted_occupancy*.55)+(Math.min(r.demand_index*30,20))+(Math.min(Math.abs(fin.revenue_change_pct),15))+(Math.min(e.expected_attendance/2,20)))));
 document.getElementById('impactScore').textContent=impact; document.getElementById('impactLevel').textContent=impact>=80?'Very High':impact>=60?'High':impact>=40?'Medium':'Low';
 document.getElementById('impactFactors').innerHTML=[['Festival / Holiday',d.detail.festival?'High':'Low'],['Hospitality demand',h.predicted_occupancy>=75?'High':h.predicted_occupancy>=50?'Medium':'Low'],['Retail demand',r.demand_index>=1.25?'High':r.demand_index>=1?'Medium':'Low'],['Financial movement',Math.abs(fin.revenue_change_pct)>=15?'High':Math.abs(fin.revenue_change_pct)>0?'Medium':'Low'],['Entertainment attendance',e.expected_attendance>=80?'High':e.expected_attendance>=50?'Medium':'Low']].map(x=>`<div class="factor"><span>${x[0]}</span><span class="badge ${x[1]==='Medium'?'medium':''} ${x[1]==='Low'?'low':''}">${x[1]}</span></div>`).join('');
 await loadDemandDrivers(d); document.getElementById('recommendations').innerHTML=d.recommendations.map(x=>`<div><span>▣</span><div><b>${x.title}</b><small>${x.reason}</small></div><span class="event-level ${x.priority==='Medium'?'medium':''}">${x.priority}</span></div>`).join('');
 const ep=await (await fetch('/api/events',{cache:'no-store'})).json(); const events=(ep.events||[]).filter(x=>x.date>=localISODate()).sort((a,b)=>a.date.localeCompare(b.date)).slice(0,5);
 document.getElementById('eventsList').innerHTML=events.length?events.map(x=>`<div class="event-row"><i class="event-dot"></i><div><b>${x.name}</b><small>${fmtDate(x.date)}${x.venue?' · '+x.venue:''}</small></div><span class="event-level ${x.impact_level==='Medium'?'medium':''}">${x.impact_level||'Event'}</span></div>`).join(''):'<p class="muted">No upcoming events available.</p>';
 await loadWeather(); await loadWeatherImpact(dateValue); await renderCalendar(calendarYear,calendarMonth); await renderMonthlySummary(calendarYear);
}

async function loadDemandDrivers(d){
 const box=document.getElementById('demandDrivers');
 try{const ep=await (await fetch('/api/events',{cache:'no-store'})).json();const nearby=(ep.events||[]).filter(x=>x.date>=dashboardDateValue).sort((a,b)=>a.date.localeCompare(b.date)).slice(0,3);
 box.innerHTML=nearby.length?`<b>Upcoming demand drivers</b>`+nearby.map(x=>`<div class="demand-driver"><span>📍 ${x.name}</span><small>${fmtDate(x.date)}${x.venue?' · '+x.venue:''}</small></div>`).join(''):`<b>Demand drivers</b><div class="demand-driver"><span>📅 Seasonal demand</span><small>${d.detail?.hospitality?.purpose||'Date-specific activity'}</small></div>`}catch(e){box.innerHTML='<b>Demand drivers</b><div class="demand-driver">Seasonal and local demand signals</div>'}
}
async function loadWeather(){const el=document.getElementById('weatherLive');try{const w=await (await fetch('/api/live/weather',{cache:'no-store'})).json();el.innerHTML=`<b>Live weather · ${w.location.name}</b><span>${w.temperature_c}°C · feels ${w.feels_like_c}°C · humidity ${w.humidity_pct}% · rain ${w.precipitation_mm} mm</span><small>${w.source}</small>`;document.getElementById('weatherMain').innerHTML=`<div class="weather-stat"><div class="weather-icon">🌤️</div><span class="label">Temperature</span><strong>${w.temperature_c}°C</strong><p>Feels like ${w.feels_like_c}°C</p></div><div class="weather-stat"><div class="weather-icon">💧</div><span class="label">Humidity</span><strong>${w.humidity_pct}%</strong><p>Rain ${w.precipitation_mm} mm · wind ${w.wind_kmh} km/h</p></div>`;document.getElementById('weatherDrivers').innerHTML='<div class="weather-driver"><b>Conditions</b><span>'+w.description+'</span></div><div class="weather-driver"><b>Location</b><span>New Delhi</span></div>';}catch(e){el.innerHTML='<b>Live weather unavailable</b><span>Check your connection</span>';document.getElementById('weatherMain').innerHTML='<div class="weather-stat"><strong>Unavailable</strong><p>Weather provider could not be reached.</p></div>'}}
async function loadWeatherImpact(dateValue){const box=document.getElementById('weatherImpactBox');try{const x=await (await fetch('/api/forecast/weather-impact?date='+dateValue,{cache:'no-store'})).json();const pct=Number(x.customer_impact_pct||0);box.innerHTML=`<span>Selected-date customer effect</span><strong class="${pct<0?'negative':'positive'}">${pct>=0?'+':''}${pct.toFixed(1)}%</strong><p>${x.weather_available?`Estimated demand effect: ${x.baseline_customers} → ${x.weather_adjusted_customers}. ${x.reasons.join(' · ')}`:'Live weather forecast is unavailable for this selected date.'}</p>`}catch(e){box.innerHTML='<span>Selected-date customer effect</span><strong>--</strong><p>Weather analysis unavailable.</p>'}}

async function renderCalendar(year,month){
 const res=await (await fetch(`/api/calendar?year=${year}&month=${month}`,{cache:'no-store'})).json();document.getElementById('calendarTitle').textContent=new Date(year,month-1,1).toLocaleDateString('en-IN',{month:'long',year:'numeric'});
 const days=res.days||[], max=Math.max(...days.map(x=>x.customers),1), first=new Date(year,month-1,1).getDay();let html='';
 for(let i=0;i<first;i++)html+='<div class="calendar-day muted-day"></div>';
 days.forEach(d=>{const pct=d.customers/max*100;const cls=pct>=75?'high':pct>=50?'medium':'low';html+=`<div class="calendar-day ${cls} ${d.date===dashboardDateValue?'selected':''}" onclick="selectCalendarDate('${d.date}')"><span class="day-number">${Number(d.date.slice(-2))}</span><div class="day-customers">${d.customers} cust.</div><div class="day-bar" style="width:${Math.max(12,Math.round(pct))}%"></div>${d.festival?`<i class="festival-dot"></i><span class="festival-name">${d.festival.name}</span>`:''}</div>`});
 document.getElementById('demandCalendar').innerHTML=html; const avg=days.length?days.reduce((a,x)=>a+x.customers,0)/days.length:0; const past=year<Number(localISODate().slice(0,4)) || (year===Number(localISODate().slice(0,4)) && month<Number(localISODate().slice(5,7))); document.getElementById('monthAverageBanner').innerHTML=`<b>${new Date(year,month-1,1).toLocaleDateString('en-IN',{month:'long',year:'numeric'})}</b><span>${Number(res.average_customers||avg).toFixed(1)} customers/day</span><small>${res.average_label|| (past?'Historical average':'Predicted average')}</small>`;
 document.getElementById('calendarLegend').innerHTML='<span><i class="legend-dot normal"></i>Normal</span><span><i class="legend-dot medium"></i>Medium</span><span><i class="legend-dot high"></i>High</span><span><i class="legend-dot festival"></i>Festival</span>';
}
async function renderMonthlySummary(year){const res=await (await fetch('/api/monthly-summary?year='+year,{cache:'no-store'})).json();document.getElementById('monthlyRows').innerHTML=(res.months||[]).map(m=>`<tr class="${m.status==='predicted'?'predicted-month':''}"><td><b>${m.month_name}</b> <em class="month-status">${m.status==='predicted'?'Predicted':'Historical'}</em></td><td>${Number(m.avg_all_customers||0).toFixed(1)}</td><td>${Number(m.avg_hospitality_customers||0).toFixed(1)}</td><td>${Number(m.avg_retail_customers||0).toFixed(1)}</td><td>${Number(m.avg_financial_customers||0).toFixed(1)}</td><td>${Number(m.avg_entertainment_customers||0).toFixed(1)}</td><td>${money(m.avg_hospitality_revenue)}</td><td>${money(m.avg_retail_revenue)}</td><td>${money(m.avg_financial_revenue)}</td><td>${money(m.avg_entertainment_revenue)}</td></tr>`).join('')
}
function selectCalendarDate(d){dashboardDateValue=d;calendarYear=+d.slice(0,4);calendarMonth=+d.slice(5,7);document.getElementById('dashboardDate').value=d;loadDashboard(d)}
document.addEventListener('DOMContentLoaded',()=>{document.getElementById('prevMonth')?.addEventListener('click',()=>{calendarMonth--;if(calendarMonth<1){calendarMonth=12;calendarYear--;}renderCalendar(calendarYear,calendarMonth)});document.getElementById('nextMonth')?.addEventListener('click',()=>{calendarMonth++;if(calendarMonth>12){calendarMonth=1;calendarYear++;}renderCalendar(calendarYear,calendarMonth)});loadDashboard(dashboardDateValue)});
