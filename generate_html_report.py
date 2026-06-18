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
        "dow_rows": dow_rows, "top_months": top_months,
        "video_funnel": {"plays": total_video_plays, "p25": total_p25, "p50": total_p50, "p75": total_p75, "p100": total_p100},
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

    return {
        "account": account, "total_campaigns": len(campaigns),
        "active_campaigns": len(active_campaigns), "paused_campaigns": paused_campaigns,
        "total_adsets": len(adsets), "total_spend": total_spend,
        "total_impressions": total_impressions, "total_clicks": total_clicks,
        "total_conversions": total_conversions, "total_reach": total_reach,
        "top_campaigns": top_campaigns, "best_cpa_campaigns": best_cpa, "worst_cpa_campaigns": worst_cpa,
        "adset_rows": adset_rows,
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

    return {
        "account": account, "total_campaigns": len(campaigns),
        "active_campaigns": len(active_campaigns), "inactive_campaigns": inactive_campaigns,
        "total_ads": len(ads), "ads": ads, "total_spend": total_spend,
        "total_impressions": total_impressions, "total_clicks": total_clicks,
        "total_conversions": total_conversions, "total_conversion_value": total_conversion_value,
        "top_campaigns": top_campaigns, "best_cpa_campaigns": best_cpa,
        "top_adgroups": top_adgroups, "top_months": top_months,
        "device_rows": device_rows, "dow_rows": dow_rows,
    }


# ===================== HTML RENDERING =====================

def escape_js(s):
    return json.dumps(str(s))


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
    .platform-card .platform-icon {{ width: 28px; height: 28px; }}
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
    "tiktok": "https://upload.wikimedia.org/wikipedia/en/a/a9/TikTok_logo.svg",
    "meta": "https://upload.wikimedia.org/wikipedia/commons/b/b8/2021_Facebook_icon.svg",
    "google": "https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg",
}


def platform_icon(platform):
    url = ICONS.get(platform, "")
    return f'<img src="{url}" class="platform-icon" alt="{platform.title()}">' if url else ""


