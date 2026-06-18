#!/usr/bin/env bash
# Fetch fresh TikTok & Google Ads data from Pipeboard MCP APIs.
# Requires PIPEBOARD_API_TOKEN environment variable.

set -euo pipefail

TOKEN="${PIPEBOARD_API_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo "Error: PIPEBOARD_API_TOKEN is not set"
  exit 1
fi

TIKTOK_ADVERTISER="7521672875829477392"
GOOGLE_CUSTOMER_ID="3482883125"
RAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/raw"
mkdir -p "$RAW_DIR"

echo "Fetching TikTok advertiser info..."
curl -s -X POST "https://tiktok-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":1,\"params\":{\"name\":\"get_tiktok_advertiser_info\",\"arguments\":{\"advertiser_id\":\"$TIKTOK_ADVERTISER\"}}}" \
  > "$RAW_DIR/tiktok_advertiser_info.json"

echo "Fetching TikTok campaigns..."
curl -s -X POST "https://tiktok-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":2,\"params\":{\"name\":\"get_tiktok_campaigns\",\"arguments\":{\"advertiser_id\":\"$TIKTOK_ADVERTISER\"}}}" \
  > "$RAW_DIR/tiktok_campaigns.json"

echo "Fetching TikTok ad groups..."
curl -s -X POST "https://tiktok-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":3,\"params\":{\"name\":\"get_tiktok_adgroups\",\"arguments\":{\"advertiser_id\":\"$TIKTOK_ADVERTISER\"}}}" \
  > "$RAW_DIR/tiktok_adgroups.json"

echo "Fetching TikTok ads..."
curl -s -X POST "https://tiktok-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":4,\"params\":{\"name\":\"get_tiktok_ads\",\"arguments\":{\"advertiser_id\":\"$TIKTOK_ADVERTISER\"}}}" \
  > "$RAW_DIR/tiktok_ads.json"

echo "Fetching TikTok campaign insights (365d)..."
curl -s -X POST "https://tiktok-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":5,\"params\":{\"name\":\"get_tiktok_insights\",\"arguments\":{\"advertiser_id\":\"$TIKTOK_ADVERTISER\",\"report_type\":\"BASIC\",\"data_level\":\"AUCTION_CAMPAIGN\",\"dimensions\":[\"campaign_id\"],\"metrics\":[\"spend\",\"impressions\",\"clicks\",\"ctr\",\"cpc\",\"conversion\",\"cost_per_conversion\",\"video_play_actions\",\"video_views_p25\",\"video_views_p50\",\"video_views_p75\",\"video_views_p100\"],\"start_date\":\"2025-06-18\",\"end_date\":\"2026-06-18\"}}}" \
  > "$RAW_DIR/tiktok_insights_campaign.json"

echo "Fetching TikTok daily insights (30d)..."
curl -s -X POST "https://tiktok-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":6,\"params\":{\"name\":\"get_tiktok_insights\",\"arguments\":{\"advertiser_id\":\"$TIKTOK_ADVERTISER\",\"report_type\":\"BASIC\",\"data_level\":\"AUCTION_ADVERTISER\",\"dimensions\":[\"stat_time_day\"],\"metrics\":[\"spend\",\"impressions\",\"clicks\",\"ctr\",\"cpc\",\"conversion\",\"cost_per_conversion\",\"video_play_actions\"],\"start_date\":\"2026-05-19\",\"end_date\":\"2026-06-18\"}}}" \
  > "$RAW_DIR/tiktok_insights_daily.json"

echo "Fetching TikTok ad insights (30d)..."
curl -s -X POST "https://tiktok-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":7,\"params\":{\"name\":\"get_tiktok_insights\",\"arguments\":{\"advertiser_id\":\"$TIKTOK_ADVERTISER\",\"report_type\":\"BASIC\",\"data_level\":\"AUCTION_AD\",\"dimensions\":[\"ad_id\"],\"metrics\":[\"spend\",\"impressions\",\"clicks\",\"ctr\",\"cpc\",\"conversion\",\"cost_per_conversion\",\"video_play_actions\",\"video_views_p25\",\"video_views_p50\",\"video_views_p75\",\"video_views_p100\"],\"start_date\":\"2026-05-19\",\"end_date\":\"2026-06-18\"}}}" \
  > "$RAW_DIR/tiktok_insights_ad.json"

echo "Fetching Google Ads account info..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":8,\"params\":{\"name\":\"get_google_ads_account_info\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\"}}}" \
  > "$RAW_DIR/google_ads_account_info.json"

echo "Fetching Google Ads campaigns..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":9,\"params\":{\"name\":\"get_google_ads_campaigns\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\"}}}" \
  > "$RAW_DIR/google_ads_campaigns.json"

echo "Fetching Google Ads ads..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":10,\"params\":{\"name\":\"get_google_ads_ads\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\"}}}" \
  > "$RAW_DIR/google_ads_ads.json"

echo "Fetching Google Ads monthly GAQL data..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":11,\"params\":{\"name\":\"execute_google_ads_gaql_query\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\",\"query\":\"SELECT segments.month, campaign.id, campaign.name, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value, metrics.ctr, metrics.average_cpc, metrics.cost_per_conversion FROM campaign WHERE segments.date BETWEEN '2025-06-18' AND '2026-06-18'\"}}}" \
  > "$RAW_DIR/google_ads_monthly.json"

echo "Done. Raw data saved to $RAW_DIR"
