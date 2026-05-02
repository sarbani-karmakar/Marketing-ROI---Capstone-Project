# 📊 Marketing ROI & Budget Reallocation: Capstone Project
**Author:** Sarbani Karmakar  
**Score:** 97 / 100

---

## Project Overview

This project is an end-to-end marketing analytics study for an e-commerce platform.
It evaluates marketing spend, channel efficiency, and customer profitability across
5 channels and 40 campaigns over a 7-month period (July 2025 – January 2026),
and produces a data-driven budget reallocation recommendation for the next month.

---

## Business Objective

Determine which marketing channels and campaigns drive sustainable, profitable growth —
and how to optimally allocate next month's marketing budget to maximize contribution margin.

**North Star Metric:** Contribution Margin ROAS (Contribution Margin / Marketing Spend)

**Attribution Method:** Last-Touch Attribution — each order is attributed to the channel
and campaign associated with the session in which the purchase occurred (session_id join).

---

## Repository Structure
Sarbani_Karmakar_Capstone_MarketingROI/
│
├── README.md
│
├── /data/                                        ← Generated output CSVs
│   ├── fact_sessions.csv
│   ├── fact_campaign_daily.csv
│   └── fact_channel_daily.csv
│
├── /etl/
│   └── etl_pipeline.py                           ← Standalone reproducible ETL pipeline
│
├── /analysis/
│   └── Capstone_Project_Sarbani_Karmakar.ipynb   ← Main analysis notebook
│
├── /dashboard/
│   ├── Capstone_Project_Sarbani_karmakar_tableau.twbx
│   └── dashboard_screenshots/
│       ├── Executive_Summary_Dashboard_1.png
│       ├── Channel___Campaign_Performance_Dashboard_2.png
│       ├── Attribution___Regression_Dashboard_3.png
│       └── Segments___Opportunities_Dashboard_4.png
│
└── /final_story/
├── Marketing_ROI_Deck.pptx
└── Decision_Memo.docx

---

## Dataset

| File | Description | Size |
|------|-------------|------|
| `users.csv` | User profiles with city tier, segment, device | 2,600 users |
| `sessions.csv` | All website sessions with channel and campaign | 660,820 sessions |
| `orders.csv` | Order-level revenue, discount, and net amount | 16,193 orders |
| `order_items.csv` | Line items per order with quantity and price | 40,456 rows |
| `products.json` | Product catalogue with cost, category, brand | 240 products |
| `campaigns.csv` | Campaign metadata (channel, name, type) | 40 campaigns |
| `ad_spend_daily.csv` | Daily spend, impressions, clicks per campaign | 211 days |

> Raw data files are **not included** in this repo. Place them in the root folder before running.

---

## How to Run

### Option 1 — Full Notebook
1. Place all raw data files in the same folder as the notebook
2. Open `Capstone_Project_Sarbani_Karmakar.ipynb` in Jupyter Notebook or JupyterLab
3. Click **Kernel → Restart & Run All**
4. All three output CSVs will be saved automatically (~2–3 minutes)

### Option 2 — Standalone ETL
```bash
python etl/etl_pipeline.py
```

---

## Output Files

| File | Description | Rows |
|------|-------------|------|
| `fact_sessions.csv` | One row per session with purchase outcome, user attributes, and margin | ~660,820 |
| `fact_campaign_daily.csv` | One row per campaign per day with spend, attributed sessions, orders, revenue, margin, and KPIs | ~8,440 |
| `fact_channel_daily.csv` | One row per channel per day with aggregated KPIs and control variables (promo_flag, day_of_week, week_index) | ~1,055 |

---

## Notebook Structure

| Section | Description |
|---------|-------------|
| Part A | Business problem framing, North Star Metric, KPIs, attribution rule |
| Part B | ETL pipeline — data loading, cleaning, deduplication, fact table construction |
| Part C | Attribution model, channel performance, segment deep dive, KPI trends |
| Part D | Campaign-day fact table, marketing investigation, spend inefficiencies |
| Part E | Regression impact model (channel-level OLS, train/test split, evaluation) |
| Part F | Budget reallocation plan with 3 scenarios and sensitivity analysis |

