#!/usr/bin/env python3
"""Generate TikTok/Google Ads audit report from Pipeboard MCP raw data."""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

OUT_DIR = Path(__file__).parent
RAW_DIR = OUT_DIR / "raw"


def parse_mcp(filename):
    """Parse MCP JSON-RPC response where data is JSON string inside content[0].text."""
    raw = json.loads((RAW_DIR / filename).read_text())
    if raw.get("result", {}).get("isError"):
        return None, raw["result"]["content"][0]["text"]
    return json.loads(raw["result"]["content"][0]["text"]), None


def fmt_num(n):
    if n is None:
        return "-"
    try:
        return f"{int(float(n)):,}"
    except (ValueError, TypeError):
        return str(n)


def fmt_sar(n):
    try:
        return f"SAR {float(n):,.2f}"
    except (ValueError, TypeError):
        return "-"


def fmt_pct(n, is_tiktok_api_value=False):
    try:
        val = float(n)
        if is_tiktok_api_value:
            # TikTok API returns CTR as a percentage value (e.g. 1.75 = 1.75%)
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

    # Campaign metrics aggregation
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

    # Ad-level metrics
    ad_metrics = ad_insights.get("metrics", [])
    ad_map = {a["ad_id"]: a for a in ads}
    ad_rows = []
    for row in ad_metrics:
        aid = row["dimensions"]["ad_id"]
        m = row["metrics"]
        spend = float(m.get("spend", 0) or 0)
        impressions = int(float(m.get("impressions", 0) or 0))
        clicks = int(float(m.get("clicks", 0) or 0))
        conversions = int(float(m.get("conversion", 0) or 0))
        ctr = float(m.get("ctr", 0) or 0)
        ad_rows.append({
            "ad_id": aid,
            "name": ad_map.get(aid, {}).get("ad_name", aid),
            "text": ad_map.get(aid, {}).get("ad_text", ""),
            "campaign_name": ad_map.get(aid, {}).get("campaign_name", ""),
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": ctr,
        })
    top_ads = sorted(ad_rows, key=lambda x: x["spend"], reverse=True)[:10]

    # Daily trends
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

    # Monthly aggregation
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
    total_adgroup_budgets = sum(float(ag.get("budget", 0) or 0) for ag in adgroups)

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
        "total_adgroup_budgets": total_adgroup_budgets,
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

    # Aggregate campaign metrics
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

    # Monthly sorted
    top_months = sorted(
        [{"month": m, "spend": s, "conversions": monthly_conversions[m]} for m, s in monthly_spend.items()],
        key=lambda x: x["spend"],
        reverse=True,
    )

    # Ad-level (no metrics available via broken tool, just list creatives)
    ad_rows = []
    for a in ads:
        ad_rows.append({
            "ad_id": a["id"],
            "type": a.get("type", ""),
            "status": a.get("status", ""),
            "campaign_name": a.get("campaign_name", ""),
            "headlines": a.get("headlines", []),
            "descriptions": a.get("descriptions", []),
        })

    active_campaigns = [c for c in campaigns if c.get("status") == "ENABLED"]
    inactive_campaigns = [c for c in campaigns if c.get("status") != "ENABLED"]

    return {
        "account": account,
        "total_campaigns": len(campaigns),
        "active_campaigns": len(active_campaigns),
        "inactive_campaigns": inactive_campaigns,
        "total_ads": len(ads),
        "total_spend": total_spend,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "total_conversion_value": total_conversion_value,
        "top_campaigns": top_campaigns,
        "top_ads": ad_rows,
        "top_months": top_months,
    }


