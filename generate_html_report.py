#!/usr/bin/env python3
"""Generate a branded, multi-tab HTML audit report for TikTok, Meta & Google Ads."""

import json
import base64
from pathlib import Path
from datetime import datetime
from collections import defaultdict

OUT_DIR = Path(__file__).parent
RAW_DIR = OUT_DIR / "raw"
ASSETS_DIR = OUT_DIR / "assets"


def load_logo_base64():
    logo_path = ASSETS_DIR / "whitecar-logo.png"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return ""


def parse_mcp(filename):
    path = RAW_DIR / filename
    if not path.exists():
        return None, "file not found"
    raw = json.loads(path.read_text())
    if raw.get("result", {}).get("isError"):
        return None, raw["result"]["content"][0]["text"]
    return json.loads(raw["result"]["content"][0]["text"]), None


def fmt_num(n):
    try:
        return f"{int(float(n)):,}"
    except (ValueError, TypeError):
        return "-"


def fmt_sar(n):
    try:
        return f"SAR {float(n):,.2f}"
    except (ValueError, TypeError):
        return "-"


def fmt_pct(n, is_tiktok_api_value=False):
    try:
        val = float(n)
        if is_tiktok_api_value:
            return f"{val:.2f}%"
        return f"{val * 100:.2f}%"
    except (ValueError, TypeError):
        return "-"


def safe_div(num, den, default=0):
    try:
        return float(num) / float(den) if float(den) else default
    except (ValueError, TypeError):
        return default


def meta_sum_conversions(actions):
    lead_actions = {
        "onsite_conversion.lead",
        "offsite_complete_registration_add_meta_leads",
        "offsite_search_add_meta_leads",
        "onsite_web_lead",
        "onsite_conversion.messaging_conversation_replied_7d",
        "onsite_conversion.total_messaging_connection",
        "lead",
    }
    total = 0
    for a in actions or []:
        if a.get("action_type") in lead_actions:
            total += int(float(a.get("value", 0) or 0))
    return total


# ===================== ANALYSIS FUNCTIONS =====================

def analyze_tiktok():
    advertiser, _ = parse_mcp("tiktok_advertiser_info.json")
    campaigns_data, _ = parse_mcp("tiktok_campaigns.json")
    adgroups_data, _ = parse_mcp("tiktok_adgroups.json")
    ads_data, _ = parse_mcp("tiktok_ads.json")
    camp_insights, _ = parse_mcp("tiktok_insights_campaign.json")
    daily_insights, _ = parse_mcp("tiktok_insights_daily.json")
    ad_insights, _ = parse_mcp("tiktok_insights_ad.json")
    adgroup_insights, _ = parse_mcp("tiktok_insights_adgroup.json")

    adv = advertiser["advertiser"]
    campaigns = campaigns_data.get("campaigns", [])
    adgroups = adgroups_data.get("adgroups", [])
    ads = ads_data.get("ads", [])
    adgroup_map = {ag["adgroup_id"]: ag for ag in adgroups}
    campaign_map = {c["campaign_id"]: c for c in campaigns}

    camp_metrics = camp_insights.get("metrics", [])
    total_spend = total_impressions = total_clicks = total_conversions = 0
    total_video_plays = total_p25 = total_p50 = total_p75 = total_p100 = 0
    campaign_rows = []

    for row in camp_metrics:
        cid = row["dimensions"]["campaign_id"]
        m = row["metrics"]
        spend = float(m.get("spend", 0) or 0)
        impressions = int(float(m.get("impressions", 0) or 0))
        clicks = int(float(m.get("clicks", 0) or 0))
        conversions = int(float(m.get("conversion", 0) or 0))
        video_plays = int(float(m.get("video_play_actions", 0) or 0))
        p25 = int(float(m.get("video_views_p25", 0) or 0))
        p50 = int(float(m.get("video_views_p50", 0) or 0))
        p75 = int(float(m.get("video_views_p75", 0) or 0))
        p100 = int(float(m.get("video_views_p100", 0) or 0))
        ctr = float(m.get("ctr", 0) or 0)
        cpc = float(m.get("cpc", 0) or 0)
        cpconv = float(m.get("cost_per_conversion", 0) or 0)

        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        total_conversions += conversions
        total_video_plays += video_plays
        total_p25 += p25
        total_p50 += p50
        total_p75 += p75
        total_p100 += p100

        c = campaign_map.get(cid, {})
        campaign_rows.append({
            "campaign_id": cid, "name": c.get("campaign_name", cid),
            "status": c.get("operation_status", "UNKNOWN"),
            "objective": c.get("objective_type", "UNKNOWN"),
            "create_time": c.get("create_time", ""),
            "budget": float(c.get("budget", 0) or 0),
            "spend": spend, "impressions": impressions, "clicks": clicks,
            "conversions": conversions, "ctr": ctr, "cpc": cpc, "cpconv": cpconv,
            "video_plays": video_plays, "p25": p25, "p50": p50, "p75": p75, "p100": p100,
            "completion_rate": safe_div(p100, video_plays),
            "vtr": safe_div(video_plays, impressions),
            "conv_rate": safe_div(conversions, clicks),
        })

    top_campaigns = sorted(campaign_rows, key=lambda x: x["spend"], reverse=True)
    best_cpa = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpconv"])[:5]
    worst_cpa = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpconv"], reverse=True)[:5]

    ad_metrics = ad_insights.get("metrics", [])
    ad_map = {a["ad_id"]: a for a in ads}
    ad_rows = []
    for row in ad_metrics:
        aid = row["dimensions"]["ad_id"]
        m = row["metrics"]
        a = ad_map.get(aid, {})
        spend = float(m.get("spend", 0) or 0)
        impressions = int(float(m.get("impressions", 0) or 0))
        clicks = int(float(m.get("clicks", 0) or 0))
        conversions = int(float(m.get("conversion", 0) or 0))
        ad_rows.append({
            "ad_id": aid, "name": a.get("ad_name", aid), "text": a.get("ad_text", ""),
            "campaign_name": a.get("campaign_name", ""), "campaign_id": a.get("campaign_id", ""),
            "status": a.get("operation_status", "UNKNOWN"),
            "spend": spend, "impressions": impressions, "clicks": clicks, "conversions": conversions,
            "ctr": float(m.get("ctr", 0) or 0), "cpc": float(m.get("cpc", 0) or 0),
            "cpconv": float(m.get("cost_per_conversion", 0) or 0),
            "conv_rate": safe_div(conversions, clicks),
        })
    top_ads = sorted(ad_rows, key=lambda x: x["spend"], reverse=True)
    best_ads_ctr = sorted([a for a in ad_rows if a["impressions"] > 1000], key=lambda x: x["ctr"], reverse=True)[:5]

    adgroup_rows = []
    if adgroup_insights:
        for row in adgroup_insights.get("metrics", []):
            agid = row["dimensions"]["adgroup_id"]
            m = row["metrics"]
            ag = adgroup_map.get(agid, {})
            spend = float(m.get("spend", 0) or 0)
            video_plays = int(float(m.get("video_play_actions", 0) or 0))
            impressions = int(float(m.get("impressions", 0) or 0))
            conversions = int(float(m.get("conversion", 0) or 0))
            p100 = int(float(m.get("video_views_p100", 0) or 0))
            adgroup_rows.append({
                "adgroup_id": agid, "name": ag.get("adgroup_name", agid),
                "campaign_name": ag.get("campaign_name", ""), "campaign_id": ag.get("campaign_id", ""),
                "status": ag.get("operation_status", "UNKNOWN"),
                "spend": spend, "impressions": impressions, "clicks": int(float(m.get("clicks", 0) or 0)),
                "conversions": conversions, "ctr": float(m.get("ctr", 0) or 0),
                "cpc": float(m.get("cpc", 0) or 0), "cpconv": float(m.get("cost_per_conversion", 0) or 0),
                "video_plays": video_plays, "completion_rate": safe_div(p100, video_plays),
                "vtr": safe_div(video_plays, impressions), "conv_rate": safe_div(conversions, clicks),
            })
    top_adgroups = sorted(adgroup_rows, key=lambda x: x["spend"], reverse=True)

    daily_rows = []
    for row in daily_insights.get("metrics", []):
        day = row["dimensions"]["stat_time_day"][:10]
        m = row["metrics"]
        daily_rows.append({
            "day": day, "spend": float(m.get("spend", 0) or 0),
            "impressions": int(float(m.get("impressions", 0) or 0)),
            "clicks": int(float(m.get("clicks", 0) or 0)),
            "conversions": int(float(m.get("conversion", 0) or 0)),
        })
    daily_rows_sorted = sorted(daily_rows, key=lambda x: x["day"])
    top_days = sorted(daily_rows, key=lambda x: x["spend"], reverse=True)[:5]
    best_cpa_days = sorted([d for d in daily_rows if d["conversions"] > 0], key=lambda x: x["spend"] / x["conversions"])[:5]

    dow_spend = defaultdict(float)
    dow_conv = defaultdict(int)
    dow_clicks = defaultdict(int)
    dow_impressions = defaultdict(int)
    for row in daily_rows:
        dow = datetime.strptime(row["day"], "%Y-%m-%d").strftime("%A")
        dow_spend[dow] += row["spend"]
        dow_conv[dow] += row["conversions"]
        dow_clicks[dow] += row["clicks"]
        dow_impressions[dow] += row["impressions"]
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_rows = []
    for dow in dow_order:
        if dow in dow_spend:
            dow_rows.append({
                "day": dow, "spend": dow_spend[dow], "conversions": dow_conv[dow],
                "clicks": dow_clicks[dow], "impressions": dow_impressions[dow],
                "ctr": safe_div(dow_clicks[dow], dow_impressions[dow]),
                "cpa": safe_div(dow_spend[dow], dow_conv[dow], 0),
            })

    monthly_spend = defaultdict(float)
    monthly_conversions = defaultdict(int)
    for row in daily_rows:
        month = row["day"][:7]
        monthly_spend[month] += row["spend"]
        monthly_conversions[month] += row["conversions"]
    top_months = sorted(
        [{"month": m, "spend": s, "conversions": monthly_conversions[m]} for m, s in monthly_spend.items()],
        key=lambda x: x["spend"], reverse=True,
    )

    active_campaigns = [c for c in campaigns if c.get("operation_status") == "ENABLE"]
    inactive_campaigns = [c for c in campaigns if c.get("operation_status") != "ENABLE"]

    # Hourly data (TikTok only allows 1-day span; use yesterday)
    hourly_data, _ = parse_mcp("tiktok_insights_hourly.json")
    hourly_data = hourly_data or {}
    hourly_rows = []
    for row in hourly_data.get("metrics", []):
        ts = row["dimensions"]["stat_time_hour"]
        hour = int(ts[11:13])
        m = row["metrics"]
        spend = float(m.get("spend", 0) or 0)
        clicks = int(float(m.get("clicks", 0) or 0))
        conversions = int(float(m.get("conversion", 0) or 0))
        hourly_rows.append({
            "hour": hour, "spend": spend, "impressions": int(float(m.get("impressions", 0) or 0)),
            "clicks": clicks, "conversions": conversions,
            "ctr": safe_div(clicks, int(float(m.get("impressions", 0) or 0))),
            "cpa": safe_div(spend, conversions, 0), "conv_rate": safe_div(conversions, clicks),
        })
    hourly_rows = sorted(hourly_rows, key=lambda x: x["hour"])

    top_weekdays = sorted(dow_rows, key=lambda x: (x["conversions"] > 0, -safe_div(x["spend"], x["conversions"], 999999), -x["spend"]), reverse=True)

    return {
        "account": adv, "total_campaigns": len(campaigns),
        "active_campaigns": len(active_campaigns), "inactive_campaigns": inactive_campaigns,
        "total_adgroups": len(adgroups), "total_ads": len(ads),
        "total_spend": total_spend, "total_impressions": total_impressions,
        "total_clicks": total_clicks, "total_conversions": total_conversions,
        "total_video_plays": total_video_plays,
        "top_campaigns": top_campaigns, "best_cpa_campaigns": best_cpa, "worst_cpa_campaigns": worst_cpa,
        "top_adgroups": top_adgroups, "top_ads": top_ads, "best_ads_by_ctr": best_ads_ctr,
        "daily_rows": daily_rows_sorted, "top_days": top_days, "best_cpa_days": best_cpa_days,
        "dow_rows": dow_rows, "top_weekdays": top_weekdays, "top_months": top_months,
        "video_funnel": {"plays": total_video_plays, "p25": total_p25, "p50": total_p50, "p75": total_p75, "p100": total_p100},
        "hourly_rows": hourly_rows,
        "cpa": safe_div(total_spend, total_conversions, 0),
    }


def analyze_meta():
    account_info, err = parse_mcp("meta_account_info.json")
    campaigns_data, _ = parse_mcp("meta_campaigns.json")
    adsets_data, _ = parse_mcp("meta_adsets.json")
    campaign_insights, _ = parse_mcp("meta_campaign_insights.json")

    if err or not account_info:
        return None

    account = account_info
    campaigns = campaigns_data.get("data", [])
    adsets = adsets_data.get("data", [])
    campaign_map = {c["id"]: c for c in campaigns}

    total_spend = total_impressions = total_clicks = total_conversions = total_reach = 0
    campaign_rows = []

    for row in campaign_insights.get("data", []):
        cid = row.get("campaign_id")
        c = campaign_map.get(cid, {})
        spend = float(row.get("spend", 0) or 0)
        impressions = int(float(row.get("impressions", 0) or 0))
        clicks = int(float(row.get("clicks", 0) or 0))
        conversions = meta_sum_conversions(row.get("actions", []))
        ctr = float(row.get("ctr", 0) or 0)
        cpc = float(row.get("cpc", 0) or 0)
        cpm = float(row.get("cpm", 0) or 0)
        reach = int(float(row.get("reach", 0) or 0))
        frequency = float(row.get("frequency", 0) or 0)

        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        total_conversions += conversions
        total_reach += reach

        campaign_rows.append({
            "campaign_id": cid, "name": row.get("campaign_name", c.get("name", cid)),
            "status": c.get("status", "UNKNOWN"), "objective": c.get("objective", "UNKNOWN"),
            "spend": spend, "impressions": impressions, "clicks": clicks, "conversions": conversions,
            "ctr": ctr, "cpc": cpc, "cpm": cpm, "reach": reach, "frequency": frequency,
            "cpa": safe_div(spend, conversions, 0), "conv_rate": safe_div(conversions, clicks),
            "daily_budget": float(c.get("daily_budget", 0) or 0) / 100,
            "start_time": c.get("start_time", ""),
        })

    top_campaigns = sorted(campaign_rows, key=lambda x: x["spend"], reverse=True)
    best_cpa = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpa"])[:5]
    worst_cpa = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpa"], reverse=True)[:5]

    active_campaigns = [c for c in campaigns if c.get("status") == "ACTIVE"]
    paused_campaigns = [c for c in campaigns if c.get("status") != "ACTIVE"]
    active_adsets = [a for a in adsets if a.get("status") == "ACTIVE"]
    paused_adsets = [a for a in adsets if a.get("status") != "ACTIVE"]

    adset_rows = []
    for ag in adsets:
        targeting = ag.get("targeting", {})
        geo = targeting.get("geo_locations", {})
        countries = geo.get("countries", [])
        interests = []
        for spec in targeting.get("flexible_spec", []):
            for interest in spec.get("interests", []):
                interests.append(interest.get("name", ""))
        age_min = targeting.get("age_min", "")
        age_max = targeting.get("age_max", "")
        adset_rows.append({
            "name": ag.get("name", ""), "campaign_id": ag.get("campaign_id", ""),
            "status": ag.get("status", ""), "budget": float(ag.get("daily_budget", 0) or 0) / 100,
            "bid_strategy": ag.get("bid_strategy", ""), "age_min": age_min, "age_max": age_max,
            "countries": ", ".join(countries), "interests": ", ".join(interests[:5]),
        })

    # Demographic & hourly breakdowns
    def agg_meta_breakdown(filename, key):
        data, _ = parse_mcp(filename)
        data = data or {}
        rows = []
        for r in data.get("data", []):
            spend = float(r.get("spend", 0) or 0)
            clicks = int(float(r.get("clicks", 0) or 0))
            conversions = meta_sum_conversions(r.get("actions", []))
            rows.append({
                "key": r.get(key, "Unknown"), "spend": spend,
                "impressions": int(float(r.get("impressions", 0) or 0)),
                "clicks": clicks, "conversions": conversions,
                "ctr": float(r.get("ctr", 0) or 0),
                "cpa": safe_div(spend, conversions, 0),
                "conv_rate": safe_div(conversions, clicks),
            })
        return rows

    age_rows = agg_meta_breakdown("meta_age.json", "age") if (RAW_DIR / "meta_age.json").exists() else []
    gender_rows = agg_meta_breakdown("meta_gender.json", "gender") if (RAW_DIR / "meta_gender.json").exists() else []
    region_rows = agg_meta_breakdown("meta_region.json", "region") if (RAW_DIR / "meta_region.json").exists() else []

    # Aggregate by demographic value
    def sum_breakdown(rows):
        totals = {}
        for r in rows:
            k = r["key"]
            if k not in totals:
                totals[k] = {"spend": 0, "impressions": 0, "clicks": 0, "conversions": 0}
            for m in ["spend", "impressions", "clicks", "conversions"]:
                totals[k][m] += r[m]
        out = []
        for k, v in totals.items():
            out.append({
                "key": k, **v,
                "ctr": safe_div(v["clicks"], v["impressions"]),
                "cpa": safe_div(v["spend"], v["conversions"], 0),
                "conv_rate": safe_div(v["conversions"], v["clicks"]),
            })
        return sorted(out, key=lambda x: x["spend"], reverse=True)

    age_rows = sum_breakdown(age_rows)
    gender_rows = sum_breakdown(gender_rows)
    region_rows = sum_breakdown(region_rows)

    hourly_data, _ = parse_mcp("meta_hourly.json")
    hourly_data = hourly_data or {}
    hourly_rows = []
    for r in hourly_data.get("data", []):
        hour_range = r.get("hourly_stats_aggregated_by_advertiser_time_zone", "00:00:00 - 00:59:59")
        hour = int(hour_range.split(":")[0])
        spend = float(r.get("spend", 0) or 0)
        clicks = int(float(r.get("clicks", 0) or 0))
        conversions = meta_sum_conversions(r.get("actions", []))
        hourly_rows.append({
            "hour": hour, "spend": spend,
            "impressions": int(float(r.get("impressions", 0) or 0)),
            "clicks": clicks, "conversions": conversions,
            "ctr": float(r.get("ctr", 0) or 0),
            "cpa": safe_div(spend, conversions, 0), "conv_rate": safe_div(conversions, clicks),
        })
    hourly_rows = sorted(hourly_rows, key=lambda x: x["hour"])

    # Day-of-week from daily data if available
    daily_meta, _ = parse_mcp("meta_daily.json")
    daily_meta = daily_meta or {}
    dow_meta = {}
    for r in daily_meta.get("data", []) if daily_meta else []:
        try:
            day = datetime.strptime(r.get("date_start", ""), "%Y-%m-%d").strftime("%A")
        except Exception:
            continue
        spend = float(r.get("spend", 0) or 0)
        clicks = int(float(r.get("clicks", 0) or 0))
        conversions = meta_sum_conversions(r.get("actions", []))
        if day not in dow_meta:
            dow_meta[day] = {"spend": 0, "impressions": 0, "clicks": 0, "conversions": 0}
        dow_meta[day]["spend"] += spend
        dow_meta[day]["impressions"] += int(float(r.get("impressions", 0) or 0))
        dow_meta[day]["clicks"] += clicks
        dow_meta[day]["conversions"] += conversions
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_rows = []
    for dow in dow_order:
        if dow in dow_meta:
            v = dow_meta[dow]
            dow_rows.append({
                "day": dow, "spend": v["spend"], "impressions": v["impressions"],
                "clicks": v["clicks"], "conversions": v["conversions"],
                "ctr": safe_div(v["clicks"], v["impressions"]),
                "cpa": safe_div(v["spend"], v["conversions"], 0),
                "conv_rate": safe_div(v["conversions"], v["clicks"]),
            })
    top_weekdays = sorted(dow_rows, key=lambda x: (x["conversions"] > 0, -x["cpa"], -x["spend"]), reverse=True)

    return {
        "account": account, "total_campaigns": len(campaigns),
        "active_campaigns": len(active_campaigns), "paused_campaigns": paused_campaigns,
        "total_adsets": len(adsets), "active_adsets": len(active_adsets), "paused_adsets": len(paused_adsets), "total_spend": total_spend,
        "total_impressions": total_impressions, "total_clicks": total_clicks,
        "total_conversions": total_conversions, "total_reach": total_reach,
        "top_campaigns": top_campaigns, "best_cpa_campaigns": best_cpa, "worst_cpa_campaigns": worst_cpa,
        "adset_rows": adset_rows,
        "age_rows": age_rows, "gender_rows": gender_rows, "region_rows": region_rows,
        "hourly_rows": hourly_rows, "dow_rows": dow_rows, "top_weekdays": top_weekdays,
        "cpa": safe_div(total_spend, total_conversions, 0),
    }


