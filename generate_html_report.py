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
        "total_adsets": len(adsets), "total_spend": total_spend,
        "total_impressions": total_impressions, "total_clicks": total_clicks,
        "total_conversions": total_conversions, "total_reach": total_reach,
        "top_campaigns": top_campaigns, "best_cpa_campaigns": best_cpa, "worst_cpa_campaigns": worst_cpa,
        "adset_rows": adset_rows,
        "age_rows": age_rows, "gender_rows": gender_rows, "region_rows": region_rows,
        "hourly_rows": hourly_rows, "dow_rows": dow_rows, "top_weekdays": top_weekdays,
    }


def analyze_google_ads():
    account_info, err = parse_mcp("google_ads_account_info.json")
    campaigns_data, _ = parse_mcp("google_ads_campaigns.json")
    ads_data, _ = parse_mcp("google_ads_ads.json")
    monthly_data, _ = parse_mcp("google_ads_monthly.json")
    adgroups_data, _ = parse_mcp("google_ads_adgroups.json")
    device_data, _ = parse_mcp("google_ads_device.json")
    dow_data, _ = parse_mcp("google_ads_dayofweek.json")

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
const palette = ['#000000', '#1877f2', '#4285f4'];
new Chart(document.getElementById('spendByPlatformChart'), {{type:'doughnut', data:{{labels:platformLabels, datasets:[{{data:platformSpend, backgroundColor:palette.slice(0, platformLabels.length), borderWidth:0}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'bottom'}}}}}}}});
new Chart(document.getElementById('convByPlatformChart'), {{type:'bar', data:{{labels:platformLabels, datasets:[{{label:'Conversions', data:platformConv, backgroundColor:palette.slice(0, platformLabels.length), borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('cpaByPlatformChart'), {{type:'bar', data:{{labels:platformLabels, datasets:[{{label:'CPA (SAR)', data:platformCpa, backgroundColor:['#e74c3c','#f39c12','#2ecc71'].slice(0, platformLabels.length), borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true, title:{{display:true, text:'CPA (SAR)'}}}}}}}}}});
new Chart(document.getElementById('spendVsConvChart'), {{type:'bar', data:{{labels:platformLabels, datasets:[{{label:'Spend', data:platformSpend, backgroundColor:palette.slice(0, platformLabels.length), borderRadius:8, yAxisID:'y'}}, {{label:'Conversions', data:platformConv, backgroundColor:palette.slice(0, platformLabels.length).map(c=>c+'80'), borderRadius:8, yAxisID:'y1'}}]}}, options:{{responsive:true, maintainAspectRatio:false, scales:{{y:{{beginAtZero:true, title:{{display:true, text:'Spend (SAR)'}}}}, y1:{{beginAtZero:true, position:'right', title:{{display:true, text:'Conversions'}}}}, x:{{}}}}, plugins:{{legend:{{position:'top'}}}}}}}});
</script>
</body></html>"""


def render_nav(active_tab, logo_b64):
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="White Car" class="nav-logo">' if logo_b64 else ""
    tabs = [
        ("index.html", "Overview", "overview"),
        ("tiktok.html", "TikTok", "tiktok"),
        ("meta.html", "Meta", "meta"),
        ("google.html", "Google Ads", "google"),
    ]
    links = []
    for href, label, tab in tabs:
        cls = "active" if tab == active_tab else ""
        links.append(f'<a href="{href}" class="{cls}">{label}</a>')
    return f"""
<nav class="navbar">
  <div class="nav-brand">
    {logo_html}
    <span class="nav-title">White Car Ads Audit</span>
  </div>
  <div class="nav-tabs">
    {"".join(links)}
  </div>
</nav>
"""


def common_head(title, active_tab):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --wc-white: #ffffff;
      --wc-black: #0b0c10;
      --wc-slate: #1f2833;
      --wc-silver: #c5c6c7;
      --wc-accent: #45a29e;
      --wc-accent-light: #66fcf1;
      --wc-danger: #e74c3c;
      --wc-warn: #f39c12;
      --wc-success: #2ecc71;
      --radius: 14px;
      --shadow: 0 4px 20px rgba(0,0,0,0.08);
      --shadow-strong: 0 10px 40px rgba(0,0,0,0.14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: linear-gradient(135deg, #f8fafc 0%, #eef2f6 100%);
      color: var(--wc-slate);
      line-height: 1.55;
    }}
    .navbar {{
      position: sticky;
      top: 0;
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 2rem;
      background: rgba(11,12,16,0.96);
      backdrop-filter: blur(12px);
      box-shadow: 0 2px 16px rgba(0,0,0,0.15);
      flex-wrap: wrap;
      gap: 0.75rem;
    }}
    .nav-brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      color: #fff;
      font-weight: 700;
      font-size: 1.25rem;
      letter-spacing: -0.01em;
    }}
    .nav-logo {{
      height: 42px;
      width: auto;
      object-fit: contain;
      filter: drop-shadow(0 1px 2px rgba(0,0,0,0.25));
    }}
    .nav-tabs {{
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }}
    .nav-tabs a {{
      color: rgba(255,255,255,0.7);
      text-decoration: none;
      padding: 0.55rem 1rem;
      border-radius: 999px;
      font-weight: 600;
      font-size: 0.9rem;
      transition: all 0.2s;
    }}
    .nav-tabs a:hover, .nav-tabs a.active {{
      color: var(--wc-black);
      background: var(--wc-accent-light);
    }}
    .hero {{
      position: relative;
      overflow: hidden;
      background: var(--wc-black);
      color: #fff;
      padding: 3.5rem 2rem 2.5rem;
      text-align: center;
    }}
    .hero::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at 20% 30%, rgba(69,162,158,0.22), transparent 40%),
                  radial-gradient(circle at 80% 70%, rgba(102,252,241,0.14), transparent 45%);
      pointer-events: none;
    }}
    .hero h1 {{
      position: relative;
      margin: 0 0 0.5rem;
      font-size: clamp(1.8rem, 4vw, 3rem);
      letter-spacing: -0.03em;
    }}
    .hero p {{
      position: relative;
      margin: 0;
      color: var(--wc-silver);
      font-size: 1.05rem;
    }}
    .container {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 1.5rem 1.25rem 3rem;
    }}
    .filters {{
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: flex-end;
      background: #fff;
      padding: 1.1rem 1.25rem;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      margin-bottom: 1.5rem;
    }}
    .filters label {{
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--wc-slate);
      flex: 1 1 160px;
      min-width: 140px;
    }}
    .filters input, .filters select {{
      padding: 0.55rem 0.7rem;
      border: 1px solid #d1d5db;
      border-radius: 10px;
      font: inherit;
      background: #fff;
    }}
    .filters button {{
      padding: 0.6rem 1.2rem;
      border: none;
      border-radius: 10px;
      background: var(--wc-black);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.15s, background 0.15s;
    }}
    .filters button:hover {{ background: var(--wc-slate); transform: translateY(-1px); }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }}
    .kpi {{
      background: #fff;
      border-radius: var(--radius);
      padding: 1.15rem;
      box-shadow: var(--shadow);
      transition: transform 0.15s;
    }}
    .kpi:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-strong); }}
    .kpi-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #64748b;
      font-weight: 700;
      margin-bottom: 0.35rem;
    }}
    .kpi-value {{
      font-size: 1.65rem;
      font-weight: 800;
      color: var(--wc-black);
      letter-spacing: -0.02em;
    }}
    .kpi.sub .kpi-value {{ font-size: 1.25rem; color: var(--wc-slate); }}
    .card {{
      background: #fff;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 1.25rem;
      margin-bottom: 1.25rem;
    }}
    .card h2 {{
      margin: 0 0 1rem;
      font-size: 1.15rem;
      color: var(--wc-black);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .card h2 .platform-icon {{
      width: 26px;
      height: 26px;
    }}
    .grid-2 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 1.25rem;
    }}
    .grid-3 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.25rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }}
    th, td {{
      padding: 0.65rem 0.6rem;
      text-align: left;
      border-bottom: 1px solid #e5e7eb;
      white-space: nowrap;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #f8fafc;
      font-weight: 700;
      color: var(--wc-black);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    tr:hover td {{ background: #f8fafc; }}
    .status {{
      display: inline-block;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 800;
      text-transform: uppercase;
    }}
    .status.active {{ background: #d1fae5; color: #065f46; }}
    .status.paused, .status.removed {{ background: #fee2e2; color: #991b1b; }}
    .status.enable {{ background: #d1fae5; color: #065f46; }}
    .status.disable, .status.unknown {{ background: #e5e7eb; color: #374151; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.35rem 0.75rem;
      border-radius: 999px;
      background: #f1f5f9;
      color: var(--wc-slate);
      font-size: 0.78rem;
      font-weight: 700;
    }}
    .chart-wrap {{
      position: relative;
      height: 320px;
    }}
    .chart-wrap.small {{ height: 240px; }}
    .no-data {{
      padding: 2rem;
      text-align: center;
      color: #64748b;
      font-size: 0.95rem;
    }}
    .footer {{
      text-align: center;
      padding: 2rem;
      color: #64748b;
      font-size: 0.85rem;
    }}
    .platform-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }}
    .platform-card {{
      background: #fff;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      transition: transform 0.15s;
      border-top: 4px solid transparent;
    }}
    .platform-card:hover {{ transform: translateY(-4px); box-shadow: var(--shadow-strong); }}
    .platform-card.tiktok {{ border-color: #000; }}
    .platform-card.meta {{ border-color: #1877f2; }}
    .platform-card.google {{ border-color: #4285f4; }}
    .platform-card h3 {{
      margin: 0;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1.15rem;
    }}
    .platform-card .platform-icon {{ width: 22px; height: 22px; flex-shrink: 0; }}
    .hero .platform-icon {{ color: #fff; width: 26px; height: 26px; }}
    .platform-card.tiktok .platform-icon {{ color: #000; }}
    .platform-card.meta .platform-icon {{ color: #1877f2; }}
    .platform-card.google .platform-icon {{ color: #4285f4; }}
    .card h2 .platform-icon {{ width: 20px; height: 20px; color: var(--wc-slate); }}
    .platform-card .metric-row {{
      display: flex;
      justify-content: space-between;
      font-size: 0.92rem;
    }}
    .platform-card .metric-row span:first-child {{ color: #64748b; }}
    .platform-card .metric-row span:last-child {{ font-weight: 700; }}
    .platform-card a {{
      margin-top: auto;
      padding-top: 0.75rem;
      color: var(--wc-accent);
      text-decoration: none;
      font-weight: 700;
      font-size: 0.9rem;
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
    }}
    .platform-card a:hover {{ text-decoration: underline; }}
    .badge {{
      display: inline-block;
      padding: 0.15rem 0.5rem;
      border-radius: 6px;
      font-size: 0.7rem;
      font-weight: 800;
      text-transform: uppercase;
      background: #e0f2fe;
      color: #0369a1;
    }}
    .section-title {{
      margin: 2rem 0 1rem;
      font-size: 1.35rem;
      color: var(--wc-black);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .recommendation {{
      background: #fff;
      border-radius: var(--radius);
      padding: 1rem 1.25rem;
      margin-bottom: 0.75rem;
      box-shadow: var(--shadow);
      border-left: 4px solid var(--wc-accent);
    }}
    .recommendation h4 {{ margin: 0 0 0.25rem; font-size: 1rem; }}
    .recommendation p {{ margin: 0; font-size: 0.92rem; color: #475569; }}
    @media (max-width: 640px) {{
      .navbar {{ padding: 0.75rem 1rem; }}
      .nav-title {{ display: none; }}
      .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
      .hero {{ padding: 2rem 1rem; }}
    }}
    table.data-table td:nth-child(1), table.data-table th:nth-child(1) {{ white-space: normal; max-width: 220px; }}
  </style>
</head>
<body>
"""


def render_filters(platform):
    return f"""
<div class="filters">
  <label>Start Date
    <input type="date" id="startDate" data-platform="{platform}">
  </label>
  <label>End Date
    <input type="date" id="endDate" data-platform="{platform}">
  </label>
  <label>Campaign Status
    <select id="statusFilter" data-platform="{platform}">
      <option value="all">All</option>
      <option value="active">Active / Enabled</option>
      <option value="inactive">Paused / Disabled</option>
    </select>
  </label>
  <label>Min Spend (SAR)
    <input type="number" id="minSpend" placeholder="0" data-platform="{platform}">
  </label>
  <button onclick="applyFilters('{platform}')">Apply Filters</button>
  <button onclick="resetFilters('{platform}')" style="background:#475569">Reset</button>
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
    platform_cpa = [round(safe_div(tiktok["total_spend"], tiktok["total_conversions"], 0), 2)]
    if meta:
        platform_labels.append("Meta")
        platform_spend.append(round(meta["total_spend"], 2))
        platform_conv.append(meta["total_conversions"])
        platform_cpa.append(round(safe_div(meta["total_spend"], meta["total_conversions"], 0), 2))
    if google:
        platform_labels.append("Google")
        platform_spend.append(round(google["total_spend"], 2))
        platform_conv.append(google["total_conversions"])
        platform_cpa.append(round(safe_div(google["total_spend"], google["total_conversions"], 0), 2))

    cards = []
    cards.append("""
    <div class="platform-card tiktok">
      <h3>{tiktok_icon} TikTok</h3>
      <div class="metric-row"><span>Spend</span><span>{tiktok_spend}</span></div>
      <div class="metric-row"><span>Conversions</span><span>{tiktok_conv}</span></div>
      <div class="metric-row"><span>Campaigns</span><span>{tiktok_camps}</span></div>
      <div class="metric-row"><span>CPA</span><span>{tiktok_cpa}</span></div>
      <a href="tiktok.html">View TikTok report &rarr;</a>
    </div>""".format(
        tiktok_icon=platform_icon('tiktok'), tiktok_spend=fmt_sar(tiktok['total_spend']),
        tiktok_conv=fmt_num(tiktok['total_conversions']), tiktok_camps=f"{tiktok['total_campaigns']} ({tiktok['active_campaigns']} active)",
        tiktok_cpa=fmt_sar(safe_div(tiktok['total_spend'], tiktok['total_conversions'], 0))
    ))
    if meta:
        cards.append("""
    <div class="platform-card meta">
      <h3>{meta_icon} Meta Ads</h3>
      <div class="metric-row"><span>Spend</span><span>{meta_spend}</span></div>
      <div class="metric-row"><span>Conversions</span><span>{meta_conv}</span></div>
      <div class="metric-row"><span>Campaigns</span><span>{meta_camps}</span></div>
      <div class="metric-row"><span>CPA</span><span>{meta_cpa}</span></div>
      <a href="meta.html">View Meta report &rarr;</a>
    </div>""".format(
            meta_icon=platform_icon('meta'), meta_spend=fmt_sar(meta['total_spend']),
            meta_conv=fmt_num(meta['total_conversions']), meta_camps=f"{meta['total_campaigns']} ({meta['active_campaigns']} active)",
            meta_cpa=fmt_sar(safe_div(meta['total_spend'], meta['total_conversions'], 0))
        ))
    if google:
        cards.append("""
    <div class="platform-card google">
      <h3>{google_icon} Google Ads</h3>
      <div class="metric-row"><span>Spend</span><span>{google_spend}</span></div>
      <div class="metric-row"><span>Conversions</span><span>{google_conv}</span></div>
      <div class="metric-row"><span>Campaigns</span><span>{google_camps}</span></div>
      <div class="metric-row"><span>CPA</span><span>{google_cpa}</span></div>
      <a href="google.html">View Google report &rarr;</a>
    </div>""".format(
            google_icon=platform_icon('google'), google_spend=fmt_sar(google['total_spend']),
            google_conv=fmt_num(google['total_conversions']), google_camps=f"{google['total_campaigns']} ({google['active_campaigns']} active)",
            google_cpa=fmt_sar(safe_div(google['total_spend'], google['total_conversions'], 0))
        ))

    recommendations = []
    if tiktok["total_conversions"] > 0 and tiktok["total_spend"] / tiktok["total_conversions"] > 100:
        recommendations.append(("TikTok CPA is above SAR 100", "Review low-converting ad groups and pause underperformers to improve efficiency."))
    if google and google["total_conversions"] > 0 and google["total_conversion_value"] / google["total_spend"] < 2:
        recommendations.append(("Google ROAS below 2x", "Expand high-converting keywords/ad groups and review search terms report for waste."))
    if meta and meta["active_campaigns"] == 0:
        recommendations.append(("Meta campaigns are paused", "Restart top-performing lead campaigns or reallocate budget to TikTok/Google."))
    if tiktok["top_campaigns"] and tiktok["top_campaigns"][0]["spend"] > tiktok["total_spend"] * 0.6:
        recommendations.append(("TikTok spend concentrated", f"'{tiktok['top_campaigns'][0]['name']}' accounts for >60% of spend; diversify creative testing."))

    recs_html = ""
    for title, body in recommendations:
        recs_html += f'<div class="recommendation"><h4>{title}</h4><p>{body}</p></div>'
    if not recs_html:
        recs_html = '<div class="no-data">No automated recommendations at this time.</div>'

    body = """
{nav}
<div class="hero">
  <h1>White Car Cross-Platform Ads Audit</h1>
  <p>Unified overview of TikTok, Meta, and Google Ads performance</p>
</div>
<div class="container">
  <div class="kpis">
    {kpi_total_spend}
    {kpi_total_conv}
    {kpi_blended_cpa}
    {kpi_platforms}
  </div>

  <h2 class="section-title">CPA Comparison by Platform</h2>
  <div class="grid-2">
    {chart_cpa}
    {chart_spend_conv}
  </div>

  <h2 class="section-title">Platform Breakdown</h2>
  <div class="platform-grid">
    {cards}
  </div>

  <h2 class="section-title">Top Spend Campaigns by Platform</h2>
  <div class="grid-3">
    {table_tiktok}
    {table_meta}
    {table_google}
  </div>

  <h2 class="section-title">Recommendations</h2>
  {recs}
</div>
<div class="footer">Generated on {generated}</div>
""".format(
        nav=render_nav('overview', logo_b64),
        kpi_total_spend=kpi_card('Total Spend', fmt_sar(total_spend)),
        kpi_total_conv=kpi_card('Total Conversions', fmt_num(total_conversions)),
        kpi_blended_cpa=kpi_card('Blended CPA', fmt_sar(overall_cpa)),
        kpi_platforms=kpi_card('Platforms', sum([1, bool(meta), bool(google)])),
        chart_cpa=render_chart_card('CPA by Platform', 'cpaByPlatformChart'),
        chart_spend_conv=render_chart_card('Spend vs Conversions', 'spendVsConvChart'),
        cards="".join(cards),
        table_tiktok=render_simple_table('TikTok Top Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpconv'] if c['conversions'] else 0)] for c in tiktok['top_campaigns'][:5]]),
        table_meta=render_simple_table('Meta Top Campaigns', ['Campaign', 'Spend', 'Leads', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in (meta['top_campaigns'][:5] if meta else [])]) if meta else '',
        table_google=render_simple_table('Google Top Campaigns', ['Campaign', 'Spend', 'Conv.', 'ROAS'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), f"{c['roas']:.2f}x"] for c in (google['top_campaigns'][:5] if google else [])]) if google else '',
        recs=recs_html,
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

    body = """
{nav}
<div class="hero">
  <h1>{icon} TikTok Ads</h1>
  <p>Advertiser: {name} (ID {id})</p>
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

  {campaigns_table}

  <div class="grid-2">
    {chart_daily_spend}
    {chart_daily_conv}
  </div>

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
    {top_ads}
    {best_ads_ctr}
  </div>

  <div class="grid-2">
    {best_cpa}
    {worst_cpa}
  </div>
</div>
<div class="footer">Generated on {generated}</div>
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
        kpi_cpa=kpi_card('CPA', fmt_sar(safe_div(data['total_spend'], data['total_conversions'], 0)), sub=True),
        kpi_camps=kpi_card('Campaigns', f"{data['total_campaigns']} ({data['active_campaigns']} active)", sub=True),
        campaigns_table=render_tiktok_campaigns_table(data['top_campaigns']),
        chart_daily_spend=render_chart_card('Daily Spend', 'ttDailySpendChart'),
        chart_daily_conv=render_chart_card('Daily Conversions', 'ttDailyConvChart'),
        chart_dow=render_chart_card('Spend & CPA by Day of Week', 'ttDowChart', small=True),
        top_weekdays=top_weekdays_html,
        chart_hourly=render_chart_card('Hourly Performance (Yesterday)', 'ttHourlyChart', small=True),
        chart_monthly=render_chart_card('Monthly Spend', 'ttMonthlyChart', small=True),
        chart_funnel=render_chart_card('Video Funnel', 'ttFunnelChart', small=True),
        top_adgroups=render_simple_table('Top Ad Groups', ['Ad Group', 'Campaign', 'Spend', 'CPA', 'Completion'], [[ag['name'][:38], ag['campaign_name'][:30], fmt_sar(ag['spend']), fmt_sar(ag['cpconv'] if ag['conversions'] else 0), fmt_pct(ag['completion_rate'])] for ag in data['top_adgroups'][:10]]),
        top_ads=render_simple_table('Top Ads', ['Ad', 'Campaign', 'Spend', 'CPA', 'CTR'], [[ad['name'][:38], ad['campaign_name'][:30], fmt_sar(ad['spend']), fmt_sar(ad['cpconv'] if ad['conversions'] else 0), fmt_pct(ad['ctr'], True)] for ad in data['top_ads'][:10]]),
        best_ads_ctr=render_simple_table('Best CTR Ads', ['Ad', 'Campaign', 'Impr.', 'CTR'], [[ad['name'][:38], ad['campaign_name'][:30], fmt_num(ad['impressions']), fmt_pct(ad['ctr'], True)] for ad in data['best_ads_by_ctr']]),
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

    top_weekdays_html = render_simple_table(
        'Top Performing Weekdays (by CPA)',
        ['Day', 'Spend', 'Leads', 'CPA', 'CTR'],
        [[r['day'], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), fmt_pct(r['ctr'])] for r in data.get('top_weekdays', [])]
    ) if data.get('top_weekdays') else ''

    body = """
{nav}
<div class="hero">
  <h1>{icon} Meta Ads</h1>
  <p>Account: {name} (ID {id})</p>
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

  {campaigns_table}

  <div class="grid-2">
    {chart_spend}
    {chart_conv}
  </div>

  <h2 class="section-title">Audience Performance</h2>
  <div class="grid-3">
    {table_age}
    {table_gender}
    {table_region}
  </div>

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
<div class="footer">Generated on {generated}</div>
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
        kpi_cpa=kpi_card('CPA', fmt_sar(safe_div(data['total_spend'], data['total_conversions'], 0)), sub=True),
        kpi_camps=kpi_card('Campaigns', f"{data['total_campaigns']} ({data['active_campaigns']} active)", sub=True),
        campaigns_table=render_meta_campaigns_table(data['top_campaigns']),
        chart_spend=render_chart_card('Spend by Campaign', 'metaSpendChart'),
        chart_conv=render_chart_card('Conversions by Campaign', 'metaConvChart'),
        table_age=render_simple_table('Age Groups', ['Age', 'Spend', 'Leads', 'CPA', 'CTR'], [[r['key'], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), fmt_pct(r['ctr'])] for r in data['age_rows']]),
        table_gender=render_simple_table('Gender', ['Gender', 'Spend', 'Leads', 'CPA', 'CTR'], [[r['key'], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), fmt_pct(r['ctr'])] for r in data['gender_rows']]),
        table_region=render_simple_table('Top Regions', ['Region', 'Spend', 'Leads', 'CPA', 'CTR'], [[r['key'], fmt_sar(r['spend']), fmt_num(r['conversions']), fmt_sar(r['cpa']), fmt_pct(r['ctr'])] for r in data['region_rows'][:10]]),
        top_weekdays=top_weekdays_html,
        chart_hourly=render_chart_card('Hourly Performance (Last 7d)', 'metaHourlyChart', small=True),
        table_best_cpa=render_simple_table('Best CPA Campaigns', ['Campaign', 'Spend', 'Leads', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in data['best_cpa_campaigns']]),
        adset_table=render_simple_table('Ad Sets', ['Ad Set', 'Campaign', 'Status', 'Budget', 'Age', 'Countries', 'Interests'], [[ag['name'][:36], ag['campaign_id'][:10], render_status(ag['status']), fmt_sar(ag['budget']), f"{ag['age_min']}-{ag['age_max']}", ag['countries'], ag['interests']] for ag in data['adset_rows'][:15]]),
        table_worst_cpa=render_simple_table('Worst CPA Campaigns', ['Campaign', 'Spend', 'Leads', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in data['worst_cpa_campaigns']]),
        generated=datetime.now().strftime('%Y-%m-%d %H:%M'),
        js_labels=json.dumps(labels),
        js_spend=json.dumps(spend),
        js_conv=json.dumps(conv),
        js_cpa=json.dumps(cpa),
        js_hourly_labels=json.dumps(hourly_labels),
        js_hourly_spend=json.dumps(hourly_spend),
        js_hourly_cpa=json.dumps(hourly_cpa),
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

    heatmap_html = render_heatmap('CPA Heatmap by Day & Hour', data['heatmap_totals'], 'cpa')
    top_weekdays_html = render_simple_table(
        'Top Performing Weekdays (by ROAS)',
        ['Day', 'Spend', 'Conv.', 'ROAS', 'CPA'],
        [[r['day'], fmt_sar(r['spend']), fmt_num(r['conversions']), f"{r['roas']:.2f}x", fmt_sar(r['cpa'])] for r in data['top_weekdays']]
    )

    body = """
{nav}
<div class="hero">
  <h1>{icon} Google Ads</h1>
  <p>Account: {name} ({id})</p>
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

  {table_best_cpa}
</div>
<div class="footer">Generated on {generated}</div>
<script>
const googleLabels = {js_labels};
const googleSpend = {js_spend};
const googleConv = {js_conv};
const googleCpa = {js_cpa};
const googleMonthLabels = {js_month_labels};
const googleMonthSpend = {js_month_spend};
new Chart(document.getElementById('googleSpendChart'), {{type:'bar', data:{{labels:googleLabels, datasets:[{{label:'Spend (SAR)', data:googleSpend, backgroundColor:'#4285f4', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('googleConvChart'), {{type:'bar', data:{{labels:googleLabels, datasets:[{{label:'Conversions', data:googleConv, backgroundColor:'#34a853', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('googleCpaChart'), {{type:'bar', data:{{labels:googleLabels, datasets:[{{label:'CPA (SAR)', data:googleCpa, backgroundColor:'#e74c3c', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true, title:{{display:true, text:'CPA (SAR)'}}}}}}}}}});
new Chart(document.getElementById('googleMonthlyChart'), {{type:'line', data:{{labels:googleMonthLabels, datasets:[{{label:'Spend', data:googleMonthSpend, borderColor:'#4285f4', backgroundColor:'rgba(66,133,244,0.1)', fill:true, tension:0.3}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
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
        heatmap=heatmap_html,
        top_weekdays=top_weekdays_html,
        chart_monthly=render_chart_card('Monthly Spend', 'googleMonthlyChart', small=True),
        table_device=render_simple_table('Device Breakdown', ['Device', 'Spend', 'Conv.', 'ROAS'], [[d['device'].title(), fmt_sar(d['spend']), fmt_num(d['conversions']), f"{d['roas']:.2f}x"] for d in data['device_rows']]),
        table_dow=render_simple_table('Day of Week', ['Day', 'Spend', 'Conv.', 'ROAS'], [[d['day'], fmt_sar(d['spend']), fmt_num(d['conversions']), f"{d['roas']:.2f}x"] for d in data['dow_rows']]),
        table_adgroups=render_simple_table('Top Ad Groups', ['Ad Group', 'Campaign', 'Spend', 'Conv.', 'CPA', 'ROAS'], [[ag['name'][:36], ag['campaign'][:30], fmt_sar(ag['spend']), fmt_num(ag['conversions']), fmt_sar(ag['cpa'] if ag['conversions'] else 0), f"{ag['roas']:.2f}x"] for ag in data['top_adgroups'][:15]]),
        table_best_cpa=render_simple_table('Best CPA Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in data['best_cpa_campaigns']]),
        generated=datetime.now().strftime('%Y-%m-%d %H:%M'),
        js_labels=json.dumps(labels),
        js_spend=json.dumps(spend),
        js_conv=json.dumps(conv),
        js_cpa=json.dumps(cpa),
        js_month_labels=json.dumps(month_labels),
        js_month_spend=json.dumps(month_spend),
    )
    return common_head("White Car Ads Audit | Google Ads", "google") + body + filter_script()


def filter_script():
    return """
<script>
function applyFilters(platform){
  const start = document.getElementById('startDate').value;
  const end = document.getElementById('endDate').value;
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
  document.getElementById('startDate').value = '';
  document.getElementById('endDate').value = '';
  document.getElementById('statusFilter').value = 'all';
  document.getElementById('minSpend').value = '';
  applyFilters(platform);
}
</script>
"""


def main():
    ASSETS_DIR.mkdir(exist_ok=True)
    logo_b64 = load_logo_base64()

    tiktok = analyze_tiktok()
    meta = analyze_meta()
    google = analyze_google_ads()

    pages = {
        "index.html": overview_page(tiktok, meta, google, logo_b64),
        "tiktok.html": tiktok_page(tiktok, logo_b64) + filter_script(),
        "meta.html": meta_page(meta, logo_b64) + filter_script(),
        "google.html": google_page(google, logo_b64) + filter_script(),
    }

    for filename, html in pages.items():
        (OUT_DIR / filename).write_text(html, encoding="utf-8")
        print(f"Wrote {OUT_DIR / filename} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