def overview_page(tiktok, meta, google, logo_b64):
    total_spend = tiktok["total_spend"] + (meta["total_spend"] if meta else 0) + (google["total_spend"] if google else 0)
    total_conversions = tiktok["total_conversions"] + (meta["total_conversions"] if meta else 0) + (google["total_conversions"] if google else 0)
    overall_cpa = safe_div(total_spend, total_conversions, 0)

    cards = []
    cards.append(f"""
    <div class="platform-card tiktok">
      <h3>{platform_icon('tiktok')} TikTok</h3>
      <div class="metric-row"><span>Spend</span><span>{fmt_sar(tiktok['total_spend'])}</span></div>
      <div class="metric-row"><span>Conversions</span><span>{fmt_num(tiktok['total_conversions'])}</span></div>
      <div class="metric-row"><span>Campaigns</span><span>{tiktok['total_campaigns']} ({tiktok['active_campaigns']} active)</span></div>
      <div class="metric-row"><span>CTR</span><span>{fmt_pct(safe_div(tiktok['total_clicks'], tiktok['total_impressions']), True)}</span></div>
      <a href="tiktok.html">View TikTok report &rarr;</a>
    </div>""")
    if meta:
        cards.append(f"""
    <div class="platform-card meta">
      <h3>{platform_icon('meta')} Meta Ads</h3>
      <div class="metric-row"><span>Spend</span><span>{fmt_sar(meta['total_spend'])}</span></div>
      <div class="metric-row"><span>Conversions</span><span>{fmt_num(meta['total_conversions'])}</span></div>
      <div class="metric-row"><span>Campaigns</span><span>{meta['total_campaigns']} ({meta['active_campaigns']} active)</span></div>
      <div class="metric-row"><span>CTR</span><span>{fmt_pct(safe_div(meta['total_clicks'], meta['total_impressions']))}</span></div>
      <a href="meta.html">View Meta report &rarr;</a>
    </div>""")
    if google:
        cards.append(f"""
    <div class="platform-card google">
      <h3>{platform_icon('google')} Google Ads</h3>
      <div class="metric-row"><span>Spend</span><span>{fmt_sar(google['total_spend'])}</span></div>
      <div class="metric-row"><span>Conversions</span><span>{fmt_num(google['total_conversions'])}</span></div>
      <div class="metric-row"><span>Campaigns</span><span>{google['total_campaigns']} ({google['active_campaigns']} active)</span></div>
      <div class="metric-row"><span>CTR</span><span>{fmt_pct(safe_div(google['total_clicks'], google['total_impressions']))}</span></div>
      <a href="google.html">View Google report &rarr;</a>
    </div>""")

    platform_labels = ["TikTok"]
    platform_spend = [round(tiktok["total_spend"], 2)]
    platform_conv = [tiktok["total_conversions"]]
    if meta:
        platform_labels.append("Meta")
        platform_spend.append(round(meta["total_spend"], 2))
        platform_conv.append(meta["total_conversions"])
    if google:
        platform_labels.append("Google")
        platform_spend.append(round(google["total_spend"], 2))
        platform_conv.append(google["total_conversions"])

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

    body = f"""
{render_nav('overview', logo_b64)}
<div class="hero">
  <h1>White Car Cross-Platform Ads Audit</h1>
  <p>Unified overview of TikTok, Meta, and Google Ads performance</p>
</div>
<div class="container">
  <div class="kpis">
    {kpi_card('Total Spend', fmt_sar(total_spend))}
    {kpi_card('Total Conversions', fmt_num(total_conversions))}
    {kpi_card('Blended CPA', fmt_sar(overall_cpa))}
    {kpi_card('Platforms', sum([1, bool(meta), bool(google)]))}
  </div>

  <h2 class="section-title">Platform Breakdown</h2>
  <div class="platform-grid">
    {"".join(cards)}
  </div>

  <div class="grid-2">
    {render_chart_card('Spend by Platform', 'spendByPlatformChart')}
    {render_chart_card('Conversions by Platform', 'convByPlatformChart')}
  </div>

  <h2 class="section-title">Top Spend Campaigns by Platform</h2>
  <div class="grid-3">
    {render_simple_table('TikTok Top Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpconv'] if c['conversions'] else 0)] for c in tiktok['top_campaigns'][:5]])}
    {render_simple_table('Meta Top Campaigns', ['Campaign', 'Spend', 'Leads', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in (meta['top_campaigns'][:5] if meta else [])]) if meta else ''}
    {render_simple_table('Google Top Campaigns', ['Campaign', 'Spend', 'Conv.', 'ROAS'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), f"{c['roas']:.2f}x"] for c in (google['top_campaigns'][:5] if google else [])]) if google else ''}
  </div>

  <h2 class="section-title">Recommendations</h2>
  {recs_html}
</div>
<div class="footer">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<script>
const platformLabels = {json.dumps(platform_labels)};
const platformSpend = {json.dumps(platform_spend)};
const platformConv = {json.dumps(platform_conv)};
const palette = ['#000000', '#1877f2', '#4285f4'];
new Chart(document.getElementById('spendByPlatformChart'), {{type:'doughnut', data:{{labels:platformLabels, datasets:[{{data:platformSpend, backgroundColor:palette.slice(0, platformLabels.length), borderWidth:0}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'bottom'}}}}}}}});
new Chart(document.getElementById('convByPlatformChart'), {{type:'bar', data:{{labels:platformLabels, datasets:[{{label:'Conversions', data:platformConv, backgroundColor:palette.slice(0, platformLabels.length), borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
</script>
</body></html>
"""
    return common_head("White Car Ads Audit | Overview", "overview") + body


