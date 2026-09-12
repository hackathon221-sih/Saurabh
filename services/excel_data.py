from pathlib import Path
from functools import lru_cache
from datetime import date
import math
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
DAILY_XLSX = DATA_DIR / 'hotel_daily_2026_all_religions_date_only.xlsx'
RETAIL_XLSX = DATA_DIR / 'hotel_retail_goods_list.xlsx'
ACTIVE_DAILY_XLSX = DATA_DIR / 'active_dataset.xlsx'


def _dataset_path():
    return ACTIVE_DAILY_XLSX if ACTIVE_DAILY_XLSX.exists() else DAILY_XLSX


def _find_col(df, candidates):
    norm = {str(c).strip().lower().replace(' ', '_').replace('-', '_'): c for c in df.columns}
    for c in candidates:
        key = c.strip().lower().replace(' ', '_').replace('-', '_')
        if key in norm:
            return norm[key]
    for original in df.columns:
        s = str(original).strip().lower()
        if any(c.replace('_',' ') in s.replace('_',' ') for c in candidates):
            return original
    return None


def _normalise_daily(df):
    df = df.copy()
    date_col = _find_col(df, ['date', 'day', 'datetime'])
    sector_col = _find_col(df, ['sector', 'industry', 'category'])
    customer_col = _find_col(df, ['customer_count', 'customers', 'customer', 'visitors', 'attendance'])
    revenue_col = _find_col(df, ['revenue_₹', 'revenue', 'sales', 'amount', 'transaction_value'])
    if not date_col or not sector_col or not customer_col:
        raise ValueError('Dataset needs Date, Sector and Customer_Count (or equivalent) columns.')
    rename = {date_col:'Date', sector_col:'Sector', customer_col:'Customer_Count'}
    if revenue_col: rename[revenue_col] = 'Revenue (₹)'
    df = df.rename(columns=rename)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Customer_Count'] = pd.to_numeric(df['Customer_Count'], errors='coerce').fillna(0)
    if 'Revenue (₹)' not in df.columns:
        df['Revenue (₹)'] = 0.0
    df['Revenue (₹)'] = pd.to_numeric(df['Revenue (₹)'], errors='coerce').fillna(0)
    df['Sector'] = df['Sector'].astype(str).str.strip()
    mapping = {'hospitality':'Hospitality','hotel':'Hospitality','retail':'Retail','financial services':'Financial Services','finance':'Financial Services','financial':'Financial Services','entertainment':'Entertainment'}
    df['Sector'] = df['Sector'].str.lower().map(lambda x: mapping.get(x, x.title()))
    df = df.dropna(subset=['Date'])
    if 'Purpose' not in df.columns: df['Purpose'] = ''
    if 'Average_Spend_Per_Customer (₹)' not in df.columns: df['Average_Spend_Per_Customer (₹)'] = df['Revenue (₹)'] / df['Customer_Count'].replace(0, pd.NA)
    if 'Recommended Staff Increase (%)' not in df.columns: df['Recommended Staff Increase (%)'] = 0.0
    if 'Staffing Recommendation' not in df.columns: df['Staffing Recommendation'] = ''
    return df


@lru_cache(maxsize=1)
def load_data():
    path = _dataset_path()
    xls = pd.ExcelFile(path)
    sheets = set(xls.sheet_names)
    if 'Daily Sector Data' in sheets:
        daily = pd.read_excel(path, sheet_name='Daily Sector Data', parse_dates=['Date'])
    else:
        daily = pd.read_excel(path, sheet_name=xls.sheet_names[0])
    daily = _normalise_daily(daily)
    if 'Daily Summary' in sheets:
        summary = pd.read_excel(path, sheet_name='Daily Summary', parse_dates=['Date'])
        if 'Total_Customers' not in summary.columns:
            summary = daily.groupby('Date', as_index=False).agg(Total_Customers=('Customer_Count','sum'), Total_Revenue=('Revenue (₹)','sum'))
    else:
        summary = daily.groupby('Date', as_index=False).agg(Total_Customers=('Customer_Count','sum'), Total_Revenue=('Revenue (₹)','sum'))
    if 'Festival Calendar' in sheets:
        festivals = pd.read_excel(path, sheet_name='Festival Calendar', parse_dates=['Date'])
        if 'Festival/Event' not in festivals.columns:
            festivals = pd.DataFrame(columns=['Date','Festival/Event','Religion/Category'])
    else:
        festivals = pd.DataFrame(columns=['Date','Festival/Event','Religion/Category'])
    if not festivals.empty:
        festivals['Date'] = pd.to_datetime(festivals['Date'], errors='coerce')
    if 'Religion/Category' not in festivals.columns: festivals['Religion/Category'] = ''
    if 'Festival/Event' not in festivals.columns: festivals['Festival/Event'] = ''
    staffing = pd.read_excel(path, sheet_name='Staffing Plan') if 'Staffing Plan' in sheets else pd.DataFrame()
    try:
        goods = pd.read_excel(RETAIL_XLSX, sheet_name='Retail Goods')
        category_summary = pd.read_excel(RETAIL_XLSX, sheet_name='Category Summary')
    except Exception:
        goods = pd.DataFrame(columns=['Good','Retail Category']); category_summary = pd.DataFrame(columns=['Retail Category','Number_of_Goods'])
    return daily, summary, festivals, staffing, goods, category_summary


