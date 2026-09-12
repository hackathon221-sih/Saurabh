from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from pathlib import Path
import tempfile
import os
import pandas as pd
from datetime import datetime, date
from database.db import init_db
from services.intelligence import get_events, get_locations
from services.live_data import weather, live_events, live_status
from services.excel_data import upcoming_festival, festival_for_date, all_sector_detail, recommendations_for_date, load_data, monthly_summary, monthly_forecast, forecast_for_month, activate_dataset, dataset_info

app = Flask(__name__)
init_db()

@app.route('/')
def index(): return render_template('dashboard.html')
@app.route('/events')
def events_page(): return render_template('events.html')
@app.route('/forecast')
def forecast_page(): return render_template('forecast.html')
@app.route('/sectors')
def sectors_page(): return render_template('sectors.html')
@app.route('/hospitality')
def hospitality_page(): return render_template('hospitality.html')
@app.route('/recommendations')
def recommendations_page(): return render_template('recommendations.html')
@app.route('/reports')
def reports_page(): return render_template('reports.html')
@app.route('/settings')
def settings_page(): return render_template('settings.html')
@app.route('/data')
def data_page(): return render_template('data.html')

@app.route('/api/data/info')
def data_info_api():
    try: return jsonify(dataset_info())
    except Exception as exc: return jsonify({'error':str(exc)}),500

@app.route('/api/data/upload', methods=['POST'])
def data_upload_api():
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'error':'Please choose an Excel file.'}),400
    if not file.filename.lower().endswith(('.xlsx','.xls')):
        return jsonify({'error':'Only .xlsx or .xls files are supported.'}),400
    temp_path=None
    try:
        fd, temp_path = tempfile.mkstemp(suffix=Path(file.filename).suffix)
        os.close(fd); file.save(temp_path)
        # Validate by loading through the same normalisation pipeline.
        import pandas as pd
        xls=pd.ExcelFile(temp_path)
        sheet='Daily Sector Data' if 'Daily Sector Data' in xls.sheet_names else xls.sheet_names[0]
        preview=pd.read_excel(temp_path, sheet_name=sheet)
        cols={str(c).strip().lower().replace(' ','_'):c for c in preview.columns}
        if not any(k in cols for k in ['date','day','datetime']) or not any(k in cols for k in ['sector','industry','category']) or not any(k in cols for k in ['customer_count','customers','customer','visitors','attendance']):
            return jsonify({'error':'The workbook must contain Date, Sector and Customer_Count (or equivalent) columns.'}),400
        activate_dataset(temp_path)
        return jsonify({'ok':True,'message':f'{secure_filename(file.filename)} is now the active dataset.','dataset':dataset_info(),'forecast':monthly_forecast(6)})
    except Exception as exc:
        return jsonify({'error':str(exc)}),400
    finally:
        if temp_path:
            try: os.remove(temp_path)
            except OSError: pass

@app.route('/api/forecast/monthly')
def monthly_forecast_api():
    try:
        count=max(1,min(12,int(request.args.get('months','6'))))
        return jsonify({'forecast':monthly_forecast(count),'dataset':dataset_info()})
    except Exception as exc: return jsonify({'error':str(exc)}),500

@app.route('/api/health')
def health(): return jsonify({'status':'ok','service':'SECTORIQ AI backend','time':datetime.now().astimezone().isoformat()})

@app.route('/api/live/weather')
def live_weather_api():
    try: return jsonify(weather())
    except Exception as exc: return jsonify({'error':str(exc),'source':'Open-Meteo'}),502

@app.route('/api/live/status')
def live_status_api(): return jsonify(live_status())

@app.route('/api/events')
def events_api():
    payload=live_events([])
    # Excel festivals are the authoritative festival source for this project.
    try:
        _,_,festivals,_,_,_=load_data()
        for _,r in festivals.iterrows():
            payload['events'].append({'name':r['Festival/Event'],'date':r['Date'].date().isoformat(),'event_type':'Festival/Holiday','impact_level':'High','source':'Uploaded Excel','religion':r['Religion/Category']})
        unique={(e['name'],e['date']):e for e in payload['events']}
        payload['events']=sorted(unique.values(),key=lambda x:x['date'])
    except Exception: pass
    return jsonify(payload)