def analyze_google_ads():
    account_info, err = parse_mcp("google_ads_account_info.json")
    campaigns_data, _ = parse_mcp("google_ads_campaigns.json")
    ads_data, _ = parse_mcp("google_ads_ads.json")
    monthly_data, _ = parse_mcp("google_ads_monthly.json")
    adgroups_data, _ = parse_mcp("google_ads_adgroups.json")
    device_data, _ = parse_mcp("google_ads_device.json")
    dow_data, _ = parse_mcp("google_ads_dayofweek.json")
    geo_data, _ = parse_mcp("google_ads_geo.json")
    geo_target_data, _ = parse_mcp("google_ads_geo_targets.json")
    geo_data = geo_data or {}
    geo_target_data = geo_target_data or {}

    if err or not account_info:
        return None

    account = account_info.get("account", {})
    campaigns = campaigns_data.get("campaigns", [])
    ads = ads_data.get("ads", [])

    campaign_totals = defaultdict(lambda: {"spend": 0.0, "impressions": 0, "clicks": 0, "conversions": 0, "conversions_value": 0})
    monthly_spend = defaultdict(float)
    monthly_conversions = defaultdict(int)
    total_spend = total_impressions = total_clicks = total_conversions = total_conversion_value = 0

    for row in monthly_data.get("results", []):
        cid = row["campaign"]["id"]
        cname = row["campaign"]["name"]
        m = row["metrics"]
        month = row["segments"]["month"]
        spend = float(m.get("costMicros", 0) or 0) / 1_000_000
        impressions = int(float(m.get("impressions", 0) or 0))
        clicks = int(float(m.get("clicks", 0) or 0))
        conversions = int(float(m.get("conversions", 0) or 0))
        conv_value = float(m.get("conversionsValue", 0) or 0)

        campaign_totals[cid]["name"] = cname
        campaign_totals[cid]["spend"] += spend
        campaign_totals[cid]["impressions"] += impressions
        campaign_totals[cid]["clicks"] += clicks
        campaign_totals[cid]["conversions"] += conversions
        campaign_totals[cid]["conversions_value"] += conv_value

        monthly_spend[month] += spend
        monthly_conversions[month] += conversions

        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        total_conversions += conversions
        total_conversion_value += conv_value

    campaign_rows = []
    for cid, data in campaign_totals.items():
        campaign_rows.append({
            "campaign_id": cid, "name": data["name"], "spend": data["spend"],
            "impressions": data["impressions"], "clicks": data["clicks"], "conversions": data["conversions"],
            "conversions_value": data["conversions_value"], "ctr": safe_div(data["clicks"], data["impressions"]),
            "cpc": safe_div(data["spend"], data["clicks"], 0), "cpa": safe_div(data["spend"], data["conversions"], 0),
            "roas": safe_div(data["conversions_value"], data["spend"], 0),
            "conv_rate": safe_div(data["conversions"], data["clicks"]),
        })
    top_campaigns = sorted(campaign_rows, key=lambda x: x["spend"], reverse=True)
    best_cpa = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpa"])[:3]

    top_months = sorted(
        [{"month": m, "spend": s, "conversions": monthly_conversions[m]} for m, s in monthly_spend.items()],
        key=lambda x: x["spend"], reverse=True,
    )

    adgroup_rows = []
    for row in adgroups_data.get("results", []):
        ag = row["adGroup"]
        c = row["campaign"]
        m = row["metrics"]
        spend = float(m.get("costMicros", 0) or 0) / 1_000_000
        clicks = int(float(m.get("clicks", 0) or 0))
        conversions = int(float(m.get("conversions", 0) or 0))
        impressions = int(float(m.get("impressions", 0) or 0))
        conv_value = float(m.get("conversionsValue", 0) or 0)
        adgroup_rows.append({
            "name": ag["name"], "campaign": c["name"], "spend": spend, "impressions": impressions,
            "clicks": clicks, "conversions": conversions, "conversions_value": conv_value,
            "ctr": m.get("ctr", 0),
            "cpc": float(m.get("averageCpc", 0) or 0) / 1_000_000,
            "cpa": float(m.get("costPerConversion", 0) or 0) / 1_000_000 if conversions else 0,
            "conv_rate": safe_div(conversions, clicks),
            "roas": safe_div(conv_value, spend, 0),
        })
    top_adgroups = sorted(adgroup_rows, key=lambda x: x["spend"], reverse=True)

    device_totals = defaultdict(lambda: {"spend": 0.0, "impressions": 0, "clicks": 0, "conversions": 0, "conversions_value": 0})
    for row in device_data.get("results", []):
        device = row["segments"]["device"]
        m = row["metrics"]
        device_totals[device]["spend"] += float(m.get("costMicros", 0) or 0) / 1_000_000
        device_totals[device]["impressions"] += int(float(m.get("impressions", 0) or 0))
        device_totals[device]["clicks"] += int(float(m.get("clicks", 0) or 0))
        device_totals[device]["conversions"] += int(float(m.get("conversions", 0) or 0))
        device_totals[device]["conversions_value"] += float(m.get("conversionsValue", 0) or 0)
    device_rows = []
    for device, data in device_totals.items():
        device_rows.append({
            "device": device, "spend": data["spend"], "impressions": data["impressions"],
            "clicks": data["clicks"], "conversions": data["conversions"], "conversions_value": data["conversions_value"],
            "ctr": safe_div(data["clicks"], data["impressions"]),
            "cpa": safe_div(data["spend"], data["conversions"], 0),
            "roas": safe_div(data["conversions_value"], data["spend"], 0),
            "conv_rate": safe_div(data["conversions"], data["clicks"]),
        })
    device_rows = sorted(device_rows, key=lambda x: x["spend"], reverse=True)

    dow_totals = defaultdict(lambda: {"spend": 0.0, "impressions": 0, "clicks": 0, "conversions": 0, "conversions_value": 0})
    for row in dow_data.get("results", []):
        dow = row["segments"]["dayOfWeek"]
        m = row["metrics"]
        dow_totals[dow]["spend"] += float(m.get("costMicros", 0) or 0) / 1_000_000
        dow_totals[dow]["impressions"] += int(float(m.get("impressions", 0) or 0))
        dow_totals[dow]["clicks"] += int(float(m.get("clicks", 0) or 0))
        dow_totals[dow]["conversions"] += int(float(m.get("conversions", 0) or 0))
        dow_totals[dow]["conversions_value"] += float(m.get("conversionsValue", 0) or 0)
    dow_order = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    dow_rows = []
    for dow in dow_order:
        if dow in dow_totals:
            data = dow_totals[dow]
            dow_rows.append({
                "day": dow.title(), "spend": data["spend"], "impressions": data["impressions"],
                "clicks": data["clicks"], "conversions": data["conversions"], "conversions_value": data["conversions_value"],
                "ctr": safe_div(data["clicks"], data["impressions"]),
                "cpa": safe_div(data["spend"], data["conversions"], 0),
                "roas": safe_div(data["conversions_value"], data["spend"], 0),
                "conv_rate": safe_div(data["conversions"], data["clicks"]),
            })

    active_campaigns = [c for c in campaigns if c.get("status") == "ENABLED"]
    inactive_campaigns = [c for c in campaigns if c.get("status") != "ENABLED"]

    # Hourly heatmap data
    hourly_data, _ = parse_mcp("google_ads_hourly.json")
    hourly_data = hourly_data or {}
    hourly_rows = []
    heatmap_totals = {}
    for row in hourly_data.get("results", []):
        dow = row["segments"]["dayOfWeek"].title()
        hour = int(row["segments"]["hour"])
        m = row["metrics"]
        spend = float(m.get("costMicros", 0) or 0) / 1_000_000
        clicks = int(float(m.get("clicks", 0) or 0))
        conversions = int(float(m.get("conversions", 0) or 0))
        conv_value = float(m.get("conversionsValue", 0) or 0)
        hourly_rows.append({
            "day": dow, "hour": hour, "spend": spend,
            "impressions": int(float(m.get("impressions", 0) or 0)),
            "clicks": clicks, "conversions": conversions, "conversions_value": conv_value,
            "ctr": safe_div(clicks, int(float(m.get("impressions", 0) or 0))),
            "cpa": safe_div(spend, conversions, 0),
            "roas": safe_div(conv_value, spend, 0),
            "conv_rate": safe_div(conversions, clicks),
        })
        key = (dow, hour)
        if key not in heatmap_totals:
            heatmap_totals[key] = {"spend": 0, "conversions": 0, "clicks": 0}
        heatmap_totals[key]["spend"] += spend
        heatmap_totals[key]["conversions"] += conversions
        heatmap_totals[key]["clicks"] += clicks

    top_weekdays = sorted(dow_rows, key=lambda x: (x["conversions"] > 0, -x["cpa"], -x["spend"]), reverse=True)

    # Geographic performance
    geo_names = {}
    if geo_target_data:
        for row in geo_target_data.get("results", []):
            gtc = row.get("geoTargetConstant", {})
            gid = str(gtc.get("id", ""))
            if gid:
                geo_names[gid] = gtc.get("name", gid)
    geo_totals = defaultdict(lambda: {"spend": 0.0, "impressions": 0, "clicks": 0, "conversions": 0, "conversions_value": 0.0})
    for row in geo_data.get("results", []):
        gv = row.get("geographicView", {})
        cid = str(gv.get("countryCriterionId", gv.get("country_criterion_id", "")))
        if not cid:
            cid = gv.get("resourceName", "Unknown")
        name = geo_names.get(cid, cid)
        m = row.get("metrics", {})
        spend = float(m.get("costMicros", 0) or 0) / 1_000_000
        impressions = int(float(m.get("impressions", 0) or 0))
        clicks = int(float(m.get("clicks", 0) or 0))
        conversions = int(float(m.get("conversions", 0) or 0))
        conv_value = float(m.get("conversionsValue", 0) or 0)
        geo_totals[name]["spend"] += spend
        geo_totals[name]["impressions"] += impressions
        geo_totals[name]["clicks"] += clicks
        geo_totals[name]["conversions"] += conversions
        geo_totals[name]["conversions_value"] += conv_value
    geo_rows = []
    for name, data in geo_totals.items():
        geo_rows.append({
            "location": name, "spend": data["spend"], "impressions": data["impressions"],
            "clicks": data["clicks"], "conversions": data["conversions"], "conversions_value": data["conversions_value"],
            "ctr": safe_div(data["clicks"], data["impressions"]),
            "cpa": safe_div(data["spend"], data["conversions"], 0),
            "roas": safe_div(data["conversions_value"], data["spend"], 0),
            "conv_rate": safe_div(data["conversions"], data["clicks"]),
        })
    geo_rows = sorted(geo_rows, key=lambda x: x["spend"], reverse=True)[:15]

    return {
        "account": account, "total_campaigns": len(campaigns),
        "active_campaigns": len(active_campaigns), "inactive_campaigns": inactive_campaigns,
        "total_ads": len(ads), "ads": ads, "total_spend": total_spend,
        "total_impressions": total_impressions, "total_clicks": total_clicks,
        "total_conversions": total_conversions, "total_conversion_value": total_conversion_value,
        "top_campaigns": top_campaigns, "best_cpa_campaigns": best_cpa,
        "top_adgroups": top_adgroups, "top_months": top_months,
        "device_rows": device_rows, "dow_rows": dow_rows, "top_weekdays": top_weekdays,
        "hourly_rows": hourly_rows, "heatmap_totals": heatmap_totals,
        "geo_rows": geo_rows,
        "cpa": safe_div(total_spend, total_conversions, 0),
    }


# ===================== HTML RENDERING =====================

def escape_js(s):
    return json.dumps(str(s))