def activate_dataset(upload_path):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(upload_path, ACTIVE_DAILY_XLSX)
    load_data.cache_clear()


def dataset_info():
    path = _dataset_path()
    daily, summary, festivals, _, _, _ = load_data()
    return {'filename': path.name, 'active_upload': path == ACTIVE_DAILY_XLSX, 'start_date': daily['Date'].min().date().isoformat() if not daily.empty else None, 'end_date': daily['Date'].max().date().isoformat() if not daily.empty else None, 'rows': int(len(daily)), 'sectors': sorted(daily['Sector'].dropna().unique().tolist())}


def _clean(v):
    if pd.isna(v): return None
    if hasattr(v, 'item'):
        try: return v.item()
        except Exception: pass
    return v

def _date_rows(df, target): return df[df['Date'].dt.date == target]

def upcoming_festival(from_date=None):
    _, _, festivals, _, _, _ = load_data(); from_date = from_date or date.today()
    if festivals.empty: return None
    f = festivals[festivals['Date'].dt.date >= from_date].sort_values('Date')
    if f.empty: return None
    row = f.iloc[0]; return {'date': row['Date'].date().isoformat(), 'name': row['Festival/Event'], 'category': row['Religion/Category']}

def festival_for_date(target):
    _, _, festivals, _, _, _ = load_data()
    if festivals.empty: return None
    rows = _date_rows(festivals, target)
    if rows.empty: return None
    row = rows.iloc[0]; return {'date': target.isoformat(), 'name': row['Festival/Event'], 'category': row['Religion/Category']}

def _sector_row(target, sector):
    daily, _, _, _, _, _ = load_data(); rows = daily[(daily['Date'].dt.date == target) & (daily['Sector'] == sector)]
    return rows.iloc[0].to_dict() if not rows.empty else None

def _sector_baseline(target, sector, metric, exclude_target=True):
    daily, _, _, _, _, _ = load_data(); d = daily[daily['Sector'] == sector].copy()
    same_weekday = d[d['Date'].dt.dayofweek == target.weekday()].copy()
    if exclude_target: same_weekday = same_weekday[same_weekday['Date'].dt.date != target]
    values = pd.to_numeric(same_weekday[metric], errors='coerce').dropna() if metric in d.columns else pd.Series(dtype=float)
    if not values.empty: return float(values.mean())
    values = pd.to_numeric(d[metric], errors='coerce').dropna() if metric in d.columns else pd.Series(dtype=float)
    return float(values.mean()) if not values.empty else 0.0

def _prediction_accuracy(actual, predicted):
    if actual is None or predicted is None or float(actual) <= 0: return None
    return round(max(0.0, 100.0 - abs(float(actual)-float(predicted))/float(actual)*100.0), 1)

def demand_level(pct):
    if pct >= 85: return 'Very High'
    if pct >= 70: return 'High'
    if pct >= 50: return 'Moderate'
    return 'Low'

