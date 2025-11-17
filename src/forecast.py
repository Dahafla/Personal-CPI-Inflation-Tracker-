import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from statsmodels.tsa.statespace.sarimax import SARIMAX

'''

Reads each user's personalized CPI time series
- fits a SARIMAX time-series model per user, generates multi-step ahead forcasts w/ confidence interval
- short or problematic history, falls back to naive flat forecast using last observed

'''


load_dotenv()

DB_URL = os.getenv("DB_URL")
if not DB_URL:
    raise SystemExit("DB_URL is not set in .env")
engine = create_engine(DB_URL, connect_args={"timeout": 30})


def forecast_all_users(steps=12):
    """
    For each user (cc_num) in personal_index, fit a simple SARIMA model
    and forecast the next `steps` months of personal CPI.
    Results are stored in the `personal_forecast` table.
    """
    # 1) Read historical personal CPI
    df = pd.read_sql(
        "SELECT cc_num, month, personal_cpi FROM personal_index ORDER BY cc_num, month",
        engine,
    )

    if df.empty:
        print("personal_index is empty. Run the CPI + SQL steps first.")
        return

    # Ensure proper datetime
    df["month"] = pd.to_datetime(df["month"])

    all_forecasts = []

    # 2) Loop over each user
    for cc_num, grp in df.groupby("cc_num"):
        s = grp.set_index("month")["personal_cpi"].sort_index()

        # Force to monthly frequency (Month Start)
        s = s.asfreq("MS")
        s = s.ffill()  

        last_date = s.index.max()
        last_value = s.iloc[-1]

        # naive flat forecast (used for short/failed series)
        def naive_forecast():

            # Flat forecast: repeat last known CPI value for the next `steps` months.

            future_dates = pd.date_range(
                start=last_date + pd.offsets.MonthBegin(1),
                periods=steps,
                freq="MS",
            )
            return pd.DataFrame(
                {
                    "cc_num": cc_num,
                    "month": future_dates,
                    "forecast": last_value,
                    "lower": last_value,
                    "upper": last_value,
                }
            )

        # If too few points -> skip SARIMAX, just use naive
        if len(s) < 6:
            print(f" Not enough data for cc_num={cc_num}, using naive forecast.")
            fc_df = naive_forecast()
            all_forecasts.append(fc_df)
            continue

        try:
            # Try SARIMAX
            model = SARIMAX(
                s,
                order=(1, 1, 1),
                seasonal_order=(0, 1, 1, 12),
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            res = model.fit(disp=False)

            fc = res.get_forecast(steps=steps)
            fc_df = fc.summary_frame()[["mean", "mean_ci_lower", "mean_ci_upper"]]

            # Convert index → 'month' column
            fc_df = fc_df.reset_index()
            if "index" in fc_df.columns:
                fc_df.rename(columns={"index": "month"}, inplace=True)

            fc_df["cc_num"] = cc_num
            fc_df.rename(
                columns={
                    "mean": "forecast",
                    "mean_ci_lower": "lower",
                    "mean_ci_upper": "upper",
                },
                inplace=True,
            )

            all_forecasts.append(fc_df)
            print(f" Forecasted {steps} months for cc_num={cc_num}")

        except Exception as e:
            print(f" Error forecasting cc_num={cc_num}, falling back to naive: {e}")
            fc_df = naive_forecast()
            all_forecasts.append(fc_df)

    if not all_forecasts:
        print("No forecasts were generated.")
        return

    # 5) Concatenate all users' forecasts and save to SQLite
    out = pd.concat(all_forecasts, ignore_index=True)

    # Make sure month is datetime
    out["month"] = pd.to_datetime(out["month"])

    out.to_sql("personal_forecast", engine, if_exists="replace", index=False)
    print("Wrote personal_forecast table to SQLite")


if __name__ == "__main__":
    forecast_all_users(steps=12)
