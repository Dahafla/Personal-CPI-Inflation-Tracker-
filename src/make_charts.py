import os
import random
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from dotenv import load_dotenv


'''
- Connects to the SQL Database, selects a user and generates:
    - Personal CPI vs Official CPI over time
    - User's category spending weights over time
    - A personal CPI forecast plot with confidence intervals

- All plots saved as PNG under 'charts/'. 
- Used to compare personalized inflation against headline CPI, understand shifts in spending behavior,
& illustrate output of forcasting model

'''
# Load DB
load_dotenv()
engine = create_engine(os.getenv("DB_URL"))

# Ensure output folder exists
os.makedirs("charts", exist_ok=True)

def get_user_mapping():
    cc_list = pd.read_sql("SELECT DISTINCT cc_num FROM personal_index", engine)["cc_num"].tolist()
    cc_list = sorted(cc_list)
    mapping = {cc: i for i, cc in enumerate(cc_list)}
    return mapping

def plot_personal_vs_cpiu(cc_num, user_id):
    personal = pd.read_sql(
        f"SELECT month, personal_cpi FROM personal_index WHERE cc_num = ? ORDER BY month",
        engine,
        params=(cc_num,),
    )
    cpiu = pd.read_sql(
        """
        SELECT DATE(ym || '-01') AS month, cpi_index
        FROM cpi_norm
        WHERE category = 'Other'
        ORDER BY ym
        """,
        engine,
    )

    personal["month"] = pd.to_datetime(personal["month"])
    cpiu["month"] = pd.to_datetime(cpiu["month"])

    start = personal["month"].min()
    end   = personal["month"].max()
    cpiu = cpiu[(cpiu["month"] >= start) & (cpiu["month"] <= end)]

    plt.figure(figsize=(12, 5))
    plt.plot(personal["month"], personal["personal_cpi"], label="Personal CPI", linewidth=2)
    plt.plot(cpiu["month"], cpiu["cpi_index"], label="Official CPI-U", linestyle="--", alpha=0.7)

    plt.title(f"Personal CPI vs CPI-U (User {user_id})")
    plt.xlabel("Month")
    plt.ylabel("Index (Base = 100)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"charts/personal_vs_cpiu_{user_id}.png", dpi=300)
    plt.close()


def plot_category_weights(cc_num, user_id):
    df = pd.read_sql(
        f"SELECT month, category, weight FROM monthly_weights WHERE cc_num = {cc_num} ORDER BY month",
        engine
    )

    if df.empty:
        print(f"No category weight data for cc_num={user_id}")
        return

    df["month"] = pd.to_datetime(df["month"])

    pivot = df.pivot_table(
    index="month",
    columns="category",
    values="weight",
    aggfunc="mean"  # or "sum", but weights should ~sum to 1
).fillna(0)

    plt.figure(figsize=(12, 6))
    pivot.plot.area(ax=plt.gca(), colormap="tab20")

    plt.title(f"Category Spending Weights Over Time (User {user_id})")
    plt.xlabel("Month")
    plt.ylabel("Weight (Share of Monthly Spend)")
    plt.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(f"charts/category_weights_{user_id}.png", dpi=300)
    plt.close()


def plot_forecast(cc_num, user_id):
    hist = pd.read_sql(
        f"SELECT month, personal_cpi FROM personal_index WHERE cc_num = ? ORDER BY month",
        engine,
        params=(cc_num,),
    )
    fc = pd.read_sql(
        f"SELECT month, forecast, lower, upper FROM personal_forecast WHERE cc_num = ? ORDER BY month",
        engine,
        params=(cc_num,),
    )

    if fc.empty:
        print(f"No forecast data for cc_num={user_id}")
        return

    hist["month"] = pd.to_datetime(hist["month"])
    fc["month"] = pd.to_datetime(fc["month"])
    
    last_hist_date = hist["month"].max()
    hist = hist[hist["month"] <= last_hist_date]
    fc = fc[fc["month"] > last_hist_date]



    plt.figure(figsize=(12, 6))

    # History
    plt.plot(hist["month"], hist["personal_cpi"], label="Historical CPI", linewidth=2)

    # Forecast
    plt.plot(fc["month"], fc["forecast"], label="Forecast", linestyle="--", linewidth=2)

    # Confidence band
    plt.fill_between(fc["month"], fc["lower"], fc["upper"], color="gray", alpha=0.2, label="95% CI")
    plt.axvline(last_hist_date, linestyle=":", alpha=0.7)

    plt.title(f"Personal CPI Forecast (User {user_id})")
    plt.xlabel("Month")
    plt.ylabel("Index (Base = 100)")

    plt.xlim(hist["month"].min(), fc["month"].max())

    y_min = min(hist["personal_cpi"].min(), fc["lower"].min())
    y_max = max(hist["personal_cpi"].max(), fc["upper"].max())
    pad = (y_max - y_min) * 0.1
    plt.ylim(y_min - pad, y_max + pad)

    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"charts/forecast_{user_id}.png", dpi=300)
    plt.close()


def generate_all_plots():
    
    mapping = get_user_mapping()
    cc_num = random.choice(list(mapping.keys()))
    user_id = mapping[cc_num]

    print(f"Generating plots for user = {user_id}")
    plot_personal_vs_cpiu(cc_num, user_id)
    plot_category_weights(cc_num, user_id)
    plot_forecast(cc_num, user_id)

    print("All plots saved in charts")


if __name__ == "__main__":
    generate_all_plots()