def hospitality_detail(target, total_rooms=100):
    row = _sector_row(target, 'Hospitality')
    if not row: return {'date': target.isoformat(), 'available': False}
    actual = float(row['Customer_Count']); predicted_customers = _sector_baseline(target,'Hospitality','Customer_Count')
    demand_ratio = predicted_customers / max(1.0,_sector_baseline(target,'Hospitality','Customer_Count',False)); predicted_occupancy=max(.25,min(.98,.70*demand_ratio)); predicted_booked=min(total_rooms,max(0,round(total_rooms*predicted_occupancy))); estimated_occupied=min(predicted_booked,round(predicted_booked*.82)); left=max(0,total_rooms-predicted_booked); accuracy=_prediction_accuracy(actual,predicted_customers)
    return {'available':True,'date':target.isoformat(),'display_date':target.strftime('%A, %d %B %Y'),'festival':festival_for_date(target),'purpose':_clean(row['Purpose']),'customers':int(actual),'predicted_customers':round(predicted_customers),'prediction_accuracy':accuracy,'avg_spend':float(row['Average_Spend_Per_Customer (₹)']),'revenue':float(row['Revenue (₹)']),'staff_increase':float(row['Recommended Staff Increase (%)']),'staffing_recommendation':_clean(row['Staffing Recommendation']),'total_rooms':int(total_rooms),'estimated_occupied':int(estimated_occupied),'predicted_booked':int(predicted_booked),'rooms_left':int(left),'predicted_occupancy':round(predicted_occupancy*100,1),'demand_level':demand_level(predicted_occupancy*100)}

def retail_detail(target):
    row=_sector_row(target,'Retail'); daily,_,_,_,goods,category_summary=load_data()
    if not row:return {'date':target.isoformat(),'available':False}
    actual=float(row['Customer_Count']); predicted_customers=_sector_baseline(target,'Retail','Customer_Count'); avg_customers=_sector_baseline(target,'Retail','Customer_Count',False); demand_index=predicted_customers/avg_customers if avg_customers else 1; total_goods=max(1,len(goods)); categories=[]
    for _,c in category_summary.iterrows():
        cat=c['Retail Category']; count=int(c['Number_of_Goods']); recommended_units=max(1,math.ceil(predicted_customers*(count/total_goods)*1.25)); examples=goods[goods['Retail Category']==cat]['Good'].head(3).tolist(); categories.append({'category':cat,'goods_count':count,'recommended_units':recommended_units,'examples':examples})
    categories.sort(key=lambda x:x['recommended_units'],reverse=True)
    return {'available':True,'date':target.isoformat(),'display_date':target.strftime('%A, %d %B %Y'),'festival':festival_for_date(target),'purpose':_clean(row['Purpose']),'customers':int(actual),'predicted_customers':round(predicted_customers),'prediction_accuracy':_prediction_accuracy(actual,predicted_customers),'revenue':float(row['Revenue (₹)']),'staff_increase':float(row['Recommended Staff Increase (%)']),'staffing_recommendation':_clean(row['Staffing Recommendation']),'demand_index':round(demand_index,2),'recommended_total_units':sum(x['recommended_units'] for x in categories),'goods_count':len(goods),'categories':categories}

def finance_detail(target):
    row=_sector_row(target,'Financial Services')
    if not row:return {'date':target.isoformat(),'available':False}
    actual_revenue=float(row['Revenue (₹)']); actual_customers=float(row['Customer_Count']); spend=float(row['Average_Spend_Per_Customer (₹)']); expected_revenue=_sector_baseline(target,'Financial Services','Revenue (₹)'); expected_customers=_sector_baseline(target,'Financial Services','Customer_Count'); delta=actual_revenue-expected_revenue; pct=(delta/expected_revenue*100) if expected_revenue else 0; cdelta=actual_customers-expected_customers; cpct=(cdelta/expected_customers*100) if expected_customers else 0
    return {'available':True,'date':target.isoformat(),'display_date':target.strftime('%A, %d %B %Y'),'festival':festival_for_date(target),'purpose':_clean(row['Purpose']),'customers':int(actual_customers),'predicted_customers':round(expected_customers),'prediction_accuracy':_prediction_accuracy(actual_customers,expected_customers),'average_spend':spend,'revenue':actual_revenue,'expected_revenue':round(expected_revenue,2),'baseline_revenue':round(expected_revenue,2),'revenue_change_amount':round(delta,2),'revenue_change_pct':round(pct,1),'customer_change':round(cdelta,1),'customer_change_pct':round(cpct,1),'staff_increase':float(row['Recommended Staff Increase (%)']),'staffing_recommendation':_clean(row['Staffing Recommendation']),'direction':'Increase' if delta>0 else 'Decrease' if delta<0 else 'No change'}