def tiktok_page(data, logo_b64):
    daily_labels = [r["day"] for r in data["daily_rows"]]
    daily_spend = [r["spend"] for r in data["daily_rows"]]
    daily_conv = [r["conversions"] for r in data["daily_rows"]]
    dow_labels = [r["day"] for r in data["dow_rows"]]
    dow_spend = [r["spend"] for r in data["dow_rows"]]
    funnel = data["video_funnel"]
    month_labels = [m["month"] for m in data["top_months"]]
    month_spend = [m["spend"] for m in data["top_months"]]

    body = f"""
{render_nav('tiktok', logo_b64)}
<div class="hero">
  <h1>{platform_icon('tiktok')} TikTok Ads</h1>
  <p>Advertiser: {data['account'].get('name', 'Whitecarx1')} (ID {data['account'].get('advertiser_id', '')})</p>
</div>
<div class="container">
  {render_filters('tiktok')}
  <div class="kpis">
    {kpi_card('Spend', fmt_sar(data['total_spend']))}
    {kpi_card('Conversions', fmt_num(data['total_conversions']))}
    {kpi_card('Impressions', fmt_num(data['total_impressions']))}
    {kpi_card('Clicks', fmt_num(data['total_clicks']))}
    {kpi_card('CTR', fmt_pct(safe_div(data['total_clicks'], data['total_impressions']), True), sub=True)}
    {kpi_card('CPA', fmt_sar(safe_div(data['total_spend'], data['total_conversions'], 0)), sub=True)}
    {kpi_card('Campaigns', f"{data['total_campaigns']} ({data['active_campaigns']} active)", sub=True)}
  </div>

  {render_tiktok_campaigns_table(data['top_campaigns'])}

  <div class="grid-2">
    {render_chart_card('Daily Spend', 'ttDailySpendChart')}
    {render_chart_card('Daily Conversions', 'ttDailyConvChart')}
  </div>

  <h2 class="section-title">Performance Deep Dive</h2>
  <div class="grid-3">
    {render_chart_card('Spend by Day of Week', 'ttDowChart', small=True)}
    {render_chart_card('Monthly Spend', 'ttMonthlyChart', small=True)}
    {render_chart_card('Video Funnel', 'ttFunnelChart', small=True)}
  </div>

  <div class="grid-2">
    {render_simple_table('Top Ad Groups', ['Ad Group', 'Campaign', 'Spend', 'CPA', 'Completion'], [[ag['name'][:38], ag['campaign_name'][:30], fmt_sar(ag['spend']), fmt_sar(ag['cpconv'] if ag['conversions'] else 0), fmt_pct(ag['completion_rate'])] for ag in data['top_adgroups'][:10]])}
    {render_simple_table('Top Ads', ['Ad', 'Campaign', 'Spend', 'CPA', 'CTR'], [[ad['name'][:38], ad['campaign_name'][:30], fmt_sar(ad['spend']), fmt_sar(ad['cpconv'] if ad['conversions'] else 0), fmt_pct(ad['ctr'], True)] for ad in data['top_ads'][:10]])}
  </div>

  <div class="grid-2">
    {render_simple_table('Best CPA Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpconv'])] for c in data['best_cpa_campaigns']])}
    {render_simple_table('Worst CPA Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpconv'])] for c in data['worst_cpa_campaigns']])}
  </div>
</div>
<div class="footer">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<script>
const ttDailyLabels = {json.dumps(daily_labels)};
const ttDailySpend = {json.dumps(daily_spend)};
const ttDailyConv = {json.dumps(daily_conv)};
const ttDowLabels = {json.dumps(dow_labels)};
const ttDowSpend = {json.dumps(dow_spend)};
const ttFunnelLabels = ['Plays', '25%', '50%', '75%', '100%'];
const ttFunnelData = [{funnel['plays']}, {funnel['p25']}, {funnel['p50']}, {funnel['p75']}, {funnel['p100']}];
const ttMonthLabels = {json.dumps(month_labels)};
const ttMonthSpend = {json.dumps(month_spend)};

new Chart(document.getElementById('ttDailySpendChart'), {{type:'line', data:{{labels:ttDailyLabels, datasets:[{{label:'Spend (SAR)', data:ttDailySpend, borderColor:'#000000', backgroundColor:'rgba(0,0,0,0.06)', fill:true, tension:0.3}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('ttDailyConvChart'), {{type:'bar', data:{{labels:ttDailyLabels, datasets:[{{label:'Conversions', data:ttDailyConv, backgroundColor:'#000000', borderRadius:6}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('ttDowChart'), {{type:'bar', data:{{labels:ttDowLabels, datasets:[{{label:'Spend', data:ttDowSpend, backgroundColor:'#000000', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('ttMonthlyChart'), {{type:'bar', data:{{labels:ttMonthLabels, datasets:[{{label:'Spend', data:ttMonthSpend, backgroundColor:'#45a29e', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('ttFunnelChart'), {{type:'bar', data:{{labels:ttFunnelLabels, datasets:[{{label:'Views', data:ttFunnelData, backgroundColor:['#000','#333','#555','#777','#999'], borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
</script>
</body></html>
"""
    return common_head("White Car Ads Audit | TikTok", "tiktok") + body


