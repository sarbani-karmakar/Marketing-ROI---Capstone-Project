"""
etl_pipeline.py
===============
Marketing ROI & Budget Reallocation — Capstone Project
Author : Sarbani Karmakar
Purpose: Reproducible ETL pipeline that transforms 7 raw data files into
         3 clean, analysis-ready fact tables.

Outputs
-------
  fact_sessions.csv       — 1 row per session
  fact_campaign_daily.csv — 1 row per date per campaign
  fact_channel_daily.csv  — 1 row per date per channel

Usage
-----
  Place this script in the same folder as all raw data files, then run:
      python etl_pipeline.py

Requirements
------------
  pip install pandas numpy
"""

import pandas as pd
import numpy as np
import os
import sys

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────

RAW_FILES = {
    "users"      : "users.csv",
    "sessions"   : "sessions.csv",
    "orders"     : "orders.csv",
    "order_items": "order_items.csv",
    "campaigns"  : "campaigns.csv",
    "ad_spend"   : "ad_spend_daily.csv",
    "products"   : "products.json",
}

OUTPUT_FILES = {
    "fact_sessions"        : "fact_sessions.csv",
    "fact_campaign_daily"  : "fact_campaign_daily.csv",
    "fact_channel_daily"   : "fact_channel_daily.csv",
}

# Promo flag rule: days where daily revenue is more than 1.5x the
# rolling 7-day average are flagged as promotional days.
PROMO_REVENUE_MULTIPLIER = 1.5


# ─────────────────────────────────────────────────────────────────
# STEP 1 — LOAD RAW FILES
# ─────────────────────────────────────────────────────────────────

def load_raw_data():
    """Load all 7 raw files and return as a dictionary of DataFrames."""
    print("\n[1/6] Loading raw files...")

    for name, fname in RAW_FILES.items():
        if not os.path.exists(fname):
            print(f"  ERROR: {fname} not found in working directory.")
            print(f"  Please place all raw data files in the same folder as this script.")
            sys.exit(1)

    users       = pd.read_csv(RAW_FILES["users"])
    sessions    = pd.read_csv(RAW_FILES["sessions"])
    orders      = pd.read_csv(RAW_FILES["orders"])
    order_items = pd.read_csv(RAW_FILES["order_items"])
    campaigns   = pd.read_csv(RAW_FILES["campaigns"])
    ad_spend    = pd.read_csv(RAW_FILES["ad_spend"])
    products    = pd.read_json(RAW_FILES["products"])

    print(f"  users        : {users.shape[0]:>7,} rows")
    print(f"  sessions     : {sessions.shape[0]:>7,} rows")
    print(f"  orders       : {orders.shape[0]:>7,} rows")
    print(f"  order_items  : {order_items.shape[0]:>7,} rows")
    print(f"  campaigns    : {campaigns.shape[0]:>7,} rows")
    print(f"  ad_spend     : {ad_spend.shape[0]:>7,} rows")
    print(f"  products     : {products.shape[0]:>7,} rows")

    return users, sessions, orders, order_items, campaigns, ad_spend, products


# ─────────────────────────────────────────────────────────────────
# STEP 2 — CLEAN & STANDARDIZE
# ─────────────────────────────────────────────────────────────────