@app.route('/api/locations')
def locations_api(): return jsonify(get_locations())

@app.route('/api/dashboard')
def dashboard_api():
    raw=request.args.get('date','')
    try: target=date.fromisoformat(raw) if raw else date.today()
    except ValueError: return jsonify({'error':'Use YYYY-MM-DD'}),400
    d=all_sector_detail(target)
    h,r,f,e=d['hospitality'],d['retail'],d['finance'],d['entertainment']
    return jsonify({'updated':datetime.now().astimezone().isoformat(),'date':target.isoformat(),'upcoming_festival':upcoming_festival(target),'sectors':{
        'hospitality':{'value':h.get('predicted_occupancy',0),'change':h.get('staff_increase',0),'label':'Predicted Occupancy'},
        'retail':{'value':round((r.get('customers',0)/max(1,43.2)-1)*100,1),'change':r.get('staff_increase',0),'label':'Demand vs average'},
        'finance':{'value':f.get('revenue_change_pct',0),'change':f.get('staff_increase',0),'label':'Financial activity change'},
        'entertainment':{'value':round((e.get('expected_attendance',0)/max(1,50.7)-1)*100,1),'change':e.get('staff_increase',0),'label':'Attendance vs average'}
    },'detail':d,'recommendations':recommendations_for_date(target)})

@app.route('/api/sector/<sector>')
def sector_api(sector):
    raw=request.args.get('date','')
    try: target=date.fromisoformat(raw) if raw else date.today()
    except ValueError: return jsonify({'error':'Use YYYY-MM-DD'}),400
    d=all_sector_detail(target)
    key={'hospitality':'hospitality','retail':'retail','financial':'finance','finance':'finance','entertainment':'entertainment'}.get(sector.lower())
    if not key: return jsonify({'error':'Unknown sector'}),404
    return jsonify(d[key])

@app.route('/api/upcoming-festival')
def upcoming_festival_api():
    raw=request.args.get('from','')
    try: start=date.fromisoformat(raw) if raw else date.today()
    except ValueError: return jsonify({'error':'Use YYYY-MM-DD'}),400
    return jsonify(upcoming_festival(start))

@app.route('/api/recommendations')
def recommendations_api():
    raw=request.args.get('date','')
    try: target=date.fromisoformat(raw) if raw else date.today()
    except ValueError: return jsonify({'error':'Use YYYY-MM-DD'}),400
    return jsonify(recommendations_for_date(target))

@app.route('/api/forecast/weather-impact')
def weather_impact_api():
    raw=request.args.get('date','')
    try: target=date.fromisoformat(raw) if raw else date.today()
    except ValueError: return jsonify({'error':'Use YYYY-MM-DD'}),400
    detail=all_sector_detail(target)
    base_customers=detail['hospitality'].get('customers',0)
    try:
        w=weather(); daily=w.get('daily',{}); dates=daily.get('time',[])
        if target.isoformat() in dates:
            i=dates.index(target.isoformat()); rain=(daily.get('precipitation_probability_max') or [0]*len(dates))[i] or 0
            tmax=(daily.get('temperature_2m_max') or [None]*len(dates))[i]
            impact=0
            reasons=[]
            if rain>=70: impact=-12; reasons.append(f'High rain probability ({rain}%)')
            elif rain>=40: impact=-6; reasons.append(f'Moderate rain probability ({rain}%)')
            else: reasons.append(f'Low rain probability ({rain}%)')
            if tmax is not None and tmax>=35: impact-=4; reasons.append(f'High temperature ({tmax}°C)')
            elif tmax is not None and tmax<=15: impact-=3; reasons.append(f'Cool temperature ({tmax}°C)')
            adjusted=max(0,round(base_customers*(1+impact/100)))
            return jsonify({'date':target.isoformat(),'weather_available':True,'rain_probability':rain,'max_temperature':tmax,'customer_impact_pct':impact,'baseline_customers':base_customers,'weather_adjusted_customers':adjusted,'reasons':reasons,'source':w.get('source','Open-Meteo')})
    except Exception as exc:
        return jsonify({'date':target.isoformat(),'weather_available':False,'baseline_customers':base_customers,'message':str(exc)})
    return jsonify({'date':target.isoformat(),'weather_available':False,'baseline_customers':base_customers,'customer_impact_pct':0,'message':'Live weather forecast is available only inside the provider forecast window for the selected date.'})