def render_overview_js(platform_labels, platform_spend, platform_conv, platform_cpa):
    labels = json.dumps(platform_labels)
    spend = json.dumps(platform_spend)
    conv = json.dumps(platform_conv)
    cpa = json.dumps(platform_cpa)
    return f"""<script>
const platformLabels = {labels};
const platformSpend = {spend};
const platformConv = {conv};
const platformCpa = {cpa};
const palette = ['#000000', '#1877f2', '#34a853'];
new Chart(document.getElementById('spendByPlatformChart'), {{type:'doughnut', data:{{labels:platformLabels, datasets:[{{data:platformSpend, backgroundColor:palette.slice(0, platformLabels.length), borderWidth:0}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'bottom'}}}}}}}});
new Chart(document.getElementById('convByPlatformChart'), {{type:'bar', data:{{labels:platformLabels, datasets:[{{label:'Conversions', data:platformConv, backgroundColor:palette.slice(0, platformLabels.length), borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('cpaByPlatformChart'), {{type:'bar', data:{{labels:platformLabels, datasets:[{{label:'CPA (SAR)', data:platformCpa, backgroundColor:['#e74c3c','#f39c12','#2ecc71'].slice(0, platformLabels.length), borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true, title:{{display:true, text:'CPA (SAR)'}}}}}}}}}});
new Chart(document.getElementById('spendVsConvChart'), {{type:'bar', data:{{labels:platformLabels, datasets:[{{label:'Spend', data:platformSpend, backgroundColor:palette.slice(0, platformLabels.length), borderRadius:8, yAxisID:'y'}}, {{label:'Conversions', data:platformConv, backgroundColor:palette.slice(0, platformLabels.length).map(c=>c+'80'), borderRadius:8, yAxisID:'y1'}}]}}, options:{{responsive:true, maintainAspectRatio:false, scales:{{y:{{beginAtZero:true, title:{{display:true, text:'Spend (SAR)'}}}}, y1:{{beginAtZero:true, position:'right', title:{{display:true, text:'Conversions'}}}}, x:{{}}}}, plugins:{{legend:{{position:'top'}}}}}}}});
</script>

<script>
document.addEventListener('DOMContentLoaded', () => {{
  const progressFill = document.getElementById('progressFill');
  function updateProgress() {{
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    if (progressFill) progressFill.style.width = pct + '%';
  }}
  window.addEventListener('scroll', updateProgress, {{ passive: true }});
  updateProgress();

  const selectors = [
    ['.card', 'reveal'],
    ['.kpi', 'reveal reveal-scale'],
    ['.platform-card', 'reveal'],
    ['.section-title', 'reveal-left'],
    ['.filters', 'reveal'],
    ['.recommendation', 'reveal'],
    ['.funnel-step', 'reveal'],
    ['.pull-quote', 'reveal'],
    ['.metadata-bar', 'reveal']
  ];
  selectors.forEach(([sel, classes]) => {{
    document.querySelectorAll(sel).forEach((el, j) => {{
      classes.split(' ').forEach(c => el.classList.add(c));
      el.classList.add('delay-' + ((j % 8) + 1));
    }});
  }});

  const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) {{
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }}
    }});
  }}, {{ threshold: 0.08, rootMargin: '0px 0px -50px 0px' }});
  document.querySelectorAll('.reveal, .reveal-scale, .reveal-left').forEach(el => observer.observe(el));

  const counterObserver = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) {{
        const el = entry.target;
        const text = el.textContent;
        const match = text.match(/([^\d\-]*)(-?[\d,]+(?:\.\d+)?)(.*)/);
        if (match) {{
          const prefix = match[1], suffix = match[3];
          const target = parseFloat(match[2].replace(/,/g, ''));
          if (!isNaN(target)) {{
            const duration = 1600;
            const start = performance.now();
            const isInt = Number.isInteger(target);
            function step(now) {{
              const p = Math.min((now - start) / duration, 1);
              const eased = 1 - Math.pow(1 - p, 3);
              const current = target * eased;
              let formatted = isInt
                ? Math.round(current).toLocaleString()
                : current.toLocaleString(undefined, {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
              el.textContent = prefix + formatted + suffix;
              if (p < 1) requestAnimationFrame(step);
            }}
            requestAnimationFrame(step);
          }}
        }}
        counterObserver.unobserve(el);
      }}
    }});
  }}, {{ threshold: 0.5 }});
  document.querySelectorAll('.kpi-value').forEach(el => counterObserver.observe(el));
}});
</script>

<script>
(function() {{
  const DICT = {{
    "Overview": "نظرة عامة", "TikTok": "تيك توك", "Meta": "ميتا", "Google Ads": "إعلانات جوجل",
    "White Car Ads Audit": "تدقيق إعلانات وايت كار",
    "Start Date": "تاريخ البدء", "End Date": "تاريخ الانتهاء", "Campaign Status": "حالة الحملة",
    "Min Spend (SAR)": "الحد الأدنى للإنفاق (ر.س)", "Apply Filters": "تطبيق الفلاتر", "Reset": "إعادة تعيين",
    "All": "الكل", "Active / Enabled": "نشط / مفعّل", "Paused / Disabled": "متوقف / معطل",
    "Active": "نشط", "Paused": "متوقف", "Unknown": "غير معروف",
    "Total Spend": "إجمالي الإنفاق", "Total Conversions": "إجمالي التحويلات", "Blended CPA": "متوسط تكلفة التحويل", "Platforms": "المنصات",
    "Spend": "الإنفاق", "Conversions": "التحويلات", "Impressions": "الظهور", "Clicks": "النقرات",
    "CTR": "معدل النقر", "CPC": "تكلفة النقرة", "CPA": "تكلفة التحويل", "Reach": "الوصول",
    "Conv. Value": "قيمة التحويل", "ROAS": "العائد على الإنفاق", "Campaigns": "الحملات",
    "Lifetime Spend": "إجمالي الإنفاق", "Video VTR": "معدل مشاهدة الفيديو", "Completion": "الاكتمال", "Conv. Rate": "معدل التحويل",
    "Campaign": "الحملة", "Status": "الحالة", "Objective": "الهدف", "Impr.": "الظهور", "Conv.": "التحويل",
    "Spend Share": "حصة الإنفاق", "Conversions by Platform": "التحويلات حسب المنصة", "Conversions by Campaign": "التحويلات حسب الحملة",
    "CPA by Platform": "تكلفة التحويل حسب المنصة", "Spend vs Conversions": "الإنفاق مقابل التحويلات",
    "Spend by Campaign": "الإنفاق حسب الحملة", "Monthly Trend": "الاتجاه الشهري", "Device Breakdown": "التفصيل حسب الجهاز",
    "Day-of-Week CPA Heatmap": "خريطة حرارية لتكلفة التحويل حسب اليوم", "Age & Gender": "العمر والجنس", "Region": "المنطقة",
    "Hourly Performance": "الأداء حسب الساعة", "Top Campaigns": "أهم الحملات", "Top Spend Campaigns by Platform": "أعلى الحملات إنفاقًا حسب المنصة",
    "Campaign Classification": "تصنيف الحملات", "Scale Winners": "الرابحون القابلون للتوسع", "Expensive Volume": "حجم مكلف", "Poor Signal": "إشارة ضعيفة",
    "Platform Mix & Efficiency": "مزيج المنصات والكفاءة", "Platform Mix & Dependency Risk": "مزيج المنصات ومخاطر الاعتماد",
    "Lead Quality & CRM Funnel": "جودة العملاء المحتملين وقمع CRM", "Data Quality Issues": "مشكلات جودة البيانات",
    "Strategic Recommendations": "التوصيات الاستراتيجية", "14-Day Action Roadmap": "خطة العمل لمدة 14 يومًا",
    "Tracking & Measurement Gaps": "فجوات التتبع والقياس", "Executive Summary": "الملخص التنفيذي",
    "TikTok Ads Deep Dive": "تحليل عميق لإعلانات تيك توك", "Meta Ads Deep Dive": "تحليل عميق لإعلانات ميتا", "Google Ads Deep Dive": "تحليل عميق لإعلانات جوجل",
    "Performance Deep Dive": "تحليل الأداء العميق", "Creative Performance": "أداء الإبداع", "Timing & Efficiency": "التوقيت والكفاءة", "Audience Performance": "أداء الجمهور",
    "Anomalies & Red Flags": "الحالات الشاذة والعلامات الحمراء",
    "No campaign data available.": "لا توجد بيانات حملات متاحة.", "No data available.": "لا توجد بيانات متاحة.",
    "Reporting period": "فترة الإبلاغ", "Data source": "مصدر البيانات", "Attribution": "النسبة", "Conversion definition": "تعريف التحويل",
    "Platform default attribution windows": "نوافذ النسبة الافتراضية للمنصة",
    "TikTok: Lead Generation form submits · Meta: Lead / messaging / form actions · Google: Form/call conversions": "تيك توك: إرسالات نموذج جلب العملاء · ميتا: عملاء / رسائل / إجراءات النموذج · جوجل: تحويلات النموذج/المكالمات",
    "Key insight from the audit": "رؤية رئيسية من التدقيق",
    "Advertiser:": "المعلن:", "Account:": "الحساب:", "Objective:": "الهدف:",
    "Lead Generation": "جلب العملاء المحتملين", "Lead Generation / Conversations": "جلب العملاء / المحادثات",
    "High-intent search & Performance Max": "بحث عالي النية و Performance Max",
    "Google": "جوجل", "TikTok": "تيك توك", "Meta": "ميتا",
    "Scale / volume driver": "محرك النطاق والحجم", "Audience test / retarget": "اختبار الجمهور / إعادة الاستهداف", "High-intent capture": "التقاط النية العالية",
    "View TikTok deep dive →": "عرض تحليل تيك توك العميق →", "View Meta deep dive →": "عرض تحليل ميتا العميق →", "View Google deep dive →": "عرض تحليل جوجل العميق →",
    "Generated on": "تم الإنشاء في"
  }};
  const REVERSE = Object.fromEntries(Object.entries(DICT).map(([k, v]) => [v, k]));

  function translateTree(lang) {{
    const map = lang === 'ar' ? DICT : REVERSE;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    const nodes = [];
    let node;
    while ((node = walker.nextNode())) {{
      if (!node.parentElement) continue;
      if (node.parentElement.hasAttribute('data-en') || node.parentElement.closest('[data-en]')) continue;
      const tag = node.parentElement.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE') continue;
      nodes.push(node);
    }}
    nodes.forEach(node => {{
      let text = node.textContent;
      Object.keys(map).forEach(key => {{
        text = text.split(key).join(map[key]);
      }});
      node.textContent = text;
    }});
  }}

  const langToggle = document.getElementById('langToggle');
  function setLang(lang) {{
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    localStorage.setItem('wc-lang', lang);
    document.querySelectorAll('[data-en][data-ar]').forEach(el => {{
      el.textContent = lang === 'ar' ? el.dataset.ar : el.dataset.en;
    }});
    translateTree(lang);
    if (langToggle) langToggle.textContent = lang === 'ar' ? langToggle.dataset.ar : langToggle.dataset.en;
  }}
  if (langToggle) {{
    langToggle.addEventListener('click', () => {{
      const newLang = document.documentElement.lang === 'ar' ? 'en' : 'ar';
      setLang(newLang);
    }});
  }}
  const savedLang = localStorage.getItem('wc-lang') || 'en';
  if (savedLang === 'ar') setLang('ar');
}})();
</script>
</body></html>"""



def report_metadata():
    return """
<div class="card metadata-bar">
  <div class="metadata-grid">
    <div><span>Reporting period</span><strong>TikTok: 18 Jun 2025 – 18 Jun 2026 · Meta: 28 Jan – 18 Jun 2026 · Google: full period</strong></div>
    <div><span>Data source</span><strong>TikTok Ads MCP, Meta Ads MCP, Google Ads MCP via Pipeboard</strong></div>
    <div><span>Attribution</span><strong>Platform default attribution windows</strong></div>
    <div><span>Conversion definition</span><strong>TikTok: Lead Generation form submits · Meta: Lead / messaging / form actions · Google: Form/call conversions</strong></div>
  </div>
</div>
"""


def platform_comparison_table(tiktok, meta, google):
    rows = [
        ["TikTok", fmt_sar(tiktok['total_spend']), f"{tiktok['spend_share']:.1f}%", fmt_num(tiktok['total_conversions']), f"{tiktok['conv_share']:.1f}%", fmt_sar(tiktok['cpa']), "Scale / volume driver"],
    ]
    if meta:
        rows.append(["Meta", fmt_sar(meta['total_spend']), f"{meta['spend_share']:.1f}%", fmt_num(meta['total_conversions']), f"{meta['conv_share']:.1f}%", fmt_sar(meta['cpa']), "Audience test / retarget"])
    if google:
        rows.append(["Google", fmt_sar(google['total_spend']), f"{google['spend_share']:.1f}%", fmt_num(google['total_conversions']), f"{google['conv_share']:.1f}%", fmt_sar(google['cpa']), "High-intent capture"])
    return render_simple_table(
        'Platform Mix & Dependency Risk',
        ['Platform', 'Spend', 'Spend Share', 'Conversions', 'Conv. Share', 'CPA', 'Strategic Role'],
        rows
    )


def executive_summary(tiktok, meta, google):
    total_spend = tiktok["total_spend"] + (meta["total_spend"] if meta else 0) + (google["total_spend"] if google else 0)
    total_conv = tiktok["total_conversions"] + (meta["total_conversions"] if meta else 0) + (google["total_conversions"] if google else 0)
    blended_cpa = safe_div(total_spend, total_conv, 0)
    tiktok_share = tiktok["total_spend"] / total_spend * 100 if total_spend else 0
    tiktok_conv_share = tiktok["total_conversions"] / total_conv * 100 if total_conv else 0

    if tiktok_share > 80:
        risk = "heavy platform dependency"
        risk_detail = "TikTok is carrying most of the spend and conversions. This drives scale but creates concentration risk."
        risk_detail_ar = "تيك توك تتحمل معظم الإنفاق والتحويلات. هذا يحقق النطاق ولكنه يخلق مخاطر تركيز."
    elif tiktok_share > 50:
        risk = "TikTok-led mix"
        risk_detail = "TikTok dominates volume; Meta and Google are underfunded relative to their CPA potential."
        risk_detail_ar = "تيك توك تهيمن على الحجم؛ ميتا وجوجل غير ممولتين بما يتناسب مع إمكانات تكلفة التحويل."
    else:
        risk = "balanced mix"
        risk_detail = "Spend is distributed across platforms, though volumes differ significantly."
        risk_detail_ar = "الإنفاق موزع عبر المنصات، على الرغم من اختلاف الحجوم بشكل كبير."
    platform_name_ar = {"Google": "جوجل", "Meta": "ميتا", "TikTok": "تيك توك"}

    best_cpa_platform = "Google"
    best_cpa_value = google["cpa"] if google else 999999
    if meta and meta["cpa"] < best_cpa_value and meta["cpa"] > 0:
        best_cpa_platform = "Meta"
        best_cpa_value = meta["cpa"]
    if tiktok["cpa"] < best_cpa_value and tiktok["cpa"] > 0:
        best_cpa_platform = "TikTok"
        best_cpa_value = tiktok["cpa"]

    return f"""
<div class="card exec-summary">
  <h2 data-en="Executive Summary" data-ar="الملخص التنفيذي">Executive Summary</h2>
  <p class="lead" data-en="White Car generated {fmt_num(total_conv)} total platform conversions at a blended CPA of {fmt_sar(blended_cpa)}, with TikTok driving the majority of scale. TikTok represents around {tiktok_share:.0f}% of spend and {tiktok_conv_share:.0f}% of conversions. {risk_detail}" data-ar="حققت وايت كار {fmt_num(total_conv)} تحويلة عبر المنصات بتكلفة تحويل متوسطة {fmt_sar(blended_cpa)}، مع قيادة تيك توك لمعظم النطاق. تمثل تيك توك حوالي {tiktok_share:.0f}% من الإنفاق و {tiktok_conv_share:.0f}% من التحويلات. {risk_detail_ar}">
    White Car generated <strong>{fmt_num(total_conv)} total platform conversions</strong> at a blended CPA of <strong>{fmt_sar(blended_cpa)}</strong>,
    with TikTok driving the majority of scale. TikTok represents around <strong>{tiktok_share:.0f}% of spend</strong> and
    <strong>{tiktok_conv_share:.0f}% of conversions</strong>. {risk_detail}
  </p>
  <p data-en="The most efficient platform by reported CPA is {best_cpa_platform} ({fmt_sar(best_cpa_value)}), but its spend volume is much smaller, so performance should be validated by lead quality before major budget shifts. The next priority is to validate lead quality, connect ad conversions to CRM outcomes, and restructure campaign naming, tracking, and budget allocation." data-ar="المنصة الأكثر كفاءة من حيث تكلفة التحويل المبلغ عنها هي {platform_name_ar.get(best_cpa_platform, best_cpa_platform)} ({fmt_sar(best_cpa_value)})، ولكن حجم إنفاقها أصغر بكثير، لذا يجب التحقق من جودة العملاء المحتملين قبل إعادة توزيع الميزانية. الأولوية التالية هي التحقق من جودة العملاء المحتملين، وربط تحويلات الإعلانات بنتائج CRM، وإعادة هيكلة تسمية الحملات والتتبع وتوزيع الميزانية.">
    The most efficient platform by reported CPA is <strong>{best_cpa_platform} ({fmt_sar(best_cpa_value)})</strong>,
    but its spend volume is much smaller, so performance should be validated by lead quality before major budget shifts.
    The next priority is to validate lead quality, connect ad conversions to CRM outcomes, and restructure campaign naming, tracking, and budget allocation.
  </p>
</div>
<blockquote class="pull-quote reveal" data-en="TikTok is the engine of White Car's paid acquisition — but over-dependence on one channel is the single biggest strategic risk hiding in plain sight." data-ar="تيك توك هي محرك اكتساب وايت كار المدفوع — ولكن الاعتماد المفرط على قناة واحدة هو أكبر مخاطر استراتيجية تختبئ في واضح الأمر.">
  TikTok is the engine of White Car's paid acquisition — but over-dependence on one channel is the single biggest strategic risk hiding in plain sight.
  <cite data-en="Key insight from the audit" data-ar="رؤية رئيسية من التدقيق">Key insight from the audit</cite>
</blockquote>
"""


def data_quality_issues(tiktok, meta, google):
    issues = []
    # Check for unknown names in TikTok top campaigns
    unknown_camps = [c for c in tiktok.get('top_campaigns', []) if c.get('name') in ('UNKNOWN', '', None) or 'unknown' in str(c.get('name', '')).lower()]
    if unknown_camps:
        issues.append(["TikTok campaigns showing UNKNOWN or missing names", "Cannot understand strategy, audience, or offer", "Verify campaign name mapping from TikTok campaigns API"])
    # Meta status inconsistency
    if meta and meta.get('active_campaigns') == 0 and meta.get('total_adsets', 0) > 0:
        issues.append(["Meta summary shows 0 active campaigns while active ad sets exist", "Inconsistent status logic creates confusion", "Separate campaign-level status from ad set-level status in reporting"])
    # Google heatmap empty
    if google and not google.get('heatmap_totals'):
        issues.append(["Google hourly heatmap unavailable", "Cannot identify best time/day performance", "Fetch segments by day_of_week and hour from Google Ads"])
    # High CPA campaigns
    high_cpa = [c for c in tiktok.get('top_campaigns', []) if c.get('conversions', 0) > 0 and c.get('cpconv', 0) > 10]
    if high_cpa:
        issues.append([f"{len(high_cpa)} TikTok campaigns above SAR 10 CPA", "Wasted spend if lead quality is not superior", "Review and reduce budget or restructure"])
    # Google ROAS context
    if google and google.get('total_conversion_value', 0) > 0 and google.get('total_spend', 0) > 0:
        issues.append(["Google ROAS shown without clear revenue source validation", "ROAS may be misleading without CRM confirmation", "Add conversion value source and revenue validation"])

    if not issues:
        issues.append(["No major data quality flags detected", "", "Continue monitoring"])
    return render_simple_table('Data Quality Issues & Fixes', ['Issue', 'Impact', 'Fix'], issues)


def lead_quality_funnel():
    return """
<div class="card">
  <h2>Platform CPA vs Real CPA</h2>
  <p class="muted">
    Platform CPA is based on ad-reported conversions. For a car business, the real metric should be
    <strong>cost per qualified lead</strong> and <strong>cost per sale</strong>. Below is the recommended lead lifecycle to track.
  </p>
  <div class="funnel">
    <div class="funnel-step"><strong>New Lead</strong><span>Form / call / WhatsApp</span></div>
    <div class="funnel-step"><strong>Valid Lead</strong><span>Real contact, correct city</span></div>
    <div class="funnel-step"><strong>Qualified Lead</strong><span>Has need, has car/budget</span></div>
    <div class="funnel-step"><strong>Sales Accepted</strong><span>Contacted & accepted</span></div>
    <div class="funnel-step"><strong>Appointment</strong><span>Showroom / test drive</span></div>
    <div class="funnel-step"><strong>Closed Deal</strong><span>Revenue</span></div>
  </div>
  <p class="muted" style="margin-top:1rem">
    Example: TikTok may show SAR 7.35 CPA, but if only 10% of leads are qualified, the real qualified-lead cost is ~SAR 73.50.
    Google may show SAR 4.38 CPA, but if intent is stronger, it may be far more valuable despite lower spend.
  </p>
</div>
"""