def clean_data(users, sessions, orders, order_items, campaigns, ad_spend, products):
    """
    Clean and standardize all raw tables.
    Actions:
      - Parse datetime columns
      - Deduplicate on primary keys
      - Fill missing categorical values with 'Unknown'
      - Normalize channel / device casing to lowercase
      - Flag revenue outliers (net > gross) without dropping rows
    """
    print("\n[2/6] Cleaning and standardizing...")

    # ── Datetime parsing ─────────────────────────────────────────
    sessions["session_ts"]  = pd.to_datetime(sessions["session_ts"])
    orders["order_ts"]      = pd.to_datetime(orders["order_ts"])
    users["signup_date"]    = pd.to_datetime(users["signup_date"])
    ad_spend["date"]        = pd.to_datetime(ad_spend["date"]).dt.date

    # ── Deduplication ────────────────────────────────────────────
    before = {
        "sessions" : len(sessions),
        "orders"   : len(orders),
        "ad_spend" : len(ad_spend),
    }
    sessions    = sessions.drop_duplicates(subset=["session_id"])
    orders      = orders.drop_duplicates(subset=["order_id"])
    ad_spend    = ad_spend.drop_duplicates()

    print(f"  Duplicates removed — sessions: {before['sessions']-len(sessions)}, "
          f"orders: {before['orders']-len(orders)}, "
          f"ad_spend: {before['ad_spend']-len(ad_spend)}")

    # ── Missing value handling ───────────────────────────────────
    sessions["user_id"] = sessions["user_id"].fillna("Unknown")
    sessions["device"]  = sessions["device"].fillna("Unknown")
    orders["user_id"]   = orders["user_id"].fillna("Unknown")

    # ── Casing normalization ─────────────────────────────────────
    sessions["channel"] = sessions["channel"].str.lower().str.strip()
    sessions["device"]  = sessions["device"].str.lower().str.strip()

    # ── Revenue outlier flag (net > gross is mathematically impossible) ──
    orders["net_gt_gross_flag"] = (
        orders["net_amount"] > orders["gross_amount"]
    ).astype(int)
    n_flagged = orders["net_gt_gross_flag"].sum()
    print(f"  Revenue outliers flagged (net > gross): {n_flagged:,} orders — retained, gross_amount used as revenue")

    # ── Margin outlier flag (IQR method, 3× fence) ───────────────
    orders["true_margin"] = orders["gross_amount"] - orders.get("total_product_cost", 0)

    return users, sessions, orders, order_items, campaigns, ad_spend, products


# ─────────────────────────────────────────────────────────────────
# STEP 3 — MARGIN ENGINEERING
# ─────────────────────────────────────────────────────────────────

def build_margin(orders, order_items, products):
    """
    Join order_items → products to compute product cost per order.
    Contribution Margin = gross_amount − total_product_cost
    """
    print("\n[3/6] Engineering contribution margin...")

    # Line-item cost and revenue
    oip = order_items.merge(
        products[["product_id", "cost", "category"]],
        on="product_id", how="left"
    )
    oip["product_cost"]    = oip["quantity"] * oip["cost"]
    oip["product_revenue"] = oip["quantity"] * oip["unit_price"]

    # Order-level cost rollup
    order_cost = (
        oip.groupby("order_id", as_index=False)["product_cost"]
        .sum()
        .rename(columns={"product_cost": "total_product_cost"})
    )

    orders = orders.merge(order_cost, on="order_id", how="left")
    orders["true_margin"] = orders["gross_amount"] - orders["total_product_cost"]

    # IQR outlier flag on true_margin
    Q1 = orders["true_margin"].quantile(0.25)
    Q3 = orders["true_margin"].quantile(0.75)
    fence = Q3 + 3 * (Q3 - Q1)
    orders["margin_outlier_flag"] = (orders["true_margin"] > fence).astype(int)
    print(f"  High-margin outliers flagged (above Rs {fence:,.0f}): {orders['margin_outlier_flag'].sum()} — retained")

    return orders, oip


# ─────────────────────────────────────────────────────────────────
# STEP 4 — BUILD fact_sessions
# ─────────────────────────────────────────────────────────────────

def build_fact_sessions(sessions, orders, users):
    """
    1 row per session.
    Last-touch attribution: each session gets credit for any order placed in it.
    """
    print("\n[4/6] Building fact_sessions...")

    # Merge orders into sessions (last-touch)
    fact = sessions.merge(
        orders[["order_id", "session_id", "gross_amount",
                "discount_amount", "net_amount", "true_margin"]],
        on="session_id", how="left"
    )

    # Purchase flag and fill revenue fields
    fact["purchase_flag"] = fact["order_id"].notna().astype(int)
    for col in ["gross_amount", "discount_amount", "net_amount", "true_margin"]:
        fact[col] = fact[col].fillna(0)

    # Merge user attributes
    fact = fact.merge(
        users[["user_id", "signup_date", "city_tier", "segment", "preferred_device"]],
        on="user_id", how="left"
    )

    # is_new_user: 1 if this session is the user's first ever session
    fact["is_new_user"] = (
        fact["session_ts"] ==
        fact.groupby("user_id")["session_ts"].transform("min")
    ).astype(int)

    # Session date
    fact["session_date"] = fact["session_ts"].dt.date

    # Discount rate per session
    fact["discount_rate"] = np.where(
        fact["gross_amount"] > 0,
        fact["discount_amount"] / fact["gross_amount"],
        0
    )

    print(f"  fact_sessions: {fact.shape[0]:,} rows | {fact['purchase_flag'].sum():,} purchases")
    return fact


