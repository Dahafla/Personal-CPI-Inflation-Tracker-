import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment + DB
load_dotenv()
DB_URL = os.getenv("DB_URL")
if not DB_URL:
    raise SystemExit("❌ DB_URL is not set in .env")

engine = create_engine(DB_URL)


@st.cache_data
def load_tables():
    personal_index = pd.read_sql("SELECT * FROM personal_index", engine)
    # cpi_norm has: category, ym, cpi_index
    cpi_norm = pd.read_sql("SELECT * FROM cpi_norm", engine)
    monthly_weights = pd.read_sql("SELECT * FROM monthly_weights", engine)
    forecast = pd.read_sql("SELECT * FROM personal_forecast", engine)
    transactions = pd.read_sql("SELECT * FROM transactions", engine)

    # Parse dates
    personal_index["month"] = pd.to_datetime(personal_index["month"])
    # ym is 'YYYY-MM' → convert to proper month date
    cpi_norm["month"] = pd.to_datetime(cpi_norm["ym"] + "-01")
    forecast["month"] = pd.to_datetime(forecast["month"])
    monthly_weights["month"] = pd.to_datetime(monthly_weights["month"] + "-01")
    transactions["date"] = pd.to_datetime(transactions["date"])

    return personal_index, cpi_norm, monthly_weights, forecast, transactions


