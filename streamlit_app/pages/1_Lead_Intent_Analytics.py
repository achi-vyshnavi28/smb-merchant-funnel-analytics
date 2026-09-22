"""
Lead-routing NLP analytics page.

Visualizes the precomputed output of nlp_lead_intent_analytics/python/
nlp_lead_routing.py (a real TF-IDF + Logistic Regression intent classifier
trained on real Twitter customer-support conversations, repurposed here to
detect sales-inquiry signal for lead routing). The classifier itself is
trained offline; this page reads its saved predictions so the deployed app
stays lightweight.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
NLP_ROOT = ROOT / "nlp_lead_intent_analytics"

st.set_page_config(page_title="Lead Intent Analytics", page_icon="\U0001F9E9", layout="wide")


@st.cache_data
def load():
    return pd.read_csv(NLP_ROOT / "data" / "processed_conversations.csv")


df = load()

st.title("Lead-Routing NLP Analytics")
st.caption(
    f"{len(df):,} real customer-support conversations across {df['company_author'].nunique()} "
    "real brand support accounts (Twitter Customer Support dataset). A TF-IDF + Logistic "
    "Regression classifier predicts whether each inbound message carries a sales-inquiry "
    "(lead) signal versus existing-customer noise — full methodology and held-out accuracy in "
    "[`nlp_lead_intent_analytics/reports/nlp_report.md`](https://github.com/achi-vyshnavi28/smb-merchant-funnel-analytics/blob/main/nlp_lead_intent_analytics/reports/nlp_report.md)."
)

c1, c2, c3 = st.columns(3)
c1.metric("Conversations analyzed", f"{len(df):,}")
c2.metric("Overall lead-signal rate", f"{df['is_lead'].mean():.1%}")
c3.metric("Brands covered", f"{df['company_author'].nunique():,}")

st.divider()

companies = st.multiselect(
    "Filter by brand", sorted(df["company_author"].value_counts().head(20).index),
    default=list(df["company_author"].value_counts().head(6).index),
)
view = df[df["company_author"].isin(companies)] if companies else df

left, right = st.columns(2)

with left:
    st.subheader("Inbound Volume by Predicted Intent")
    intent_counts = view["predicted_intent"].value_counts().reset_index()
    intent_counts.columns = ["intent", "conversations"]
    colors = ["#2e9e5b" if lbl == "sales_inquiry" else "#6b7280" for lbl in intent_counts["intent"]]
    fig = px.bar(intent_counts, x="conversations", y="intent", orientation="h")
    fig.update_traces(marker_color=colors)
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, yaxis_title="", height=420)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Lead-Signal Rate by Brand")
    lead_rate = view.groupby("company_author")["is_lead"].mean().sort_values(ascending=False).reset_index()
    fig2 = px.bar(lead_rate, x="is_lead", y="company_author", orientation="h",
                  color_discrete_sequence=["#0f7a6c"])
    fig2.update_layout(yaxis={"categoryorder": "total ascending"}, yaxis_title="",
                        xaxis_title="Share classified as sales inquiry", xaxis_tickformat=".0%", height=420)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("Volume vs. Lead Rate by Brand")
by_company = (
    view.groupby("company_author")
    .agg(conversations=("dialogue_id", "count"), lead_rate=("is_lead", "mean"))
    .sort_values("conversations", ascending=False)
)
by_company["lead_rate"] = (by_company["lead_rate"] * 100).round(1)
st.dataframe(
    by_company.rename(columns={"conversations": "Conversations", "lead_rate": "Lead Signal Rate (%)"}),
    use_container_width=True,
)

st.divider()
st.subheader("Classifier Evaluation")
st.caption("Held-out test-set confusion matrix for the intent classifier (fixed evaluation artifact, not filtered by the selection above).")
st.image(str(NLP_ROOT / "reports" / "figures" / "nlp_01_confusion_matrix.png"), width=600)

st.caption(
    "Data source: [Twitter Customer Support conversations](https://huggingface.co/datasets/jphwang/twitter_customer_support_weaviate_export_200000_nomic-embed-text) "
    "(derived from the public Kaggle Customer Support on Twitter dataset). Built with Streamlit, Pandas, scikit-learn, and Plotly."
)