# ─────────────────────────────────────────────────────────────────
# STEP 5 — BUILD fact_campaign_daily
# ─────────────────────────────────────────────────────────────────

def build_fact_campaign_daily(fact_sessions, ad_spend):
    """
    1 row per date per campaign.
    Merges session-level attribution aggregates with ad spend.
    Derives KPIs: CPC, CTR, CVR, ROAS, CAC proxy.
    """
    print("\n[5/6] Building fact_campaign_daily...")

    # Session-level aggregation by date + campaign
    paid = fact_sessions[fact_sessions["campaign_id"].notna()]

    daily_sessions = (
        paid.groupby(["session_date", "campaign_id", "channel"], as_index=False)
        .agg(
            attributed_sessions = ("session_id",    "count"),
            attributed_orders   = ("purchase_flag", "sum"),
            attributed_revenue  = ("gross_amount",  "sum"),
            attributed_margin   = ("true_margin",   "sum"),
        )
    )

    # Merge with ad spend
    ad_spend["date"] = pd.to_datetime(ad_spend["date"]).dt.date
    fact = ad_spend.merge(
        daily_sessions,
        left_on  = ["date", "campaign_id"],
        right_on = ["session_date", "campaign_id"],
        how      = "left"
    )

    # Drop duplicate channel column and session_date
    if "channel_y" in fact.columns:
        fact = fact.drop(columns=["channel_y", "session_date"])
    if "channel_x" in fact.columns:
        fact = fact.rename(columns={"channel_x": "channel"})

    # Fill nulls from unmatched days
    for col in ["attributed_sessions", "attributed_orders",
                "attributed_revenue", "attributed_margin"]:
        fact[col] = fact[col].fillna(0)

    # Normalize channel
    fact["channel"] = fact["channel"].str.lower().str.strip()

    # Derived KPIs
    fact["roas"] = np.where(
        fact["spend"] > 0,
        fact["attributed_revenue"] / fact["spend"], np.nan
    )
    fact["cpc"] = np.where(
        fact["clicks"] > 0,
        fact["spend"] / fact["clicks"], np.nan
    )
    fact["ctr"] = np.where(
        fact["impressions"] > 0,
        fact["clicks"] / fact["impressions"], np.nan
    )
    fact["cvr"] = np.where(
        fact["attributed_sessions"] > 0,
        fact["attributed_orders"] / fact["attributed_sessions"], np.nan
    )
    fact["cac_proxy"] = np.where(
        fact["attributed_orders"] > 0,
        fact["spend"] / fact["attributed_orders"], np.nan
    )

    print(f"  fact_campaign_daily: {fact.shape[0]:,} rows")
    return fact


# ─────────────────────────────────────────────────────────────────
# STEP 6 — BUILD fact_channel_daily
# ─────────────────────────────────────────────────────────────────

