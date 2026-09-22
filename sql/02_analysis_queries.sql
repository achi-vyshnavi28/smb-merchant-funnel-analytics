-- ============================================================================
-- smb-merchant-funnel-analytics
-- Analytical SQL: multi-table joins, subqueries, CTEs, window functions
-- Run against merchant_funnel_analytics (see sql/01_schema.sql + python/load_data.py)
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Q1. Top-line funnel: leads -> won deals -> activated sellers (3-stage funnel
--     with drop-off at each stage).
-- ----------------------------------------------------------------------------
WITH stages AS (
    SELECT
        (SELECT COUNT(*) FROM marketing_qualified_leads)                       AS total_leads,
        (SELECT COUNT(*) FROM closed_deals)                                    AS won_deals,
        (SELECT COUNT(*) FROM closed_deals cd
            WHERE EXISTS (SELECT 1 FROM sellers s WHERE s.seller_id = cd.seller_id)) AS activated_sellers
)
SELECT
    total_leads,
    won_deals,
    ROUND(100.0 * won_deals / total_leads, 2)          AS lead_to_won_pct,
    activated_sellers,
    ROUND(100.0 * activated_sellers / won_deals, 2)     AS won_to_activated_pct,
    ROUND(100.0 * activated_sellers / total_leads, 2)   AS lead_to_activated_pct
FROM stages;


-- ----------------------------------------------------------------------------
-- Q2. Conversion rate by lead origin (channel performance) -- multi-table
--     join + LEFT JOIN to preserve leads that never closed.
-- ----------------------------------------------------------------------------
SELECT
    mql.origin,
    COUNT(DISTINCT mql.mql_id)                                          AS leads,
    COUNT(DISTINCT cd.mql_id)                                           AS won,
    ROUND(100.0 * COUNT(DISTINCT cd.mql_id) / COUNT(DISTINCT mql.mql_id), 2) AS win_rate_pct
FROM marketing_qualified_leads mql
LEFT JOIN closed_deals cd ON cd.mql_id = mql.mql_id
GROUP BY mql.origin
ORDER BY win_rate_pct DESC;


-- ----------------------------------------------------------------------------
-- Q3. Time-to-close by lead origin (CTE + date math + aggregation).
-- ----------------------------------------------------------------------------
WITH time_to_close AS (
    SELECT
        mql.origin,
        EXTRACT(EPOCH FROM (cd.won_date - mql.first_contact_date)) / 86400.0 AS days_to_close
    FROM closed_deals cd
    JOIN marketing_qualified_leads mql ON mql.mql_id = cd.mql_id
)
SELECT
    origin,
    COUNT(*)                                    AS won_deals,
    ROUND(AVG(days_to_close)::numeric, 1)       AS avg_days_to_close,
    ROUND(MIN(days_to_close)::numeric, 1)       AS fastest_close,
    ROUND(MAX(days_to_close)::numeric, 1)       AS slowest_close
FROM time_to_close
GROUP BY origin
HAVING COUNT(*) >= 10
ORDER BY avg_days_to_close;


-- ----------------------------------------------------------------------------
-- Q4. Sales Rep (SR) leaderboard with window functions: RANK + running share
--     of total deals closed.
-- ----------------------------------------------------------------------------
WITH sr_deals AS (
    SELECT sr_id, COUNT(*) AS deals_won
    FROM closed_deals
    GROUP BY sr_id
)
SELECT
    sr_id,
    deals_won,
    RANK() OVER (ORDER BY deals_won DESC)                                     AS rank,
    ROUND(100.0 * deals_won / SUM(deals_won) OVER (), 2)                      AS pct_of_all_deals,
    ROUND(100.0 * SUM(deals_won) OVER (ORDER BY deals_won DESC) / SUM(deals_won) OVER (), 2)
                                                                               AS cumulative_pct
FROM sr_deals
ORDER BY rank
LIMIT 15;