def meta_page(data, logo_b64):
    top_campaigns = data["top_campaigns"]
    labels = [c["name"][:30] for c in top_campaigns]
    spend = [c["spend"] for c in top_campaigns]
    conv = [c["conversions"] for c in top_campaigns]

    body = f"""
{render_nav('meta', logo_b64)}
<div class="hero">
  <h1>{platform_icon('meta')} Meta Ads</h1>
  <p>Account: {data['account'].get('name', '255')} (ID {data['account'].get('id', '')})</p>
</div>
<div class="container">
  {render_filters('meta')}
  <div class="kpis">
    {kpi_card('Lifetime Spend', fmt_sar(data['total_spend']))}
    {kpi_card('Conversions', fmt_num(data['total_conversions']))}
    {kpi_card('Impressions', fmt_num(data['total_impressions']))}
    {kpi_card('Clicks', fmt_num(data['total_clicks']))}
    {kpi_card('Reach', fmt_num(data['total_reach']), sub=True)}
    {kpi_card('CPA', fmt_sar(safe_div(data['total_spend'], data['total_conversions'], 0)), sub=True)}
    {kpi_card('Campaigns', f"{data['total_campaigns']} ({data['active_campaigns']} active)", sub=True)}
  </div>

  {render_meta_campaigns_table(data['top_campaigns'])}

  <div class="grid-2">
    {render_chart_card('Spend by Campaign', 'metaSpendChart')}
    {render_chart_card('Conversions by Campaign', 'metaConvChart')}
  </div>

  <h2 class="section-title">Targeting Snapshot</h2>
  {render_simple_table('Ad Sets', ['Ad Set', 'Campaign', 'Status', 'Budget', 'Age', 'Countries', 'Interests'], [[ag['name'][:36], ag['campaign_id'][:10], render_status(ag['status']), fmt_sar(ag['budget']), f"{ag['age_min']}-{ag['age_max']}", ag['countries'], ag['interests']] for ag in data['adset_rows'][:15]])}

  <div class="grid-2">
    {render_simple_table('Best CPA Campaigns', ['Campaign', 'Spend', 'Leads', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in data['best_cpa_campaigns']])}
    {render_simple_table('Worst CPA Campaigns', ['Campaign', 'Spend', 'Leads', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in data['worst_cpa_campaigns']])}
  </div>
</div>
<div class="footer">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<script>
const metaLabels = {json.dumps(labels)};
const metaSpend = {json.dumps(spend)};
const metaConv = {json.dumps(conv)};
new Chart(document.getElementById('metaSpendChart'), {{type:'bar', data:{{labels:metaLabels, datasets:[{{label:'Spend (SAR)', data:metaSpend, backgroundColor:'#1877f2', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('metaConvChart'), {{type:'bar', data:{{labels:metaLabels, datasets:[{{label:'Leads', data:metaConv, backgroundColor:'#42b72a', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
</script>
</body></html>
"""
    return common_head("White Car Ads Audit | Meta", "meta") + body