---

## How to Open the Dashboard

1. Open `Capstone_Project_Sarbani_karmakar_tableau.twbx` in **Tableau Desktop (v2022.1 or later)**
2. All data is embedded in the `.twbx` file — no separate CSVs needed
3. The dashboard has 4 views:
   - **Dashboard 1 — Executive Summary:** North Star KPI tiles, spend vs revenue by channel, budget plan
   - **Dashboard 2 — Channel & Campaign Performance:** ROAS/CAC by channel, top campaigns table, date filter
   - **Dashboard 3 — Attribution & Regression:** Attributed vs OLS-estimated revenue side-by-side, weekly trend
   - **Dashboard 4 — Segments & Opportunities:** New vs returning users, device × channel, top categories

> Note: Device filter is not available on Dashboard 2 — device data resides in `fact_sessions`, a separate data source.

---

## Key Findings

1. **Budget is structurally misaligned** — Organic (Margin ROAS 5.15) and Email (Margin ROAS 2.18) receive only 6.4% of budget combined; Paid Social (Margin ROAS 0.25) receives 38.4%
2. **Paid Social is destroying value at scale** — all 8 campaigns show Revenue ROAS below 0.75; every Rs 4 spent returns only Rs 1 in contribution margin
3. **C016 and C011 are the clearest waste** — together 9.7% of spend, only 4.4% of revenue, CAC above Rs 9,000
4. **Fashion and Beauty are highest-margin categories (~42%)** — under-targeted relative to Books which drives most revenue at only 38.7% margin
5. **Value segment customers have highest AOV (Rs 6,897)** — the best target for Email upsell and retention campaigns
6. **Returning users drive 99.6% of all conversions** — retention investment is more efficient than new user acquisition at current CAC levels
7. **Revenue anomalies are demand-driven** — Aug 11 spike (+49%) and holiday peaks are explained by promo_flag and seasonality, controlled for in regression

---

## Regression Model

- **Target:** Daily gross revenue
- **Features:** 5 channel spend columns + day_of_week + trend + promo_flag
- **Split:** Time-based 80/20 (Jul–Dec 18 train, Dec 19–Jan 30 test)
- **Results:** Train R² = 0.48, Test R² = 0.61, RMSE Rs 74,979, MAE Rs 56,330
- Only Paid Social statistically significant (p=0.024); Search coefficient not significant (p=0.187) — collinearity likely
- **Limitation:** OLS is unreliable for channels with very low spend share (Email 5.1%, Organic 1.3%); attribution data is the more reliable efficiency signal for those channels

---

## Budget Reallocation Plan

**Fixed next-month budget:** Rs 10,622,971

| Channel | Current % | Suggested % | Action |
|---------|-----------|-------------|--------|
| Email | 5.1% | 20.0% | ⬆ INCREASE |
| Organic | 1.3% | 8.0% | ⬆ INCREASE |
| Paid Social | 38.4% | 20.0% | ⬇ DECREASE |
| Referral | 9.0% | 12.0% | ⬆ INCREASE |
| Search | 46.2% | 40.0% | ⬇ DECREASE |

**30-Day Impact Estimate:**
- Base Case: +Rs 7.12M incremental revenue
- Best Case: +Rs 11.67M
- Worst Case: +Rs 2.58M

---

## Tech Stack

- **Language:** Python 3.x
- **Libraries:** `pandas`, `numpy`, `matplotlib`, `seaborn`, `statsmodels`, `scikit-learn`
- **Dashboard:** Tableau Desktop v2022.1+
- **All monetary values:** Indian Rupees (Rs)

> If `statsmodels` is not installed, the notebook installs it automatically via `pip install statsmodels`.


