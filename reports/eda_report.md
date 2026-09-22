# smb-merchant-funnel-analytics — Automated EDA Report

_Generated programmatically by `python/eda_analysis.py` from live queries against the `merchant_funnel_analytics` PostgreSQL database._

## Data Source
Real, anonymized data from Olist's [Marketing Funnel dataset](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist) (8,000 leads, 842 closed deals, CC BY-NC-SA 4.0), joined to real seller revenue derived from the companion e-commerce order data.

## Data Cleaning Notes
- **closed deals total**: 842
- **missing has company flag**: 779
- **missing has gtin flag**: 778
- **declared revenue outliers zero actual**: 14

## 1. The Headline Finding: Won ≠ Activated
![Activation drop-off](reports/figures/01_activation_dropoff.png)

Of 842 closed ('won') deals, only 380 (45.1%) ever actually listed a product or made a sale. **More than half of merchant acquisition wins never activate.** This is the single highest-leverage number in the whole funnel — fixing lead quality or onboarding support here is worth more than optimizing the top of the funnel.

## 2. Activation Rate by Lead Type
![Activation by lead type](reports/figures/02_activation_by_leadtype.png)

| lead_type       |   won |   activated |   activation_rate |
|:----------------|------:|------------:|------------------:|
| other           |     3 |           0 |               0   |
| offline         |   104 |          30 |              28.8 |
| industry        |   123 |          41 |              33.3 |
| online_small    |    77 |          28 |              36.4 |
| online_beginner |    57 |          21 |              36.8 |
| online_top      |    14 |           6 |              42.9 |
| online_medium   |   332 |         171 |              51.5 |
| online_big      |   126 |          79 |              62.7 |

Chi-square test of independence (activation vs. lead type): χ² = 45.69, dof = 7, p < 0.001. Activation is **not** independent of lead type — `online_big` leads activate at 62.7% vs. just 28.9% for `offline` leads, a statistically confirmed gap worth targeting acquisition spend toward.

## 3. Revenue by Acquisition Channel
![Channel ROI](reports/figures/03_channel_roi.png)

| origin         |   activated_sellers |   total_revenue |   avg_revenue |
|:---------------|--------------------:|----------------:|--------------:|
| unknown        |                  81 |       238479    |       2944.18 |
| organic_search |                 112 |       235919    |       2106.42 |
| paid_search    |                 101 |       179427    |       1776.51 |
| social         |                  31 |        51292    |       1654.58 |
| direct_traffic |                  31 |        27517.1  |        887.65 |
| referral       |                   9 |        19687.8  |       2187.54 |
| email          |                   6 |         9122.41 |       1520.4  |
| other          |                   2 |         8766.63 |       4383.32 |
| display        |                   2 |         1207.95 |        603.98 |

`unknown` and `organic_search` generate the most total revenue among activated sellers — `social`, despite reasonable lead volume, converts far less efficiently into revenue.

## 4. Predicting Activation at the Moment a Deal Is Won
A logistic regression model trained on features known the moment a deal closes (lead type, business segment, has_company, has_gtin, declared catalog size) predicts whether that seller will actually activate, with **58.8% accuracy** and **ROC-AUC = 0.645** on 211 held-out deals.

```
              precision    recall  f1-score   support

           0       0.64      0.58      0.61       116
           1       0.54      0.60      0.57        95

    accuracy                           0.59       211
   macro avg       0.59      0.59      0.59       211
weighted avg       0.59      0.59      0.59       211

```

Strongest predictive features (logistic regression coefficients):
- `business_segment=jewerly` decreases activation likelihood (coef = -1.26)
- `business_segment=household_utilities` increases activation likelihood (coef = 0.95)
- `business_segment=baby` increases activation likelihood (coef = 0.90)
- `lead_type=online_big` increases activation likelihood (coef = 0.87)
- `business_segment=home_office_furniture` decreases activation likelihood (coef = -0.85)
- `declared_product_catalog_size` decreases activation likelihood (coef = -0.83)
- `business_segment=handcrafted` decreases activation likelihood (coef = -0.75)
- `business_segment=sports_leisure` increases activation likelihood (coef = 0.74)

**Business use**: this model could flag low-activation-probability merchants for extra onboarding support the moment they sign — turning a purely descriptive funnel report into an operational early-warning list.

## 5. Anomaly: Declared Revenue vs. Reality
| seller_id                        | business_segment                |   declared_monthly_revenue |
|:---------------------------------|:--------------------------------|---------------------------:|
| 6fcc97197c64771f3c18aea3aa9d3913 | construction_tools_house_garden |                      5e+07 |
| 9966324e28b7fa38165d2d3d12d53b7f | phone_mobile                    |                      8e+06 |
| c33e6d3ad32fd5bec1b0f2522f668213 | other                           |                 500000     |
| 157497483bb7876340ea4441c9bd1774 | pet                             |                 300000     |
| 7c7d0dee362960b1d9b01fe7284e19ba | home_decor                      |                 300000     |
| 8c6d188ef073e289887bc52bc37f3e61 | audio_video_electronics         |                 250000     |
| 0d7d5bca59d45d750fb7913b974e9d08 | construction_tools_house_garden |                 250000     |
| 366b6b05f39997f102dc5179de14d43c | health_beauty                   |                 210000     |
| 4a82eab98441aeb64566e2776c1fb2b6 | construction_tools_house_garden |                 200000     |
| 5181ea7b0d346ed14c5c07f0ff22b2b4 | toys                            |                 180000     |
| f233b575e585413f12fe2f847d922447 | household_utilities             |                 150000     |
| 53be10ff134691e94a4089b41c75874f | construction_tools_house_garden |                 130000     |
| 7e1f0755f1c75e301dfa37c21fd01efe | other                           |                 120000     |
| 7e165d0fd266781dbf944faf150e265b | home_decor                      |                 120000     |

Two sellers declared R$50,000,000 and R$8,000,000 in expected monthly revenue at sign-up and generated **zero** actual revenue. Declared figures at onboarding are self-reported and essentially unverified — a real data-quality/fraud-risk signal worth a sanity-check cap in the sign-up flow.

## Summary
- Only 45% of won deals ever activate — the funnel's biggest leak is *after* the sale closes, not before.
- Activation is statistically linked to lead type (χ² test) — `online_big` merchants are the highest-value acquisition target.
- `organic_search` and `unknown`-origin leads generate more revenue per activated seller than paid channels — paid acquisition spend isn't obviously paying off.
- A simple logistic regression predicts activation well enough to be operationally useful as an early-warning flag, not just a retrospective report.
- Self-reported onboarding data (declared revenue) contains obvious outliers that a sanity check would catch.