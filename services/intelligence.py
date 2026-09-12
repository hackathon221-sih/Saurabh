from datetime import datetime, timedelta
import math
from database.db import get_connection

SECTOR_BASELINES = {
    'hospitality': 80,
    'retail': 32,
    'finance': 22,
    'entertainment': 30,
}

def get_events():
    conn = get_connection()
    rows = conn.execute('SELECT id,name,date,event_type,impact_level,latitude,longitude FROM events ORDER BY date').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_locations():
    conn = get_connection()
    rows = conn.execute('SELECT id,name,sector,latitude,longitude FROM locations').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def impact_analysis(event_name='Diwali Festival'):
    event = next((e for e in get_events() if e['name'] == event_name), None)
    if not event:
        event = get_events()[0]
    factors = [
        ('Festival/Holiday','High'),
        ('Weekend','Medium'),
        ('Good Weather','Medium'),
        ('Large Crowd','High'),
        ('Location Proximity','High'),
        ('Historical Demand','High'),
    ]
    return {'event': event['name'], 'score': 85, 'level': 'Very High', 'factors': factors}

def forecast():
    dates=[]; series={k:[] for k in SECTOR_BASELINES}
    start=datetime(2026,9,8)
    for i in range(30):
        d=start+timedelta(days=i)
        dates.append(d.strftime('%b %d'))
        series['hospitality'].append(round(34+i*1.75+4*math.sin(i/3),1))
        series['retail'].append(round(20+i*1.25+3*math.sin(i/4),1))
        series['finance'].append(round(15+i*1.0+2*math.sin(i/5),1))
        series['entertainment'].append(round(27+i*1.45+3*math.cos(i/4),1))
    series['dates']=dates
    return series

def recommendations():
    return [
        {'sector':'Hospitality','title':'Increase staff by 15%','reason':'High demand expected due to festivals','priority':'High'},
        {'sector':'Retail','title':'Increase inventory for key products','reason':'Sales may rise by 40%+','priority':'High'},
        {'sector':'Financial','title':'Prepare operational capacity','reason':'Transaction volume likely to increase','priority':'Medium'},
        {'sector':'Entertainment','title':'Increase venue staffing','reason':'Higher event attendance expected','priority':'High'},
    ]