def entertainment_detail(target):
    row=_sector_row(target,'Entertainment')
    if not row:return {'date':target.isoformat(),'available':False}
    actual=float(row['Customer_Count']); revenue=float(row['Revenue (₹)']); predicted=_sector_baseline(target,'Entertainment','Customer_Count'); avg=_sector_baseline(target,'Entertainment','Customer_Count',False)
    return {'available':True,'date':target.isoformat(),'display_date':target.strftime('%A, %d %B %Y'),'festival':festival_for_date(target),'purpose':_clean(row['Purpose']),'expected_attendance':int(actual),'predicted_attendance':round(predicted),'prediction_accuracy':_prediction_accuracy(actual,predicted),'ticket_revenue':revenue,'average_spend':float(row['Average_Spend_Per_Customer (₹)']),'staff_increase':float(row['Recommended Staff Increase (%)']),'staffing_recommendation':_clean(row['Staffing Recommendation']),'demand_level':demand_level(predicted/max(1,avg)*100),'venue_capacity_recommendation':max(0,math.ceil(predicted*1.15))}

def _monthly_actual(year, month):
    daily,_,_,_,_,_=load_data(); m=daily[(daily['Date'].dt.year==year)&(daily['Date'].dt.month==month)].copy()
    if m.empty:return None
    out={'month':month,'month_name':date(year,month,1).strftime('%B'),'days_recorded':int(m['Date'].dt.date.nunique()),'avg_all_customers':round(float(m.groupby('Date')['Customer_Count'].sum().mean()),1)}
    for sec,key in [('Hospitality','hospitality'),('Retail','retail'),('Financial Services','financial'),('Entertainment','entertainment')]:
        sm=m[m['Sector']==sec]; out[f'avg_{key}_customers']=round(float(pd.to_numeric(sm['Customer_Count'],errors='coerce').mean()),1) if not sm.empty else 0; out[f'avg_{key}_revenue']=round(float(pd.to_numeric(sm['Revenue (₹)'],errors='coerce').mean()),0) if not sm.empty else 0
    return out

def _forecast_months(year, start_month, count=6):
    daily,_,_,_,_,_=load_data(); monthly=[]
    for period in pd.period_range(f'{year}-{start_month:02d}', periods=count, freq='M'):
        monthly.append(period)
    history=[]
    for p in sorted(daily['Date'].dt.to_period('M').unique()):
        m=daily[daily['Date'].dt.to_period('M')==p]
        if m.empty: continue
        total_avg=float(m.groupby('Date')['Customer_Count'].sum().mean()); vals={ 'all':total_avg }
        for sec,key in [('Hospitality','hospitality'),('Retail','retail'),('Financial Services','financial'),('Entertainment','entertainment')]:
            sm=m[m['Sector']==sec]; vals[key]=float(pd.to_numeric(sm['Customer_Count'],errors='coerce').mean()) if not sm.empty else 0; vals[key+'_revenue']=float(pd.to_numeric(sm['Revenue (₹)'],errors='coerce').mean()) if not sm.empty else 0
        history.append((p,vals))
    # Only use months completed before the first forecast month. This prevents the
    # current month from leaking into its own prediction and makes future-month
    # forecasts genuinely forward-looking.
    first_forecast = monthly[0] if monthly else None
    history = [(p,v) for p,v in history if first_forecast is None or p < first_forecast]
    recent=history[-6:]
    def trend(key):
        if len(recent)<2:return recent[-1][1].get(key,0) if recent else 0
        y=pd.Series([v.get(key,0) for _,v in recent],dtype=float); x=pd.Series(range(len(y)),dtype=float); slope=float(((x-x.mean())*(y-y.mean())).sum()/max(1,((x-x.mean())**2).sum())); pred=float(y.iloc[-1]+slope); return max(0,pred)
    rows=[]
    for p in monthly:
        vals={k:round(trend(k),1) for k in ['all','hospitality','retail','financial','entertainment']}; vals.update({k+'_revenue':round(trend(k+'_revenue'),0) for k in ['hospitality','retail','financial','entertainment']}); vals['month']=p.month; vals['month_name']=p.strftime('%B'); vals['year']=p.year; vals['status']='predicted'; vals['days_in_month']=p.days_in_month; rows.append(vals)
    return rows

