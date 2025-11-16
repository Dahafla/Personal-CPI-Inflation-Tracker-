import os, requests, pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv


load_dotenv()
engine = create_engine(os.getenv("DB_URL"))
BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


# Headline CPI-U NSA series id (US city average, all items): CUUR0000SA0
SERIES = ["CUUR0000SA0"]


def fetch_cpi(series_ids=SERIES, start=2018, end=2030):
    api_key = os.getenv("BLS_API_KEY", "").strip()
    payload = {
    "seriesid": series_ids,
    "startyear": str(start),
    "endyear": str(end),
}
    
    if api_key:
        payload["registrationkey"] = api_key

    r = requests.post(BLS_URL, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    
    if "Results" not in data:
        print("❌ BLS API did not return 'Results'. Full response:")
        print(data)
        raise SystemExit("BLS API error – check API key or payload.")
    
    rows=[]


    for s in data["Results"]["series"]:
        sid = s['seriesID']
        for d in s['data']:
            if d['period'].startswith('M'):
                rows.append({
                    'series_id': sid,
                    'year': int(d['year']),
                    'm': int(d['period'][1:]),
                    'value': float(d['value'])
                    })
    df = pd.DataFrame(rows)
    df['month'] = pd.to_datetime(df['year'].astype(str)+'-'+df['m'].astype(str)+'-01')
    df = df[['month','series_id','value']].sort_values('month')
    df.to_sql('cpi_series', engine, if_exists='replace', index=False)
    print("Stored CPI in SQLite: cpi_series")


if __name__ == "__main__":
    fetch_cpi()