def google_page(data, logo_b64):
    top_campaigns = data["top_campaigns"]
    labels = [c["name"][:30] for c in top_campaigns]
    spend = [c["spend"] for c in top_campaigns]
    conv = [c["conversions"] for c in top_campaigns]
    month_labels = [m["month"] for m in data["top_months"]]
    month_spend = [m["spend"] for m in data["top_months"]]

    body = f"""
{render_nav('google', logo_b64)}
<div class="hero">
  <h1>{platform_icon('google')} Google Ads</h1>
  <p>Account: {data['account'].get('descriptiveName', 'white car')} ({data['account'].get('id', '348-288-3125')})</p>
</div>
<div class="container">
  {render_filters('google')}
  <div class="kpis">
    {kpi_card('Spend', fmt_sar(data['total_spend']))}
    {kpi_card('Conversions', fmt_num(data['total_conversions']))}
    {kpi_card('Impressions', fmt_num(data['total_impressions']))}
    {kpi_card('Clicks', fmt_num(data['total_clicks']))}
    {kpi_card('Conv. Value', fmt_sar(data['total_conversion_value']), sub=True)}
    {kpi_card('ROAS', f"{safe_div(data['total_conversion_value'], data['total_spend'], 0):.2f}x", sub=True)}
    {kpi_card('Campaigns', f"{data['total_campaigns']} ({data['active_campaigns']} active)", sub=True)}
  </div>

  {render_google_campaigns_table(data['top_campaigns'])}

  <div class="grid-2">
    {render_chart_card('Spend by Campaign', 'googleSpendChart')}
    {render_chart_card('Conversions by Campaign', 'googleConvChart')}
  </div>

  <div class="grid-3">
    {render_chart_card('Monthly Spend', 'googleMonthlyChart', small=True)}
    {render_simple_table('Device Breakdown', ['Device', 'Spend', 'Conv.', 'ROAS'], [[d['device'].title(), fmt_sar(d['spend']), fmt_num(d['conversions']), f"{d['roas']:.2f}x"] for d in data['device_rows']])}
    {render_simple_table('Day of Week', ['Day', 'Spend', 'Conv.', 'ROAS'], [[d['day'], fmt_sar(d['spend']), fmt_num(d['conversions']), f"{d['roas']:.2f}x"] for d in data['dow_rows']])}
  </div>

  <h2 class="section-title">Ad Group Insights</h2>
  {render_simple_table('Top Ad Groups', ['Ad Group', 'Campaign', 'Spend', 'Conv.', 'CPA', 'ROAS'], [[ag['name'][:36], ag['campaign'][:30], fmt_sar(ag['spend']), fmt_num(ag['conversions']), fmt_sar(ag['cpa'] if ag['conversions'] else 0), f"{ag['roas']:.2f}x"] for ag in data['top_adgroups'][:15]])}

  {render_simple_table('Best CPA Campaigns', ['Campaign', 'Spend', 'Conv.', 'CPA'], [[c['name'][:40], fmt_sar(c['spend']), fmt_num(c['conversions']), fmt_sar(c['cpa'])] for c in data['best_cpa_campaigns']])}
</div>
<div class="footer">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<script>
const googleLabels = {json.dumps(labels)};
const googleSpend = {json.dumps(spend)};
const googleConv = {json.dumps(conv)};
const googleMonthLabels = {json.dumps(month_labels)};
const googleMonthSpend = {json.dumps(month_spend)};
new Chart(document.getElementById('googleSpendChart'), {{type:'bar', data:{{labels:googleLabels, datasets:[{{label:'Spend (SAR)', data:googleSpend, backgroundColor:'#4285f4', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('googleConvChart'), {{type:'bar', data:{{labels:googleLabels, datasets:[{{label:'Conversions', data:googleConv, backgroundColor:'#34a853', borderRadius:8}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
new Chart(document.getElementById('googleMonthlyChart'), {{type:'line', data:{{labels:googleMonthLabels, datasets:[{{label:'Spend', data:googleMonthSpend, borderColor:'#4285f4', backgroundColor:'rgba(66,133,244,0.1)', fill:true, tension:0.3}}]}}, options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true}}}}}}}});
</script>
</body></html>
"""
    return common_head("White Car Ads Audit | Google Ads", "google") + body


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