def monthly_summary(year=None):
    year=int(year or date.today().year); today=date.today(); rows=[]
    for month in range(1,13):
        actual=_monthly_actual(year,month); month_start=date(year,month,1)
        if actual and month_start < date(today.year,today.month,1): actual['status']='historical'; rows.append(actual)
        elif year==today.year and month>=today.month:
            pred=_forecast_months(year,month,1)[0]; actual = actual or {}; actual.update(pred)
            # For current/future months, the displayed averages must be forecasts.
            actual['avg_all_customers']=pred['all']; actual['avg_hospitality_customers']=pred['hospitality']; actual['avg_retail_customers']=pred['retail']; actual['avg_financial_customers']=pred['financial']; actual['avg_entertainment_customers']=pred['entertainment']
            actual['avg_hospitality_revenue']=pred['hospitality_revenue']; actual['avg_retail_revenue']=pred['retail_revenue']; actual['avg_financial_revenue']=pred['financial_revenue']; actual['avg_entertainment_revenue']=pred['entertainment_revenue']
            actual['status']='predicted'; rows.append(actual)
        elif year>today.year:
            pred=_forecast_months(year,month,1)[0]
            pred.update({'days_recorded':0,'avg_all_customers':pred['all'],'avg_hospitality_customers':pred['hospitality'],'avg_retail_customers':pred['retail'],'avg_financial_customers':pred['financial'],'avg_entertainment_customers':pred['entertainment'],'avg_hospitality_revenue':pred['hospitality_revenue'],'avg_retail_revenue':pred['retail_revenue'],'avg_financial_revenue':pred['financial_revenue'],'avg_entertainment_revenue':pred['entertainment_revenue']})
            rows.append(pred);
    return rows

def monthly_forecast(count=6):
    today=date.today(); return _forecast_months(today.year,today.month,count)

def forecast_for_month(year, month):
    rows=_forecast_months(int(year), int(month), 1)
    return rows[0] if rows else None

def all_sector_detail(target): return {'date':target.isoformat(),'festival':festival_for_date(target),'hospitality':hospitality_detail(target),'retail':retail_detail(target),'finance':finance_detail(target),'entertainment':entertainment_detail(target)}

def recommendations_for_date(target):
    data=all_sector_detail(target); out=[]; h=data['hospitality']; r=data['retail']; f=data['finance']; e=data['entertainment']
    if h.get('available'): out.append({'sector':'Hospitality','title':f"Prepare {h['predicted_booked']} rooms for demand",'reason':f"Predicted demand is {h['predicted_customers']} hospitality customers. Staff plan: +{h['staff_increase']:.1f}%.",'priority':'High' if h['staff_increase']>=20 else 'Medium'})
    if r.get('available'):
        top=r['categories'][:3]; cats=', '.join(f"{x['category']} ({x['recommended_units']} units)" for x in top); out.append({'sector':'Retail','title':f"Stock approximately {r['recommended_total_units']} units",'reason':f"Top category requirements: {cats}. Based on predicted customer demand.",'priority':'High' if r['demand_index']>=1.25 else 'Medium'})
    if f.get('available'):
        sign='increase' if f['revenue_change_amount']>=0 else 'decrease'; out.append({'sector':'Financial Services','title':f"Financial activity expected to {sign} by ₹{abs(f['revenue_change_amount']):,.0f}",'reason':f"Expected revenue is ₹{f['expected_revenue']:,.0f}; movement vs weekday baseline is {f['revenue_change_pct']:+.1f}%.",'priority':'High' if abs(f['revenue_change_pct'])>=15 else 'Medium'})
    if e.get('available'): out.append({'sector':'Entertainment','title':f"Prepare venue capacity for {e['predicted_attendance']} attendees",'reason':f"Expected attendance is {e['predicted_attendance']}; plan around {e['venue_capacity_recommendation']} seats and +{e['staff_increase']:.1f}% staff.",'priority':'High' if e['staff_increase']>=20 else 'Medium'})
    return out
