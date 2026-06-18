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


def analyze_tiktok():
    advertiser, _ = parse_mcp("tiktok_advertiser_info.json")
    campaigns_data, _ = parse_mcp("tiktok_campaigns.json")
    adgroups_data, _ = parse_mcp("tiktok_adgroups.json")
    ads_data, _ = parse_mcp("tiktok_ads.json")
    camp_insights, _ = parse_mcp("tiktok_insights_campaign.json")
    daily_insights, _ = parse_mcp("tiktok_insights_daily.json")
    ad_insights, _ = parse_mcp("tiktok_insights_ad.json")

    adv = advertiser["advertiser"]
    campaigns = campaigns_data.get("campaigns", [])
    adgroups = adgroups_data.get("adgroups", [])
    ads = ads_data.get("ads", [])
    campaign_map = {c["campaign_id"]: c for c in campaigns}

    camp_metrics = camp_insights.get("metrics", [])
    total_spend = 0.0
    total_impressions = 0
    total_clicks = 0
    total_conversions = 0
    total_video_plays = 0
    campaign_rows = []

    for row in camp_metrics:
        cid = row["dimensions"]["campaign_id"]
        m = row["metrics"]
        spend = float(m.get("spend", 0) or 0)
        impressions = int(float(m.get("impressions", 0) or 0))
        clicks = int(float(m.get("clicks", 0) or 0))
        conversions = int(float(m.get("conversion", 0) or 0))
        video_plays = int(float(m.get("video_play_actions", 0) or 0))
        ctr = float(m.get("ctr", 0) or 0)
        cpc = float(m.get("cpc", 0) or 0)
        cpconv = float(m.get("cost_per_conversion", 0) or 0)

        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        total_conversions += conversions
        total_video_plays += video_plays

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
        })

    top_campaigns = sorted(campaign_rows, key=lambda x: x["spend"], reverse=True)

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
        "top_ads": top_ads,
        "daily_rows": daily_rows_sorted,
        "top_days": top_days,
        "top_months": top_months,
    }


def analyze_google_ads():
    account_info, err = parse_mcp("google_ads_account_info.json")
    campaigns_data, _ = parse_mcp("google_ads_campaigns.json")
    ads_data, _ = parse_mcp("google_ads_ads.json")
    monthly_data, _ = parse_mcp("google_ads_monthly.json")

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
        })
    top_campaigns = sorted(campaign_rows, key=lambda x: x["spend"], reverse=True)

    top_months = sorted(
        [{"month": m, "spend": s, "conversions": monthly_conversions[m]} for m, s in monthly_spend.items()],
        key=lambda x: x["spend"],
        reverse=True,
    )

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
        "top_months": top_months,
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

    # Chart data JSON
    tiktok_daily_labels = [r["day"] for r in tiktok["daily_rows"]]
    tiktok_daily_spend = [r["spend"] for r in tiktok["daily_rows"]]
    tiktok_daily_conv = [r["conversions"] for r in tiktok["daily_rows"]]
    tiktok_month_labels = [m["month"] for m in tiktok["top_months"]]
    tiktok_month_spend = [m["spend"] for m in tiktok["top_months"]]

    google_month_labels = [m["month"][:7] for m in google["top_months"]] if google else []
    google_month_spend = [m["spend"] for m in google["top_months"]] if google else []

    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TikTok & Google Ads Audit - Whitecarx</title>
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
.container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
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
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin: 1.5rem 0; }
.metric-card {
  background: var(--surface-2);
  border-radius: 12px;
  padding: 1.25rem;
  text-align: center;
  border: 1px solid var(--border);
}
.metric-card .label { color: var(--text-muted); font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; }
.metric-card .value { font-size: 1.75rem; font-weight: 700; margin-top: 0.25rem; }
.metric-card.positive .value { color: var(--success); }
.metric-card.negative .value { color: var(--danger); }
.metric-card.warning .value { color: var(--warning); }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }
th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }
th { background: var(--surface-2); color: var(--accent); font-weight: 600; }
tr:hover { background: rgba(255,255,255,0.03); }
.chart-container { position: relative; height: 350px; margin: 2rem 0; }
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
.note {
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid var(--accent);
  border-radius: 8px;
  padding: 1rem;
  margin: 1rem 0;
  color: var(--text);
}
footer { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem; }
@media (max-width: 768px) {
  .container { padding: 1rem; }
  header h1 { font-size: 1.75rem; }
  .section { padding: 1.25rem; }
  table { font-size: 0.8rem; }
  th, td { padding: 0.5rem; }
}
</style>
</head>
<body>
<header>
  <h1>TikTok & Google Ads Audit</h1>
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
    <div class="metric-card"><div class="label">Google Ads</div><div class="value">348-288-3125</div><div style="color:var(--text-muted);font-size:.85rem">""")
    html_parts.append(google["account"].get("name", "Unknown") if google else "Not accessible")
    html_parts.append("""</div></div>
  </div>