def campaign_classification(campaign_rows, platform_name):
    if not campaign_rows:
        return '<div class="no-data">No campaign data available.</div>'

    winners = []
    testers = []
    expensive = []
    poor = []

    # Use account average CPA as benchmark
    total_spend = sum(c.get('spend', 0) for c in campaign_rows)
    total_conv = sum(c.get('conversions', 0) for c in campaign_rows)
    avg_cpa = safe_div(total_spend, total_conv, 0)

    for c in campaign_rows:
        spend = c.get('spend', 0)
        conv = c.get('conversions', 0)
        cpa = c.get('cpconv', 0) if 'cpconv' in c else c.get('cpa', 0)
        if conv > 0:
            if cpa <= avg_cpa * 0.8 and spend >= avg_cpa * 5:
                winners.append([c.get('name', c.get('campaign_id', '')), fmt_sar(spend), fmt_num(conv), fmt_sar(cpa), "Scale"])
            elif cpa <= avg_cpa * 0.9 and spend < avg_cpa * 5:
                testers.append([c.get('name', c.get('campaign_id', '')), fmt_sar(spend), fmt_num(conv), fmt_sar(cpa), "Test more budget"])
            elif cpa >= avg_cpa * 1.3 and spend >= avg_cpa * 5:
                expensive.append([c.get('name', c.get('campaign_id', '')), fmt_sar(spend), fmt_num(conv), fmt_sar(cpa), "Reduce / Restructure"])
            elif cpa >= avg_cpa * 1.2:
                poor.append([c.get('name', c.get('campaign_id', '')), fmt_sar(spend), fmt_num(conv), fmt_sar(cpa), "Watch / Pause"])
        else:
            if spend > avg_cpa * 2:
                poor.append([c.get('name', c.get('campaign_id', '')), fmt_sar(spend), fmt_num(conv), "—", "Pause / Relaunch"])

    html = f'<div class="card"><h2>{platform_name} Campaign Classification</h2>'
    def render_sub_table(rows):
        if not rows:
            return ''
        ths = "".join(f"<th>{h}</th>" for h in ['Campaign', 'Spend', 'Conv.', 'CPA', 'Action'])
        body = ""
        for row in rows:
            body += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        return f'<div style="overflow-x:auto"><table class="data-table"><thead><tr>{ths}</tr></thead><tbody>{body}</tbody></table></div>'
    if winners:
        html += '<h3 class="sub-heading">🏆 Scale Winners</h3>' + render_sub_table(winners)
    if testers:
        html += '<h3 class="sub-heading">🧪 Efficient Testers</h3>' + render_sub_table(testers)
    if expensive:
        html += '<h3 class="sub-heading">⚠️ Expensive Volume</h3>' + render_sub_table(expensive)
    if poor:
        html += '<h3 class="sub-heading">🛑 Poor Signal</h3>' + render_sub_table(poor)
    if not any([winners, testers, expensive, poor]):
        html += '<div class="no-data">Not enough conversion data to classify campaigns.</div>'
    html += '</div>'
    return html


def budget_reallocation_plan(tiktok, meta, google):
    rows = [
        ["TikTok", "Main volume driver", "Heavy dependency, mixed campaign quality", "Keep scale but reduce waste from high CPA campaigns"],
    ]
    if meta:
        rows.append(["Meta", "Efficient but paused/underused", "Low spend and unclear campaign status", "Relaunch best lead campaigns with cleaner structure"])
    if google:
        rows.append(["Google", "High-intent capture", "Very low spend, limited data", "Increase gradually after search-term & lead-quality review"])
    return render_simple_table('Suggested Budget Direction', ['Platform', 'Current Role', 'Issue', 'Next Action'], rows)


def action_plan_14_days():
    return render_simple_table(
        '14-Day Optimization Roadmap',
        ['Timeline', 'Action', 'Owner'],
        [
            ["Day 1–2", "Fix campaign naming and data mapping; confirm active vs paused status", "Media Team"],
            ["Day 3–4", "Validate lead quality from CRM/sales; map platform leads to lifecycle stages", "Sales + Analytics"],
            ["Day 5–7", "Pause or reduce budget for campaigns above blended CPA without quality proof", "Media Team"],
            ["Week 2", "Relaunch Meta winners and increase Google high-intent budget in controlled test", "Media Team"],
            ["Week 2", "Add creative testing plan by hook, car model, offer, and audience", "Creative Team"],
            ["Day 14", "Review qualified CPA, not just platform CPA; report cost per qualified lead", "Analytics"],
        ]
    )


def tracking_gaps():
    return render_simple_table(
        'Tracking & Measurement Gaps',
        ['Gap', 'Why It Matters', 'Fix'],
        [
            ["Platform conversions are not enough", "Cannot know real lead quality", "Connect leads to CRM/sales sheet"],
            ["No visible UTM framework", "Cannot compare campaigns in GA4/CRM", "Standardize UTMs across all ads"],
            ["No lead status tracking", "Cannot calculate qualified CPA", "Add lifecycle stages"],
            ["No sales outcome tracking", "Cannot know real ROI", "Track booked / visited / sold"],
            ["No deduplication logic", "Same lead may be counted multiple times", "Deduplicate by phone number / email"],
        ]
    )


def anomalies_red_flags(tiktok, meta, google):
    flags = []
    total_spend = tiktok["total_spend"] + (meta["total_spend"] if meta else 0) + (google["total_spend"] if google else 0)
    tiktok_share = tiktok["total_spend"] / total_spend * 100 if total_spend else 0
    if tiktok_share > 80:
        flags.append(["Platform concentration risk", f"TikTok accounts for {tiktok_share:.0f}% of spend; one policy or performance issue could sharply cut lead volume."])
    # campaigns with CPA 0 and no conversions but spend
    zero_conv_spend = [c for c in tiktok.get('top_campaigns', []) if c.get('conversions', 0) == 0 and c.get('spend', 0) > 0]
    if zero_conv_spend:
        total_waste = sum(c.get('spend', 0) for c in zero_conv_spend)
        flags.append(["Spend with zero conversions", f"{len(zero_conv_spend)} TikTok campaign(s) spent {fmt_sar(total_waste)} without conversions."])
    # very low CPA campaigns - possible data quality issue
    low_cpa = [c for c in tiktok.get('top_campaigns', []) if c.get('conversions', 0) > 0 and c.get('cpconv', 0) < 1]
    if low_cpa:
        flags.append(["Suspiciously low CPA", f"{len(low_cpa)} TikTok campaign(s) report CPA below SAR 1. Validate conversion definition and deduplication."])
    if meta and meta.get('active_campaigns', 0) == 0 and meta.get('total_adsets', 0) > 0:
        flags.append(["Meta status inconsistency", "0 active campaigns but active ad sets exist. Review campaign vs ad set status."])
    if google and google.get('total_conversion_value', 0) > 0:
        roas = safe_div(google['total_conversion_value'], google['total_spend'], 0)
        if roas < 1:
            flags.append(["Google ROAS below 1x", f"Reported ROAS is {roas:.2f}x. Confirm conversion value accuracy and lead quality before scaling."])
    if not flags:
        flags.append(["No major red flags", "Continue monitoring performance and lead quality."])
    return render_simple_table('Anomalies & Red Flags', ['Flag', 'Detail'], flags)


def strategic_recommendations(tiktok, meta, google):
    recs = [
        ("1. Do not judge performance by CPA alone", "لا تحكم على الأداء بناءً على تكلفة التحويل وحدها", "TikTok drives the majority of leads, but the business must validate which platform produces qualified leads and sales opportunities.", "تيك توك يقود غالبية العملاء المحتملين، ولكن يجب على العمل التحقق من أي منصة تنتج عملاء مؤهلين وفرص مبيعات."),
        ("2. Reduce TikTok waste before scaling", "قلل الهدر في تيك توك قبل التوسع", "Campaigns above the blended CPA should be reviewed, especially high-spend campaigns with CPA above SAR 9–13.", "يجب مراجعة الحملات التي تتجاوز متوسط تكلفة التحويل، وخاصة الحملات ذات الإنفاق العالي بتكلفة تحويل تزيد عن 9–13 ر.س."),
        ("3. Relaunch Meta with a cleaner structure", "أعد إطلاق ميتا بهيكل أنظف", "Meta shows strong CPA potential, but the current setup appears paused or inconsistent. Relaunch with separated audiences, clear naming, and creative testing.", "تظهر ميتا إمكانية قوية لتكلفة التحويل، ولكن الإعداد الحالي يبدو متوقفًا أو غير متسق. أعد الإطلاق مع جماعات منفصلة وتسميات واضحة واختبار إبداعي."),
        ("4. Give Google a controlled scale test", "امنح جوجل اختبار توسع متحكم فيه", "Google has the lowest CPA, but spend is very small. Increase gradually only after reviewing search terms and lead quality.", "تمتلك جوجل أقل تكلفة تحويل، ولكن الإنفاق صغير جدًا. زد تدريجيًا فقط بعد مراجعة مصطلحات البحث وجودة العملاء المحتملين."),
        ("5. Add CRM outcome tracking", "أضف تتبع نتائج CRM", "The report should show not only leads, but qualified leads, sales calls, appointments, visits, and closed deals.", "يجب أن يظهر التقرير ليس فقط العملاء المحتملين، بل العملاء المؤهلين ومكالمات المبيعات والمواعيد والزيارات والصفقات المغلقة."),
        ("6. Build a creative testing system", "ابنِ نظام اختبار إبداعي", "TikTok and Meta need weekly creative testing by hook, car model, offer, and audience segment.", "يحتاج تيك توك وميتا إلى اختبار إبداعي أسبوعي حسب النقطة الجذابة وموديل السيارة والعرض والجمهور."),
    ]
    html = '<div class="card"><h2 data-en="Strategic Recommendations" data-ar="التوصيات الاستراتيجية">Strategic Recommendations</h2>'
    for title, title_ar, body, body_ar in recs:
        html += f'<div class="recommendation"><h4 data-en="{title}" data-ar="{title_ar}">{title}</h4><p data-en="{body}" data-ar="{body_ar}">{body}</p></div>'
    html += '</div>'
    return html


def render_nav(active_tab, logo_b64):
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="White Car" class="nav-logo">' if logo_b64 else ""
    tabs = [
        ("index.html", "Overview", "overview", "نظرة عامة"),
        ("tiktok.html", "TikTok", "tiktok", "تيك توك"),
        ("meta.html", "Meta", "meta", "ميتا"),
        ("google.html", "Google Ads", "google", "إعلانات جوجل"),
    ]
    links = []
    for href, label, tab, label_ar in tabs:
        cls = "active" if tab == active_tab else ""
        links.append(f'<a href="{href}" class="{cls}" data-en="{label}" data-ar="{label_ar}">{label}</a>')
    return f"""
<nav class="navbar">
  <div class="nav-brand">
    {logo_html}
    <span class="nav-title" data-en="White Car Ads Audit" data-ar="تدقيق إعلانات وايت كار">White Car Ads Audit</span>
  </div>
  <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
    <div class="nav-tabs">
      {"".join(links)}
    </div>
    <button class="lang-toggle" id="langToggle" data-en="العربية" data-ar="English">العربية</button>
  </div>
</nav>
"""