def main():
    st.set_page_config(
        page_title="Personal CPI Tracker",
        layout="wide",
    )

    st.title("📈 Personal CPI Tracker")
    st.caption("Personalized CPI engine using Python, SQL, and BLS data to model your true cost of living.")

    personal_index, cpi_norm, monthly_weights, forecast, transactions = load_tables()

    # Sidebar: choose user
    cc_nums = sorted(personal_index["cc_num"].unique())
    selected_cc = st.sidebar.selectbox("Select user (cc_num)", cc_nums)

    # Filter per-user data
    pi = personal_index[personal_index["cc_num"] == selected_cc].sort_values("month")
    mw = monthly_weights[monthly_weights["cc_num"] == selected_cc].sort_values("month")
    fc = forecast[forecast["cc_num"] == selected_cc].sort_values("month")
    tx = transactions[transactions["cc_num"] == selected_cc].sort_values("date")

    # ---- Scenario controls ----
    st.sidebar.markdown("### 🧪 What-if Scenario")

    if not mw.empty:
        categories = sorted(mw["category"].unique())
        scenario_cat = st.sidebar.selectbox("Category to shock", ["(none)"] + categories)
        shock_pct = st.sidebar.slider("Shock to that category's inflation (%)", -50, 50, 0)
    else:
        scenario_cat = "(none)"
        shock_pct = 0

    # Compute scenario CPI (if selected)
    scenario_df = None
    if scenario_cat != "(none)" and shock_pct != 0 and not mw.empty and not pi.empty:
        # Weights for the selected category
        cat_weights = mw[mw["category"] == scenario_cat][["month", "weight"]].copy()

        # Merge with personal CPI series
        merged = pi.merge(cat_weights, on="month", how="left")
        merged["weight"] = merged["weight"].fillna(0.0)

        # Scenario: shock that category's contribution
        merged["scenario_cpi"] = merged["personal_cpi"] * (
            1 + merged["weight"] * (shock_pct / 100.0)
        )

        merged["delta"] = merged["scenario_cpi"] - merged["personal_cpi"]
        if not merged.empty and merged["scenario_cpi"].notna().any():
            scenario_df = merged

    # ========== 1) Personal CPI vs Official CPI ==========
    with st.container():
        st.subheader("Personal CPI vs Official CPI (CPI-U)")

        if not pi.empty:
            # Use 'Other' as headline/all-items CPI bucket
            cpi_head = cpi_norm[cpi_norm["category"] == "Other"].copy()
            cpi_head = cpi_head.sort_values("month")

            # Crop CPI-U to same date range as personal CPI
            start = pi["month"].min()
            end = pi["month"].max()
            cpi_head = cpi_head[(cpi_head["month"] >= start) & (cpi_head["month"] <= end)]

            fig_cpi = go.Figure()
            fig_cpi.add_trace(go.Scatter(
                x=pi["month"],
                y=pi["personal_cpi"],
                mode="lines",
                name="Personal CPI",
            ))
            fig_cpi.add_trace(go.Scatter(
                x=cpi_head["month"],
                y=cpi_head["cpi_index"],
                mode="lines",
                name="CPI-U (Official)",
                line=dict(dash="dash"),
            ))
            fig_cpi.update_layout(
                xaxis_title="Month",
                yaxis_title="Index (base=100)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
            )
            st.plotly_chart(fig_cpi, use_container_width=True)
        else:
            st.info("No personal CPI data for this user yet.")

    # ========== 2) Category Weights Over Time ==========
    with st.container():
        st.subheader("Spending Weights by Category Over Time")

        if not mw.empty:
            pivot = mw.pivot_table(
                index="month",
                columns="category",
                values="weight",
                aggfunc="mean",
            ).reset_index()

            fig_weights = px.area(
                pivot,
                x="month",
                y=[col for col in pivot.columns if col != "month"],
                labels={"value": "Weight (share of spend)", "month": "Month"},
            )
            fig_weights.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
            )
            st.plotly_chart(fig_weights, use_container_width=True)
        else:
            st.info("No monthly weights available for this user yet.")

    # ========== 3) Personal CPI + Forecast ==========
    with st.container():
        st.subheader("Personal CPI with Forecast")

        if not fc.empty and not pi.empty:
            fig_fc = go.Figure()

            # History
            fig_fc.add_trace(go.Scatter(
                x=pi["month"],
                y=pi["personal_cpi"],
                mode="lines",
                name="History",
            ))

            # Forecast line
            fig_fc.add_trace(go.Scatter(
                x=fc["month"],
                y=fc["forecast"],
                mode="lines",
                name="Forecast",
                line=dict(dash="dash"),
            ))

            # Forecast interval band
            fig_fc.add_trace(go.Scatter(
                x=pd.concat([fc["month"], fc["month"][::-1]]),
                y=pd.concat([fc["upper"], fc["lower"][::-1]]),
                fill="toself",
                fillcolor="rgba(100,100,200,0.2)",
                line=dict(width=0),
                name="Forecast interval",
                showlegend=True,
            ))

            fig_fc.update_layout(
                xaxis_title="Month",
                yaxis_title="Index (base=100)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
            )
            st.plotly_chart(fig_fc, use_container_width=True)
        else:
            st.info("No forecast data available for this user yet.")

    # ========== 4) Scenario impact ==========
    with st.container():
        st.subheader("What-if Scenario Impact on Your Personal Inflation")

        if scenario_df is None or scenario_df.empty:
            st.info("Select a category and non-zero shock in the sidebar to see scenario impact.")
        else:
            latest = scenario_df.dropna(subset=["scenario_cpi"]).iloc[-1]
            base_val = latest["personal_cpi"]
            scen_val = latest["scenario_cpi"]
            diff = latest["delta"]

            col1, col2, col3 = st.columns(3)
            col1.metric("Baseline personal CPI (latest)", f"{base_val:.2f}")
            col2.metric(
                "Scenario CPI (latest)",
                f"{scen_val:.2f}",
                delta=f"{diff:+.2f}",
            )
            col3.metric(
                "Category shocked",
                f"{scenario_cat} {shock_pct:+d}%",
            )

            fig_delta = go.Figure()
            fig_delta.add_trace(go.Bar(
                x=scenario_df["month"],
                y=scenario_df["delta"],
                name="Scenario - Baseline (CPI pts)",
            ))
            fig_delta.update_layout(
                xaxis_title="Month",
                yaxis_title="Change in CPI index (points)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
            )
            st.plotly_chart(fig_delta, use_container_width=True)

            st.caption(
                "Bars show how much your overall personal CPI index would change each month "
                f"if **{scenario_cat}** inflation were shocked by **{shock_pct:+d}%**, "
                "based on its weight in your spending basket."
            )

    # ========== 5) Transactions Table ==========
    with st.container():
        st.subheader("Transactions (sample)")
        st.dataframe(
            tx[["date", "category", "spend"]].head(50)
        )


if __name__ == "__main__":
    main()
