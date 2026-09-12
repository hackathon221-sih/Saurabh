# SECTORIQ AI — Excel-driven four-sector version

This version continues the original SECTORIQ AI project and uses the two uploaded Excel workbooks as the main business-data source.

## Data files
- `data/hotel_daily_2026_all_religions_date_only.xlsx` — daily sector demand, revenue, staffing, festival calendar.
- `data/hotel_retail_goods_list.xlsx` — retail product catalogue and category counts.

## Run
```powershell
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000`.

## Implemented changes
1. Removed the Hospitality calendar grid. Hospitality uses a date picker and a date-specific intelligence panel.
2. The dashboard automatically finds the next festival from the uploaded Festival Calendar Excel and provides a date selector beside it.
3. Financial Services shows the rupee amount and percentage increase/decrease versus a same-weekday Excel baseline.
4. View Details gives sector-specific outputs: hospitality rooms, retail stock recommendations, finance amount change, and entertainment attendance/revenue/capacity.
5. Removed Map from navigation and dashboard.
6. Recommendations are generated from the selected date's Excel customer/revenue/staffing values.
7. Forecast page is now Weather Impact instead of the old four-line graph. Live Open-Meteo weather is used when the selected date is in the provider's forecast window.
8. Welcome message uses `Team Ctrl Alt Defeat`.

## Important calculation notes
- The hospitality workbook contains customer counts, not room-level booking/occupancy records. The app therefore estimates room demand from the customer-demand pattern and the configured 100-room demo hotel. The UI labels this as an estimate.
- The retail goods workbook contains product/category lists, not stock quantities. Recommended stock units are therefore demand-derived: selected-date retail customers are allocated by category size, with a 25% safety buffer.
- Financial change is directly calculated from workbook revenue against the same-weekday historical baseline.
- Entertainment uses workbook attendance/customer count, revenue, purpose and staffing recommendation.
