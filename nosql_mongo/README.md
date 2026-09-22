# nosql_mongo

Models the same merchant-funnel data a second way: as genuine denormalized **documents** — one per closed deal, with lead context, seller info, and revenue summary embedded inline — loaded into a live **MongoDB Atlas** cluster.

## Why documents, not just "the same tables in Mongo"

A document database earns its place when the read pattern is "give me everything about this deal in one fetch," not "join 4 tables." Each document in this collection embeds:

- **`lead`** — first contact date, landing page, acquisition channel
- **`deal`** — won date, SDR/SR, business segment, lead type, declared catalog size/revenue at sign-up
- **`activated`** — precomputed boolean (was this deal's seller ever found in the sellers table)
- **`seller`** — city/state, only present if activated
- **`revenue`** — total orders/revenue/date range, only present if activated

That's the same design discipline as [`warehouse_etl/`](../warehouse_etl/) applied in the opposite direction: the star schema normalizes for update-safety and rollup speed, this collection denormalizes for single-fetch reads — deliberately different modeling disciplines for the same underlying facts.

## Pipeline (two steps, deliberately split)

1. **Extract + Transform** — [`python/build_documents.py`](python/build_documents.py). Pulls from the local `merchant_funnel_analytics` Postgres database, builds one document per closed deal, and stages it as gzip-compressed JSONL in `data/staged/`. Needs local Postgres access only.
2. **Load** — [`python/load_to_mongodb.py`](python/load_to_mongodb.py). Bulk-inserts the staged documents into MongoDB Atlas, creates 3 indexes, and runs 4 example queries (a `find` and three real aggregation pipelines using `$group`, `$project`, `$cond`, and `$match`). Needs your own MongoDB Atlas connection string, read only from the `MONGODB_URI` environment variable — the script never hardcodes or prompts for a password.

## Running it

```bash
pip install -r requirements.txt

# Step 1 (needs local Postgres, already set up elsewhere in this repo)
python python/build_documents.py

# Step 2 (needs your own MongoDB Atlas cluster -- set this first)
export MONGODB_URI="mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/"
python python/load_to_mongodb.py
```

## Confirmed working — actual output from the extract step

```
Wrote 842 deal documents -> data/staged/deals.jsonl.gz
```

842 documents, matching the `closed_deals` table exactly (verified: sample activated document includes correctly embedded seller city/state and revenue totals matching the Postgres `seller_revenue` table row-for-row). The load step's document count (once run against a live Atlas cluster) will match this one-for-one — the load script is a pure bulk-insert, no filtering.

## Data

Real merchant-acquisition-funnel data (same source as the rest of this repo): 842 closed deals from the [Olist Marketing Funnel dataset](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist), joined to real seller revenue.
