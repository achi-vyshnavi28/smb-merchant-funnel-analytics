# smb-merchant-funnel-analytics

A merchant-acquisition funnel analytics project asking the question a growth team eventually has to face: **of the merchants a platform signs, how many actually go on to activate?**

**Why this dataset:** I wanted to look at the other half of the same platform's business — not what happens after a merchant is already operating, but whether the acquisition funnel that got them there actually works. [Olist](https://olist.com)'s public **Marketing Funnel** dataset (8,000 real, anonymized leads and 842 closed deals, 2017–2018) is a real sales/marketing funnel that hands off to an operational platform, joined here to real seller order/revenue data from my [order-operations project](https://github.com/achi-vyshnavi28/whatsapp-order-ops-analytics) so every query answers a real "did the deal actually turn into revenue?" question.

**Start here:** [`docs/case_study.md`](docs/case_study.md) — a narrative write-up of the analysis (business question → findings → quantified revenue impact → recommendations), not just raw output.

**Live dashboard:** [smb-merchant-funnel-analytics-5ey63g5wxmxidc6v3sj3kg.streamlit.app](https://smb-merchant-funnel-analytics-5ey63g5wxmxidc6v3sj3kg.streamlit.app) — interactive, includes a live activation-opportunity what-if calculator.

## What's in this project

- **SQL** — a 4-table PostgreSQL schema (deliberately without a foreign key on `closed_deals.seller_id`, because the 54.9% orphan rate is the headline finding, not a bug to constrain away) and 9 analysis queries using joins, CTEs, window functions, and subqueries ([`sql/`](sql/)).
- **Python** — data cleaning, EDA, a chi-square test of independence, and a logistic regression predicting deal activation at sign-up time, all with an automated report generated on every run ([`python/eda_analysis.py`](python/eda_analysis.py)).
- **Excel** — a financial model with live formulas for funnel-rate calculations and an activation-opportunity what-if calculator ([`excel/funnel_financial_model.xlsx`](excel/funnel_financial_model.xlsx)).
- **Power BI** — a dashboard connected live to PostgreSQL across all 4 tables, with 6 DAX measures and KPI, activation-by-lead-type, and revenue-by-channel visuals ([`dashboard/funnel_activation_dashboard.pbix`](dashboard/funnel_activation_dashboard.pbix)).
- **Streamlit** — a public, interactive version of the dashboard, deployed live ([`streamlit_app/`](streamlit_app/)).
- **Conversational AI / NLP** — a TF-IDF + Logistic Regression intent classifier repurposed to detect sales-inquiry ("lead") signal in inbound messages, with a live dashboard page ([`nlp_lead_intent_analytics/`](nlp_lead_intent_analytics/)).
- **Snowflake** — a star-schema data warehouse built from the same funnel data via an automated ETL pipeline ([`warehouse_etl/`](warehouse_etl/)).
- **MongoDB** — the same funnel data remodeled as denormalized documents in a live MongoDB Atlas cluster ([`nosql_mongo/`](nosql_mongo/)).

## Data source

[Marketing Funnel by Olist](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist) — CC BY-NC-SA 4.0. Real, anonymized marketing-qualified-lead and closed-deal data (2017–2018), joined here to real seller order/revenue data derived from the [Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (same license). Not synthetic.

## Repo structure

```
data/raw/          4 CSVs: leads, closed deals, sellers, derived seller-revenue summary
sql/               01_schema.sql (DDL) + 02_analysis_queries.sql (analysis)
python/            load_data.py, eda_analysis.py, build_excel_model.py
excel/             funnel_financial_model.xlsx
dashboard/         funnel_activation_dashboard.pbix
streamlit_app/     app.py, pages/1_Lead_Intent_Analytics.py (live interactive dashboard)
reports/           eda_report.md + figures/ (auto-generated)
docs/              case_study.md
nlp_lead_intent_analytics/  conversational AI / lead-intent classification module (see its own README)
warehouse_etl/     automated ETL -> Snowflake star schema (see its own README)
nosql_mongo/       document modeling -> MongoDB Atlas (see its own README)
```

## Reproducing this locally

1. **Database**: Create a PostgreSQL database, then apply the schema:
   ```
   psql -U postgres -d merchant_funnel_analytics -f sql/01_schema.sql
   ```
2. **Load data**: `python python/load_data.py` (loads all 4 CSVs respecting FK order)
3. **Run the analysis queries**: `psql -U postgres -d merchant_funnel_analytics -f sql/02_analysis_queries.sql`
4. **Python EDA + auto report**: `pip install -r requirements.txt && python python/eda_analysis.py`
5. **Excel model**: `python python/build_excel_model.py`
6. **Power BI**: open `dashboard/funnel_activation_dashboard.pbix` in Power BI Desktop (connection details point at `localhost:5432/merchant_funnel_analytics`)
7. **Live dashboard**: `streamlit run streamlit_app/app.py` (reads directly from `data/raw/`, no database required)

## Key findings (from the automated EDA report)

- **54.9% of won deals never activate**: of 842 closed deals, only 380 (45.1%) ever listed a product or made a sale. Win-rate and activation-rate are not the same metric, and the gap between them is the funnel's single biggest leak.
- **Activation is statistically tied to lead type**: chi-square test of independence, χ² = 45.69 (p < 0.001) — `online_big` leads activate at 62.7% vs. 28.8% for `offline` leads, a real targeting signal, not noise.
- **Paid acquisition isn't obviously paying off**: `organic_search` and `unknown`-origin leads generate more total revenue among activated sellers than `paid_search`, despite paid search costing more to acquire.
- **Activation is predictable at sign-up time**: a logistic regression using only features known the moment a deal closes reaches 58.8% accuracy / 0.645 ROC-AUC — enough to flag at-risk merchants for extra onboarding before they churn out of the funnel.
- **Data-quality gap found and documented, not silently patched**: `closed_deals.seller_id` has no FK to `sellers` on purpose — 462 of 842 (54.9%) closed deals reference a seller that never appears in the sellers table at all. That's not a data error; it's the finding.

Full report with charts: [`reports/eda_report.md`](reports/eda_report.md)

## Notes on the Power BI file

The `.pbix` connects live to a local PostgreSQL instance across all 4 tables (`marketing_qualified_leads`, `closed_deals`, `sellers`, `seller_revenue`). Because `closed_deals.seller_id` has no database-level FK (by design — see above), the `sellers` relationship was added manually in Power BI's model view rather than auto-detected. Six DAX measures (`Total Leads`, `Total Won Deals`, `Total Activated Sellers`, `Win Rate %`, `Activation Rate %`, `Total Revenue`) drive a 6-card KPI row plus an activation-rate-by-lead-type chart and a revenue-by-channel chart. The report opens fine on any machine since the data is already imported; if you want to hit **Refresh**, point the connection at your own Postgres instance first via **Transform data → Data source settings → Change Source**.

## Conversational AI / Lead-Intent NLP Analytics

[`nlp_lead_intent_analytics/`](nlp_lead_intent_analytics/) is a self-contained module analyzing 9,795 real customer-support conversations. A **TF-IDF + Logistic Regression intent classifier** reaches **94.3% accuracy / 0.867 macro F1** across 6 intent classes, with a `sales_inquiry` class purpose-built to detect lead signal in inbound messages — the pre-sale counterpart to my order-operations project's post-sale chatbot-analytics module. Drives a live "Lead Intent Analytics" page in the [Streamlit dashboard](https://smb-merchant-funnel-analytics-5ey63g5wxmxidc6v3sj3kg.streamlit.app) tracking lead-signal rate by brand/channel. Full write-up: [`nlp_lead_intent_analytics/README.md`](nlp_lead_intent_analytics/README.md).

## Data Warehouse / Automated ETL (Snowflake)

[`warehouse_etl/`](warehouse_etl/) extracts the funnel data from PostgreSQL, models it as a proper **star schema** (dimension tables for lead/seller/business-segment/date + a fact table at the closed-deal grain — not just a copy of the source tables), and loads it into a live **Snowflake** data warehouse via an automated Python pipeline. Confirmed working end-to-end: all 8,000 leads / 842 deals loaded and verified with a live analytical query (activation rate by lead type, matching the rest of this repo's findings exactly). Full write-up: [`warehouse_etl/README.md`](warehouse_etl/README.md).

## NoSQL / Document Database (MongoDB)

[`nosql_mongo/`](nosql_mongo/) remodels the same funnel data a second way: as **denormalized documents** (one per closed deal, with lead context, seller info, and revenue summary embedded inline) loaded into a live **MongoDB Atlas** cluster. Demonstrates real document-database querying — `find` filters, and aggregation pipelines using `$group`, `$project`, and `$cond` — not just a data dump. Confirmed working end-to-end: all 842 deal documents loaded, with a 45.1% activation rate matching the PostgreSQL, Snowflake, Power BI, and Streamlit versions of this same analysis exactly. Full write-up: [`nosql_mongo/README.md`](nosql_mongo/README.md).