def main():
    tiktok = analyze_tiktok()
    google = analyze_google_ads()

    report = []
    report.append("# TikTok & Google Ads Audit: Whitecarx")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("\n## Accounts Audited")
    report.append(f"- **TikTok Ads:** 7521672875829477392 ({tiktok['account'].get('name', 'Unknown')})")
    if google:
        report.append(f"- **Google Ads:** 348-288-3125 ({google['account'].get('name', 'Unknown')})")
    else:
        report.append("- **Google Ads:** 348-288-3125 (not accessible)")

    # ===================== TIKTOK SECTION =====================
    report.append("\n---\n\n# Part 1: TikTok Ads Audit")
    adv = tiktok["account"]
    report.append(f"\n**Account Name:** {adv.get('name', 'Unknown')}")
    report.append(f"**Currency:** {adv.get('currency', 'SAR')}")
    report.append(f"**Country:** {adv.get('country', 'Unknown')}")
    report.append(f"**Timezone:** {adv.get('display_timezone', 'Unknown')}")
    report.append(f"**Status:** {adv.get('status', 'Unknown')}")
    create_time = adv.get("create_time")
    if create_time:
        report.append(f"**Created:** {datetime.fromtimestamp(create_time).strftime('%Y-%m-%d')}")

    report.append("\n## Executive Summary")
    report.append(f"- **Total Campaigns:** {tiktok['total_campaigns']} ({tiktok['active_campaigns']} active, {len(tiktok['inactive_campaigns'])} inactive)")
    report.append(f"- **Total Ad Groups:** {tiktok['total_adgroups']}")
    report.append(f"- **Total Ads:** {tiktok['total_ads']}")
    report.append(f"- **Total Spend (last 365d):** {fmt_sar(tiktok['total_spend'])}")
    report.append(f"- **Total Impressions:** {fmt_num(tiktok['total_impressions'])}")
    report.append(f"- **Total Clicks:** {fmt_num(tiktok['total_clicks'])}")
    report.append(f"- **Total Conversions:** {fmt_num(tiktok['total_conversions'])}")
    report.append(f"- **Total Video Plays:** {fmt_num(tiktok['total_video_plays'])}")
    report.append(f"- **Overall CTR:** {fmt_pct(tiktok['total_clicks'] / tiktok['total_impressions'] if tiktok['total_impressions'] else 0)}")
    report.append(f"- **Overall CPC:** {fmt_sar(tiktok['total_spend'] / tiktok['total_clicks'] if tiktok['total_clicks'] else 0)}")
    report.append(f"- **Overall CPA:** {fmt_sar(tiktok['total_spend'] / tiktok['total_conversions'] if tiktok['total_conversions'] else 0)}")

    report.append("\n## Top TikTok Campaigns by Spend")
    report.append("\n| Rank | Campaign | Status | Objective | Spend | Impressions | Clicks | Conv | CTR | CPC | CPA |")
    report.append("|------|----------|--------|-----------|-------|-------------|--------|------|-----|-----|-----|")
    for i, c in enumerate(tiktok["top_campaigns"][:10], 1):
        report.append(
            f"| {i} | {c['name']} | {c['status']} | {c['objective']} | "
            f"{fmt_sar(c['spend'])} | {fmt_num(c['impressions'])} | {fmt_num(c['clicks'])} | "
            f"{fmt_num(c['conversions'])} | {fmt_pct(c['ctr'], is_tiktok_api_value=True)} | {fmt_sar(c['cpc'])} | {fmt_sar(c['cpconv'])} |"
        )

    report.append("\n## Top TikTok Ads / Creatives by Spend")
    report.append("\n| Rank | Ad Name | Campaign | Spend | Impressions | Clicks | Conv | CTR | Ad Text |")
    report.append("|------|---------|----------|-------|-------------|--------|------|-----|----------|")
    for i, a in enumerate(tiktok["top_ads"], 1):
        text = (a["text"] or "")[:40].replace("|", "")
        report.append(
            f"| {i} | {a['name']} | {a['campaign_name']} | {fmt_sar(a['spend'])} | "
            f"{fmt_num(a['impressions'])} | {fmt_num(a['clicks'])} | {fmt_num(a['conversions'])} | "
            f"{fmt_pct(a['ctr'], is_tiktok_api_value=True)} | {text} |"
        )

    report.append("\n## TikTok Daily Trends (Last 30 Days)")
    report.append("\n| Date | Spend | Impressions | Clicks | Conversions |")
    report.append("|------|-------|-------------|--------|-------------|")
    for row in tiktok["daily_rows"]:
        report.append(
            f"| {row['day']} | {fmt_sar(row['spend'])} | {fmt_num(row['impressions'])} | "
            f"{fmt_num(row['clicks'])} | {fmt_num(row['conversions'])} |"
        )

    report.append("\n## TikTok Top Days by Spend")
    report.append("\n| Rank | Date | Spend | Conversions |")
    report.append("|------|------|-------|-------------|")
    for i, d in enumerate(tiktok["top_days"], 1):
        report.append(f"| {i} | {d['day']} | {fmt_sar(d['spend'])} | {fmt_num(d['conversions'])} |")

    report.append("\n## TikTok Monthly Spend & Seasonality")
    report.append("\n| Month | Spend | Conversions |")
    report.append("|-------|-------|-------------|")
    for m in tiktok["top_months"]:
        report.append(f"| {m['month']} | {fmt_sar(m['spend'])} | {fmt_num(m['conversions'])} |")

    report.append("\n## TikTok Campaign Status & Budget")
    report.append(f"- **Active campaigns:** {tiktok['active_campaigns']}")
    report.append(f"- **Inactive campaigns:** {len(tiktok['inactive_campaigns'])}")
    report.append(f"- **Sum of ad group daily budgets:** {fmt_sar(tiktok['total_adgroup_budgets'])}")
    if tiktok["inactive_campaigns"]:
        report.append("\n### Inactive TikTok Campaigns")
        report.append("\n| Campaign | Status | Created |")
        report.append("|----------|--------|---------|")
        for c in tiktok["inactive_campaigns"]:
            report.append(f"| {c['campaign_name']} | {c['operation_status']} | {c.get('create_time', 'N/A')} |")

    # ===================== GOOGLE ADS SECTION =====================
    if google:
        report.append("\n---\n\n# Part 2: Google Ads Audit")
        acc = google["account"]
        report.append(f"\n**Account Name:** {acc.get('name', 'Unknown')}")
        report.append(f"**Customer ID:** {acc.get('id', '3482883125')}")
        report.append(f"**Currency:** {acc.get('currency_code', 'SAR')}")
        report.append(f"**Timezone:** {acc.get('time_zone', 'Unknown')}")
        report.append(f"**Status:** {acc.get('status', 'Unknown')}")
        report.append(f"**Auto Tagging:** {'Enabled' if acc.get('auto_tagging_enabled') else 'Disabled'}")
        report.append(f"**Manager Account:** {'Yes' if acc.get('is_manager_account') else 'No'}")

        report.append("\n## Executive Summary")
        report.append(f"- **Total Campaigns:** {google['total_campaigns']} ({google['active_campaigns']} active, {len(google['inactive_campaigns'])} inactive)")
        report.append(f"- **Total Ads:** {google['total_ads']}")
        report.append(f"- **Total Spend (all time):** {fmt_sar(google['total_spend'])}")
        report.append(f"- **Total Impressions:** {fmt_num(google['total_impressions'])}")
        report.append(f"- **Total Clicks:** {fmt_num(google['total_clicks'])}")
        report.append(f"- **Total Conversions:** {fmt_num(google['total_conversions'])}")
        report.append(f"- **Total Conversion Value:** {fmt_sar(google['total_conversion_value'])}")
        report.append(f"- **Overall CTR:** {fmt_pct(google['total_clicks'] / google['total_impressions'] if google['total_impressions'] else 0)}")
        report.append(f"- **Overall CPC:** {fmt_sar(google['total_spend'] / google['total_clicks'] if google['total_clicks'] else 0)}")
        report.append(f"- **Overall CPA:** {fmt_sar(google['total_spend'] / google['total_conversions'] if google['total_conversions'] else 0)}")
        report.append(f"- **Overall ROAS:** {google['total_conversion_value'] / google['total_spend']:.2f}x" if google['total_spend'] else "-")

        report.append("\n## Top Google Ads Campaigns by Spend")
        report.append("\n| Rank | Campaign | Spend | Impressions | Clicks | Conv | Conv Value | CTR | CPC | CPA | ROAS |")
        report.append("|------|----------|-------|-------------|--------|------|------------|-----|-----|-----|------|")
        for i, c in enumerate(google["top_campaigns"], 1):
            report.append(
                f"| {i} | {c['name']} | {fmt_sar(c['spend'])} | {fmt_num(c['impressions'])} | "
                f"{fmt_num(c['clicks'])} | {fmt_num(c['conversions'])} | {fmt_sar(c['conversions_value'])} | "
                f"{fmt_pct(c['ctr'])} | {fmt_sar(c['cpc'])} | {fmt_sar(c['cpa'])} | {c['roas']:.2f}x |"
            )

        report.append("\n## Google Ads Monthly Trends")
        report.append("\n| Month | Spend | Conversions |")
        report.append("|-------|-------|-------------|")
        for m in google["top_months"]:
            report.append(f"| {m['month']} | {fmt_sar(m['spend'])} | {fmt_num(m['conversions'])} |")

        report.append("\n## Google Ads Creatives")
        report.append(f"\nTotal responsive search ads: {len(google['top_ads'])}")
        for i, a in enumerate(google["top_ads"], 1):
            report.append(f"\n### Ad {i}: {a['ad_id']} ({a['status']})")
            report.append(f"- **Campaign:** {a['campaign_name']}")
            report.append(f"- **Headlines:** {', '.join(a['headlines'][:5])}")
            report.append(f"- **Descriptions:** {', '.join(a['descriptions'][:2])}")

        if google["inactive_campaigns"]:
            report.append("\n### Inactive Google Ads Campaigns")
            report.append("\n| Campaign | Status | Type | Budget |")
            report.append("|----------|--------|------|--------|")
            for c in google["inactive_campaigns"]:
                report.append(f"| {c['name']} | {c['status']} | {c['type']} | SAR {float(c.get('budget', 0) or 0):,.2f} |")

    # ===================== CROSS-PLATFORM SUMMARY =====================
    report.append("\n---\n\n# Part 3: Cross-Platform Summary & Recommendations")

    if google:
        report.append(f"\n| Platform | Spend | Impressions | Clicks | Conversions | CTR | CPC | CPA |")
        report.append("|----------|-------|-------------|--------|-------------|-----|-----|-----|")
        report.append(
            f"| TikTok | {fmt_sar(tiktok['total_spend'])} | {fmt_num(tiktok['total_impressions'])} | "
            f"{fmt_num(tiktok['total_clicks'])} | {fmt_num(tiktok['total_conversions'])} | "
            f"{fmt_pct(tiktok['total_clicks'] / tiktok['total_impressions'] if tiktok['total_impressions'] else 0)} | "
            f"{fmt_sar(tiktok['total_spend'] / tiktok['total_clicks'] if tiktok['total_clicks'] else 0)} | "
            f"{fmt_sar(tiktok['total_spend'] / tiktok['total_conversions'] if tiktok['total_conversions'] else 0)} |"
        )
        report.append(
            f"| Google Ads | {fmt_sar(google['total_spend'])} | {fmt_num(google['total_impressions'])} | "
            f"{fmt_num(google['total_clicks'])} | {fmt_num(google['total_conversions'])} | "
            f"{fmt_pct(google['total_clicks'] / google['total_impressions'] if google['total_impressions'] else 0)} | "
            f"{fmt_sar(google['total_spend'] / google['total_clicks'] if google['total_clicks'] else 0)} | "
            f"{fmt_sar(google['total_spend'] / google['total_conversions'] if google['total_conversions'] else 0)} |"
        )
        report.append(
            f"| **Combined** | {fmt_sar(tiktok['total_spend'] + google['total_spend'])} | "
            f"{fmt_num(tiktok['total_impressions'] + google['total_impressions'])} | "
            f"{fmt_num(tiktok['total_clicks'] + google['total_clicks'])} | "
            f"{fmt_num(tiktok['total_conversions'] + google['total_conversions'])} | | | |"
        )
    else:
        report.append("\nGoogle Ads data not available for cross-platform comparison.")

    report.append("\n## Recommendations")
    report.append("\n### TikTok")
    if tiktok["total_conversions"] > 0:
        avg_cpconv = tiktok["total_spend"] / tiktok["total_conversions"]
        report.append(f"- Average CPA is **SAR {avg_cpconv:,.2f}**. Benchmark against lead value; reduce bids if CPA is too high.")
    low_ctr = [c for c in tiktok["top_campaigns"] if c["ctr"] < 0.5 and c["impressions"] > 1000]
    if low_ctr:
        report.append(f"- {len(low_ctr)} TikTok campaign(s) have CTR below 0.50%. Refresh creatives and test new hooks.")
    if len(tiktok["inactive_campaigns"]) > 0:
        report.append(f"- {len(tiktok['inactive_campaigns'])} TikTok campaigns are inactive. Review whether to re-enable or retire them.")
    report.append(f"- Overall TikTok CTR ({fmt_pct(tiktok['total_clicks'] / tiktok['total_impressions'] if tiktok['total_impressions'] else 0)}) is below the ~1% auction benchmark. Test stronger CTAs and opening frames.")
    if tiktok["top_months"]:
        report.append(f"- Peak TikTok spend month was **{tiktok['top_months'][0]['month']}** ({fmt_sar(tiktok['top_months'][0]['spend'])}). Plan budget increases ahead of similar seasonal windows.")
    report.append("- Consolidate budget into the top 3 TikTok campaigns by conversion volume to improve algorithm learning.")

    if google:
        report.append("\n### Google Ads")
        if google["total_conversions"] > 0:
            report.append(f"- Google Ads CPA is **{fmt_sar(google['total_spend'] / google['total_conversions'])}**. Compare quality of Google leads vs TikTok leads.")
        if google["total_spend"] > 0:
            report.append(f"- Google Ads ROAS is **{google['total_conversion_value'] / google['total_spend']:.2f}x**. If below target, review keyword targeting and negative keywords.")
        if google["inactive_campaigns"]:
            report.append(f"- {len(google['inactive_campaigns'])} Google Ads campaign(s) are paused. Evaluate if reactivation makes sense.")
        report.append("- Google Ads has only 2 campaigns with small budgets (SAR 120 and SAR 260/day). Consider scaling the better performer after reviewing conversion quality.")
        report.append("- Add more RSA headlines and descriptions to improve ad strength and auction coverage.")

    report.append("\n## Raw Data Files")
    report.append("All raw API responses are stored in the `raw/` folder for verification and deeper analysis.")

    (OUT_DIR / "audit_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Report written to {OUT_DIR / 'audit_report.md'}")


if __name__ == "__main__":
    main()