def common_head(title, active_tab):
    css = """
    :root {
      --bg: #fbfaf8;
      --surface: #ffffff;
      --surface-warm: #fffefb;
      --ink: #0f172a;
      --ink-light: #334155;
      --muted: #64748b;
      --border: #e7e5e4;
      --accent: #0d9488;
      --accent-dark: #0f766e;
      --accent-light: #5eead4;
      --warm: #d97706;
      --danger: #dc2626;
      --success: #16a34a;
      --platform-tiktok: #000000;
      --platform-meta: #1877f2;
      --platform-google: #34a853;
      --radius: 22px;
      --radius-sm: 14px;
      --shadow: 0 1px 3px rgba(15,23,42,0.04), 0 12px 32px rgba(15,23,42,0.06);
      --shadow-hover: 0 6px 16px rgba(15,23,42,0.08), 0 28px 56px rgba(15,23,42,0.12);
      --font-display: "DM Serif Display", Georgia, serif;
      --font-body: "Plus Jakarta Sans", system-ui, sans-serif;
      --transition: cubic-bezier(0.22, 1, 0.36, 1);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    html[dir="rtl"] body { direction: rtl; text-align: right; }
    body {
      margin: 0;
      font-family: var(--font-body);
      background: var(--bg);
      color: var(--ink);
      line-height: 1.65;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      background:
        radial-gradient(circle at 15% 0%, rgba(13,148,136,0.05), transparent 35%),
        radial-gradient(circle at 85% 100%, rgba(217,119,6,0.04), transparent 35%),
        url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
      opacity: 0.45;
      pointer-events: none;
      z-index: -1;
    }
    .progress-bar {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 4px;
      background: rgba(15,23,42,0.08);
      z-index: 200;
    }
    .progress-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--accent), var(--accent-light));
      transition: width 0.1s linear;
    }
    .reveal {
      opacity: 0;
      transform: translateY(40px);
      transition: opacity 0.85s var(--transition), transform 0.85s var(--transition);
    }
    .reveal.visible {
      opacity: 1;
      transform: translateY(0);
    }
    .reveal-scale {
      opacity: 0;
      transform: scale(0.92);
      transition: opacity 0.85s var(--transition), transform 0.85s var(--transition);
    }
    .reveal-scale.visible {
      opacity: 1;
      transform: scale(1);
    }
    .reveal-left {
      opacity: 0;
      transform: translateX(-40px);
      transition: opacity 0.85s var(--transition), transform 0.85s var(--transition);
    }
    .reveal-left.visible {
      opacity: 1;
      transform: translateX(0);
    }
    .reveal.delay-1 { transition-delay: 80ms; }
    .reveal.delay-2 { transition-delay: 160ms; }
    .reveal.delay-3 { transition-delay: 240ms; }
    .reveal.delay-4 { transition-delay: 320ms; }
    .reveal.delay-5 { transition-delay: 400ms; }
    .reveal.delay-6 { transition-delay: 480ms; }
    .reveal.delay-7 { transition-delay: 560ms; }
    .reveal.delay-8 { transition-delay: 640ms; }
    .navbar {
      position: sticky;
      top: 0;
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.85rem 2rem;
      background: rgba(15,23,42,0.98);
      backdrop-filter: blur(16px);
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
      flex-wrap: wrap;
      gap: 0.75rem;
    }
    .nav-brand {
      display: flex;
      align-items: center;
      gap: 0.8rem;
      color: #fff;
      font-weight: 800;
      font-size: 1.15rem;
      letter-spacing: -0.01em;
    }
    .nav-logo {
      height: 40px;
      width: auto;
      object-fit: contain;
      filter: drop-shadow(0 1px 2px rgba(0,0,0,0.25));
    }
    .nav-title { font-weight: 800; }
    .nav-tabs {
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
      background: rgba(255,255,255,0.08);
      padding: 0.35rem;
      border-radius: 999px;
    }
    .nav-tabs a {
      color: rgba(255,255,255,0.7);
      text-decoration: none;
      padding: 0.5rem 1rem;
      border-radius: 999px;
      font-weight: 700;
      font-size: 0.85rem;
      transition: all 0.25s var(--transition);
    }
    .nav-tabs a:hover, .nav-tabs a.active {
      color: var(--ink);
      background: var(--accent-light);
      box-shadow: 0 2px 8px rgba(94,234,212,0.25);
    }
    .lang-toggle {
      background: transparent;
      border: 1px solid rgba(255,255,255,0.25);
      color: #fff;
      padding: 0.45rem 0.9rem;
      border-radius: 999px;
      font-weight: 700;
      font-size: 0.78rem;
      cursor: pointer;
      transition: all 0.2s;
      font-family: var(--font-body);
    }
    .lang-toggle:hover { background: rgba(255,255,255,0.12); border-color: rgba(255,255,255,0.5); }
    .hero {
      position: relative;
      min-height: 42vh;
      max-height: 520px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 5rem 2rem 4.5rem;
      background: var(--ink);
      color: #fff;
      overflow: hidden;
    }
    .hero::before {
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at 25% 30%, rgba(13,148,136,0.25), transparent 40%),
        radial-gradient(circle at 75% 70%, rgba(217,119,6,0.18), transparent 45%),
        linear-gradient(135deg, rgba(15,23,42,1) 0%, rgba(30,41,59,1) 100%);
      pointer-events: none;
    }
    .hero::after {
      content: "";
      position: absolute;
      inset: 0;
      background: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
      opacity: 0.12;
      pointer-events: none;
    }
    .hero h1 {
      position: relative;
      margin: 0 0 1rem;
      font-family: var(--font-display);
      font-size: clamp(2.2rem, 5vw, 4.2rem);
      font-weight: 400;
      letter-spacing: -0.03em;
      line-height: 1.05;
      animation: fadeInUp 1s var(--transition) forwards;
    }
    .hero p {
      position: relative;
      margin: 0 auto;
      max-width: 680px;
      color: rgba(255,255,255,0.72);
      font-size: 1.2rem;
      font-weight: 500;
      animation: fadeInUp 1s var(--transition) 0.15s forwards;
      opacity: 0;
    }
    html[dir="rtl"] .navbar,
    html[dir="rtl"] .nav-brand,
    html[dir="rtl"] .nav-tabs { direction: rtl; }
    html[dir="rtl"] .section-title { padding-left: 0; padding-right: 4rem; }
    html[dir="rtl"] .section-title::before { left: auto; right: 0; }
    html[dir="rtl"] .section-title::after { left: auto; right: 2.6rem; }
    html[dir="rtl"] .pull-quote { padding-left: 0; padding-right: 1.5rem; border-left: none; border-right: 5px solid var(--accent); }
    html[dir="rtl"] .recommendation { border-left: none; border-right: 5px solid var(--accent); }
    html[dir="rtl"] .exec-summary { border-left: none; border-right: 5px solid var(--accent); }
    html[dir="rtl"] table th,
    html[dir="rtl"] table td { text-align: right; }
    html[dir="rtl"] .platform-card .metric-row { direction: rtl; }
    .hero h1 .platform-icon {
      width: 64px;
      height: 64px;
      vertical-align: middle;
      margin-right: 0.35rem;
      filter: drop-shadow(0 2px 8px rgba(0,0,0,0.3));
    }
    .scroll-hint {
      position: absolute;
      bottom: 1.5rem;
      left: 50%;
      transform: translateX(-50%);
      color: rgba(255,255,255,0.55);
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      animation: bounce 2.2s infinite;
      pointer-events: none;
    }
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(30px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes bounce {
      0%, 20%, 50%, 80%, 100% { transform: translateX(-50%) translateY(0); }
      40% { transform: translateX(-50%) translateY(10px); }
      60% { transform: translateX(-50%) translateY(5px); }
    }
    .container {
      max-width: 1280px;
      margin: 0 auto;
      padding: 2.5rem 1.5rem 4rem;
      counter-reset: chapter;
    }
    .filters {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: flex-end;
      background: var(--surface);
      padding: 1.25rem;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
      margin-bottom: 1.5rem;
    }
    .filters label {
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      font-size: 0.78rem;
      font-weight: 800;
      color: var(--ink-light);
      flex: 1 1 160px;
      min-width: 140px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .filters input, .filters select {
      padding: 0.65rem 0.85rem;
      border: 1px solid var(--border);
      border-radius: 12px;
      font: inherit;
      background: var(--surface-warm);
      color: var(--ink);
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .filters input:focus, .filters select:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(13,148,136,0.12);
    }
    .filters button {
      padding: 0.7rem 1.4rem;
      border: none;
      border-radius: 12px;
      background: var(--ink);
      color: #fff;
      font-weight: 800;
      cursor: pointer;
      transition: transform 0.2s, background 0.2s, box-shadow 0.2s;
    }
    .filters button:hover { background: var(--accent-dark); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(13,148,136,0.25); }
    .kpis {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .kpi {
      background: var(--surface);
      border-radius: var(--radius-sm);
      padding: 1.35rem;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
      position: relative;
      overflow: hidden;
      transition: transform 0.35s var(--transition), box-shadow 0.35s var(--transition);
    }
    .kpi::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 4px;
      background: linear-gradient(90deg, var(--accent), var(--accent-light));
      transform: scaleX(0);
      transform-origin: left;
      transition: transform 0.5s var(--transition);
    }
    .kpi:hover { transform: translateY(-5px); box-shadow: var(--shadow-hover); }
    .kpi:hover::before { transform: scaleX(1); }
    .kpi-label {
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      font-weight: 800;
      margin-bottom: 0.45rem;
    }
    .kpi-value {
      font-size: 1.75rem;
      font-weight: 800;
      color: var(--ink);
      letter-spacing: -0.03em;
      line-height: 1.1;
    }
    .kpi.sub .kpi-value { font-size: 1.35rem; color: var(--ink-light); }
    .card {
      background: var(--surface);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 1.5rem;
      border: 1px solid var(--border);
      margin-bottom: 1.25rem;
      transition: transform 0.4s var(--transition), box-shadow 0.4s var(--transition);
    }
    .card:hover { transform: translateY(-5px); box-shadow: var(--shadow-hover); }
    .card h2 {
      margin: 0 0 1.1rem;
      font-size: 1.25rem;
      color: var(--ink);
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-weight: 800;
    }
    .card h2 .platform-icon { width: 26px; height: 26px; }
    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 1.25rem;
    }
    .grid-3 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.25rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }
    th, td {
      padding: 0.75rem 0.7rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    th {
      background: var(--bg);
      color: var(--ink-light);
      font-size: 0.68rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    tr { transition: background 0.2s, transform 0.2s; }
    tbody tr:hover { background: rgba(13,148,136,0.04); }
    .data-table th, .data-table td { white-space: nowrap; }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.25rem 0.65rem;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 800;
    }
    .status::before {
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
    }
    .status.active { background: rgba(22,163,74,0.1); color: #15803d; }
    .status.paused { background: rgba(220,38,38,0.1); color: #b91c1c; }
    .status.unknown { background: rgba(100,116,139,0.1); color: var(--muted); }
    .pill {
      display: inline-block;
      padding: 0.15rem 0.45rem;
      border-radius: 6px;
      background: var(--bg);
      color: var(--muted);
      font-size: 0.7rem;
      font-weight: 700;
    }
    .chart-wrap {
      position: relative;
      height: 360px;
      width: 100%;
    }
    .chart-wrap.small { height: 260px; }
    .no-data {
      padding: 3rem 2rem;
      text-align: center;
      color: var(--muted);
      font-size: 0.95rem;
      background: var(--bg);
      border-radius: var(--radius-sm);
      border: 1px dashed var(--border);
    }
    .footer {
      text-align: center;
      padding: 3rem 2rem;
      color: var(--muted);
      font-size: 0.85rem;
      background: var(--surface);
      border-top: 1px solid var(--border);
    }
    .platform-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.25rem;
      margin-bottom: 1.5rem;
    }
    .platform-card {
      background: var(--surface);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      transition: transform 0.4s var(--transition), box-shadow 0.4s var(--transition);
      border: 1px solid var(--border);
      border-top: 5px solid transparent;
    }
    .platform-card:hover { transform: translateY(-7px); box-shadow: var(--shadow-hover); }
    .platform-card.tiktok { border-top-color: var(--platform-tiktok); }
    .platform-card.meta { border-top-color: var(--platform-meta); }
    .platform-card.google { border-top-color: var(--platform-google); }
    .platform-card h3 {
      margin: 0;
      display: flex;
      align-items: center;
      gap: 0.55rem;
      font-size: 1.15rem;
      font-weight: 800;
      font-family: var(--font-body);
    }
    .platform-card .platform-icon { width: 26px; height: 26px; }
    .platform-card.tiktok .platform-icon { color: var(--platform-tiktok); }
    .platform-card.meta .platform-icon { color: var(--platform-meta); }
    .platform-card.google .platform-icon { color: var(--platform-google); }
    .platform-card .metric-row {
      display: flex;
      justify-content: space-between;
      font-size: 0.92rem;
      padding: 0.45rem 0;
      border-bottom: 1px solid var(--border);
    }
    .platform-card .metric-row:last-of-type { border-bottom: none; }
    .platform-card .metric-row span:first-child { color: var(--muted); font-weight: 600; }
    .platform-card .metric-row span:last-child { font-weight: 800; color: var(--ink); }
    .platform-card a {
      margin-top: auto;
      padding-top: 0.85rem;
      color: var(--accent-dark);
      text-decoration: none;
      font-weight: 800;
      font-size: 0.88rem;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: gap 0.2s, color 0.2s;
    }
    .platform-card a:hover { gap: 0.6rem; color: var(--ink); }
    .badge {
      display: inline-block;
      padding: 0.2rem 0.6rem;
      border-radius: 6px;
      font-size: 0.68rem;
      font-weight: 800;
      text-transform: uppercase;
      background: #e0f2fe;
      color: #0369a1;
    }
    .section-title {
      counter-increment: chapter;
      position: relative;
      margin: 3rem 0 1.25rem;
      padding-left: 4rem;
      font-family: var(--font-display);
      font-size: 2rem;
      color: var(--ink);
      font-weight: 400;
      line-height: 1.2;
    }
    .section-title::before {
      content: "0" counter(chapter);
      position: absolute;
      left: 0;
      top: 0.15rem;
      font-family: var(--font-body);
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--accent);
      letter-spacing: 0.12em;
    }
    .section-title::after {
      content: "";
      position: absolute;
      left: 2.6rem;
      top: 0.55rem;
      bottom: 0.55rem;
      width: 2px;
      background: var(--border);
    }
    .recommendation {
      background: var(--surface);
      border-radius: var(--radius-sm);
      padding: 1.25rem 1.5rem;
      margin-bottom: 1rem;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
      border-left: 5px solid var(--accent);
      transition: transform 0.3s var(--transition), box-shadow 0.3s var(--transition);
    }
    .recommendation:hover { transform: translateX(6px); box-shadow: var(--shadow-hover); }
    .recommendation h4 { margin: 0 0 0.35rem; font-size: 1.05rem; font-weight: 800; color: var(--ink); }
    .recommendation p { margin: 0; font-size: 0.94rem; color: var(--ink-light); }
    @media (max-width: 900px) {
      .hero h1 { font-size: clamp(2rem, 6vw, 3.5rem); }
      .hero { padding: 4rem 1.5rem 3.5rem; }
      .section-title { font-size: 1.7rem; }
      .chart-wrap { height: 300px; }
    }
    @media (max-width: 640px) {
      .navbar { padding: 0.75rem 1rem; flex-direction: column; align-items: stretch; gap: 0.5rem; }
      .nav-brand { justify-content: center; font-size: 1rem; }
      .nav-logo { height: 34px; }
      .nav-title { display: none; }
      .nav-tabs { justify-content: center; }
      .nav-tabs a { padding: 0.45rem 0.85rem; font-size: 0.78rem; }
      .lang-toggle { margin-left: auto; }
      .hero { padding: 2.5rem 1rem 3rem; min-height: auto; max-height: none; }
      .hero h1 { font-size: clamp(1.8rem, 8vw, 2.6rem); }
      html[dir="rtl"] .navbar,
    html[dir="rtl"] .nav-brand,
    html[dir="rtl"] .nav-tabs { direction: rtl; }
    html[dir="rtl"] .section-title { padding-left: 0; padding-right: 4rem; }
    html[dir="rtl"] .section-title::before { left: auto; right: 0; }
    html[dir="rtl"] .section-title::after { left: auto; right: 2.6rem; }
    html[dir="rtl"] .pull-quote { padding-left: 0; padding-right: 1.5rem; border-left: none; border-right: 5px solid var(--accent); }
    html[dir="rtl"] .recommendation { border-left: none; border-right: 5px solid var(--accent); }
    html[dir="rtl"] .exec-summary { border-left: none; border-right: 5px solid var(--accent); }
    html[dir="rtl"] table th,
    html[dir="rtl"] table td { text-align: right; }
    html[dir="rtl"] .platform-card .metric-row { direction: rtl; }
    .hero h1 .platform-icon { width: 42px; height: 42px; }
      .hero p { font-size: 1rem; max-width: 100%; }
      .scroll-hint { display: none; }
      .container { padding: 1.5rem 1rem 3rem; }
      .kpis { grid-template-columns: repeat(2, 1fr); gap: 0.75rem; }
      .kpi { padding: 1rem; }
      .kpi-value { font-size: 1.35rem; }
      .kpi-label { font-size: 0.65rem; }
      .filters { flex-direction: column; gap: 0.75rem; padding: 1rem; }
      .filters label { min-width: auto; width: 100%; }
      .filters button { width: 100%; }
      .grid-2, .grid-3 { grid-template-columns: 1fr; gap: 1rem; }
      .platform-grid { grid-template-columns: 1fr; }
      .card { padding: 1.1rem; overflow-x: auto; }
      .card h2 { font-size: 1.1rem; }
      .section-title { padding-left: 2.5rem; font-size: 1.5rem; margin: 2.5rem 0 1rem; }
      .section-title::before { font-size: 0.65rem; }
      .section-title::after { left: 1.6rem; }
      html[dir="rtl"] .section-title { padding-left: 0; padding-right: 2.5rem; }
      html[dir="rtl"] .section-title::before { left: auto; right: 0; }
      html[dir="rtl"] .section-title::after { left: auto; right: 1.6rem; }
      .pull-quote { font-size: 1.15rem; padding-left: 1.1rem; }
      html[dir="rtl"] .pull-quote { padding-left: 0; padding-right: 1.1rem; border-left: none; border-right: 5px solid var(--accent); }
      .metadata-grid { grid-template-columns: 1fr; gap: 0.75rem; }
      .chart-wrap { height: 260px; }
      .chart-wrap.small { height: 200px; }
      .funnel-step { flex: 1 1 100px; padding: 0.75rem; }
      .funnel-step:not(:last-child)::after { right: -0.7rem; font-size: 0.8rem; }
      html[dir="rtl"] .funnel-step:not(:last-child)::after { right: auto; left: -0.7rem; }
      .heatmap { overflow-x: auto; }
      table { font-size: 0.78rem; }
      th, td { padding: 0.55rem 0.45rem; }
      .recommendation { padding: 1rem; }
      .platform-card { padding: 1.1rem; }
    }
    .metadata-bar { padding: 1.25rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); }
    .metadata-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 0.75rem 1.5rem;
    }
    .metadata-grid div { display: flex; flex-direction: column; gap: 0.25rem; }
    .metadata-grid span { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); font-weight: 800; }
    .metadata-grid strong { font-size: 0.85rem; color: var(--ink-light); font-weight: 700; }
    .exec-summary { background: linear-gradient(135deg, #ffffff 0%, #f0fdfa 100%); border-left: 5px solid var(--accent); }
    .exec-summary .lead { font-size: 1.15rem; color: var(--ink); margin-bottom: 0.85rem; line-height: 1.7; font-weight: 600; }
    .exec-summary p { margin: 0; color: var(--ink-light); font-size: 0.96rem; line-height: 1.7; }
    .exec-summary strong { color: var(--ink); }
    .story-lead {
      font-size: 1.1rem;
      color: var(--ink-light);
      line-height: 1.75;
      margin-bottom: 1.5rem;
    }
    .pull-quote {
      font-family: var(--font-display);
      font-size: 1.45rem;
      color: var(--ink);
      line-height: 1.45;
      border-left: 5px solid var(--accent);
      padding: 0.75rem 0 0.75rem 1.5rem;
      margin: 2rem 0;
    }
    .pull-quote cite {
      display: block;
      margin-top: 0.5rem;
      font-family: var(--font-body);
      font-size: 0.8rem;
      font-style: normal;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .funnel {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-top: 1.25rem;
    }
    .funnel-step {
      flex: 1 1 130px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 1rem;
      text-align: center;
      position: relative;
      transition: transform 0.3s var(--transition), box-shadow 0.3s var(--transition);
    }
    .funnel-step:hover { transform: translateY(-4px); box-shadow: var(--shadow); }
    .funnel-step:not(:last-child)::after {
      content: "→";
      position: absolute;
      right: -0.9rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--accent);
      font-weight: 800;
      font-size: 0.9rem;
    }
    .funnel-step strong { display: block; font-size: 0.85rem; color: var(--ink); margin-bottom: 0.25rem; font-weight: 800; }
    .funnel-step span { font-size: 0.72rem; color: var(--muted); }
    .sub-heading { font-size: 1rem; margin: 1.5rem 0 0.6rem; color: var(--ink); font-weight: 800; }
    .muted { color: var(--muted); font-size: 0.92rem; }
    .heatmap {
      display: grid;
      grid-template-columns: 46px repeat(24, 1fr);
      gap: 2px;
      overflow-x: auto;
      padding-bottom: 0.5rem;
      font-size: 0.6rem;
      margin-top: 0.5rem;
    }
    .heatmap-cell {
      aspect-ratio: 1;
      border-radius: 3px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: transparent;
      font-weight: 700;
      position: relative;
      transition: transform 0.2s, color 0.2s;
      cursor: pointer;
    }
    .heatmap-cell:hover { color: var(--ink); z-index: 2; transform: scale(1.15); box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
    .heatmap-label {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      padding-right: 0.4rem;
      font-weight: 800;
      font-size: 0.6rem;
      color: var(--muted);
    }
    .heatmap-header {
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.55rem;
      color: var(--muted);
      font-weight: 700;
    }
    .counter { display: inline-block; }
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>{css}</style>
</head>
<body>
<div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
"""




def render_filters(platform):
    return f"""
<div class="filters">
  <label><span data-en="Campaign Status" data-ar="حالة الحملة">Campaign Status</span>
    <select id="statusFilter" data-platform="{platform}">
      <option value="all" data-en="All" data-ar="الكل">All</option>
      <option value="active" data-en="Active / Enabled" data-ar="نشط / مفعّل">Active / Enabled</option>
      <option value="inactive" data-en="Paused / Disabled" data-ar="متوقف / معطل">Paused / Disabled</option>
    </select>
  </label>
  <label><span data-en="Min Spend (SAR)" data-ar="الحد الأدنى للإنفاق (ر.س)">Min Spend (SAR)</span>
    <input type="number" id="minSpend" placeholder="0" data-platform="{platform}">
  </label>
  <button onclick="applyFilters('{platform}')" data-en="Apply Filters" data-ar="تطبيق الفلاتر">Apply Filters</button>
  <button onclick="resetFilters('{platform}')" style="background:#475569" data-en="Reset" data-ar="إعادة تعيين">Reset</button>
</div>
"""


def kpi_card(label, value, sub=False):
    cls = "kpi sub" if sub else "kpi"
    return f'<div class="{cls}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>'


def render_status(status):
    s = str(status).lower()
    if s in ("enable", "enabled", "active"):
        return '<span class="status active">Active</span>'
    if s in ("disable", "disabled", "paused", "removed", "deleted"):
        return '<span class="status paused">Paused</span>'
    return f'<span class="status unknown">{status}</span>'


def render_tiktok_campaigns_table(rows, table_id="tiktokCampaignsTable"):
    if not rows:
        return '<div class="no-data">No campaign data available.</div>'
    header = """
    <tr>
      <th>Campaign</th><th>Status</th><th>Objective</th><th>Spend</th><th>Impr.</th><th>Clicks</th>
      <th>Conv.</th><th>CTR</th><th>CPC</th><th>CPA</th><th>Conv. Rate</th><th>Video VTR</th><th>Completion</th>
    </tr>"""
    body = ""
    for r in rows:
        body += f"""
    <tr data-status="{r['status'].lower()}" data-spend="{r['spend']:.2f}">
      <td><strong>{r['name']}</strong><br><span class="pill">{r['campaign_id']}</span></td>
      <td>{render_status(r['status'])}</td>
      <td>{r['objective']}</td>
      <td>{fmt_sar(r['spend'])}</td>
      <td>{fmt_num(r['impressions'])}</td>
      <td>{fmt_num(r['clicks'])}</td>
      <td>{fmt_num(r['conversions'])}</td>
      <td>{fmt_pct(r['ctr'], True)}</td>
      <td>{fmt_sar(r['cpc'])}</td>
      <td>{fmt_sar(r['cpconv'])}</td>
      <td>{fmt_pct(r['conv_rate'])}</td>
      <td>{fmt_pct(r['vtr'], True)}</td>
      <td>{fmt_pct(r['completion_rate'])}</td>
    </tr>"""
    return f'<div class="card"><h2>Campaigns</h2><div style="overflow-x:auto"><table class="data-table" id="{table_id}">{header}<tbody>{body}</tbody></table></div></div>'


