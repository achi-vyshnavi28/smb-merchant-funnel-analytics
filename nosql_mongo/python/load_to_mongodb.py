"""
Load step. Run this yourself, after setting MONGODB_URI in your own
terminal -- this script never asks for or hardcodes a connection string
(it contains your password).

Usage:
    python build_documents.py   # extract + transform (needs local Postgres)
    python load_to_mongodb.py   # load (needs your own MongoDB Atlas URI)
"""
import gzip
import json
import os
from pathlib import Path

from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "data" / "staged" / "deals.jsonl.gz"

DB_NAME = "merchant_funnel_nosql"
COLLECTION_NAME = "deals"
BATCH_SIZE = 500


def get_client() -> MongoClient:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise SystemExit(
            "Missing required environment variable MONGODB_URI. "
            "Set it in your own terminal before running this script, e.g.\n"
            '  set MONGODB_URI=mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/'
        )
    return MongoClient(uri)


def load_documents(collection) -> int:
    collection.delete_many({})  # idempotent re-run
    batch = []
    n = 0
    with gzip.open(STAGED, "rt", encoding="utf-8") as f:
        for line in f:
            batch.append(json.loads(line))
            if len(batch) >= BATCH_SIZE:
                collection.insert_many(batch)
                n += len(batch)
                batch = []
        if batch:
            collection.insert_many(batch)
            n += len(batch)
    return n


def run_example_queries(collection) -> None:
    print("\n--- Example NoSQL queries against the loaded documents ---\n")

    print("1) Find: 3 activated deals from the online_big lead type")
    for doc in collection.find({"activated": True, "deal.lead_type": "online_big"}).limit(3):
        print(f"   deal {doc['_id'][:12]}...  segment={doc['deal']['business_segment']}  "
              f"revenue=R$ {doc['revenue']['total_revenue']}")

    print("\n2) Aggregation: activation rate by lead type")
    pipeline = [
        {"$group": {
            "_id": "$deal.lead_type",
            "won": {"$sum": 1},
            "activated": {"$sum": {"$cond": ["$activated", 1, 0]}},
        }},
        {"$project": {
            "won": 1, "activated": 1,
            "activation_rate": {"$round": [{"$multiply": [{"$divide": ["$activated", "$won"]}, 100]}, 1]},
        }},
        {"$sort": {"activation_rate": -1}},
    ]
    for row in collection.aggregate(pipeline):
        print(f"   {row['_id']}: {row['activated']}/{row['won']} activated ({row['activation_rate']}%)")

    print("\n3) Aggregation: total revenue by acquisition channel (embedded lead.origin, no join needed)")
    pipeline2 = [
        {"$match": {"activated": True}},
        {"$group": {"_id": "$lead.origin", "revenue": {"$sum": "$revenue.total_revenue"}, "sellers": {"$sum": 1}}},
        {"$sort": {"revenue": -1}},
        {"$limit": 5},
    ]
    for row in collection.aggregate(pipeline2):
        print(f"   {row['_id']}: R$ {row['revenue']:,.2f} across {row['sellers']} activated sellers")

    print("\n4) Activation rate computed directly from embedded fields (no join needed)")
    total = collection.count_documents({})
    activated = collection.count_documents({"activated": True})
    print(f"   {activated:,} / {total:,} won deals activated ({activated / total:.1%})")


def main() -> None:
    client = get_client()
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    print(f"Loading documents into {DB_NAME}.{COLLECTION_NAME} ...")
    n = load_documents(collection)
    print(f"Loaded {n:,} documents")

    collection.create_index("deal.lead_type")
    collection.create_index("activated")
    collection.create_index("lead.origin")
    print("Created indexes on deal.lead_type, activated, lead.origin")

    run_example_queries(collection)

    client.close()
    print(f"\nDone. Data is live in MongoDB Atlas: {DB_NAME}.{COLLECTION_NAME}")


if __name__ == "__main__":
    main()
