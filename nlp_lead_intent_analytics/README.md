# nlp_lead_intent_analytics

A conversational-AI / NLP module answering a question specific to an acquisition funnel: when an inbound message arrives, is it a **new sales lead** or **existing-customer noise** — and can that be automated well enough to route it correctly?

## Why this question, not generic chatbot analytics

The sibling [whatsapp-order-ops-analytics](https://github.com/achi-vyshnavi28/whatsapp-order-ops-analytics) repo already has a chatbot-analytics module classifying **post-sale support intent** (billing, delivery, technical issues). This module reuses the same real dataset and the same core technique (TF-IDF + Logistic Regression intent classification) but points it at a different, funnel-specific question: **pre-sale lead detection.** A growth/SDR team wastes its highest-leverage moment — a warm inbound inquiry — if that message sits in a general support queue instead of getting routed to sales immediately.

## Method

1. Parse each real Twitter customer-support conversation into speaker turns.
2. Weak-supervision labeling: a documented, rule-based first pass tags each conversation's opening customer message with one of 6 intents, including a new `sales_inquiry` class (pricing, demos, "how do I sign up", trial/upgrade language) — the "this is a lead" signal.
3. Train a **TF-IDF + Logistic Regression classifier** on an 80/20 split of those weak labels, and report its actual held-out accuracy, per-class precision/recall/F1, and a confusion matrix.
4. Drive all downstream lead-routing analytics off the **trained classifier's predictions**, not the raw rules.

## Confirmed results — actual output from a real run

```
Accuracy: 0.943  Macro F1: 0.867
```

- **94.3% accuracy** / **0.867 macro F1** across 6 intent classes on 1,959 held-out conversations.
- **4.1%** of inbound volume overall carries a sales-inquiry signal.
- Lead-signal rate ranges from **11.3%** (TMobileHelp) down to **1.5%** (comcastcares) across the top 10 brands by volume — a real, usable signal for prioritizing which channels deserve SDR staffing.

Full report with the confusion matrix and per-brand breakdown: [`reports/nlp_report.md`](reports/nlp_report.md).

## Data

Real, anonymized conversations from the [Twitter Customer Support dataset](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter) (9,795 conversations, 108 real brand support accounts) — the same real dataset used in the sibling repo's chatbot-analytics module, reused here for a different, domain-relevant question rather than re-downloaded, since it's already real public data and the point is the technique + framing, not the raw source.

## Running it

```bash
pip install -r ../requirements.txt
python python/nlp_lead_routing.py
```

Regenerates [`reports/nlp_report.md`](reports/nlp_report.md), all 3 figures in `reports/figures/`, and `data/processed_conversations.csv` (consumed by the Streamlit "Lead Intent Analytics" page).