</div>
""")

    # Cross-platform summary
    if google:
        html_parts.append("""<div class="section">
  <h2>Cross-Platform Summary</h2>
  <div class="grid">
    <div class="metric-card"><div class="label">Combined Spend</div><div class="value">""")
        html_parts.append(fmt_sar(tiktok["total_spend"] + google["total_spend"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Combined Impressions</div><div class="value">""")
        html_parts.append(fmt_num(tiktok["total_impressions"] + google["total_impressions"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Combined Clicks</div><div class="value">""")
        html_parts.append(fmt_num(tiktok["total_clicks"] + google["total_clicks"]))
        html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Combined Conversions</div><div class="value">""")
        html_parts.append(fmt_num(tiktok["total_conversions"] + google["total_conversions"]))
        html_parts.append("""</div></div>
  </div>
  """)
        html_parts.append(render_table(
            ["Platform", "Spend", "Impressions", "Clicks", "Conversions", "CTR", "CPC", "CPA"],
            [
                ["TikTok", fmt_sar(tiktok["total_spend"]), fmt_num(tiktok["total_impressions"]), fmt_num(tiktok["total_clicks"]), fmt_num(tiktok["total_conversions"]),
                 fmt_pct(tiktok["total_clicks"] / tiktok["total_impressions"] if tiktok["total_impressions"] else 0),
                 fmt_sar(tiktok["total_spend"] / tiktok["total_clicks"] if tiktok["total_clicks"] else 0),
                 fmt_sar(tiktok["total_spend"] / tiktok["total_conversions"] if tiktok["total_conversions"] else 0)],
                ["Google Ads", fmt_sar(google["total_spend"]), fmt_num(google["total_impressions"]), fmt_num(google["total_clicks"]), fmt_num(google["total_conversions"]),
                 fmt_pct(google["total_clicks"] / google["total_impressions"] if google["total_impressions"] else 0),
                 fmt_sar(google["total_spend"] / google["total_clicks"] if google["total_clicks"] else 0),
                 fmt_sar(google["total_spend"] / google["total_conversions"] if google["total_conversions"] else 0)],
            ]
        ))
        html_parts.append("</div>")

    # TikTok section
    html_parts.append("""<div class="section">
  <h2>Part 1: TikTok Ads Audit</h2>
  <p><strong>Account:</strong> """)
    html_parts.append(tiktok["account"].get("name", "Unknown"))
    html_parts.append(""" · <strong>Currency:</strong> """)
    html_parts.append(tiktok["account"].get("currency", "SAR"))
    html_parts.append(""" · <strong>Country:</strong> """)
    html_parts.append(tiktok["account"].get("country", "Unknown"))
    html_parts.append(""" · <strong>Timezone:</strong> """)
    html_parts.append(tiktok["account"].get("display_timezone", "Unknown"))
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
    <div class="metric-card"><div class="label">CPC</div><div class="value">""")
    html_parts.append(fmt_sar(tiktok["total_spend"] / tiktok["total_clicks"] if tiktok["total_clicks"] else 0))
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">CPA</div><div class="value">""")
    html_parts.append(fmt_sar(tiktok["total_spend"] / tiktok["total_conversions"] if tiktok["total_conversions"] else 0))
    html_parts.append("""</div></div>
    <div class="metric-card"><div class="label">Active / Total Campaigns</div><div class="value">""")
    html_parts.append(f"{tiktok['active_campaigns']} / {tiktok['total_campaigns']}")
    html_parts.append("""</div></div>
  </div>

  <h3>Top Campaigns by Spend</h3>
  """)
    html_parts.append(render_table(
        ["Rank", "Campaign", "Status", "Objective", "Spend", "Impressions", "Clicks", "Conv", "CTR", "CPC", "CPA"],
        [[str(i), c["name"], c["status"], c["objective"], fmt_sar(c["spend"]), fmt_num(c["impressions"]), fmt_num(c["clicks"]),
          fmt_num(c["conversions"]), fmt_pct(c["ctr"], is_tiktok_api_value=True), fmt_sar(c["cpc"]), fmt_sar(c["cpconv"])]
         for i, c in enumerate(tiktok["top_campaigns"][:10], 1)]
    ))

    html_parts.append("""  <h3>Top Ads / Creatives by Spend</h3>
  """)
    html_parts.append(render_table(
        ["Rank", "Ad Name", "Campaign", "Spend", "Impressions", "Clicks", "Conv", "CTR", "Ad Text"],
        [[str(i), a["name"], a["campaign_name"], fmt_sar(a["spend"]), fmt_num(a["impressions"]), fmt_num(a["clicks"]),
          fmt_num(a["conversions"]), fmt_pct(a["ctr"], is_tiktok_api_value=True), (a["text"] or "")[:50]]
         for i, a in enumerate(tiktok["top_ads"], 1)]
    ))

    html_parts.append("""  <h3>Daily Spend & Conversions (Last 30 Days)</h3>
  <div class="chart-container"><canvas id="tiktokDailyChart"></canvas></div>

  <h3>Monthly Seasonality</h3>
  <div class="chart-container"><canvas id="tiktokMonthlyChart"></canvas></div>

  <h3>Inactive Campaigns</h3>
  """)
    if tiktok["inactive_campaigns"]:
        html_parts.append(render_table(
            ["Campaign", "Status", "Created"],
            [[c["campaign_name"], c["operation_status"], c.get("create_time", "N/A")] for c in tiktok["inactive_campaigns"]]
        ))
    else:
        html_parts.append("<p>All campaigns are active.</p>")
    html_parts.append("</div>")

    # Google Ads section
    if google:
        html_parts.append("""<div class="section">
  <h2>Part 2: Google Ads Audit</h2>
  <p><strong>Account:</strong> """)
        html_parts.append(google["account"].get("name", "Unknown"))
        html_parts.append(""" · <strong>Currency:</strong> """)
        html_parts.append(google["account"].get("currency_code", "SAR"))
        html_parts.append(""" · <strong>Timezone:</strong> """)
        html_parts.append(google["account"].get("time_zone", "Unknown"))
        html_parts.append(""" · <strong>Status:</strong> """)
        html_parts.append(google["account"].get("status", "Unknown"))
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
        <div class="metric-card"><div class="label">Active / Total Campaigns</div><div class="value">""")
        html_parts.append(f"{google['active_campaigns']} / {google['total_campaigns']}")
        html_parts.append("""</div></div>
  </div>

  <h3>Top Campaigns by Spend</h3>
  """)
        html_parts.append(render_table(
            ["Rank", "Campaign", "Spend", "Impressions", "Clicks", "Conv", "Conv Value", "CTR", "CPC", "CPA", "ROAS"],
            [[str(i), c["name"], fmt_sar(c["spend"]), fmt_num(c["impressions"]), fmt_num(c["clicks"]),
              fmt_num(c["conversions"]), fmt_sar(c["conversions_value"]), fmt_pct(c["ctr"]), fmt_sar(c["cpc"]),
              fmt_sar(c["cpa"]), f"{c['roas']:.2f}x"] for i, c in enumerate(google["top_campaigns"], 1)]
        ))

        html_parts.append("""  <h3>Monthly Trends</h3>
  <div class="chart-container"><canvas id="googleMonthlyChart"></canvas></div>

  <h3>Responsive Search Ads</h3>
  """)
        for i, a in enumerate(google["ads"], 1):
            html_parts.append(f"""  <div class="note" style="margin-bottom:1rem">
    <strong>Ad {i}:</strong> {a['id']} ({a['status']})<br>
    <strong>Campaign:</strong> {a.get('campaign_name', '')}<br>
    <strong>Headlines:</strong> {', '.join(a.get('headlines', [])[:8])}<br>
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

    # Recommendations
    html_parts.append("""<div class="section">
  <h2>Recommendations</h2>
  <ul class="recommendations">
""")
    recs = []
    if tiktok["total_conversions"] > 0:
        avg_cpconv = tiktok["total_spend"] / tiktok["total_conversions"]
        recs.append(("warning", f"TikTok average CPA is <strong>SAR {avg_cpconv:,.2f}</strong>. Benchmark against lead value; reduce bids if CPA exceeds 30% of LTV."))
    low_ctr = [c for c in tiktok["top_campaigns"] if c["ctr"] < 0.5 and c["impressions"] > 1000]
    if low_ctr:
        recs.append(("warning", f"<strong>{len(low_ctr)} TikTok campaigns</strong> have CTR below 0.50%. Refresh creatives and test new hooks/thumbnails."))
    if tiktok["inactive_campaigns"]:
        recs.append(("danger", f"<strong>{len(tiktok['inactive_campaigns'])} TikTok campaigns</strong> are inactive. Review whether to re-enable or retire them."))
    recs.append(("warning", f"Overall TikTok CTR is <strong>{fmt_pct(tiktok['total_clicks'] / tiktok['total_impressions'] if tiktok['total_impressions'] else 0)}</strong>, below the ~1% auction benchmark. Test stronger CTAs and opening frames."))
    if tiktok["top_months"]:
        recs.append(("success", f"Peak TikTok spend month was <strong>{tiktok['top_months'][0]['month']}</strong> ({fmt_sar(tiktok['top_months'][0]['spend'])}). Plan budget increases ahead of similar seasonal windows."))
    recs.append(("success", "Consolidate TikTok budget into the top 3 conversion-driving campaigns to improve algorithm learning and efficiency."))

    if google:
        if google["total_conversions"] > 0:
            recs.append(("warning", f"Google Ads CPA is <strong>{fmt_sar(google['total_spend'] / google['total_conversions'])}</strong>. Compare quality of Google leads vs TikTok leads."))
        if google["total_spend"] > 0:
            recs.append(("danger", f"Google Ads ROAS is <strong>{google['total_conversion_value'] / google['total_spend']:.2f}x</strong>. If below target, review keyword targeting and negative keywords."))
        if google["inactive_campaigns"]:
            recs.append(("warning", f"<strong>{len(google['inactive_campaigns'])} Google Ads campaign</strong> is paused. Evaluate if reactivation makes sense."))
        recs.append(("success", "Google Ads has only 2 campaigns with small budgets (SAR 120 and SAR 260/day). Consider scaling the better performer after reviewing conversion quality."))
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
    # Chart.js config
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
""")

    html_parts.append("""
</script>
</body>
</html>
""")

    (OUT_DIR / "index.html").write_text("".join(html_parts), encoding="utf-8")
    print(f"HTML report written to {OUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