def build_fact_channel_daily(fact_campaign_daily):
    """
    1 row per date per channel.
    Adds control variables: day_of_week, week_index, promo_flag.

    Promo flag rule (documented):
        A day is flagged as promotional (promo_flag = 1) if the total
        daily revenue across all channels exceeds 1.5× the 7-day
        rolling average revenue for that same day. This is a data-driven
        rule that identifies unusually high-revenue days without requiring
        an external promotion calendar.
    """
    print("\n[6/6] Building fact_channel_daily...")

    fact = (
        fact_campaign_daily
        .groupby(["date", "channel"], as_index=False)
        .agg(
            total_spend         = ("spend",               "sum"),
            total_impressions   = ("impressions",         "sum"),
            total_clicks        = ("clicks",              "sum"),
            attributed_orders   = ("attributed_orders",   "sum"),
            attributed_revenue  = ("attributed_revenue",  "sum"),
            attributed_margin   = ("attributed_margin",   "sum"),
        )
    )

    fact["date"] = pd.to_datetime(fact["date"])

    # Control variables
    fact["day_of_week"] = fact["date"].dt.dayofweek   # 0=Monday
    fact["week_index"]  = (
        (fact["date"] - fact["date"].min()).dt.days // 7
    ).astype(int)

    # Promo flag — data-driven rule (documented above)
    daily_rev = (
        fact.groupby("date")["attributed_revenue"]
        .sum()
        .reset_index()
        .rename(columns={"attributed_revenue": "total_daily_rev"})
    )
    daily_rev["date"] = pd.to_datetime(daily_rev["date"])
    daily_rev = daily_rev.sort_values("date")
    daily_rev["rolling_7d_avg"] = (
        daily_rev["total_daily_rev"]
        .rolling(7, min_periods=1)
        .mean()
        .shift(1)   # use prior 7 days, not including today
    )
    daily_rev["promo_flag"] = (
        daily_rev["total_daily_rev"] >
        PROMO_REVENUE_MULTIPLIER * daily_rev["rolling_7d_avg"]
    ).astype(int)

    fact = fact.merge(
        daily_rev[["date", "promo_flag"]], on="date", how="left"
    )
    fact["promo_flag"] = fact["promo_flag"].fillna(0).astype(int)

    # ROAS at channel-day level
    fact["roas"] = np.where(
        fact["total_spend"] > 0,
        fact["attributed_revenue"] / fact["total_spend"], np.nan
    )

    print(f"  fact_channel_daily: {fact.shape[0]:,} rows")
    print(f"  Promo days flagged : {daily_rev['promo_flag'].sum()} days")
    return fact


# ─────────────────────────────────────────────────────────────────
# SAVE OUTPUTS
# ─────────────────────────────────────────────────────────────────

def save_outputs(fact_sessions, fact_campaign_daily, fact_channel_daily):
    """Save all 3 curated datasets to CSV."""
    print("\n[✓] Saving output files...")

    fact_sessions.to_csv(OUTPUT_FILES["fact_sessions"], index=False)
    print(f"  Saved: {OUTPUT_FILES['fact_sessions']} "
          f"({fact_sessions.shape[0]:,} rows, {fact_sessions.shape[1]} cols)")

    fact_campaign_daily.to_csv(OUTPUT_FILES["fact_campaign_daily"], index=False)
    print(f"  Saved: {OUTPUT_FILES['fact_campaign_daily']} "
          f"({fact_campaign_daily.shape[0]:,} rows, {fact_campaign_daily.shape[1]} cols)")

    fact_channel_daily.to_csv(OUTPUT_FILES["fact_channel_daily"], index=False)
    print(f"  Saved: {OUTPUT_FILES['fact_channel_daily']} "
          f"({fact_channel_daily.shape[0]:,} rows, {fact_channel_daily.shape[1]} cols)")


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Marketing ROI Capstone — ETL Pipeline")
    print("=" * 60)

    # Load
    users, sessions, orders, order_items, campaigns, ad_spend, products = (
        load_raw_data()
    )

    # Clean
    users, sessions, orders, order_items, campaigns, ad_spend, products = (
        clean_data(users, sessions, orders, order_items, campaigns, ad_spend, products)
    )

    # Margin engineering
    orders, order_items_products = build_margin(orders, order_items, products)

    # Build fact tables
    fact_sessions       = build_fact_sessions(sessions, orders, users)
    fact_campaign_daily = build_fact_campaign_daily(fact_sessions, ad_spend)
    fact_channel_daily  = build_fact_channel_daily(fact_campaign_daily)

    # Save
    save_outputs(fact_sessions, fact_campaign_daily, fact_channel_daily)

    print("\n" + "=" * 60)
    print("  ETL complete. All 3 output files saved successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
