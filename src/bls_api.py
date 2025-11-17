import os, requests, pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv


'''
- pulls official CPI time-series data from BLS API
- standardizes dates, sorts the data and write a unified cpi_series
- External data ingestion layer
'''

load_dotenv()
DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL, connect_args={"timeout": 30})

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


# Headline CPI-U NSA series id (US city average, all items): CUUR0000SA0
SERIES_MAP = {
    "CUUR0000SA0" : "Other", #overall CPI
    "CUUR0000SAF11" : "Groceries", #food at home
    "CUUR0000SEFV" : "Restaurants & Dining", #food away from home
    "CUUR0000SETB01" : "Gas & Transport",
    "CUUR0000SAM" : "Health & Fitness",
}

SERIES = list(SERIES_MAP.keys())

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
        print("BLS API did not return 'Results'. Full response:")
        print(data)
        raise SystemExit("BLS API error: check API key or payload.")
    
    rows=[]


    for s in data["Results"]["series"]:
        sid = s['seriesID']
        cpi_category = SERIES_MAP.get(sid, "Other")
        for d in s['data']:
            if d['period'].startswith('M'):
                rows.append({
                    "month": f"{d['year']}-{int(d['period'][1:]):02d}-01",
                    "series_id": sid,
                    "category": cpi_category,
                    "value": float(d["value"]),
                    })
                
    df = pd.DataFrame(rows)
    df["month"] = pd.to_datetime(df["month"])
    df = df.sort_values("month")
    
    df.to_sql('cpi_series', engine, if_exists='replace', index=False)
    print("Stored CPI in Table cpi_series")


if __name__ == "__main__":
    fetch_cpi()