@app.route('/api/monthly-summary')
def monthly_summary_api():
    raw=request.args.get('year','')
    try: year=int(raw) if raw else datetime.now().year
    except ValueError: return jsonify({'error':'Use valid year'}),400
    return jsonify({'year':year,'months':monthly_summary(year)})

@app.route('/api/calendar')
def calendar_api():
    raw_year=request.args.get('year',''); raw_month=request.args.get('month','')
    try:
        year=int(raw_year) if raw_year else datetime.now().year; month=int(raw_month) if raw_month else datetime.now().month
        if month<1 or month>12: raise ValueError
    except ValueError: return jsonify({'error':'Use valid year/month'}),400
    daily, summary, festivals, _, _, _=load_data()
    month_start=date(year,month,1); today=date.today(); is_historical=month_start < date(today.year,today.month,1)
    rows=summary[(summary['Date'].dt.year==year)&(summary['Date'].dt.month==month)].copy()
    festival_map={r['Date'].date().isoformat():{'name':r['Festival/Event'],'category':r['Religion/Category']} for _,r in festivals[(festivals['Date'].dt.year==year)&(festivals['Date'].dt.month==month)].iterrows()} if not festivals.empty else {}
    result=[]
    # Historical months use recorded daily values. Current/future months use the forecasting engine.
    if is_historical and not rows.empty:
        for _,r in rows.iterrows():
            ds=r['Date'].date().isoformat(); sector_rows=daily[daily['Date'].dt.date==r['Date'].date()]
            sectors={str(x['Sector']).lower().replace(' ','_'):int(x['Customer_Count']) for _,x in sector_rows.iterrows()}
            result.append({'date':ds,'day':r['Day'] if 'Day' in r else r['Date'].strftime('%A'),'customers':int(r['Total_Customers']),'revenue':float(r['Total_Revenue']),'festival':festival_map.get(ds),'sectors':sectors,'mode':'historical'})
        avg=sum(x['customers'] for x in result)/len(result) if result else 0
        status='historical'; label='Historical average'
    else:
        # Forecast daily customer demand from recent monthly/weekday patterns.
        target=forecast_for_month(year, month)
        if target is None:
            target=pred[0] if pred else {'all':0}
        hist=daily.copy(); hist['weekday']=hist['Date'].dt.dayofweek
        overall=float(hist.groupby('Date')['Customer_Count'].sum().mean()) if not hist.empty else max(1,float(target.get('all',0)))
        weekday_avg=hist.groupby('weekday')['Customer_Count'].sum().groupby(level=0).mean() if not hist.empty else pd.Series()
        weekday_mean=float(weekday_avg.mean()) if len(weekday_avg) else overall
        import calendar as _cal
        for day_num in range(1,_cal.monthrange(year,month)[1]+1):
            dt=date(year,month,day_num); wd=dt.weekday(); factor=(float(weekday_avg.get(wd,weekday_mean))/weekday_mean) if weekday_mean else 1
            customers=max(0,round(float(target.get('all',overall))*factor)); ds=dt.isoformat()
            result.append({'date':ds,'day':dt.strftime('%A'),'customers':customers,'revenue':0,'festival':festival_map.get(ds),'sectors':{},'mode':'predicted'})
        avg=sum(x['customers'] for x in result)/len(result) if result else float(target.get('all',0)); status='predicted'; label='Predicted average'
    return jsonify({'year':year,'month':month,'days':result,'status':status,'average_customers':round(avg,1),'average_label':label})

@app.route('/api/search')
def search_api():
    q=request.args.get('q','').lower().strip()
    if not q:return jsonify([])
    payload=events_api().get_json()
    return jsonify([e for e in payload['events'] if q in e.get('name','').lower() or q in e.get('event_type','').lower()])

if __name__=='__main__': app.run(debug=True,host='127.0.0.1',port=5000)