def render_meta_campaigns_table(rows, table_id="metaCampaignsTable"):
    if not rows:
        return '<div class="no-data">No campaign data available.</div>'
    header = """
    <tr>
      <th>Campaign</th><th>Status</th><th>Objective</th><th>Spend</th><th>Impr.</th><th>Clicks</th>
      <th>Leads</th><th>Reach</th><th>CTR</th><th>CPC</th><th>CPM</th><th>CPA</th><th>Conv. Rate</th>
    </tr>"""
    body = ""
    for r in rows:
        body += f"""
    <tr data-status="{r['status'].lower()}" data-spend="{r['spend']:.2f}">
      <td><strong>{r['name']}</strong><br><span class="pill">{r['campaign_id']}</span></td>
      <td>{render_status(r['status'])}</td>
      <td>{r['objective']}</td>
      <td>{fmt_sar(r['spend'])}</td>
      <td>{fmt_num(r['impressions'])}</td>
      <td>{fmt_num(r['clicks'])}</td>
      <td>{fmt_num(r['conversions'])}</td>
      <td>{fmt_num(r['reach'])}</td>
      <td>{fmt_pct(r['ctr'])}</td>
      <td>{fmt_sar(r['cpc'])}</td>
      <td>{fmt_sar(r['cpm'])}</td>
      <td>{fmt_sar(r['cpa'])}</td>
      <td>{fmt_pct(r['conv_rate'])}</td>
    </tr>"""
    return f'<div class="card"><h2>Campaigns</h2><div style="overflow-x:auto"><table class="data-table" id="{table_id}">{header}<tbody>{body}</tbody></table></div></div>'


def render_google_campaigns_table(rows, table_id="googleCampaignsTable"):
    if not rows:
        return '<div class="no-data">No campaign data available.</div>'
    header = """
    <tr>
      <th>Campaign</th><th>Spend</th><th>Impr.</th><th>Clicks</th><th>Conv.</th><th>Conv. Value</th>
      <th>CTR</th><th>CPC</th><th>CPA</th><th>ROAS</th><th>Conv. Rate</th>
    </tr>"""
    body = ""
    for r in rows:
        body += f"""
    <tr data-status="enabled" data-spend="{r['spend']:.2f}">
      <td><strong>{r['name']}</strong><br><span class="pill">{r['campaign_id']}</span></td>
      <td>{fmt_sar(r['spend'])}</td>
      <td>{fmt_num(r['impressions'])}</td>
      <td>{fmt_num(r['clicks'])}</td>
      <td>{fmt_num(r['conversions'])}</td>
      <td>{fmt_sar(r['conversions_value'])}</td>
      <td>{fmt_pct(r['ctr'])}</td>
      <td>{fmt_sar(r['cpc'])}</td>
      <td>{fmt_sar(r['cpa'])}</td>
      <td>{r['roas']:.2f}x</td>
      <td>{fmt_pct(r['conv_rate'])}</td>
    </tr>"""
    return f'<div class="card"><h2>Campaigns</h2><div style="overflow-x:auto"><table class="data-table" id="{table_id}">{header}<tbody>{body}</tbody></table></div></div>'


def render_simple_table(title, headers, rows, empty_msg="No data available."):
    if not rows:
        return f'<div class="card"><h2>{title}</h2><div class="no-data">{empty_msg}</div></div>'
    ths = "".join(f"<th>{h}</th>" for h in headers)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
    return f'<div class="card"><h2>{title}</h2><div style="overflow-x:auto"><table class="data-table"><thead><tr>{ths}</tr></thead><tbody>{body}</tbody></table></div></div>'


def render_chart_card(title, canvas_id, small=False):
    cls = "chart-wrap small" if small else "chart-wrap"
    return f'<div class="card"><h2>{title}</h2><div class="{cls}"><canvas id="{canvas_id}"></canvas></div></div>'


ICONS = {
    "tiktok": '<svg class="platform-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/></svg>',
    "meta": '<svg class="platform-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M24 12.073C24 5.403 18.627 0 12 0S0 5.403 0 12.073C0 18.1 4.388 23.095 10.125 24v-8.437H7.078v-3.49h3.047V9.297c0-3.017 1.792-4.688 4.533-4.688 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.875v2.25h3.328l-.532 3.49h-2.796V24C19.612 23.095 24 18.1 24 12.073z"/></svg>',
    "google": '<svg class="platform-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>',
}


def platform_icon(platform):
    return ICONS.get(platform, "")


def overview_page(tiktok, meta, google, logo_b64):
    total_spend = tiktok["total_spend"] + (meta["total_spend"] if meta else 0) + (google["total_spend"] if google else 0)
    total_conversions = tiktok["total_conversions"] + (meta["total_conversions"] if meta else 0) + (google["total_conversions"] if google else 0)
    overall_cpa = safe_div(total_spend, total_conversions, 0)

    platform_labels = ["TikTok"]
    platform_spend = [round(tiktok["total_spend"], 2)]
    platform_conv = [tiktok["total_conversions"]]
    platform_cpa = [round(tiktok["cpa"], 2)]
    if meta:
        platform_labels.append("Meta")
        platform_spend.append(round(meta["total_spend"], 2))
        platform_conv.append(meta["total_conversions"])
        platform_cpa.append(round(meta["cpa"], 2))
    if google:
        platform_labels.append("Google")
        platform_spend.append(round(google["total_spend"], 2))
        platform_conv.append(google["total_conversions"])
        platform_cpa.append(round(google["cpa"], 2))

    cards = []
    cards.append("""
    <div class="platform-card tiktok">
      <h3>{tiktok_icon} TikTok</h3>
      <div class="metric-row"><span>Spend</span><span>{tiktok_spend}</span></div>
      <div class="metric-row"><span>Conversions</span><span>{tiktok_conv}</span></div>
      <div class="metric-row"><span>CPA</span><span>{tiktok_cpa}</span></div>
      <div class="metric-row"><span>Share</span><span>{tiktok_share:.1f}% spend · {tiktok_conv_share:.1f}% conv</span></div>
      <a href="tiktok.html">View TikTok deep dive &rarr;</a>
    </div>""".format(
        tiktok_icon=platform_icon('tiktok'), tiktok_spend=fmt_sar(tiktok['total_spend']),
        tiktok_conv=fmt_num(tiktok['total_conversions']), tiktok_cpa=fmt_sar(tiktok['cpa']),
        tiktok_share=tiktok['spend_share'], tiktok_conv_share=tiktok['conv_share']
    ))
    if meta:
        cards.append("""
    <div class="platform-card meta">
      <h3>{meta_icon} Meta Ads</h3>
      <div class="metric-row"><span>Spend</span><span>{meta_spend}</span></div>
      <div class="metric-row"><span>Conversions</span><span>{meta_conv}</span></div>
      <div class="metric-row"><span>CPA</span><span>{meta_cpa}</span></div>
      <div class="metric-row"><span>Share</span><span>{meta_share:.1f}% spend · {meta_conv_share:.1f}% conv</span></div>
      <a href="meta.html">View Meta deep dive &rarr;</a>
    </div>""".format(
            meta_icon=platform_icon('meta'), meta_spend=fmt_sar(meta['total_spend']),
            meta_conv=fmt_num(meta['total_conversions']), meta_cpa=fmt_sar(meta['cpa']),
            meta_share=meta['spend_share'], meta_conv_share=meta['conv_share']
        ))
    if google:
        cards.append("""
    <div class="platform-card google">
      <h3>{google_icon} Google Ads</h3>
      <div class="metric-row"><span>Spend</span><span>{google_spend}</span></div>
      <div class="metric-row"><span>Conversions</span><span>{google_conv}</span></div>
      <div class="metric-row"><span>CPA</span><span>{google_cpa}</span></div>
      <div class="metric-row"><span>Share</span><span>{google_share:.1f}% spend · {google_conv_share:.1f}% conv</span></div>
      <a href="google.html">View Google deep dive &rarr;</a>
    </div>""".format(
            google_icon=platform_icon('google'), google_spend=fmt_sar(google['total_spend']),
            google_conv=fmt_num(google['total_conversions']), google_cpa=fmt_sar(google['cpa']),
            google_share=google['spend_share'], google_conv_share=google['conv_share']
        ))

    body = """
{nav}
<div class="hero">
  <h1>White Car Cross-Platform Ads Audit</h1>
  <p data-en="Executive overview of TikTok, Meta, and Google Ads performance" data-ar="نظرة عامة على أداء إعلانات تيك توك وميتا وجوجل">Executive overview of TikTok, Meta, and Google Ads performance</p>
  <div class="scroll-hint">↓ Scroll to explore</div>
</div>
<div class="container">
  {metadata}

  <div class="kpis">
    {kpi_total_spend}
    {kpi_total_conv}
    {kpi_blended_cpa}
    {kpi_platforms}
  </div>

  {exec_summary}

  <h2 class="section-title">Platform Mix & Efficiency</h2>
  <div class="grid-2">
    {chart_spend_share}
    {chart_conv_share}
  </div>
  <div class="grid-2">
    {chart_cpa}
    {chart_spend_conv}
  </div>

  <div class="platform-grid">
    {cards}
  </div>

  {platform_table}

  <div class="grid-2">
    {data_quality}
    {lead_quality}
  </div>

  <div class="grid-2">
    {anomalies}
    {budget_plan}
  </div>

  {strategic_recs}

  {action_plan}

  {tracking_gaps}

  <h2 class="section-title">Top Spend Campaigns by Platform</h2>
  <div class="grid-3">
    {table_tiktok}
    {table_meta}
    {table_google}
  </div>
</div>
<div class="footer" data-en="Generated on {generated}" data-ar="تم الإنشاء في {generated}">Generated on {generated}</div>
""".format(
        nav=render_nav('overview', logo_b64),
        metadata=report_metadata(),
        kpi_total_spend=kpi_card('Total Spend', fmt_sar(total_spend)),
        kpi_total_conv=kpi_card('Total Conversions', fmt_num(total_conversions)),
        kpi_blended_cpa=kpi_card('Blended CPA', fmt_sar(overall_cpa)),
        kpi_platforms=kpi_card('Platforms', sum([1, bool(meta), bool(google)])),
        exec_summary=executive_summary(tiktok, meta, google),
        chart_spend_share=render_chart_card('Spend Share', 'spendByPlatformChart'),
        chart_conv_share=render_chart_card('Conversions by Platform', 'convByPlatformChart'),
        chart_cpa=render_chart_card('CPA by Platform', 'cpaByPlatformChart'),
        chart_spend_conv=render_chart_card('Spend vs Conversions', 'spendVsConvChart'),
        cards="".join(cards),
        platform_table=platform_comparison_table(tiktok, meta, google),
        data_quality=data_quality_issues(tiktok, meta, google),
        lead_quality=lead_quality_funnel(),
        anomalies=anomalies_red_flags(tiktok, meta, google),
        budget_plan=budget_reallocation_plan(tiktok, meta, google),
        strategic_recs=strategic_recommendations(tiktok, meta, google),
        action_plan=action_plan_14_days(),
        tracking_gaps=tracking_gaps(),
        table_tiktok=render_simple_table('TikTok Top Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpconv'] if c['conversions'] else 0)] for c in tiktok['top_campaigns'][:5]]),
        table_meta=render_simple_table('Meta Top Campaigns', ['Campaign', 'Spend', 'Leads', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in (meta['top_campaigns'][:5] if meta else [])]) if meta else '',
        table_google=render_simple_table('Google Top Campaigns', ['Campaign', 'Spend', 'Conv.', 'ROAS'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), f"{c['roas']:.2f}x"] for c in (google['top_campaigns'][:5] if google else [])]) if google else '',
        generated=datetime.now().strftime('%Y-%m-%d %H:%M')
    )

    return common_head("White Car Ads Audit | Overview", "overview") + body + render_overview_js(platform_labels, platform_spend, platform_conv, platform_cpa)



def render_heatmap(title, heatmap_totals, value_key="cpa"):
    """Render a 7x24 heatmap. heatmap_totals is dict of (day, hour)->metrics."""
    if not heatmap_totals:
        return f'<div class="card"><h2>{title}</h2><div class="no-data">No hourly breakdown available.</div></div>'
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hours = list(range(24))
    values = []
    for day in days:
        for h in hours:
            cell = heatmap_totals.get((day, h), {})
            if value_key == "cpa":
                val = safe_div(cell.get("spend", 0), cell.get("conversions", 0), 0)
            elif value_key == "spend":
                val = cell.get("spend", 0)
            else:
                val = cell.get("conversions", 0)
            values.append(val)
    max_val = max(values) if values else 1
    min_val = min([v for v in values if v > 0]) if any(v > 0 for v in values) else 0

    def color(val):
        if val <= 0:
            return "#f1f5f9"
        if value_key == "cpa":
            intensity = min(1, (val - min_val) / max(max_val - min_val, 0.01))
            return f"rgba(231, 76, 60, {0.15 + intensity * 0.85})"
        intensity = min(1, val / max(max_val, 0.01))
        return f"rgba(69, 162, 158, {0.15 + intensity * 0.85})"

    html = f'<div class="card"><h2>{title}</h2><div class="heatmap">'
    html += '<div></div>' + "".join(f'<div class="heatmap-header">{h}</div>' for h in hours)
    for day in days:
        html += f'<div class="heatmap-label">{day[:3]}</div>'
        for h in hours:
            cell = heatmap_totals.get((day, h), {})
            if value_key == "cpa":
                val = safe_div(cell.get("spend", 0), cell.get("conversions", 0), 0)
                tooltip = f"CPA: SAR {val:.2f}"
            elif value_key == "spend":
                val = cell.get("spend", 0)
                tooltip = f"Spend: SAR {val:.2f}"
            else:
                val = cell.get("conversions", 0)
                tooltip = f"Conv: {int(val)}"
            display = f"{val:.0f}" if value_key in ("spend", "conversions") else f"{val:.0f}"
            html += f'<div class="heatmap-cell" style="background:{color(val)}" title="{day} {h:02d}:00\n{tooltip}">{display}</div>'
    html += '</div></div>'
    return html


