# smb-merchant-funnel-analytics

A merchant-acquisition funnel analytics project built to demonstrate a **Data Analyst (SQL, Python & Business Intelligence)** skill set: complex SQL, Python EDA + statistical testing + a genuine predictive model, Excel financial modeling, and a live Power BI dashboard — applied to the problem every SMB platform's growth team eventually has to answer: **of the merchants we sign, how many actually activate?**

**Why this dataset:** a WhatsApp-first SMB platform's growth depends on merchants activating after they sign up, not just signing up. [Olist](https://olist.com)'s public **Marketing Funnel** dataset (8,000 real, anonymized leads and 842 closed deals, 2017–2018) is a structurally identical problem — a sales/marketing funnel that hands off to an operational platform — so it's used here joined to real seller order/revenue data from the [sibling order-operations project](https://github.com/achi-vyshnavi28/whatsapp-order-ops-analytics), giving every query in this repo a real "did the deal actually turn into revenue?" answer.

**Start here:** [`docs/case_study.md`](docs/case_study.md) — a narrative write-up of the analysis (business question → findings → quantified revenue impact → recommendations), not just raw output.

**Live dashboard:** [smb-merchant-funnel-analytics-5ey63g5wxmxidc6v3sj3kg.streamlit.app](https://smb-merchant-funnel-analytics-5ey63g5wxmxidc6v3sj3kg.streamlit.app) — interactive, includes a live activation-opportunity what-if calculator.

## Skills demonstrated → where to find them

| Skill | Where |
|---|---|
| Complex SQL: multi-table joins, subqueries, CTEs, window functions | [`sql/02_analysis_queries.sql`](sql/02_analysis_queries.sql) — 9 queries, all run against live PostgreSQL |
| PostgreSQL, deliberate data-quality-driven schema design | [`sql/01_schema.sql`](sql/01_schema.sql) — `closed_deals.seller_id` intentionally has no FK to `sellers`, because the 54.9% orphan rate *is* the headline finding, not a bug to constrain away |
| Python for data analysis (Pandas, NumPy, Matplotlib/Seaborn) | [`python/eda_analysis.py`](python/eda_analysis.py) — cleaning, EDA, SciPy statistical tests |
| Automated reporting | `eda_analysis.py` generates [`reports/eda_report.md`](reports/eda_report.md) + 3 charts on every run, no manual editing |
| Dashboard & visualization (Power BI) | [`dashboard/funnel_activation_dashboard.pbix`](dashboard/funnel_activation_dashboard.pbix) — live PostgreSQL connection, 4-table data model, 6 DAX measures, KPI cards + activation-by-lead-type + revenue-by-channel visuals |
| Descriptive statistics, metric definitions, anomaly detection | Chi-square test of independence in the EDA report; declared-vs-actual-revenue anomaly detection in SQL Q8 |
| Predictive modeling | Logistic regression predicting deal activation at sign-up time (58.8% accuracy, 0.645 ROC-AUC) — a genuine supervised model, not just descriptive stats |
| Excel / spreadsheet modeling | [`excel/funnel_financial_model.xlsx`](excel/funnel_financial_model.xlsx) — live formulas (funnel-rate calculations, activation-opportunity what-if model) |
| Real analytical case study | [`docs/case_study.md`](docs/case_study.md) — business question → findings → quantified revenue impact → recommendations |
| Live dashboard link | **[smb-merchant-funnel-analytics-5ey63g5wxmxidc6v3sj3kg.streamlit.app](https://smb-merchant-funnel-analytics-5ey63g5wxmxidc6v3sj3kg.streamlit.app)** — interactive Streamlit + Plotly app ([`streamlit_app/app.py`](streamlit_app/app.py)), including a live activation-opportunity what-if calculator |
| *Bonus:* Conversational AI / NLP intent classification | [`nlp_lead_intent_analytics/`](nlp_lead_intent_analytics/) — real TF-IDF + Logistic Regression classifier (94.3% held-out accuracy, 0.867 macro F1) on 9,795 real customer-support conversations, repurposed to detect sales-inquiry ("lead") signal for inbound-message routing, plus a live "Lead Intent Analytics" page in the Streamlit app |
| *Bonus:* Data warehouse concepts (Snowflake) / automated ETL | [`warehouse_etl/`](warehouse_etl/) — automated ETL pipeline: extracts from PostgreSQL, models a proper star schema (4 dimension tables + 1 fact table at the deal grain), loads into Snowflake |
| *Bonus:* NoSQL / document databases (MongoDB) | [`nosql_mongo/`](nosql_mongo/) — the same funnel data remodeled as denormalized documents (one per closed deal, with lead/seller/revenue embedded inline) for a live MongoDB Atlas cluster, queried with `find` + aggregation pipelines (`$group`, `$project`, `$cond`) |
| Proof of work | This repo — real data, real queries, real dashboard, all reproducible from a fresh clone |

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
nlp_lead_intent_analytics/  bonus module: conversational AI / lead-intent classification (see its own README)
warehouse_etl/     bonus module: automated ETL -> Snowflake star schema (see its own README)
nosql_mongo/       bonus module: document modeling -> MongoDB Atlas (see its own README)
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

## Bonus: Conversational AI / Lead-Intent NLP Analytics

[`nlp_lead_intent_analytics/`](nlp_lead_intent_analytics/) is a self-contained module analyzing 9,795 real customer-support conversations. A **TF-IDF + Logistic Regression intent classifier** reaches **94.3% accuracy / 0.867 macro F1** across 6 intent classes, with a `sales_inquiry` class purpose-built to detect lead signal in inbound messages — the pre-sale counterpart to the sibling repo's post-sale chatbot-analytics module. Drives a live "Lead Intent Analytics" page in the [Streamlit dashboard](https://smb-merchant-funnel-analytics-5ey63g5wxmxidc6v3sj3kg.streamlit.app) tracking lead-signal rate by brand/channel. Full write-up: [`nlp_lead_intent_analytics/README.md`](nlp_lead_intent_analytics/README.md).

## Bonus: Data Warehouse / Automated ETL (Snowflake)

[`warehouse_etl/`](warehouse_etl/) extracts the funnel data from PostgreSQL, models it as a proper **star schema** (dimension tables for lead/seller/business-segment/date + a fact table at the closed-deal grain — not just a copy of the source tables), and loads it into a live **Snowflake** data warehouse via an automated Python pipeline. Confirmed working end-to-end: all 8,000 leads / 842 deals loaded and verified with a live analytical query (activation rate by lead type, matching the rest of this repo's findings exactly). Full write-up: [`warehouse_etl/README.md`](warehouse_etl/README.md).

## Bonus: NoSQL / Document Database (MongoDB)

[`nosql_mongo/`](nosql_mongo/) remodels the same funnel data a second way: as **denormalized documents** (one per closed deal, with lead context, seller info, and revenue summary embedded inline) for a live **MongoDB Atlas** cluster. Demonstrates real document-database querying — `find` filters, and aggregation pipelines using `$group`, `$project`, and `$cond` — not just a data dump. Extract step confirmed working: all 842 deal documents staged and verified against the source Postgres tables. Full write-up: [`nosql_mongo/README.md`](nosql_mongo/README.md).