-- ----------------------------------------------------------------------------
-- Q5. THE HEADLINE FINDING: activation rate by lead_type and business_segment
--     -- of the deals that were "won," how many merchants actually went on
--     to list a product / make a sale? (subquery via EXISTS + CASE aggregation)
-- ----------------------------------------------------------------------------
SELECT
    cd.lead_type,
    COUNT(*)                                                                  AS won_deals,
    SUM(CASE WHEN EXISTS (SELECT 1 FROM sellers s WHERE s.seller_id = cd.seller_id)
             THEN 1 ELSE 0 END)                                               AS activated,
    ROUND(100.0 * SUM(CASE WHEN EXISTS (SELECT 1 FROM sellers s WHERE s.seller_id = cd.seller_id)
                           THEN 1 ELSE 0 END) / COUNT(*), 2)                  AS activation_rate_pct
FROM closed_deals cd
GROUP BY cd.lead_type
HAVING COUNT(*) >= 10
ORDER BY activation_rate_pct ASC;


-- ----------------------------------------------------------------------------
-- Q6. Same headline finding, cut by business_segment (top 10 by volume) --
--     spotting WHICH merchant categories are worst at actually activating.
-- ----------------------------------------------------------------------------
SELECT
    cd.business_segment,
    COUNT(*)                                                                  AS won_deals,
    SUM(CASE WHEN EXISTS (SELECT 1 FROM sellers s WHERE s.seller_id = cd.seller_id)
             THEN 1 ELSE 0 END)                                               AS activated,
    ROUND(100.0 * SUM(CASE WHEN EXISTS (SELECT 1 FROM sellers s WHERE s.seller_id = cd.seller_id)
                           THEN 1 ELSE 0 END) / COUNT(*), 2)                  AS activation_rate_pct
FROM closed_deals cd
GROUP BY cd.business_segment
ORDER BY won_deals DESC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- Q7. Revenue ROI by acquisition channel: of the sellers who DID activate,
--     how much actual revenue did each origin channel generate? (3-table
--     join: leads -> deals -> revenue)
-- ----------------------------------------------------------------------------
SELECT
    mql.origin,
    COUNT(DISTINCT sr.seller_id)                        AS activated_sellers,
    ROUND(SUM(sr.total_revenue)::numeric, 2)            AS total_revenue_generated,
    ROUND(AVG(sr.total_revenue)::numeric, 2)            AS avg_revenue_per_seller
FROM marketing_qualified_leads mql
JOIN closed_deals cd ON cd.mql_id = mql.mql_id
JOIN seller_revenue sr ON sr.seller_id = cd.seller_id
GROUP BY mql.origin
ORDER BY total_revenue_generated DESC;


-- ----------------------------------------------------------------------------
-- Q8. Anomaly: sellers who DECLARED high monthly revenue at sign-up but
--     generated little-to-no actual revenue (subquery comparing declared vs
--     actual) -- a concrete "over-promised at onboarding" flag list.
-- ----------------------------------------------------------------------------
SELECT
    cd.seller_id,
    cd.business_segment,
    cd.declared_monthly_revenue,
    COALESCE(sr.total_revenue, 0)                                    AS actual_total_revenue,
    COALESCE(sr.total_orders, 0)                                     AS actual_orders
FROM closed_deals cd
LEFT JOIN seller_revenue sr ON sr.seller_id = cd.seller_id
WHERE cd.declared_monthly_revenue > (
        SELECT AVG(declared_monthly_revenue) FROM closed_deals WHERE declared_monthly_revenue > 0
      )
  AND COALESCE(sr.total_revenue, 0) < 100
ORDER BY cd.declared_monthly_revenue DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- Q9. Monthly cohort trend: leads acquired per month vs. win rate for that
--     cohort (CTE + date_trunc + window function for month-over-month change).
-- ----------------------------------------------------------------------------
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', mql.first_contact_date)::date AS cohort_month,
        COUNT(DISTINCT mql.mql_id)                          AS leads,
        COUNT(DISTINCT cd.mql_id)                           AS won
    FROM marketing_qualified_leads mql
    LEFT JOIN closed_deals cd ON cd.mql_id = mql.mql_id
    GROUP BY 1
)
SELECT
    cohort_month,
    leads,
    won,
    ROUND(100.0 * won / NULLIF(leads, 0), 2)                                 AS win_rate_pct,
    ROUND(100.0 * (leads - LAG(leads) OVER (ORDER BY cohort_month)) /
          NULLIF(LAG(leads) OVER (ORDER BY cohort_month), 0), 1)             AS lead_volume_mom_change_pct
FROM monthly
ORDER BY cohort_month;
