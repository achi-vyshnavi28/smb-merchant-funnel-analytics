"""
Interactive merchant-acquisition funnel dashboard (Streamlit).

Reads directly from the raw Olist CSVs shipped in this repo (data/raw/) --
no database required, so it runs anywhere this repo is cloned, including
Streamlit Community Cloud.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

st.set_page_config(page_title="Merchant Funnel Dashboard", page_icon="\U0001F4C8", layout="wide")


@st.cache_data
def load_data():
    mql = pd.read_csv(RAW / "olist_marketing_qualified_leads_dataset.csv", parse_dates=["first_contact_date"])
    deals = pd.read_csv(RAW / "olist_closed_deals_dataset.csv", parse_dates=["won_date"])
    sellers = pd.read_csv(RAW / "olist_sellers_dataset.csv")
    revenue = pd.read_csv(
        RAW / "seller_revenue_summary.csv",
        parse_dates=["first_order_date", "last_order_date"],
    )

    activated_ids = set(sellers["seller_id"])
    deals["activated"] = deals["seller_id"].isin(activated_ids)
    deals = deals.merge(revenue[["seller_id", "total_revenue", "total_orders"]], on="seller_id", how="left")
    deals = deals.merge(mql[["mql_id", "origin", "first_contact_date"]], on="mql_id", how="left")

    return mql, deals, sellers, revenue


mql, deals, sellers, revenue = load_data()

st.title("Merchant Acquisition Funnel Dashboard")
st.caption(
    "Real marketing-funnel and seller-revenue data from Olist (2017–2018), used as a structural analogue "
    "for a WhatsApp-first SMB platform's merchant acquisition funnel. "
    "[Full case study & repo](https://github.com/achi-vyshnavi28/smb-merchant-funnel-analytics)."
)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
total_leads = len(mql)
total_won = len(deals)
total_activated = int(deals["activated"].sum())
win_rate = total_won / total_leads * 100
activation_rate = total_activated / total_won * 100
total_revenue = deals.loc[deals["activated"], "total_revenue"].sum()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Leads", f"{total_leads:,}")
c2.metric("Won Deals", f"{total_won:,}")
c3.metric("Activated Sellers", f"{total_activated:,}")
c4.metric("Win Rate", f"{win_rate:.1f}%")
c5.metric("Activation Rate", f"{activation_rate:.1f}%", help="% of won deals that ever listed a product or made a sale")
c6.metric("Revenue (Activated)", f"R$ {total_revenue / 1e3:.1f}K")

st.divider()

# ---------------------------------------------------------------------------
# Funnel + activation drop-off
# ---------------------------------------------------------------------------
left, right = st.columns([1, 1.2])

with left:
    st.subheader("The Funnel: Leads → Won → Activated")
    funnel_df = pd.DataFrame(
        {"stage": ["Leads", "Won Deals", "Activated Sellers"], "count": [total_leads, total_won, total_activated]}
    )
    fig_funnel = px.funnel(funnel_df, x="count", y="stage")
    fig_funnel.update_traces(marker_color=["#0f7a6c", "#2e9e5b", "#c9791f"])
    fig_funnel.update_layout(height=380)
    st.plotly_chart(fig_funnel, use_container_width=True)
    st.caption(
        f"**{100 - activation_rate:.1f}% of won deals never activate.** That's the funnel's biggest leak — "
        "and it happens *after* the sale closes, not before."
    )

with right:
    st.subheader("Activation Rate by Lead Type")
    by_leadtype = (
        deals.groupby("lead_type")
        .agg(won=("mql_id", "count"), activated=("activated", "sum"))
        .query("won >= 10")
        .assign(activation_rate=lambda d: d["activated"] / d["won"] * 100)
        .sort_values("activation_rate")
        .reset_index()
    )
    fig_lt = px.bar(
        by_leadtype, x="activation_rate", y="lead_type", orientation="h",
        color="activation_rate", color_continuous_scale=["#c1443a", "#c9791f", "#2e9e5b"],
    )
    fig_lt.update_layout(
        yaxis={"categoryorder": "total ascending"}, xaxis_title="Activation rate (%)", yaxis_title="",
        height=380, coloraxis_showscale=False,
    )
    st.plotly_chart(fig_lt, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Channel ROI + Activation Opportunity what-if (interactive)
# ---------------------------------------------------------------------------
left2, right2 = st.columns([1.2, 1])

with left2:
    st.subheader("Revenue by Acquisition Channel")
    by_channel = (
        deals[deals["activated"]]
        .groupby("origin")
        .agg(activated_sellers=("seller_id", "nunique"), total_revenue=("total_revenue", "sum"))
        .sort_values("total_revenue", ascending=False)
        .reset_index()
    )
    fig_ch = px.bar(
        by_channel, x="total_revenue", y="origin", orientation="h",
        color_discrete_sequence=["#0f7a6c"],
    )
    fig_ch.update_layout(
        yaxis={"categoryorder": "total ascending"}, xaxis_title="Total revenue (R$)", yaxis_title="",
        height=380,
    )
    st.plotly_chart(fig_ch, use_container_width=True)
    st.caption("`organic_search` and `unknown`-origin leads out-earn `paid_search` despite lower acquisition spend.")

with right2:
    st.subheader("Activation Opportunity Calculator")
    st.caption("Same formula as the Excel model — move the slider to stress-test the assumption.")

    avg_revenue_per_activated = deals.loc[deals["activated"], "total_revenue"].mean()
    st.metric("Current activation rate", f"{activation_rate:.1f}%")
    st.metric("Avg revenue per activated seller", f"R$ {avg_revenue_per_activated:,.2f}")

    target_rate = st.slider("Target activation rate (%)", 45, 100, 60, 1)

    additional_sellers = max(round(target_rate / 100 * total_won) - total_activated, 0)
    additional_revenue = additional_sellers * avg_revenue_per_activated

    st.metric("Additional sellers to activate", f"{additional_sellers:,}")
    st.metric(f"Additional revenue at {target_rate}% activation", f"R$ {additional_revenue:,.0f}")

st.divider()

# ---------------------------------------------------------------------------
# Anomaly table
# ---------------------------------------------------------------------------
st.subheader("Anomaly: Declared Revenue vs. Reality")
anomaly = deals[
    (deals["declared_monthly_revenue"] > deals.loc[deals["declared_monthly_revenue"] > 0, "declared_monthly_revenue"].mean())
    & (deals["total_revenue"].fillna(0) < 100)
].sort_values("declared_monthly_revenue", ascending=False).head(10)
anomaly_display = anomaly[["seller_id", "business_segment", "declared_monthly_revenue"]].copy()
anomaly_display["seller_id"] = anomaly_display["seller_id"].fillna("(never activated)").astype(str).str[:10] + "…"
anomaly_display["declared_monthly_revenue"] = anomaly_display["declared_monthly_revenue"].map(lambda v: f"R$ {v:,.0f}")
st.dataframe(anomaly_display, hide_index=True, use_container_width=True)
st.caption("Sellers who declared high expected revenue at sign-up but generated little to none in reality.")

st.divider()
st.caption(
    "Data source: [Olist Marketing Funnel Dataset](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist) "
    "(CC BY-NC-SA 4.0), joined to real seller order data. Built with Streamlit, Pandas, and Plotly."
)