def tiktok_page(data, logo_b64):
    daily_labels = [r["day"] for r in data["daily_rows"]]
    daily_spend = [r["spend"] for r in data["daily_rows"]]
    daily_conv = [r["conversions"] for r in data["daily_rows"]]
    dow_labels = [r["day"] for r in data["dow_rows"]]
    dow_spend = [r["spend"] for r in data["dow_rows"]]
    dow_cpa = [r["cpa"] for r in data["dow_rows"]]
    funnel = data["video_funnel"]
    month_labels = [m["month"] for m in data["top_months"]]
    month_spend = [m["spend"] for m in data["top_months"]]
    hourly_labels = [f"{r['hour']:02d}:00" for r in data["hourly_rows"]]
    hourly_spend = [r["spend"] for r in data["hourly_rows"]]
    hourly_cpa = [r["cpa"] for r in data["hourly_rows"]]

    top_weekdays_html = render_simple_table(
        'Top Performing Weekdays (by CPA)',
        ['Day', 'Spend', 'Conv.', 'CPA', 'CTR'],
        [[r['day'], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), fmt_pct(r['ctr'], True)] for r in data['top_weekdays']]
    )

    # Creative performance snapshot
    creative_rows = []
    for ad in data.get('top_ads', [])[:10]:
        creative_rows.append([
            ad['name'][:36],
            ad.get('campaign_name', '')[:24],
            fmt_sar(ad['spend']),
            fmt_num(ad['conversions']),
            fmt_sar(ad['cpconv'] if ad['conversions'] else 0),
            fmt_pct(ad['ctr'], True),
            fmt_pct(ad['conv_rate']),
            "Scale" if ad['conversions'] > 0 and ad['cpconv'] < data['cpa'] * 0.8 else ("Test" if ad['conversions'] > 0 and ad['cpconv'] < data['cpa'] else "Review")
        ])
    creative_table = render_simple_table('Creative Performance Snapshot', ['Ad', 'Campaign', 'Spend', 'Conv.', 'CPA', 'CTR', 'CVR', 'Action'], creative_rows)

    body = """
{nav}
<div class="hero">
  <h1>{icon} TikTok Ads Deep Dive</h1>
  <p><span data-en="Advertiser:" data-ar="المعلن:">Advertiser:</span> {name} (ID {id}) · <span data-en="Objective:" data-ar="الهدف:">Objective:</span> <span data-en="Lead Generation" data-ar="جلب العملاء المحتملين">Lead Generation</span></p>
  <div class="scroll-hint">↓ Scroll to explore</div>
</div>
<div class="container">
  {filters}
  <div class="kpis">
    {kpi_spend}
    {kpi_conv}
    {kpi_impr}
    {kpi_clicks}
    {kpi_ctr}
    {kpi_cpa}
    {kpi_camps}
  </div>

  {campaign_classification}

  {campaigns_table}

  <div class="grid-2">
    {chart_daily_spend}
    {chart_daily_conv}
  </div>

  <h2 class="section-title">Creative Performance</h2>
  {creative_table}

  <h2 class="section-title">Timing & Efficiency</h2>
  <div class="grid-3">
    {chart_dow}
    {top_weekdays}
    {chart_hourly}
  </div>

  <h2 class="section-title">Performance Deep Dive</h2>
  <div class="grid-3">
    {chart_monthly}
    {chart_funnel}
    {top_adgroups}
  </div>

  <div class="grid-2">
    {best_cpa}
    {worst_cpa}
  </div>
</div>
<div class="footer" data-en="Generated on {generated}" data-ar="تم الإنشاء في {generated}">Generated on {generated}</div>
<script>
const ttDailyLabels = {js_daily_labels};
const ttDailySpend = {js_daily_spend};
const ttDailyConv = {js_daily_conv};
const ttDowLabels = {js_dow_labels};
const ttDowSpend = {js_dow_spend};
const ttDowCpa = {js_dow_cpa};
const ttFunnelLabels = ['Plays', '25%', '50%', '75%', '100%'];
const ttFunnelData = {js_funnel};
const ttMonthLabels = {js_month_labels};
const ttMonthSpend = {js_month_spend};
const ttHourlyLabels = {js_hourly_labels};
const ttHourlySpend = {js_hourly_spend};
const ttHourlyCpa = {js_hourly_cpa};
new Chart(document.getElementById('ttDailySpendChart'), {{type:'line', data:{{labels:ttDailyLabels, datasets:[{{label:'Spend (SAR)', data:ttDailySpend, borderColor:'#000000', backgroundColor:'rgba(0,0,0,0.06)', fill:true, tension:0.3}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('ttDailyConvChart'), {{type:'bar', data:{{labels:ttDailyLabels, datasets:[{{label:'Conversions', data:ttDailyConv, backgroundColor:'#000000', borderRadius:6}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('ttDowChart'), {{type:'bar', data:{{labels:ttDowLabels, datasets:[{{label:'CPA (SAR)', data:ttDowCpa, backgroundColor:'#e74c3c', borderRadius:8}}, {{label:'Spend', data:ttDowSpend, backgroundColor:'#000000', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'top'}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('ttHourlyChart'), {{type:'line', data:{{labels:ttHourlyLabels, datasets:[{{label:'Spend', data:ttHourlySpend, borderColor:'#45a29e', backgroundColor:'rgba(69,162,158,0.1)', fill:true, tension:0.3, yAxisID:'y'}}, {{label:'CPA', data:ttHourlyCpa, borderColor:'#e74c3c', backgroundColor:'#e74c3c', tension:0.3, yAxisID:'y1'}}]}}, options:{{responsive:true, maintainAspectRatio:false, scales:{{y:{{beginAtZero:true, title:{{display:true, text:'Spend (SAR)'}}}}, y1:{{beginAtZero:true, position:'right', title:{{display:true, text:'CPA (SAR)'}}}}}}, plugins:{{legend:{{position:'top'}}}}}}}});
new Chart(document.getElementById('ttMonthlyChart'), {{type:'bar', data:{{labels:ttMonthLabels, datasets:[{{label:'Spend', data:ttMonthSpend, backgroundColor:'#45a29e', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('ttFunnelChart'), {{type:'bar', data:{{labels:ttFunnelLabels, datasets:[{{label:'Views', data:ttFunnelData, backgroundColor:['#000','#333','#555','#777','#999'], borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
</script>
</body></html>
""".format(
        nav=render_nav('tiktok', logo_b64),
        icon=platform_icon('tiktok'),
        name=data['account'].get('name', 'Whitecarx1'),
        id=data['account'].get('advertiser_id', ''),
        filters=render_filters('tiktok'),
        kpi_spend=kpi_card('Spend', fmt_sar(data['total_spend'])),
        kpi_conv=kpi_card('Conversions', fmt_num(data['total_conversions'])),
        kpi_impr=kpi_card('Impressions', fmt_num(data['total_impressions'])),
        kpi_clicks=kpi_card('Clicks', fmt_num(data['total_clicks'])),
        kpi_ctr=kpi_card('CTR', fmt_pct(safe_div(data['total_clicks'], data['total_impressions']), True), sub=True),
        kpi_cpa=kpi_card('CPA', fmt_sar(data['cpa']), sub=True),
        kpi_camps=kpi_card('Campaigns', f"{data['total_campaigns']} ({data['active_campaigns']} active)", sub=True),
        campaign_classification=campaign_classification(data['top_campaigns'], 'TikTok'),
        campaigns_table=render_tiktok_campaigns_table(data['top_campaigns']),
        chart_daily_spend=render_chart_card('Daily Spend', 'ttDailySpendChart'),
        chart_daily_conv=render_chart_card('Daily Conversions', 'ttDailyConvChart'),
        chart_dow=render_chart_card('Spend & CPA by Day of Week', 'ttDowChart', small=True),
        top_weekdays=top_weekdays_html,
        chart_hourly=render_chart_card('Hourly Performance (Yesterday)', 'ttHourlyChart', small=True),
        chart_monthly=render_chart_card('Monthly Spend', 'ttMonthlyChart', small=True),
        chart_funnel=render_chart_card('Video Funnel', 'ttFunnelChart', small=True),
        top_adgroups=render_simple_table('Top Ad Groups', ['Ad Group', 'Campaign', 'Spend', 'CPA', 'Completion'], [[ag['name'][:38], ag['campaign_name'][:30], fmt_sar(ag['spend']), fmt_sar(ag['cpconv'] if ag['conversions'] else 0), fmt_pct(ag['completion_rate'])] for ag in data['top_adgroups'][:10]]),
        creative_table=creative_table,
        best_cpa=render_simple_table('Best CPA Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpconv'])] for c in data['best_cpa_campaigns']]),
        worst_cpa=render_simple_table('Worst CPA Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpconv'])] for c in data['worst_cpa_campaigns']]),
        generated=datetime.now().strftime('%Y-%m-%d %H:%M'),
        js_daily_labels=json.dumps(daily_labels),
        js_daily_spend=json.dumps(daily_spend),
        js_daily_conv=json.dumps(daily_conv),
        js_dow_labels=json.dumps(dow_labels),
        js_dow_spend=json.dumps(dow_spend),
        js_dow_cpa=json.dumps(dow_cpa),
        js_funnel=json.dumps([funnel['plays'], funnel['p25'], funnel['p50'], funnel['p75'], funnel['p100']]),
        js_month_labels=json.dumps(month_labels),
        js_month_spend=json.dumps(month_spend),
        js_hourly_labels=json.dumps(hourly_labels),
        js_hourly_spend=json.dumps(hourly_spend),
        js_hourly_cpa=json.dumps(hourly_cpa),
    )
    return common_head("White Car Ads Audit | TikTok", "tiktok") + body + filter_script()


def meta_page(data, logo_b64):
    top_campaigns = data["top_campaigns"]
    labels = [c["name"][:30] for c in top_campaigns]
    spend = [c["spend"] for c in top_campaigns]
    conv = [c["conversions"] for c in top_campaigns]
    cpa = [c["cpa"] for c in top_campaigns]
    hourly_labels = [f"{r['hour']:02d}:00" for r in data["hourly_rows"]]
    hourly_spend = [r["spend"] for r in data["hourly_rows"]]
    hourly_cpa = [r["cpa"] for r in data["hourly_rows"]]
    region_labels = [r["key"][:30] for r in data["region_rows"][:10]]
    region_spend = [r["spend"] for r in data["region_rows"][:10]]
    region_cpa = [r["cpa"] for r in data["region_rows"][:10]]
    chart_region = render_chart_card('Spend by Region', 'metaRegionChart') if data['region_rows'] else ''
    meta_region_chart_js = ""
    if data['region_rows']:
        meta_region_chart_js = (
            f"new Chart(document.getElementById('metaRegionChart'), {{type:'bar', data:{{labels:{json.dumps(region_labels)}, "
            f"datasets:[{{label:'Spend (SAR)', data:{json.dumps(region_spend)}, backgroundColor:'#1877f2', borderRadius:8}}]}}, "
            f"options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});"
        )

    top_weekdays_html = render_simple_table(
        'Top Performing Weekdays (by CPA)',
        ['Day', 'Spend', 'Leads', 'CPA', 'CTR'],
        [[r['day'], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), fmt_pct(r['ctr'])] for r in data.get('top_weekdays', [])]
    ) if data.get('top_weekdays') else ''

    status_note = ''
    if data.get('active_campaigns', 0) == 0 and data.get('active_adsets', 0) > 0:
        status_note = ('<div class="recommendation"><h4>Status inconsistency detected</h4><p>All '
                       + str(data['total_campaigns']) + ' Meta campaigns are paused, but '
                       + str(data['active_adsets']) + ' ad set(s) remain active. Campaign-level budget/status is off while ad sets may still deliver. Clean up campaign/ad set status before relaunching.</p></div>')

    objective_rows = {}
    for c in data.get('top_campaigns', []):
        obj = c.get('objective', 'Unknown')
        if obj not in objective_rows:
            objective_rows[obj] = {"spend": 0, "conversions": 0}
        objective_rows[obj]["spend"] += c.get("spend", 0)
        objective_rows[obj]["conversions"] += c.get("conversions", 0)
    objective_table = render_simple_table(
        'Campaign Objectives',
        ['Objective', 'Spend', 'Leads', 'CPA'],
        [[obj, fmt_sar(v["spend"]), fmt_num(v["conversions"]), fmt_sar(safe_div(v["spend"], v["conversions"], 0))] for obj, v in objective_rows.items()]
    )

    body = """
{nav}
<div class="hero">
  <h1>{icon} Meta Ads Deep Dive</h1>
  <p><span data-en="Account:" data-ar="الحساب:">Account:</span> {name} (ID {id}) · <span data-en="Objective:" data-ar="الهدف:">Objective:</span> <span data-en="Lead Generation / Conversations" data-ar="جلب العملاء / المحادثات">Lead Generation / Conversations</span></p>
  <div class="scroll-hint">↓ Scroll to explore</div>
</div>
<div class="container">
  {filters}
  <div class="kpis">
    {kpi_spend}
    {kpi_conv}
    {kpi_impr}
    {kpi_clicks}
    {kpi_reach}
    {kpi_cpa}
    {kpi_camps}
  </div>

  {status_note}

  {campaigns_table}

  <div class="grid-2">
    {chart_spend}
    {chart_conv}
  </div>

  <div class="grid-2">
    {chart_cpa}
    {objective_table}
  </div>

  <h2 class="section-title">Audience Performance</h2>
  <div class="grid-3">
    {table_age}
    {table_gender}
    {table_region}
  </div>

  {chart_region}

  <h2 class="section-title">Timing & Efficiency</h2>
  <div class="grid-3">
    {top_weekdays}
    {chart_hourly}
    {table_best_cpa}
  </div>

  <h2 class="section-title">Targeting Snapshot</h2>
  {adset_table}

  {table_worst_cpa}
</div>
<div class="footer" data-en="Generated on {generated}" data-ar="تم الإنشاء في {generated}">Generated on {generated}</div>
<script>
const metaLabels = {js_labels};
const metaSpend = {js_spend};
const metaConv = {js_conv};
const metaCpa = {js_cpa};
const metaHourlyLabels = {js_hourly_labels};
const metaHourlySpend = {js_hourly_spend};
const metaHourlyCpa = {js_hourly_cpa};
new Chart(document.getElementById('metaSpendChart'), {{type:'bar', data:{{labels:metaLabels, datasets:[{{label:'Spend (SAR)', data:metaSpend, backgroundColor:'#1877f2', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('metaConvChart'), {{type:'bar', data:{{labels:metaLabels, datasets:[{{label:'Leads', data:metaConv, backgroundColor:'#42b72a', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('metaCpaChart'), {{type:'bar', data:{{labels:metaLabels, datasets:[{{label:'CPA (SAR)', data:metaCpa, backgroundColor:'#e74c3c', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true, title:{{display:true, text:'CPA (SAR)'}}}}}}}}}});
new Chart(document.getElementById('metaHourlyChart'), {{type:'line', data:{{labels:metaHourlyLabels, datasets:[{{label:'Spend', data:metaHourlySpend, borderColor:'#1877f2', backgroundColor:'rgba(24,119,242,0.1)', fill:true, tension:0.3, yAxisID:'y'}}, {{label:'CPA', data:metaHourlyCpa, borderColor:'#e74c3c', backgroundColor:'#e74c3c', tension:0.3, yAxisID:'y1'}}]}}, options:{{responsive:true, maintainAspectRatio:false, scales:{{y:{{beginAtZero:true, title:{{display:true, text:'Spend (SAR)'}}}}, y1:{{beginAtZero:true, position:'right', title:{{display:true, text:'CPA (SAR)'}}}}}}, plugins:{{legend:{{position:'top'}}}}}}}});
</script>
</body></html>
""".format(
        nav=render_nav('meta', logo_b64),
        icon=platform_icon('meta'),
        name=data['account'].get('name', '255'),
        id=data['account'].get('id', ''),
        filters=render_filters('meta'),
        kpi_spend=kpi_card('Lifetime Spend', fmt_sar(data['total_spend'])),
        kpi_conv=kpi_card('Conversions', fmt_num(data['total_conversions'])),
        kpi_impr=kpi_card('Impressions', fmt_num(data['total_impressions'])),
        kpi_clicks=kpi_card('Clicks', fmt_num(data['total_clicks'])),
        kpi_reach=kpi_card('Reach', fmt_num(data['total_reach']), sub=True),
        kpi_cpa=kpi_card('CPA', fmt_sar(data['cpa']), sub=True),
        kpi_camps=kpi_card('Campaigns', f"{data['total_campaigns']} active {data['active_campaigns']} / ad sets active {data['active_adsets']}", sub=True),
        status_note=status_note,
        campaigns_table=render_meta_campaigns_table(data['top_campaigns']),
        chart_spend=render_chart_card('Spend by Campaign', 'metaSpendChart'),
        chart_conv=render_chart_card('Conversions by Campaign', 'metaConvChart'),
        chart_cpa=render_chart_card('CPA by Campaign', 'metaCpaChart'),
        objective_table=objective_table,
        table_age=render_simple_table('Age Groups', ['Age', 'Spend', 'Leads', 'CPA', 'CTR'], [[r['key'], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), fmt_pct(r['ctr'])] for r in data['age_rows']]),
        table_gender=render_simple_table('Gender', ['Gender', 'Spend', 'Leads', 'CPA', 'CTR'], [[r['key'], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), fmt_pct(r['ctr'])] for r in data['gender_rows']]),
        table_region=render_simple_table('Top Regions', ['Region', 'Spend', 'Leads', 'CPA', 'CTR'], [[r['key'], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), fmt_pct(r['ctr'])] for r in data['region_rows'][:10]]),
        top_weekdays=top_weekdays_html,
        chart_hourly=render_chart_card('Hourly Performance (Last 7d)', 'metaHourlyChart', small=True),
        chart_region=chart_region,
        table_best_cpa=render_simple_table('Best CPA Campaigns', ['Campaign', 'Spend', 'Leads', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in data['best_cpa_campaigns']]),
        adset_table=render_simple_table('Ad Sets', ['Ad Set', 'Campaign', 'Status', 'Budget', 'Age', 'Optimization', 'Countries', 'Interests'], [[ag['name'][:36], ag['campaign_id'][:10], render_status(ag['status']), fmt_sar(ag['budget']), f"{ag['age_min']}-{ag['age_max']}", ag['bid_strategy'], ag['countries'], ag['interests']] for ag in data['adset_rows'][:15]]),
        table_worst_cpa=render_simple_table('Worst CPA Campaigns', ['Campaign', 'Spend', 'Leads', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in data['worst_cpa_campaigns']]),
        generated=datetime.now().strftime('%Y-%m-%d %H:%M'),
        js_labels=json.dumps(labels),
        js_spend=json.dumps(spend),
        js_conv=json.dumps(conv),
        js_cpa=json.dumps(cpa),
        js_hourly_labels=json.dumps(hourly_labels),
        js_hourly_spend=json.dumps(hourly_spend),
        js_hourly_cpa=json.dumps(hourly_cpa),
        meta_region_chart_js=meta_region_chart_js,
    )
    return common_head("White Car Ads Audit | Meta", "meta") + body + filter_script()


