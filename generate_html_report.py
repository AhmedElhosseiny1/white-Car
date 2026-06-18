#!/usr/bin/env python3
"""Generate a self-contained HTML audit report from Pipeboard MCP raw data."""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

OUT_DIR = Path(__file__).parent
RAW_DIR = OUT_DIR / "raw"


def parse_mcp(filename):
    raw = json.loads((RAW_DIR / filename).read_text())
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


def analyze_tiktok():
    advertiser, _ = parse_mcp("tiktok_advertiser_info.json")
    campaigns_data, _ = parse_mcp("tiktok_campaigns.json")
    adgroups_data, _ = parse_mcp("tiktok_adgroups.json")
    ads_data, _ = parse_mcp("tiktok_ads.json")
    camp_insights, _ = parse_mcp("tiktok_insights_campaign.json")
    daily_insights, _ = parse_mcp("tiktok_insights_daily.json")
    ad_insights, _ = parse_mcp("tiktok_insights_ad.json")
    adgroup_insights, err = parse_mcp("tiktok_insights_adgroup.json")

    adv = advertiser["advertiser"]
    campaigns = campaigns_data.get("campaigns", [])
    adgroups = adgroups_data.get("adgroups", [])
    ads = ads_data.get("ads", [])
    adgroup_map = {ag["adgroup_id"]: ag for ag in adgroups}
    campaign_map = {c["campaign_id"]: c for c in campaigns}

    camp_metrics = camp_insights.get("metrics", [])
    total_spend = 0.0
    total_impressions = 0
    total_clicks = 0
    total_conversions = 0
    total_video_plays = 0
    total_p25 = 0
    total_p50 = 0
    total_p75 = 0
    total_p100 = 0
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

        campaign_rows.append({
            "campaign_id": cid,
            "name": campaign_map.get(cid, {}).get("campaign_name", cid),
            "status": campaign_map.get(cid, {}).get("operation_status", "UNKNOWN"),
            "objective": campaign_map.get(cid, {}).get("objective_type", "UNKNOWN"),
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": ctr,
            "cpc": cpc,
            "cpconv": cpconv,
            "video_plays": video_plays,
            "p25": p25, "p50": p50, "p75": p75, "p100": p100,
            "completion_rate": p100 / video_plays if video_plays else 0,
        })

    top_campaigns = sorted(campaign_rows, key=lambda x: x["spend"], reverse=True)
    best_cpa_campaigns = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpconv"])[:5]
    worst_cpa_campaigns = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpconv"], reverse=True)[:5]

    ad_metrics = ad_insights.get("metrics", [])
    ad_map = {a["ad_id"]: a for a in ads}
    ad_rows = []
    for row in ad_metrics:
        aid = row["dimensions"]["ad_id"]
        m = row["metrics"]
        ad_rows.append({
            "ad_id": aid,
            "name": ad_map.get(aid, {}).get("ad_name", aid),
            "text": ad_map.get(aid, {}).get("ad_text", ""),
            "campaign_name": ad_map.get(aid, {}).get("campaign_name", ""),
            "spend": float(m.get("spend", 0) or 0),
            "impressions": int(float(m.get("impressions", 0) or 0)),
            "clicks": int(float(m.get("clicks", 0) or 0)),
            "conversions": int(float(m.get("conversion", 0) or 0)),
            "ctr": float(m.get("ctr", 0) or 0),
        })
    top_ads = sorted(ad_rows, key=lambda x: x["spend"], reverse=True)[:10]
    best_ads_by_ctr = sorted([a for a in ad_rows if a["impressions"] > 1000], key=lambda x: x["ctr"], reverse=True)[:5]

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
                "adgroup_id": agid,
                "name": ag.get("adgroup_name", agid),
                "campaign_name": ag.get("campaign_name", ""),
                "spend": spend,
                "impressions": impressions,
                "clicks": int(float(m.get("clicks", 0) or 0)),
                "conversions": conversions,
                "ctr": float(m.get("ctr", 0) or 0),
                "cpc": float(m.get("cpc", 0) or 0),
                "cpconv": float(m.get("cost_per_conversion", 0) or 0),
                "video_plays": video_plays,
                "completion_rate": p100 / video_plays if video_plays else 0,
                "vtr": video_plays / impressions if impressions else 0,
            })
    top_adgroups = sorted(adgroup_rows, key=lambda x: x["spend"], reverse=True)[:10]

    daily_rows = []
    for row in daily_insights.get("metrics", []):
        day = row["dimensions"]["stat_time_day"][:10]
        m = row["metrics"]
        daily_rows.append({
            "day": day,
            "spend": float(m.get("spend", 0) or 0),
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
                "day": dow,
                "spend": dow_spend[dow],
                "conversions": dow_conv[dow],
                "clicks": dow_clicks[dow],
                "impressions": dow_impressions[dow],
                "ctr": dow_clicks[dow] / dow_impressions[dow] if dow_impressions[dow] else 0,
                "cpa": dow_spend[dow] / dow_conv[dow] if dow_conv[dow] else 0,
            })

    monthly_spend = defaultdict(float)
    monthly_conversions = defaultdict(int)
    for row in daily_rows:
        month = row["day"][:7]
        monthly_spend[month] += row["spend"]
        monthly_conversions[month] += row["conversions"]
    top_months = sorted(
        [{"month": m, "spend": s, "conversions": monthly_conversions[m]} for m, s in monthly_spend.items()],
        key=lambda x: x["spend"],
        reverse=True,
    )

    active_campaigns = [c for c in campaigns if c.get("operation_status") == "ENABLE"]
    inactive_campaigns = [c for c in campaigns if c.get("operation_status") != "ENABLE"]

    return {
        "account": adv,
        "total_campaigns": len(campaigns),
        "active_campaigns": len(active_campaigns),
        "inactive_campaigns": inactive_campaigns,
        "total_adgroups": len(adgroups),
        "total_ads": len(ads),
        "total_spend": total_spend,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "total_video_plays": total_video_plays,
        "top_campaigns": top_campaigns,
        "best_cpa_campaigns": best_cpa_campaigns,
        "worst_cpa_campaigns": worst_cpa_campaigns,
        "top_adgroups": top_adgroups,
        "top_ads": top_ads,
        "best_ads_by_ctr": best_ads_by_ctr,
        "daily_rows": daily_rows_sorted,
        "top_days": top_days,
        "best_cpa_days": best_cpa_days,
        "dow_rows": dow_rows,
        "top_months": top_months,
        "video_funnel": {"plays": total_video_plays, "p25": total_p25, "p50": total_p50, "p75": total_p75, "p100": total_p100},
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
    total_spend = 0.0
    total_impressions = 0
    total_clicks = 0
    total_conversions = 0
    total_conversion_value = 0

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
            "campaign_id": cid,
            "name": data["name"],
            "spend": data["spend"],
            "impressions": data["impressions"],
            "clicks": data["clicks"],
            "conversions": data["conversions"],
            "conversions_value": data["conversions_value"],
            "ctr": data["clicks"] / data["impressions"] if data["impressions"] else 0,
            "cpc": data["spend"] / data["clicks"] if data["clicks"] else 0,
            "cpa": data["spend"] / data["conversions"] if data["conversions"] else 0,
            "roas": data["conversions_value"] / data["spend"] if data["spend"] else 0,
            "conv_rate": data["conversions"] / data["clicks"] if data["clicks"] else 0,
        })
    top_campaigns = sorted(campaign_rows, key=lambda x: x["spend"], reverse=True)
    best_cpa_campaigns = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpa"])[:3]

    top_months = sorted(
        [{"month": m, "spend": s, "conversions": monthly_conversions[m]} for m, s in monthly_spend.items()],
        key=lambda x: x["spend"],
        reverse=True,
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
        adgroup_rows.append({
            "name": ag["name"],
            "campaign": c["name"],
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": m.get("ctr", 0),
            "cpc": float(m.get("averageCpc", 0) or 0) / 1_000_000,
            "cpa": float(m.get("costPerConversion", 0) or 0) / 1_000_000 if conversions else 0,
            "conv_rate": conversions / clicks if clicks else 0,
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
            "device": device,
            "spend": data["spend"],
            "impressions": data["impressions"],
            "clicks": data["clicks"],
            "conversions": data["conversions"],
            "conversions_value": data["conversions_value"],
            "ctr": data["clicks"] / data["impressions"] if data["impressions"] else 0,
            "cpa": data["spend"] / data["conversions"] if data["conversions"] else 0,
            "roas": data["conversions_value"] / data["spend"] if data["spend"] else 0,
            "conv_rate": data["conversions"] / data["clicks"] if data["clicks"] else 0,
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
                "day": dow.title(),
                "spend": data["spend"],
                "impressions": data["impressions"],
                "clicks": data["clicks"],
                "conversions": data["conversions"],
                "conversions_value": data["conversions_value"],
                "ctr": data["clicks"] / data["impressions"] if data["impressions"] else 0,
                "cpa": data["spend"] / data["conversions"] if data["conversions"] else 0,
                "roas": data["conversions_value"] / data["spend"] if data["spend"] else 0,
                "conv_rate": data["conversions"] / data["clicks"] if data["clicks"] else 0,
            })

    active_campaigns = [c for c in campaigns if c.get("status") == "ENABLED"]
    inactive_campaigns = [c for c in campaigns if c.get("status") != "ENABLED"]

    return {
        "account": account,
        "total_campaigns": len(campaigns),
        "active_campaigns": len(active_campaigns),
        "inactive_campaigns": inactive_campaigns,
        "total_ads": len(ads),
        "ads": ads,
        "total_spend": total_spend,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "total_conversion_value": total_conversion_value,
        "top_campaigns": top_campaigns,
        "best_cpa_campaigns": best_cpa_campaigns,
        "top_adgroups": top_adgroups,
        "top_months": top_months,
        "device_rows": device_rows,
        "dow_rows": dow_rows,
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

    total_spend = 0.0
    total_impressions = 0
    total_clicks = 0
    total_conversions = 0
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

        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        total_conversions += conversions

        campaign_rows.append({
            "campaign_id": cid,
            "name": row.get("campaign_name", c.get("name", cid)),
            "status": c.get("status", "UNKNOWN"),
            "objective": c.get("objective", "UNKNOWN"),
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": ctr,
            "cpc": cpc,
            "cpm": cpm,
            "reach": reach,
            "frequency": float(row.get("frequency", 0) or 0),
            "cpa": spend / conversions if conversions else 0,
            "conv_rate": conversions / clicks if clicks else 0,
        })

    top_campaigns = sorted(campaign_rows, key=lambda x: x["spend"], reverse=True)
    best_cpa_campaigns = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpa"])[:5]
    worst_cpa_campaigns = sorted([c for c in campaign_rows if c["conversions"] > 0], key=lambda x: x["cpa"], reverse=True)[:5]

    active_campaigns = [c for c in campaigns if c.get("status") == "ACTIVE"]
    paused_campaigns = [c for c in campaigns if c.get("status") != "ACTIVE"]

    # Adset summary
    adset_rows = []
    for ag in adsets[:20]:
        targeting = ag.get("targeting", {})
        age_range = targeting.get("age_range", [])
        geo = targeting.get("geo_locations", {})
        countries = geo.get("countries", [])
        interests = []
        for spec in targeting.get("flexible_spec", []):
            for interest in spec.get("interests", []):
                interests.append(interest.get("name", ""))
        adset_rows.append({
            "name": ag.get("name", ""),
            "campaign_id": ag.get("campaign_id", ""),
            "status": ag.get("status", ""),
            "budget": float(ag.get("daily_budget", 0) or 0) / 100,
            "bid_strategy": ag.get("bid_strategy", ""),
            "age_min": targeting.get("age_min", ""),
            "age_max": targeting.get("age_max", ""),
            "countries": ", ".join(countries),
            "interests": ", ".join(interests[:5]),
        })

    return {
        "account": account,
        "total_campaigns": len(campaigns),
        "active_campaigns": len(active_campaigns),
        "paused_campaigns": paused_campaigns,
        "total_adsets": len(adsets),
        "total_spend": total_spend,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "top_campaigns": top_campaigns,
        "best_cpa_campaigns": best_cpa_campaigns,
        "worst_cpa_campaigns": worst_cpa_campaigns,
        "adset_rows": adset_rows,
    }


def render_table(headers, rows, cls=""):
    html = [f'<table class="{cls}">', "<thead><tr>"]
    html += [f"<th>{h}</th>" for h in headers]
    html += ["</tr></thead><tbody>"]
    for row in rows:
        html.append("<tr>")
        for cell in row:
            html.append(f"<td>{cell}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    return "\n".join(html)


def main():
    tiktok = analyze_tiktok()
    google = analyze_google_ads()
    meta = analyze_meta()

    tiktok_daily_labels = [r["day"] for r in tiktok["daily_rows"]]
    tiktok_daily_spend = [r["spend"] for r in tiktok["daily_rows"]]
    tiktok_daily_conv = [r["conversions"] for r in tiktok["daily_rows"]]
    tiktok_month_labels = [m["month"] for m in tiktok["top_months"]]
    tiktok_month_spend = [m["spend"] for m in tiktok["top_months"]]
    tiktok_dow_labels = [r["day"][:3] for r in tiktok["dow_rows"]]
    tiktok_dow_spend = [r["spend"] for r in tiktok["dow_rows"]]

    google_month_labels = [m["month"][:7] for m in google["top_months"]] if google else []
    google_month_spend = [m["spend"] for m in google["top_months"]] if google else []
    google_device_labels = [r["device"].title() for r in google["device_rows"]] if google else []
    google_device_spend = [r["spend"] for r in google["device_rows"]] if google else []
    google_dow_labels = [r["day"][:3] for r in google["dow_rows"]] if google else []
    google_dow_cpa = [r["cpa"] for r in google["dow_rows"]] if google else []

    meta_month_labels = [c["name"][:15] for c in meta["top_campaigns"]] if meta else []
    meta_month_spend = [c["spend"] for c in meta["top_campaigns"]] if meta else []

    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TikTok, Meta & Google Ads Audit - Whitecarx</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-2: #334155;
  --text: #f8fafc;
  --text-muted: #94a3b8;
  --accent: #38bdf8;
  --accent-2: #a855f7;
  --meta: #f43f5e;
  --danger: #ef4444;
  --success: #22c55e;
  --warning: #f59e0b;
  --border: #334155;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}
.container { max-width: 1300px; margin: 0 auto; padding: 2rem; }
header {
  text-align: center;
  padding: 3rem 1rem;
  background: linear-gradient(135deg, var(--surface) 0%, var(--bg) 100%);
  border-bottom: 1px solid var(--border);
}
header h1 { margin: 0; font-size: 2.5rem; background: linear-gradient(90deg, var(--accent), var(--accent-2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
header p { color: var(--text-muted); margin-top: 0.5rem; }
.section { background: var(--surface); border-radius: 16px; padding: 2rem; margin: 2rem 0; border: 1px solid var(--border); }
.section h2 { margin-top: 0; color: var(--accent); font-size: 1.75rem; }
.section h3 { color: var(--text); margin-top: 1.5rem; font-size: 1.25rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0; }
.metric-card {
  background: var(--surface-2);
  border-radius: 12px;
  padding: 1.25rem;
  text-align: center;
  border: 1px solid var(--border);
}
.metric-card .label { color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
.metric-card .value { font-size: 1.6rem; font-weight: 700; margin-top: 0.25rem; }
.metric-card.positive .value { color: var(--success); }
.metric-card.negative .value { color: var(--danger); }
.metric-card.warning .value { color: var(--warning); }
.metric-card.meta .value { color: var(--meta); }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }
th, td { padding: 0.65rem; text-align: left; border-bottom: 1px solid var(--border); }
th { background: var(--surface-2); color: var(--accent); font-weight: 600; }
tr:hover { background: rgba(255,255,255,0.03); }
.chart-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 1.5rem; }
.chart-container { position: relative; height: 320px; background: var(--surface-2); border-radius: 12px; padding: 1rem; border: 1px solid var(--border); }
.insight-card {
  background: var(--surface-2);
  border-radius: 12px;
  padding: 1.25rem;
  margin: 1rem 0;
  border-left: 4px solid var(--accent);
}
.insight-card.danger { border-left-color: var(--danger); }
.insight-card.warning { border-left-color: var(--warning); }
.insight-card.success { border-left-color: var(--success); }
.insight-card.meta { border-left-color: var(--meta); }
.insight-card .title { font-weight: 700; margin-bottom: 0.5rem; color: var(--text); }
.insight-card .body { color: var(--text-muted); font-size: 0.95rem; }
.recommendations { list-style: none; padding: 0; }
.recommendations li {
  background: var(--surface-2);
  border-left: 4px solid var(--accent);
  padding: 1rem 1.25rem;
  margin-bottom: 0.75rem;
  border-radius: 0 8px 8px 0;
}
.recommendations li.danger { border-left-color: var(--danger); }
.recommendations li.warning { border-left-color: var(--warning); }
.recommendations li.success { border-left-color: var(--success); }
.recommendations li.meta { border-left-color: var(--meta); }
.note {
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid var(--accent);
  border-radius: 8px;
  padding: 1rem;
  margin: 1rem 0;
  color: var(--text);
}
.funnel {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
  margin: 1.5rem 0;
}
.funnel-step {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem;
  text-align: center;
  min-width: 120px;
}
.funnel-step .value { font-size: 1.4rem; font-weight: 700; color: var(--accent); }
.funnel-step .label { font-size: 0.8rem; color: var(--text-muted); }
.funnel-step .rate { font-size: 0.75rem; color: var(--success); margin-top: 0.25rem; }
.funnel-arrow { color: var(--text-muted); font-size: 1.5rem; }
.platform-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  margin-right: 0.5rem;
}
.badge-tiktok { background: rgba(56, 189, 248, 0.2); color: var(--accent); }
.badge-google { background: rgba(34, 197, 94, 0.2); color: var(--success); }
.badge-meta { background: rgba(244, 63, 94, 0.2); color: var(--meta); }
footer { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem; }
@media (max-width: 768px) {
  .container { padding: 1rem; }
  header h1 { font-size: 1.75rem; }
  .section { padding: 1.25rem; }
  table { font-size: 0.8rem; }
  th, td { padding: 0.5rem; }
  .chart-row { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<header>
  <h1>TikTok, Meta & Google Ads Audit</h1>
  <p>Whitecarx · Generated on """)
    html_parts.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
    html_parts.append("""</p>
</header>
<div class="container">
""")

    # Accounts audited
    html_parts.append("""<div class="section">
  <h2>Accounts Audited</h2>
  <div class="grid">
    <div class="metric-card"><div class="label">TikTok Ads</div><div class="value">7521672875829477392</div><div style="color:var(--text-muted);font-size:.85rem">""")
    html_parts.append(tiktok["account"].get("name", "Unknown"))
    html_parts.append("""</div></div>
    <div class="metric-card meta"><div class="label">Meta Ads</div><div class="value">908730431603058</div><div style="color:var(--text-muted);font-size:.85rem">""")
    html_parts.append(meta["account"].get("name", "Unknown") if meta else "Not accessible")
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Google Ads</div><div class="value">348-288-3125</div><div style="color:var(--text-muted);font-size:.85rem">""")
    html_parts.append(google["account"].get("name", "Unknown") if google else "Not accessible")
    html_parts.append("""</div></div>
  </div>
</div>
""")

    # Cross-platform summary
    if meta and google:
        html_parts.append("""<div class="section">
  <h2>Cross-Platform Summary</h2>
  <div class="grid">
    <div class="metric-card"><div class="label">Combined Spend</div><div class="value">""")
        html_parts.append(fmt_sar(tiktok["total_spend"] + google["total_spend"] + meta["total_spend"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Combined Impressions</div><div class="value">""")
        html_parts.append(fmt_num(tiktok["total_impressions"] + google["total_impressions"] + meta["total_impressions"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Combined Clicks</div><div class="value">""")
        html_parts.append(fmt_num(tiktok["total_clicks"] + google["total_clicks"] + meta["total_clicks"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Combined Conversions</div><div class="value">""")
        html_parts.append(fmt_num(tiktok["total_conversions"] + google["total_conversions"] + meta["total_conversions"]))
        html_parts.append("""</div></div>
  </div>
  """)
        html_parts.append(render_table(
            ["Platform", "Spend", "Impressions", "Clicks", "Conversions", "CTR", "CPC", "CPA", "Conv Rate"],
            [
                ["TikTok", fmt_sar(tiktok["total_spend"]), fmt_num(tiktok["total_impressions"]), fmt_num(tiktok["total_clicks"]), fmt_num(tiktok["total_conversions"]),
                 fmt_pct(tiktok["total_clicks"] / tiktok["total_impressions"] if tiktok["total_impressions"] else 0),
                 fmt_sar(tiktok["total_spend"] / tiktok["total_clicks"] if tiktok["total_clicks"] else 0),
                 fmt_sar(tiktok["total_spend"] / tiktok["total_conversions"] if tiktok["total_conversions"] else 0),
                 fmt_pct(tiktok["total_conversions"] / tiktok["total_clicks"] if tiktok["total_clicks"] else 0)],
                ["Meta", fmt_sar(meta["total_spend"]), fmt_num(meta["total_impressions"]), fmt_num(meta["total_clicks"]), fmt_num(meta["total_conversions"]),
                 fmt_pct(meta["total_clicks"] / meta["total_impressions"] if meta["total_impressions"] else 0),
                 fmt_sar(meta["total_spend"] / meta["total_clicks"] if meta["total_clicks"] else 0),
                 fmt_sar(meta["total_spend"] / meta["total_conversions"] if meta["total_conversions"] else 0),
                 fmt_pct(meta["total_conversions"] / meta["total_clicks"] if meta["total_clicks"] else 0)],
                ["Google Ads", fmt_sar(google["total_spend"]), fmt_num(google["total_impressions"]), fmt_num(google["total_clicks"]), fmt_num(google["total_conversions"]),
                 fmt_pct(google["total_clicks"] / google["total_impressions"] if google["total_impressions"] else 0),
                 fmt_sar(google["total_spend"] / google["total_clicks"] if google["total_clicks"] else 0),
                 fmt_sar(google["total_spend"] / google["total_conversions"] if google["total_conversions"] else 0),
                 fmt_pct(google["total_conversions"] / google["total_clicks"] if google["total_clicks"] else 0)],
            ]
        ))
        html_parts.append("</div>")

    # TIKTOK SECTION
    html_parts.append("""<div class="section">
  <h2><span class="platform-badge badge-tiktok">TikTok</span> TikTok Ads Audit</h2>
  <p><strong>Account:</strong> """)
    html_parts.append(tiktok["account"].get("name", "Unknown"))
    html_parts.append(""" · <strong>Currency:</strong> """)
    html_parts.append(tiktok["account"].get("currency", "SAR"))
    html_parts.append("""</p>
  <div class="grid">
    <div class="metric-card"><div class="label">Spend (365d)</div><div class="value">""")
    html_parts.append(fmt_sar(tiktok["total_spend"]))
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Impressions</div><div class="value">""")
    html_parts.append(fmt_num(tiktok["total_impressions"]))
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Clicks</div><div class="value">""")
    html_parts.append(fmt_num(tiktok["total_clicks"]))
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Conversions</div><div class="value">""")
    html_parts.append(fmt_num(tiktok["total_conversions"]))
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">CTR</div><div class="value">""")
    html_parts.append(fmt_pct(tiktok["total_clicks"] / tiktok["total_impressions"] if tiktok["total_impressions"] else 0))
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">CPA</div><div class="value">""")
    html_parts.append(fmt_sar(tiktok["total_spend"] / tiktok["total_conversions"] if tiktok["total_conversions"] else 0))
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Active / Total</div><div class="value">""")
    html_parts.append(f"{tiktok['active_campaigns']} / {tiktok['total_campaigns']}")
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Video Plays</div><div class="value">""")
    html_parts.append(fmt_num(tiktok["total_video_plays"]))
    html_parts.append("""</div></div>
  </div>

  <h3>Video View Funnel</h3>
  <div class="funnel">
    <div class="funnel-step"><div class="value">""")
    html_parts.append(fmt_num(tiktok["total_impressions"]))
    html_parts.append("""</div><div class="label">Impressions</div></div>
    <div class="funnel-arrow">→</div>
    <div class="funnel-step"><div class="value">""")
    html_parts.append(fmt_num(tiktok["video_funnel"]["plays"]))
    html_parts.append("""</div><div class="label">Video Plays</div><div class="rate">""")
    html_parts.append(fmt_pct(tiktok["video_funnel"]["plays"] / tiktok["total_impressions"] if tiktok["total_impressions"] else 0))
    html_parts.append("""</div></div>
    <div class="funnel-arrow">→</div>
    <div class="funnel-step"><div class="value">""")
    html_parts.append(fmt_num(tiktok["video_funnel"]["p25"]))
    html_parts.append("""</div><div class="label">25% View</div><div class="rate">""")
    html_parts.append(fmt_pct(tiktok["video_funnel"]["p25"] / tiktok["video_funnel"]["plays"] if tiktok["video_funnel"]["plays"] else 0))
    html_parts.append("""</div></div>
    <div class="funnel-arrow">→</div>
    <div class="funnel-step"><div class="value">""")
    html_parts.append(fmt_num(tiktok["video_funnel"]["p50"]))
    html_parts.append("""</div><div class="label">50% View</div><div class="rate">""")
    html_parts.append(fmt_pct(tiktok["video_funnel"]["p50"] / tiktok["video_funnel"]["plays"] if tiktok["video_funnel"]["plays"] else 0))
    html_parts.append("""</div></div>
    <div class="funnel-arrow">→</div>
    <div class="funnel-step"><div class="value">""")
    html_parts.append(fmt_num(tiktok["video_funnel"]["p75"]))
    html_parts.append("""</div><div class="label">75% View</div><div class="rate">""")
    html_parts.append(fmt_pct(tiktok["video_funnel"]["p75"] / tiktok["video_funnel"]["plays"] if tiktok["video_funnel"]["plays"] else 0))
    html_parts.append("""</div></div>
    <div class="funnel-arrow">→</div>
    <div class="funnel-step"><div class="value">""")
    html_parts.append(fmt_num(tiktok["video_funnel"]["p100"]))
    html_parts.append("""</div><div class="label">100% View</div><div class="rate">""")
    html_parts.append(fmt_pct(tiktok["video_funnel"]["p100"] / tiktok["video_funnel"]["plays"] if tiktok["video_funnel"]["plays"] else 0))
    html_parts.append("""</div></div>
  </div>

  <h3>Top Campaigns by Spend</h3>
  """)
    html_parts.append(render_table(
        ["Rank", "Campaign", "Status", "Objective", "Spend", "Impressions", "Clicks", "Conv", "CTR", "CPC", "CPA", "Conv Rate"],
        [[str(i), c["name"], c["status"], c["objective"], fmt_sar(c["spend"]), fmt_num(c["impressions"]), fmt_num(c["clicks"]),
          fmt_num(c["conversions"]), fmt_pct(c["ctr"], is_tiktok_api_value=True), fmt_sar(c["cpc"]), fmt_sar(c["cpconv"]),
          fmt_pct(c["conversions"] / c["clicks"] if c["clicks"] else 0)]
         for i, c in enumerate(tiktok["top_campaigns"][:10], 1)]
    ))

    html_parts.append("""  <h3>Best Campaigns by CPA</h3>
  """)
    html_parts.append(render_table(
        ["Rank", "Campaign", "Spend", "Conversions", "CPA", "CTR", "Completion Rate"],
        [[str(i), c["name"], fmt_sar(c["spend"]), fmt_num(c["conversions"]), fmt_sar(c["cpconv"]),
          fmt_pct(c["ctr"], is_tiktok_api_value=True), fmt_pct(c["completion_rate"])]
         for i, c in enumerate(tiktok["best_cpa_campaigns"], 1)]
    ))

    html_parts.append("""  <h3>Worst Campaigns by CPA</h3>
  """)
    html_parts.append(render_table(
        ["Rank", "Campaign", "Spend", "Conversions", "CPA", "CTR", "Completion Rate"],
        [[str(i), c["name"], fmt_sar(c["spend"]), fmt_num(c["conversions"]), fmt_sar(c["cpconv"]),
          fmt_pct(c["ctr"], is_tiktok_api_value=True), fmt_pct(c["completion_rate"])]
         for i, c in enumerate(tiktok["worst_cpa_campaigns"], 1)]
    ))

    html_parts.append("""  <h3>Top Ad Groups by Spend</h3>
  """)
    html_parts.append(render_table(
        ["Rank", "Ad Group", "Campaign", "Spend", "Impressions", "Clicks", "Conv", "CPA", "Completion"],
        [[str(i), ag["name"], ag["campaign_name"], fmt_sar(ag["spend"]), fmt_num(ag["impressions"]), fmt_num(ag["clicks"]),
          fmt_num(ag["conversions"]), fmt_sar(ag["cpconv"]), fmt_pct(ag["completion_rate"])]
         for i, ag in enumerate(tiktok["top_adgroups"], 1)]
    ))

    html_parts.append("""  <h3>Top Ads / Creatives by Spend</h3>
  """)
    html_parts.append(render_table(
        ["Rank", "Ad Name", "Campaign", "Spend", "Impressions", "Clicks", "Conv", "CTR", "Ad Text"],
        [[str(i), a["name"], a["campaign_name"], fmt_sar(a["spend"]), fmt_num(a["impressions"]), fmt_num(a["clicks"]),
          fmt_num(a["conversions"]), fmt_pct(a["ctr"], is_tiktok_api_value=True), (a["text"] or "")[:45]]
         for i, a in enumerate(tiktok["top_ads"], 1)]
    ))

    html_parts.append("""  <h3>Best Ads by CTR</h3>
  """)
    html_parts.append(render_table(
        ["Rank", "Ad Name", "Impressions", "Clicks", "CTR", "Spend", "Conversions"],
        [[str(i), a["name"], fmt_num(a["impressions"]), fmt_num(a["clicks"]), fmt_pct(a["ctr"], is_tiktok_api_value=True),
          fmt_sar(a["spend"]), fmt_num(a["conversions"])]
         for i, a in enumerate(tiktok["best_ads_by_ctr"], 1)]
    ))

    html_parts.append("""  <h3>Daily Spend & Conversions (Last 30 Days)</h3>
  <div class="chart-container"><canvas id="tiktokDailyChart"></canvas></div>

  <h3>Monthly Seasonality & Day-of-Week</h3>
  <div class="chart-row">
    <div class="chart-container"><canvas id="tiktokMonthlyChart"></canvas></div>
    <div class="chart-container"><canvas id="tiktokDowChart"></canvas></div>
  </div>

  <h3>Top Days by Spend</h3>
  """)
    html_parts.append(render_table(
        ["Rank", "Date", "Spend", "Conversions", "CPA"],
        [[str(i), d["day"], fmt_sar(d["spend"]), fmt_num(d["conversions"]),
          fmt_sar(d["spend"] / d["conversions"] if d["conversions"] else 0)]
         for i, d in enumerate(tiktok["top_days"], 1)]
    ))

    html_parts.append("""  <h3>Day-of-Week Performance</h3>
  """)
    html_parts.append(render_table(
        ["Day", "Spend", "Impressions", "Clicks", "Conversions", "CTR", "CPA"],
        [[r["day"], fmt_sar(r["spend"]), fmt_num(r["impressions"]), fmt_num(r["clicks"]), fmt_num(r["conversions"]),
          fmt_pct(r["ctr"]), fmt_sar(r["cpa"] if r["conversions"] else 0)]
         for r in tiktok["dow_rows"]]
    ))

    html_parts.append("""  <h3>Inactive Campaigns</h3>
  """)
    if tiktok["inactive_campaigns"]:
        html_parts.append(render_table(
            ["Campaign", "Status", "Created"],
            [[c["campaign_name"], c["operation_status"], c.get("create_time", "N/A")] for c in tiktok["inactive_campaigns"]]
        ))
    else:
        html_parts.append("<p>All campaigns are active.</p>")
    html_parts.append("</div>")

    # META SECTION
    if meta:
        html_parts.append("""<div class="section">
  <h2><span class="platform-badge badge-meta">Meta</span> Meta Ads Audit</h2>
  <p><strong>Account:</strong> """)
        html_parts.append(meta["account"].get("name", "Unknown"))
        html_parts.append(""" · <strong>Currency:</strong> """)
        html_parts.append(meta["account"].get("currency", "SAR"))
        html_parts.append(""" · <strong>Timezone:</strong> """)
        html_parts.append(meta["account"].get("timezone_name", "Unknown"))
        html_parts.append(""" · <strong>Status:</strong> """)
        html_parts.append("Active" if meta["account"].get("account_status") == 1 else "Inactive")
        html_parts.append("""</p>
  <div class="grid">
    <div class="metric-card meta"><div class="label">Spend (Lifetime)</div><div class="value">""")
        html_parts.append(fmt_sar(meta["total_spend"]))
        html_parts.append("""</div></div>
    <div class="metric-card meta"><div class="label">Impressions</div><div class="value">""")
        html_parts.append(fmt_num(meta["total_impressions"]))
        html_parts.append("""</div></div>
    <div class="metric-card meta"><div class="label">Clicks</div><div class="value">""")
        html_parts.append(fmt_num(meta["total_clicks"]))
        html_parts.append("""</div></div>
    <div class="metric-card meta"><div class="label">Conversions</div><div class="value">""")
        html_parts.append(fmt_num(meta["total_conversions"]))
        html_parts.append("""</div></div>
    <div class="metric-card meta"><div class="label">CTR</div><div class="value">""")
        html_parts.append(fmt_pct(meta["total_clicks"] / meta["total_impressions"] if meta["total_impressions"] else 0))
        html_parts.append("""</div></div>
    <div class="metric-card meta"><div class="label">CPA</div><div class="value">""")
        html_parts.append(fmt_sar(meta["total_spend"] / meta["total_conversions"] if meta["total_conversions"] else 0))
        html_parts.append("""</div></div>
    <div class="metric-card meta"><div class="label">Active / Total</div><div class="value">""")
        html_parts.append(f"{meta['active_campaigns']} / {meta['total_campaigns']}")
        html_parts.append("""</div></div>
    <div class="metric-card meta"><div class="label">Account Balance</div><div class="value">""")
        html_parts.append(fmt_sar(meta["account"].get("balance", 0)))
        html_parts.append("""</div></div>
  </div>

  <h3>Top Campaigns by Spend</h3>
  """)
        html_parts.append(render_table(
            ["Rank", "Campaign", "Status", "Objective", "Spend", "Impressions", "Clicks", "Conv", "CTR", "CPC", "CPA", "Conv Rate"],
            [[str(i), c["name"], c["status"], c["objective"], fmt_sar(c["spend"]), fmt_num(c["impressions"]), fmt_num(c["clicks"]),
              fmt_num(c["conversions"]), fmt_pct(c["ctr"]), fmt_sar(c["cpc"]), fmt_sar(c["cpa"]), fmt_pct(c["conv_rate"])]
             for i, c in enumerate(meta["top_campaigns"], 1)]
        ))

        html_parts.append("""  <h3>Best Campaigns by CPA</h3>
  """)
        html_parts.append(render_table(
            ["Rank", "Campaign", "Spend", "Conversions", "CPA", "CTR", "Conv Rate"],
            [[str(i), c["name"], fmt_sar(c["spend"]), fmt_num(c["conversions"]), fmt_sar(c["cpa"]),
              fmt_pct(c["ctr"]), fmt_pct(c["conv_rate"])] for i, c in enumerate(meta["best_cpa_campaigns"], 1)]
        ))

        html_parts.append("""  <h3>Worst Campaigns by CPA</h3>
  """)
        html_parts.append(render_table(
            ["Rank", "Campaign", "Spend", "Conversions", "CPA", "CTR", "Conv Rate"],
            [[str(i), c["name"], fmt_sar(c["spend"]), fmt_num(c["conversions"]), fmt_sar(c["cpa"]),
              fmt_pct(c["ctr"]), fmt_pct(c["conv_rate"])] for i, c in enumerate(meta["worst_cpa_campaigns"], 1)]
        ))

        html_parts.append("""  <h3>Campaign Spend Distribution</h3>
  <div class="chart-container"><canvas id="metaCampaignChart"></canvas></div>

  <h3>Ad Set Targeting Summary</h3>
  """)
        html_parts.append(render_table(
            ["Ad Set", "Campaign", "Status", "Daily Budget", "Age", "Countries", "Top Interests"],
            [[ag["name"], ag["campaign_id"], ag["status"], fmt_sar(ag["budget"]),
              f"{ag['age_min']}-{ag['age_max']}" if ag["age_min"] else "-",
              ag["countries"], ag["interests"]] for ag in meta["adset_rows"]]
        ))

        html_parts.append("""  <h3>Paused Campaigns</h3>
  """)
        if meta["paused_campaigns"]:
            html_parts.append(render_table(
                ["Campaign", "Objective", "Daily Budget", "Start Time"],
                [[c["name"], c["objective"], fmt_sar(float(c.get("daily_budget", 0) or 0) / 100), c.get("start_time", "N/A")] for c in meta["paused_campaigns"]]
            ))
        else:
            html_parts.append("<p>All campaigns are active.</p>")
        html_parts.append("</div>")

    # GOOGLE ADS SECTION
    if google:
        html_parts.append("""<div class="section">
  <h2><span class="platform-badge badge-google">Google</span> Google Ads Audit</h2>
  <p><strong>Account:</strong> """)
        html_parts.append(google["account"].get("name", "Unknown"))
        html_parts.append(""" · <strong>Currency:</strong> """)
        html_parts.append(google["account"].get("currency_code", "SAR"))
        html_parts.append("""</p>
  <div class="grid">
    <div class="metric-card"><div class="label">Spend (All Time)</div><div class="value">""")
        html_parts.append(fmt_sar(google["total_spend"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Impressions</div><div class="value">""")
        html_parts.append(fmt_num(google["total_impressions"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Clicks</div><div class="value">""")
        html_parts.append(fmt_num(google["total_clicks"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Conversions</div><div class="value">""")
        html_parts.append(fmt_num(google["total_conversions"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">CTR</div><div class="value">""")
        html_parts.append(fmt_pct(google["total_clicks"] / google["total_impressions"] if google["total_impressions"] else 0))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">CPA</div><div class="value">""")
        html_parts.append(fmt_sar(google["total_spend"] / google["total_conversions"] if google["total_conversions"] else 0))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">ROAS</div><div class="value">""")
        html_parts.append(f"{google['total_conversion_value'] / google['total_spend']:.2f}x" if google["total_spend"] else "-")
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Active / Total</div><div class="value">""")
        html_parts.append(f"{google['active_campaigns']} / {google['total_campaigns']}")
        html_parts.append("""</div></div>
  </div>

  <h3>Top Campaigns by Spend</h3>
  """)
        html_parts.append(render_table(
            ["Rank", "Campaign", "Spend", "Impressions", "Clicks", "Conv", "Conv Value", "CTR", "CPC", "CPA", "ROAS", "Conv Rate"],
            [[str(i), c["name"], fmt_sar(c["spend"]), fmt_num(c["impressions"]), fmt_num(c["clicks"]),
              fmt_num(c["conversions"]), fmt_sar(c["conversions_value"]), fmt_pct(c["ctr"]), fmt_sar(c["cpc"]),
              fmt_sar(c["cpa"]), f"{c['roas']:.2f}x", fmt_pct(c["conv_rate"])] for i, c in enumerate(google["top_campaigns"], 1)]
        ))

        html_parts.append("""  <h3>Best Campaigns by CPA</h3>
  """)
        html_parts.append(render_table(
            ["Rank", "Campaign", "Spend", "Conversions", "CPA", "ROAS", "Conv Rate"],
            [[str(i), c["name"], fmt_sar(c["spend"]), fmt_num(c["conversions"]), fmt_sar(c["cpa"]),
              f"{c['roas']:.2f}x", fmt_pct(c["conv_rate"])] for i, c in enumerate(google["best_cpa_campaigns"], 1)]
        ))

        html_parts.append("""  <h3>Ad Group Performance</h3>
  """)
        html_parts.append(render_table(
            ["Rank", "Ad Group", "Campaign", "Spend", "Clicks", "Conv", "CPA", "CTR", "Conv Rate"],
            [[str(i), ag["name"], ag["campaign"], fmt_sar(ag["spend"]), fmt_num(ag["clicks"]), fmt_num(ag["conversions"]),
              fmt_sar(ag["cpa"]), fmt_pct(ag["ctr"]), fmt_pct(ag["conv_rate"])] for i, ag in enumerate(google["top_adgroups"], 1)]
        ))

        html_parts.append("""  <h3>Monthly Trends & Day-of-Week CPA</h3>
  <div class="chart-row">
    <div class="chart-container"><canvas id="googleMonthlyChart"></canvas></div>
    <div class="chart-container"><canvas id="googleDowChart"></canvas></div>
  </div>

  <h3>Device Breakdown</h3>
  """)
        html_parts.append(render_table(
            ["Device", "Spend", "Impressions", "Clicks", "Conversions", "CTR", "CPA", "ROAS", "Conv Rate"],
            [[r["device"].title(), fmt_sar(r["spend"]), fmt_num(r["impressions"]), fmt_num(r["clicks"]), fmt_num(r["conversions"]),
              fmt_pct(r["ctr"]), fmt_sar(r["cpa"]), f"{r['roas']:.2f}x", fmt_pct(r["conv_rate"])] for r in google["device_rows"]]
        ))

        html_parts.append("""  <h3>Day-of-Week Performance</h3>
  """)
        html_parts.append(render_table(
            ["Day", "Spend", "Impressions", "Clicks", "Conversions", "CTR", "CPA", "ROAS", "Conv Rate"],
            [[r["day"], fmt_sar(r["spend"]), fmt_num(r["impressions"]), fmt_num(r["clicks"]), fmt_num(r["conversions"]),
              fmt_pct(r["ctr"]), fmt_sar(r["cpa"]), f"{r['roas']:.2f}x", fmt_pct(r["conv_rate"])] for r in google["dow_rows"]]
        ))

        html_parts.append("""  <h3>Responsive Search Ads</h3>
  """)
        for i, a in enumerate(google["ads"], 1):
            html_parts.append(f"""  <div class="note" style="margin-bottom:1rem">
    <strong>Ad {i}:</strong> {a['id']} ({a['status']})<br>
    <strong>Campaign:</strong> {a.get('campaign_name', '')}<br>
    <strong>Headlines:</strong> {', '.join(a.get('headlines', [])[:10])}<br>
    <strong>Descriptions:</strong> {', '.join(a.get('descriptions', [])[:3])}
  </div>
""")

        if google["inactive_campaigns"]:
            html_parts.append("""  <h3>Inactive Campaigns</h3>
  """)
            html_parts.append(render_table(
                ["Campaign", "Status", "Type", "Budget"],
                [[c["name"], c["status"], c["type"], fmt_sar(c.get("budget", 0))] for c in google["inactive_campaigns"]]
            ))
        html_parts.append("</div>")

    # KEY INSIGHTS
    html_parts.append("""<div class="section">
  <h2>Key Insights</h2>
""")
    insights = []
    if tiktok["top_campaigns"]:
        best = tiktok["top_campaigns"][0]
        insights.append(("success", "Top TikTok Spender", f"{best['name']} spent {fmt_sar(best['spend'])} with CPA {fmt_sar(best['cpconv'])} and CTR {fmt_pct(best['ctr'], is_tiktok_api_value=True)}."))
    if tiktok["best_cpa_campaigns"]:
        cheap = tiktok["best_cpa_campaigns"][0]
        insights.append(("success", "Best TikTok CPA", f"{cheap['name']} has the lowest CPA at {fmt_sar(cheap['cpconv'])} — consider scaling."))
    if tiktok["worst_cpa_campaigns"]:
        worst = tiktok["worst_cpa_campaigns"][0]
        insights.append(("danger", "Worst TikTok CPA", f"{worst['name']} has the highest CPA at {fmt_sar(worst['cpconv'])} — review targeting and creative."))
    if tiktok["video_funnel"]["plays"] > 0:
        completion = tiktok["video_funnel"]["p100"] / tiktok["video_funnel"]["plays"]
        insights.append(("warning" if completion < 0.05 else "success", "TikTok Video Completion", f"{fmt_pct(completion)} of viewers watch to 100%. {'Strong retention' if completion >= 0.05 else 'Improve hook and pacing to boost retention'}."))

    if meta:
        insights.append(("meta", "Meta Account Health", f"Account '{meta['account'].get('name')}' has spent {fmt_sar(meta['total_spend'])} with {fmt_num(meta['total_conversions'])} conversions (CPA {fmt_sar(meta['total_spend'] / meta['total_conversions'] if meta['total_conversions'] else 0)}). Balance remaining: {fmt_sar(meta['account'].get('balance', 0))}."))
        if meta["top_campaigns"]:
            best_m = meta["top_campaigns"][0]
            insights.append(("meta", "Top Meta Spender", f"{best_m['name']} is the highest spender at {fmt_sar(best_m['spend'])} with CTR {fmt_pct(best_m['ctr'])}."))
        if meta["best_cpa_campaigns"]:
            cheap_m = meta["best_cpa_campaigns"][0]
            insights.append(("meta", "Best Meta CPA", f"{cheap_m['name']} has the lowest CPA at {fmt_sar(cheap_m['cpa'])} — scale this campaign."))
        if meta["paused_campaigns"]:
            insights.append(("warning", "Meta Campaigns Paused", f"{len(meta['paused_campaigns'])} of {meta['total_campaigns']} Meta campaigns are paused."))

    if google:
        if google["top_campaigns"]:
            best_g = google["top_campaigns"][0]
            insights.append(("success", "Top Google Spender", f"{best_g['name']} spent {fmt_sar(best_g['spend'])} with CPA {fmt_sar(best_g['cpa'])} and ROAS {best_g['roas']:.2f}x."))
        if google["device_rows"]:
            best_device = max(google["device_rows"], key=lambda x: x["conv_rate"])
            insights.append(("success", "Best Google Device", f"{best_device['device'].title()} has the highest conversion rate ({fmt_pct(best_device['conv_rate'])})."))
        if google["total_spend"] > 0:
            roas = google['total_conversion_value'] / google['total_spend']
            insights.append(("danger" if roas < 1 else "warning", "Google ROAS", f"Overall ROAS is {roas:.2f}x. {'Revenue does not cover ad spend.' if roas < 1 else 'Monitor conversion value quality.'}"))

    for cls, title, body in insights:
        html_parts.append(f"""  <div class="insight-card {cls}">
    <div class="title">{title}</div>
    <div class="body">{body}</div>
  </div>
""")
    html_parts.append("</div>")

    # RECOMMENDATIONS
    html_parts.append("""<div class="section">
  <h2>Strategic Recommendations</h2>
  <ul class="recommendations">
""")
    recs = []
    if tiktok["total_conversions"] > 0:
        avg_cpconv = tiktok["total_spend"] / tiktok["total_conversions"]
        recs.append(("warning", f"TikTok average CPA is <strong>SAR {avg_cpconv:,.2f}</strong>. Benchmark against lead value; reduce bids on ad groups with CPA > 30% of LTV."))
    low_ctr = [c for c in tiktok["top_campaigns"] if c["ctr"] < 0.5 and c["impressions"] > 1000]
    if low_ctr:
        recs.append(("warning", f"<strong>{len(low_ctr)} TikTok campaigns</strong> have CTR below 0.50%. Refresh creatives and test new hooks/thumbnails."))
    if tiktok["inactive_campaigns"]:
        recs.append(("danger", f"<strong>{len(tiktok['inactive_campaigns'])} TikTok campaigns</strong> are inactive. Review whether to re-enable or retire them."))
    if tiktok["video_funnel"]["plays"] > 0:
        completion = tiktok["video_funnel"]["p100"] / tiktok["video_funnel"]["plays"]
        if completion < 0.05:
            recs.append(("warning", f"TikTok video completion is only <strong>{fmt_pct(completion)}</strong>. Test shorter videos or stronger hooks in the first 3 seconds."))
    if tiktok["top_months"]:
        recs.append(("success", f"Peak TikTok spend month was <strong>{tiktok['top_months'][0]['month']}</strong> ({fmt_sar(tiktok['top_months'][0]['spend'])}). Plan budget increases ahead of similar seasonal windows."))
    recs.append(("success", "Consolidate TikTok budget into the top 3 campaigns by conversion volume to improve algorithm learning and efficiency."))

    if meta:
        if meta["total_conversions"] > 0:
            recs.append(("meta", f"Meta CPA is <strong>SAR {meta['total_spend'] / meta['total_conversions']:,.2f}</strong>. Compare lead quality vs TikTok/Google and reallocate budget to the best CPA campaign: <strong>{meta['best_cpa_campaigns'][0]['name'] if meta['best_cpa_campaigns'] else 'N/A'}</strong>."))
        if meta["paused_campaigns"]:
            recs.append(("warning", f"<strong>{len(meta['paused_campaigns'])} Meta campaigns</strong> are paused. If they had good CPA, reactivate them; if poor, keep paused and reallocate budget."))
        if float(meta["account"].get("balance", 0) or 0) < 500:
            recs.append(("danger", f"Meta account balance is low (<strong>{fmt_sar(meta['account'].get('balance', 0))}</strong>). Top up soon to avoid delivery interruptions."))
        recs.append(("meta", "Test Meta Advantage+ Audiences and broader targeting on the best-performing campaign to scale efficiently."))

    if google:
        if google["total_conversions"] > 0:
            recs.append(("warning", f"Google Ads CPA is <strong>{fmt_sar(google['total_spend'] / google['total_conversions'])}</strong>. Compare quality of Google leads vs TikTok/Meta leads."))
        if google["total_spend"] > 0:
            roas = google['total_conversion_value'] / google['total_spend']
            recs.append(("danger" if roas < 1 else "warning", f"Google Ads ROAS is <strong>{roas:.2f}x</strong>. {'Revenue does not cover ad spend — review keywords and landing pages.' if roas < 1 else 'Monitor conversion value and optimize for higher-value actions.'}"))
        if google["inactive_campaigns"]:
            recs.append(("warning", f"<strong>{len(google['inactive_campaigns'])} Google Ads campaign</strong> is paused. Evaluate if reactivation makes sense."))
        recs.append(("success", "Google Ads has only 2 campaigns with small budgets. Consider scaling the better performer after reviewing conversion quality."))
        recs.append(("success", "Add more RSA headlines and descriptions to improve ad strength and auction coverage."))

    for cls, text in recs:
        html_parts.append(f"    <li class='{cls}'>{text}</li>\n")

    html_parts.append("""  </ul>
</div>
""")

    html_parts.append("""<footer>
  Generated by automated audit pipeline · Raw data in <code>raw/</code> folder
</footer>

<script>
""")
    html_parts.append(f"""
const tiktokDailyCtx = document.getElementById('tiktokDailyChart').getContext('2d');
new Chart(tiktokDailyCtx, {{
  type: 'bar',
  data: {{
    labels: {json.dumps(tiktok_daily_labels)},
    datasets: [
      {{
        label: 'Spend (SAR)',
        data: {json.dumps(tiktok_daily_spend)},
        backgroundColor: 'rgba(56, 189, 248, 0.7)',
        yAxisID: 'y'
      }},
      {{
        label: 'Conversions',
        data: {json.dumps(tiktok_daily_conv)},
        type: 'line',
        borderColor: 'rgba(168, 85, 247, 1)',
        backgroundColor: 'rgba(168, 85, 247, 0.2)',
        yAxisID: 'y1',
        tension: 0.3
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    scales: {{
      y: {{ type: 'linear', display: true, position: 'left', grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
      y1: {{ type: 'linear', display: true, position: 'right', grid: {{ drawOnChartArea: false }} }},
      x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
    }},
    plugins: {{ legend: {{ labels: {{ color: '#f8fafc' }} }} }}
  }}
}});

const tiktokMonthlyCtx = document.getElementById('tiktokMonthlyChart').getContext('2d');
new Chart(tiktokMonthlyCtx, {{
  type: 'bar',
  data: {{
    labels: {json.dumps(tiktok_month_labels)},
    datasets: [{{
      label: 'Spend (SAR)',
      data: {json.dumps(tiktok_month_spend)},
      backgroundColor: 'rgba(56, 189, 248, 0.7)'
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    scales: {{ y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }}, x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }} }},
    plugins: {{ legend: {{ labels: {{ color: '#f8fafc' }} }} }}
  }}
}});

const tiktokDowCtx = document.getElementById('tiktokDowChart').getContext('2d');
new Chart(tiktokDowCtx, {{
  type: 'bar',
  data: {{
    labels: {json.dumps(tiktok_dow_labels)},
    datasets: [{{
      label: 'Spend (SAR)',
      data: {json.dumps(tiktok_dow_spend)},
      backgroundColor: 'rgba(168, 85, 247, 0.7)'
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    scales: {{ y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }}, x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }} }},
    plugins: {{ legend: {{ labels: {{ color: '#f8fafc' }} }} }}
  }}
}});
""")

    if meta:
        html_parts.append(f"""
const metaCampaignCtx = document.getElementById('metaCampaignChart').getContext('2d');
new Chart(metaCampaignCtx, {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(meta_month_labels[:10])},
    datasets: [{{
      data: {json.dumps(meta_month_spend[:10])},
      backgroundColor: [
        'rgba(244, 63, 94, 0.8)',
        'rgba(56, 189, 248, 0.8)',
        'rgba(34, 197, 94, 0.8)',
        'rgba(245, 158, 11, 0.8)',
        'rgba(168, 85, 247, 0.8)',
        'rgba(236, 72, 153, 0.8)',
        'rgba(99, 102, 241, 0.8)',
        'rgba(20, 184, 166, 0.8)',
        'rgba(251, 146, 60, 0.8)',
        'rgba(139, 92, 246, 0.8)'
      ]
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'right', labels: {{ color: '#f8fafc' }} }} }}
  }}
}});
""")

    if google:
        html_parts.append(f"""
const googleMonthlyCtx = document.getElementById('googleMonthlyChart').getContext('2d');
new Chart(googleMonthlyCtx, {{
  type: 'bar',
  data: {{
    labels: {json.dumps(google_month_labels)},
    datasets: [{{
      label: 'Spend (SAR)',
      data: {json.dumps(google_month_spend)},
      backgroundColor: 'rgba(34, 197, 94, 0.7)'
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    scales: {{ y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }}, x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }} }},
    plugins: {{ legend: {{ labels: {{ color: '#f8fafc' }} }} }}
  }}
}});

const googleDowCtx = document.getElementById('googleDowChart').getContext('2d');
new Chart(googleDowCtx, {{
  type: 'line',
  data: {{
    labels: {json.dumps(google_dow_labels)},
    datasets: [{{
      label: 'CPA (SAR)',
      data: {json.dumps(google_dow_cpa)},
      borderColor: 'rgba(34, 197, 94, 1)',
      backgroundColor: 'rgba(34, 197, 94, 0.2)',
      tension: 0.3,
      fill: true
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    scales: {{ y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }}, x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }} }},
    plugins: {{ legend: {{ labels: {{ color: '#f8fafc' }} }} }}
  }}
}});
""")

    html_parts.append("""
</script>
</body>
</html>
""")

    (OUT_DIR / "index.html").write_text("".join(html_parts), encoding="utf-8")
    print(f"Enhanced HTML report written to {OUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
