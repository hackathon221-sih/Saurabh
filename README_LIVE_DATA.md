# SECTORIQ AI — Live Data Phase

This phase adds live external data without replacing the existing UI.

## Live sources

- Open-Meteo: current weather + 7-day forecast for New Delhi.
- Nager.Date: India public holidays/festivals.
- Google Calendar: optional, for a public/shared calendar when API key + calendar ID are configured.
- Ticketmaster Discovery API: optional event source when an API key is configured.
- Existing SQLite database: fallback and source for your own sector data.

## Important accuracy distinction

External API values are live source data. The sector demand numbers are still model estimates. They should not be presented as real-world measured demand unless you connect actual hotel, retail, financial and entertainment datasets.

## Setup

1. Install requirements:
   `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`.
3. Add optional API credentials.
4. Run `python app.py`.

The dashboard refreshes live weather/events every 5 minutes. The backend caches external calls to reduce unnecessary requests.