def google_page(data, logo_b64):
    top_campaigns = data["top_campaigns"]
    labels = [c["name"][:30] for c in top_campaigns]
    spend = [c["spend"] for c in top_campaigns]
    conv = [c["conversions"] for c in top_campaigns]
    cpa = [c["cpa"] for c in top_campaigns]
    month_labels = [m["month"] for m in data["top_months"]]
    month_spend = [m["spend"] for m in data["top_months"]]
    geo_labels = [r["location"][:30] for r in data["geo_rows"]]
    geo_spend = [r["spend"] for r in data["geo_rows"]]
    geo_cpa = [r["cpa"] for r in data["geo_rows"]]

    geo_html = ''
    if data['geo_rows']:
        geo_html = f"""
        <h2 class="section-title">Geo Insights</h2>
        <div class="grid-2">
          {render_chart_card('Spend by Location', 'googleGeoChart')}
          {render_simple_table('Top Locations', ['Location', 'Spend', 'Conv.', 'CPA', 'ROAS'], [[r['location'][:36], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), f"{{r['roas']:.2f}}x"] for r in data['geo_rows'][:10]])}
        </div>
        """
    else:
        geo_html = ('<h2 class="section-title">Geo Insights</h2><div class="card"><p class="muted" data-en="No geographic data available. '
                    'Run fetch_data.sh to pull Google Ads geographic_view performance. If you are on the Pipeboard free plan, '
                    'this may be empty until the weekly execution limit resets." '
                    'data-ar="لا توجد بيانات جغرافية متاحة. قم بتشغيل fetch_data.sh لسحب بيانات الأداء الجغرافي من Google Ads. إذا كنت تستخدم خطة Pipeboard المجانية، '
                    'قد يكون هذا فارغًا حتى تتم إعادة تعيين حد التنفيذ الأسبوعي.">No geographic data available. '
                    'Run fetch_data.sh to pull Google Ads geographic_view performance. If you are on the Pipeboard free plan, '
                    'this may be empty until the weekly execution limit resets.</p></div>')

    google_geo_chart_js = ""
    if data['geo_rows']:
        google_geo_chart_js = (
            f"new Chart(document.getElementById('googleGeoChart'), {{type:'bar', data:{{labels:{json.dumps(geo_labels)}, "
            f"datasets:[{{label:'Spend (SAR)', data:{json.dumps(geo_spend)}, backgroundColor:'#34a853', borderRadius:8}}]}}, "
            f"options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});"
        )

    heatmap_html = render_heatmap('CPA Heatmap by Day & Hour', data['heatmap_totals'], 'cpa')
    top_weekdays_html = render_simple_table(
        'Top Performing Weekdays (by ROAS)',
        ['Day', 'Spend', 'Conv.', 'ROAS', 'CPA'],
        [[r['day'], fmt_sar(r['spend']), fmt_num(r['conversions']), f"{r['roas']:.2f}x", fmt_sar(r['cpa'])] for r in data['top_weekdays']]
    )

    campaign_type_rows = {}
    for c in data.get('top_campaigns', []):
        ctype = c.get('type', 'Unknown')
        if ctype not in campaign_type_rows:
            campaign_type_rows[ctype] = {"spend": 0, "conversions": 0, "value": 0}
        campaign_type_rows[ctype]["spend"] += c.get("spend", 0)
        campaign_type_rows[ctype]["conversions"] += c.get("conversions", 0)
        campaign_type_rows[ctype]["value"] += c.get("conversions_value", 0)
    type_table = render_simple_table(
        'Campaign Types',
        ['Type', 'Spend', 'Conv.', 'CPA', 'ROAS'],
        [[ctype, fmt_sar(v["spend"]), fmt_num(v["conversions"]), fmt_sar(safe_div(v["spend"], v["conversions"], 0)), f"{safe_div(v['value'], v['spend'], 0):.2f}x"] for ctype, v in campaign_type_rows.items()]
    )

    search_terms_note = ('<div class="card"><h2>Search Terms & Keyword Analysis</h2>'
                         '<p class="muted">Search-term and keyword-level data is not currently pulled from Google Ads. '
                         'To complete this audit, fetch search_term_view and keyword_view with metrics.clicks, '
                         'metrics.conversions, metrics.cost_micros, and metrics.conversions_value. This will reveal '
                         'high-intent terms to scale and waste terms to negate.</p></div>')

    body = """
{nav}
<div class="hero">
  <h1>{icon} Google Ads Deep Dive</h1>
  <p><span data-en="Account:" data-ar="الحساب:">Account:</span> {name} ({id}) · <span data-en="High-intent search & Performance Max" data-ar="بحث عالي النية و Performance Max">High-intent search & Performance Max</span></p>
  <div class="scroll-hint">↓ Scroll to explore</div>
</div>
<div class="container">
  {filters}
  <div class="kpis">
    {kpi_spend}
    {kpi_conv}
    {kpi_impr}
    {kpi_clicks}
    {kpi_value}
    {kpi_roas}
    {kpi_camps}
  </div>

  {campaigns_table}

  <div class="grid-2">
    {chart_spend}
    {chart_conv}
  </div>

  <div class="grid-2">
    {chart_cpa}
    {type_table}
  </div>

  <h2 class="section-title">Timing & Efficiency</h2>
  <div class="grid-3">
    {heatmap}
    {top_weekdays}
    {chart_monthly}
  </div>

  <h2 class="section-title">Breakdowns</h2>
  <div class="grid-3">
    {table_device}
    {table_dow}
    {table_adgroups}
  </div>

  {geo_html}

  {search_terms}

  {table_best_cpa}
</div>
<div class="footer" data-en="Generated on {generated}" data-ar="تم الإنشاء في {generated}">Generated on {generated}</div>
<script>
const googleLabels = {js_labels};
const googleSpend = {js_spend};
const googleConv = {js_conv};
const googleCpa = {js_cpa};
const googleMonthLabels = {js_month_labels};
const googleMonthSpend = {js_month_spend};
new Chart(document.getElementById('googleSpendChart'), {{type:'bar', data:{{labels:googleLabels, datasets:[{{label:'Spend (SAR)', data:googleSpend, backgroundColor:'#34a853', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('googleConvChart'), {{type:'bar', data:{{labels:googleLabels, datasets:[{{label:'Conversions', data:googleConv, backgroundColor:'#34a853', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('googleCpaChart'), {{type:'bar', data:{{labels:googleLabels, datasets:[{{label:'CPA (SAR)', data:googleCpa, backgroundColor:'#e74c3c', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true, title:{{display:true, text:'CPA (SAR)'}}}}}}}}}});
new Chart(document.getElementById('googleMonthlyChart'), {{type:'line', data:{{labels:googleMonthLabels, datasets:[{{label:'Spend', data:googleMonthSpend, borderColor:'#34a853', backgroundColor:'rgba(52,168,83,0.1)', fill:true, tension:0.3}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
{google_geo_chart_js}
</script>
</body></html>
""".format(
        nav=render_nav('google', logo_b64),
        icon=platform_icon('google'),
        name=data['account'].get('descriptiveName', 'white car'),
        id=data['account'].get('id', '348-288-3125'),
        filters=render_filters('google'),
        kpi_spend=kpi_card('Spend', fmt_sar(data['total_spend'])),
        kpi_conv=kpi_card('Conversions', fmt_num(data['total_conversions'])),
        kpi_impr=kpi_card('Impressions', fmt_num(data['total_impressions'])),
        kpi_clicks=kpi_card('Clicks', fmt_num(data['total_clicks'])),
        kpi_value=kpi_card('Conv. Value', fmt_sar(data['total_conversion_value']), sub=True),
        kpi_roas=kpi_card('ROAS', f"{safe_div(data['total_conversion_value'], data['total_spend'], 0):.2f}x", sub=True),
        kpi_camps=kpi_card('Campaigns', f"{data['total_campaigns']} ({data['active_campaigns']} active)", sub=True),
        campaigns_table=render_google_campaigns_table(data['top_campaigns']),
        chart_spend=render_chart_card('Spend by Campaign', 'googleSpendChart'),
        chart_conv=render_chart_card('Conversions by Campaign', 'googleConvChart'),
        chart_cpa=render_chart_card('CPA by Campaign', 'googleCpaChart'),
        type_table=type_table,
        heatmap=heatmap_html,
        top_weekdays=top_weekdays_html,
        chart_monthly=render_chart_card('Monthly Spend', 'googleMonthlyChart', small=True),
        table_device=render_simple_table('Device Breakdown', ['Device', 'Spend', 'Conv.', 'ROAS'], [[d['device'].title(), fmt_sar(d['spend']), fmt_num(d['conversions']), f"{d['roas']:.2f}x"] for d in data['device_rows']]),
        table_dow=render_simple_table('Day of Week', ['Day', 'Spend', 'Conv.', 'ROAS'], [[d['day'], fmt_sar(d['spend']), fmt_num(d['conversions']), f"{d['roas']:.2f}x"] for d in data['dow_rows']]),
        table_adgroups=render_simple_table('Top Ad Groups', ['Ad Group', 'Campaign', 'Spend', 'Conv.', 'CPA', 'ROAS'], [[ag['name'][:36], ag['campaign'][:30], fmt_sar(ag['spend']), fmt_num(ag['conversions']), fmt_sar(ag['cpa'] if ag['conversions'] else 0), f"{ag['roas']:.2f}x"] for ag in data['top_adgroups'][:15]]),
        search_terms=search_terms_note,
        table_best_cpa=render_simple_table('Best CPA Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in data['best_cpa_campaigns']]),
        geo_html=geo_html,
        generated=datetime.now().strftime('%Y-%m-%d %H:%M'),
        js_labels=json.dumps(labels),
        js_spend=json.dumps(spend),
        js_conv=json.dumps(conv),
        js_cpa=json.dumps(cpa),
        js_month_labels=json.dumps(month_labels),
        js_month_spend=json.dumps(month_spend),
        google_geo_chart_js=google_geo_chart_js,
    )
    return common_head("White Car Ads Audit | Google Ads", "google") + body + filter_script()


def filter_script():
    return """
<script>
function applyFilters(platform){
  const status = document.getElementById('statusFilter').value;
  const minSpend = parseFloat(document.getElementById('minSpend').value || 0);
  const tableIds = {
    tiktok: 'tiktokCampaignsTable',
    meta: 'metaCampaignsTable',
    google: 'googleCampaignsTable'
  };
  const table = document.getElementById(tableIds[platform]);
  if(!table) return;
  const rows = table.querySelectorAll('tbody tr');
  rows.forEach(row => {
    let show = true;
    const rowStatus = row.getAttribute('data-status') || '';
    const rowSpend = parseFloat(row.getAttribute('data-spend') || 0);
    if(status === 'active' && !(rowStatus.includes('enable') || rowStatus.includes('active'))) show = false;
    if(status === 'inactive' && (rowStatus.includes('enable') || rowStatus.includes('active'))) show = false;
    if(rowSpend < minSpend) show = false;
    row.style.display = show ? '' : 'none';
  });
}
function resetFilters(platform){
  document.getElementById('statusFilter').value = 'all';
  document.getElementById('minSpend').value = '';
  applyFilters(platform);
}
</script>

<script>
document.addEventListener('DOMContentLoaded', () => {
  const progressFill = document.getElementById('progressFill');
  function updateProgress() {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    if (progressFill) progressFill.style.width = pct + '%';
  }
  window.addEventListener('scroll', updateProgress, { passive: true });
  updateProgress();

  const selectors = [
    ['.card', 'reveal'],
    ['.kpi', 'reveal reveal-scale'],
    ['.platform-card', 'reveal'],
    ['.section-title', 'reveal-left'],
    ['.filters', 'reveal'],
    ['.recommendation', 'reveal'],
    ['.funnel-step', 'reveal'],
    ['.pull-quote', 'reveal'],
    ['.metadata-bar', 'reveal']
  ];
  selectors.forEach(([sel, classes]) => {
    document.querySelectorAll(sel).forEach((el, j) => {
      classes.split(' ').forEach(c => el.classList.add(c));
      el.classList.add('delay-' + ((j % 8) + 1));
    });
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -50px 0px' });
  document.querySelectorAll('.reveal, .reveal-scale, .reveal-left').forEach(el => observer.observe(el));

  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const text = el.textContent;
        const match = text.match(/([^\d\-]*)(-?[\d,]+(?:\.\d+)?)(.*)/);
        if (match) {
          const prefix = match[1], suffix = match[3];
          const target = parseFloat(match[2].replace(/,/g, ''));
          if (!isNaN(target)) {
            const duration = 1600;
            const start = performance.now();
            const isInt = Number.isInteger(target);
            function step(now) {
              const p = Math.min((now - start) / duration, 1);
              const eased = 1 - Math.pow(1 - p, 3);
              const current = target * eased;
              let formatted = isInt
                ? Math.round(current).toLocaleString()
                : current.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
              el.textContent = prefix + formatted + suffix;
              if (p < 1) requestAnimationFrame(step);
            }
            requestAnimationFrame(step);
          }
        }
        counterObserver.unobserve(el);
      }
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('.kpi-value').forEach(el => counterObserver.observe(el));
});
</script>

<script>
(function() {
  const DICT = {
    "Overview": "نظرة عامة", "TikTok": "تيك توك", "Meta": "ميتا", "Google Ads": "إعلانات جوجل",
    "White Car Ads Audit": "تدقيق إعلانات وايت كار",
    "Start Date": "تاريخ البدء", "End Date": "تاريخ الانتهاء", "Campaign Status": "حالة الحملة",
    "Min Spend (SAR)": "الحد الأدنى للإنفاق (ر.س)", "Apply Filters": "تطبيق الفلاتر", "Reset": "إعادة تعيين",
    "All": "الكل", "Active / Enabled": "نشط / مفعّل", "Paused / Disabled": "متوقف / معطل",
    "Active": "نشط", "Paused": "متوقف", "Unknown": "غير معروف",
    "Total Spend": "إجمالي الإنفاق", "Total Conversions": "إجمالي التحويلات", "Blended CPA": "متوسط تكلفة التحويل", "Platforms": "المنصات",
    "Spend": "الإنفاق", "Conversions": "التحويلات", "Impressions": "الظهور", "Clicks": "النقرات",
    "CTR": "معدل النقر", "CPC": "تكلفة النقرة", "CPA": "تكلفة التحويل", "Reach": "الوصول",
    "Conv. Value": "قيمة التحويل", "ROAS": "العائد على الإنفاق", "Campaigns": "الحملات",
    "Lifetime Spend": "إجمالي الإنفاق", "Video VTR": "معدل مشاهدة الفيديو", "Completion": "الاكتمال", "Conv. Rate": "معدل التحويل",
    "Campaign": "الحملة", "Status": "الحالة", "Objective": "الهدف", "Impr.": "الظهور", "Conv.": "التحويل",
    "Spend Share": "حصة الإنفاق", "Conversions by Platform": "التحويلات حسب المنصة", "Conversions by Campaign": "التحويلات حسب الحملة",
    "CPA by Platform": "تكلفة التحويل حسب المنصة", "Spend vs Conversions": "الإنفاق مقابل التحويلات",
    "Spend by Campaign": "الإنفاق حسب الحملة", "Monthly Trend": "الاتجاه الشهري", "Device Breakdown": "التفصيل حسب الجهاز",
    "Day-of-Week CPA Heatmap": "خريطة حرارية لتكلفة التحويل حسب اليوم", "Age & Gender": "العمر والجنس", "Region": "المنطقة",
    "Hourly Performance": "الأداء حسب الساعة", "Top Campaigns": "أهم الحملات", "Top Spend Campaigns by Platform": "أعلى الحملات إنفاقًا حسب المنصة",
    "Campaign Classification": "تصنيف الحملات", "Scale Winners": "الرابحون القابلون للتوسع", "Expensive Volume": "حجم مكلف", "Poor Signal": "إشارة ضعيفة",
    "Platform Mix & Efficiency": "مزيج المنصات والكفاءة", "Platform Mix & Dependency Risk": "مزيج المنصات ومخاطر الاعتماد",
    "Lead Quality & CRM Funnel": "جودة العملاء المحتملين وقمع CRM", "Data Quality Issues": "مشكلات جودة البيانات",
    "Strategic Recommendations": "التوصيات الاستراتيجية", "14-Day Action Roadmap": "خطة العمل لمدة 14 يومًا",
    "Tracking & Measurement Gaps": "فجوات التتبع والقياس", "Executive Summary": "الملخص التنفيذي",
    "TikTok Ads Deep Dive": "تحليل عميق لإعلانات تيك توك", "Meta Ads Deep Dive": "تحليل عميق لإعلانات ميتا", "Google Ads Deep Dive": "تحليل عميق لإعلانات جوجل",
    "Performance Deep Dive": "تحليل الأداء العميق", "Creative Performance": "أداء الإبداع", "Timing & Efficiency": "التوقيت والكفاءة", "Audience Performance": "أداء الجمهور",
    "Anomalies & Red Flags": "الحالات الشاذة والعلامات الحمراء",
    "No campaign data available.": "لا توجد بيانات حملات متاحة.", "No data available.": "لا توجد بيانات متاحة.",
    "Reporting period": "فترة الإبلاغ", "Data source": "مصدر البيانات", "Attribution": "النسبة", "Conversion definition": "تعريف التحويل",
    "Platform default attribution windows": "نوافذ النسبة الافتراضية للمنصة",
    "TikTok: Lead Generation form submits · Meta: Lead / messaging / form actions · Google: Form/call conversions": "تيك توك: إرسالات نموذج جلب العملاء · ميتا: عملاء / رسائل / إجراءات النموذج · جوجل: تحويلات النموذج/المكالمات",
    "Key insight from the audit": "رؤية رئيسية من التدقيق",
    "Advertiser:": "المعلن:", "Account:": "الحساب:", "Objective:": "الهدف:",
    "Lead Generation": "جلب العملاء المحتملين", "Lead Generation / Conversations": "جلب العملاء / المحادثات",
    "High-intent search & Performance Max": "بحث عالي النية و Performance Max",
    "Google": "جوجل", "TikTok": "تيك توك", "Meta": "ميتا",
    "Scale / volume driver": "محرك النطاق والحجم", "Audience test / retarget": "اختبار الجمهور / إعادة الاستهداف", "High-intent capture": "التقاط النية العالية",
    "View TikTok deep dive →": "عرض تحليل تيك توك العميق →", "View Meta deep dive →": "عرض تحليل ميتا العميق →", "View Google deep dive →": "عرض تحليل جوجل العميق →",
    "Generated on": "تم الإنشاء في",
    "Geo Insights": "رؤى جغرافية", "Spend by Location": "الإنفاق حسب الموقع", "Top Locations": "أهم المواقع",
    "Spend by Region": "الإنفاق حسب المنطقة", "Location": "الموقع", "Region": "المنطقة"
  };
  const REVERSE = Object.fromEntries(Object.entries(DICT).map(([k, v]) => [v, k]));

  function translateTree(lang) {
    const map = lang === 'ar' ? DICT : REVERSE;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    const nodes = [];
    let node;
    while ((node = walker.nextNode())) {
      if (!node.parentElement) continue;
      if (node.parentElement.hasAttribute('data-en') || node.parentElement.closest('[data-en]')) continue;
      const tag = node.parentElement.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE') continue;
      nodes.push(node);
    }
    nodes.forEach(node => {
      let text = node.textContent;
      Object.keys(map).forEach(key => {
        text = text.split(key).join(map[key]);
      });
      node.textContent = text;
    });
  }

  const langToggle = document.getElementById('langToggle');
  function setLang(lang) {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    localStorage.setItem('wc-lang', lang);
    document.querySelectorAll('[data-en][data-ar]').forEach(el => {
      el.textContent = lang === 'ar' ? el.dataset.ar : el.dataset.en;
    });
    translateTree(lang);
    if (langToggle) langToggle.textContent = lang === 'ar' ? langToggle.dataset.ar : langToggle.dataset.en;
  }
  if (langToggle) {
    langToggle.addEventListener('click', () => {
      const newLang = document.documentElement.lang === 'ar' ? 'en' : 'ar';
      setLang(newLang);
    });
  }
  const savedLang = localStorage.getItem('wc-lang') || 'en';
  if (savedLang === 'ar') setLang('ar');
})();
</script>
"""


def main():
    ASSETS_DIR.mkdir(exist_ok=True)
    logo_b64 = load_logo_base64()

    tiktok = analyze_tiktok()
    meta = analyze_meta()
    google = analyze_google_ads()

    total_spend = tiktok["total_spend"] + (meta["total_spend"] if meta else 0) + (google["total_spend"] if google else 0)
    total_conv = tiktok["total_conversions"] + (meta["total_conversions"] if meta else 0) + (google["total_conversions"] if google else 0)
    tiktok["spend_share"] = tiktok["total_spend"] / total_spend * 100 if total_spend else 0
    tiktok["conv_share"] = tiktok["total_conversions"] / total_conv * 100 if total_conv else 0
    if meta:
        meta["spend_share"] = meta["total_spend"] / total_spend * 100 if total_spend else 0
        meta["conv_share"] = meta["total_conversions"] / total_conv * 100 if total_conv else 0
    if google:
        google["spend_share"] = google["total_spend"] / total_spend * 100 if total_spend else 0
        google["conv_share"] = google["total_conversions"] / total_conv * 100 if total_conv else 0

    pages = {
        "index.html": overview_page(tiktok, meta, google, logo_b64),
        "tiktok.html": tiktok_page(tiktok, logo_b64),
        "meta.html": meta_page(meta, logo_b64),
        "google.html": google_page(google, logo_b64),
    }

    for filename, html in pages.items():
        (OUT_DIR / filename).write_text(html, encoding="utf-8")
        print(f"Wrote {OUT_DIR / filename} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
