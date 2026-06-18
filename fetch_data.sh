#!/usr/bin/env bash
# Fetch fresh TikTok, Meta & Google Ads data from Pipeboard MCP APIs.
# Requires PIPEBOARD_API_TOKEN environment variable.

set -euo pipefail

TOKEN="${PIPEBOARD_API_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo "Error: PIPEBOARD_API_TOKEN is not set"
  exit 1
fi

TIKTOK_ADVERTISER="7521672875829477392"
META_ACCOUNT_ID="act_908730431603058"
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

echo "Fetching TikTok ad group insights (30d)..."
curl -s -X POST "https://tiktok-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":8,\"params\":{\"name\":\"get_tiktok_insights\",\"arguments\":{\"advertiser_id\":\"$TIKTOK_ADVERTISER\",\"report_type\":\"BASIC\",\"data_level\":\"AUCTION_ADGROUP\",\"dimensions\":[\"adgroup_id\"],\"metrics\":[\"spend\",\"impressions\",\"clicks\",\"ctr\",\"cpc\",\"conversion\",\"cost_per_conversion\",\"video_play_actions\",\"video_views_p25\",\"video_views_p50\",\"video_views_p75\",\"video_views_p100\"],\"start_date\":\"2026-05-19\",\"end_date\":\"2026-06-18\"}}}" \
  > "$RAW_DIR/tiktok_insights_adgroup.json"

echo "Fetching Meta account info..."
curl -s -X POST "https://meta-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":9,\"params\":{\"name\":\"get_account_info\",\"arguments\":{\"account_id\":\"$META_ACCOUNT_ID\"}}}" \
  > "$RAW_DIR/meta_account_info.json"

echo "Fetching Meta campaigns..."
curl -s -X POST "https://meta-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":10,\"params\":{\"name\":\"get_campaigns\",\"arguments\":{\"account_id\":\"$META_ACCOUNT_ID\",\"limit\":100}}}" \
  > "$RAW_DIR/meta_campaigns.json"

echo "Fetching Meta adsets..."
curl -s -X POST "https://meta-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":11,\"params\":{\"name\":\"get_adsets\",\"arguments\":{\"account_id\":\"$META_ACCOUNT_ID\",\"limit\":100}}}" \
  > "$RAW_DIR/meta_adsets.json"

echo "Fetching Meta campaign insights (365d)..."
curl -s -X POST "https://meta-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":12,\"params\":{\"name\":\"get_insights\",\"arguments\":{\"account_id\":\"$META_ACCOUNT_ID\",\"level\":\"campaign\",\"date_preset\":\"last_365d\",\"fields\":[\"campaign_id\",\"campaign_name\",\"spend\",\"impressions\",\"clicks\",\"ctr\",\"cpc\",\"cpm\",\"reach\",\"frequency\",\"actions\"],\"limit\":100}}}" \
  > "$RAW_DIR/meta_campaign_insights.json"

echo "Fetching Google Ads account info..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":13,\"params\":{\"name\":\"get_google_ads_account_info\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\"}}}" \
  > "$RAW_DIR/google_ads_account_info.json"

echo "Fetching Google Ads campaigns..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":14,\"params\":{\"name\":\"get_google_ads_campaigns\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\"}}}" \
  > "$RAW_DIR/google_ads_campaigns.json"

echo "Fetching Google Ads ads..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":15,\"params\":{\"name\":\"get_google_ads_ads\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\"}}}" \
  > "$RAW_DIR/google_ads_ads.json"

echo "Fetching Google Ads monthly GAQL data..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":16,\"params\":{\"name\":\"execute_google_ads_gaql_query\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\",\"query\":\"SELECT segments.month, campaign.id, campaign.name, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value, metrics.ctr, metrics.average_cpc, metrics.cost_per_conversion FROM campaign WHERE segments.date BETWEEN '2025-06-18' AND '2026-06-18'\"}}}" \
  > "$RAW_DIR/google_ads_monthly.json"

echo "Fetching Google Ads ad group GAQL data..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":17,\"params\":{\"name\":\"execute_google_ads_gaql_query\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\",\"query\":\"SELECT ad_group.id, ad_group.name, campaign.id, campaign.name, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value, metrics.ctr, metrics.average_cpc, metrics.cost_per_conversion FROM ad_group WHERE segments.date BETWEEN '2025-06-18' AND '2026-06-18'\"}}}" \
  > "$RAW_DIR/google_ads_adgroups.json"

echo "Fetching Google Ads device GAQL data..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":18,\"params\":{\"name\":\"execute_google_ads_gaql_query\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\",\"query\":\"SELECT segments.device, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value FROM campaign WHERE segments.date BETWEEN '2025-06-18' AND '2026-06-18'\"}}}" \
  > "$RAW_DIR/google_ads_device.json"

echo "Fetching Google Ads day-of-week GAQL data..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":19,\"params\":{\"name\":\"execute_google_ads_gaql_query\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\",\"query\":\"SELECT segments.day_of_week, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value FROM campaign WHERE segments.date BETWEEN '2025-06-18' AND '2026-06-18'\"}}}" \
  > "$RAW_DIR/google_ads_dayofweek.json"


echo "Fetching Meta age insights (365d)..."
curl -s -X POST "https://meta-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":20,\"params\":{\"name\":\"get_insights\",\"arguments\":{\"account_id\":\"$META_ACCOUNT_ID\",\"level\":\"campaign\",\"date_preset\":\"last_365d\",\"fields\":[\"campaign_id\",\"campaign_name\",\"spend\",\"impressions\",\"clicks\",\"actions\"],\"breakdown\":\"age\",\"limit\":200}}}" \
  > "$RAW_DIR/meta_age.json"

echo "Fetching Meta gender insights (365d)..."
curl -s -X POST "https://meta-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":21,\"params\":{\"name\":\"get_insights\",\"arguments\":{\"account_id\":\"$META_ACCOUNT_ID\",\"level\":\"campaign\",\"date_preset\":\"last_365d\",\"fields\":[\"campaign_id\",\"campaign_name\",\"spend\",\"impressions\",\"clicks\",\"actions\"],\"breakdown\":\"gender\",\"limit\":200}}}" \
  > "$RAW_DIR/meta_gender.json"

echo "Fetching Meta region insights (365d)..."
curl -s -X POST "https://meta-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":22,\"params\":{\"name\":\"get_insights\",\"arguments\":{\"account_id\":\"$META_ACCOUNT_ID\",\"level\":\"campaign\",\"date_preset\":\"last_365d\",\"fields\":[\"campaign_id\",\"campaign_name\",\"spend\",\"impressions\",\"clicks\",\"actions\"],\"breakdown\":\"region\",\"limit\":200}}}" \
  > "$RAW_DIR/meta_region.json"

echo "Fetching Meta hourly insights (last 7d)..."
curl -s -X POST "https://meta-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":23,\"params\":{\"name\":\"get_insights\",\"arguments\":{\"account_id\":\"$META_ACCOUNT_ID\",\"level\":\"campaign\",\"date_preset\":\"last_7d\",\"fields\":[\"campaign_id\",\"campaign_name\",\"spend\",\"impressions\",\"clicks\",\"actions\"],\"breakdown\":\"hourly_stats_aggregated_by_advertiser_time_zone\",\"limit\":200}}}" \
  > "$RAW_DIR/meta_hourly.json"

echo "Fetching TikTok hourly insights (yesterday)..."
YESTERDAY=$(date -u -v-1d +%Y-%m-%d)
curl -s -X POST "https://tiktok-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":23,\"params\":{\"name\":\"get_tiktok_insights\",\"arguments\":{\"advertiser_id\":\"$TIKTOK_ADVERTISER\",\"report_type\":\"BASIC\",\"data_level\":\"AUCTION_ADVERTISER\",\"dimensions\":[\"stat_time_hour\"],\"metrics\":[\"spend\",\"impressions\",\"clicks\",\"conversion\",\"cost_per_conversion\"],\"start_date\":\"$YESTERDAY\",\"end_date\":\"$YESTERDAY\"}}}" \
  > "$RAW_DIR/tiktok_insights_hourly.json"

echo "Fetching Google Ads age range GAQL data..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":27,\"params\":{\"name\":\"execute_google_ads_gaql_query\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\",\"query\":\"SELECT segments.age_range, ad_group.id, ad_group.name, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value FROM ad_group WHERE segments.date BETWEEN '2025-06-18' AND '2026-06-18'\"}}}" \
  > "$RAW_DIR/google_ads_age.json"

echo "Fetching Google Ads gender GAQL data..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":28,\"params\":{\"name\":\"execute_google_ads_gaql_query\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\",\"query\":\"SELECT segments.gender, ad_group.id, ad_group.name, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value FROM ad_group WHERE segments.date BETWEEN '2025-06-18' AND '2026-06-18'\"}}}" \
  > "$RAW_DIR/google_ads_gender.json"

echo "Fetching Google Ads location GAQL data..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":29,\"params\":{\"name\":\"execute_google_ads_gaql_query\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\",\"query\":\"SELECT geographic_view.country_criterion_id, geographic_view.location_type, segments.geo_target_constant, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value FROM geographic_view WHERE segments.date BETWEEN '2025-06-18' AND '2026-06-18'\"}}}" \
  > "$RAW_DIR/google_ads_location.json"

echo "Fetching Google Ads hour-of-day GAQL data..."
curl -s -X POST "https://google-ads.mcp.pipeboard.co/?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"id\":30,\"params\":{\"name\":\"execute_google_ads_gaql_query\",\"arguments\":{\"customer_id\":\"$GOOGLE_CUSTOMER_ID\",\"query\":\"SELECT segments.day_of_week, segments.hour, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value FROM campaign WHERE segments.date BETWEEN '2025-06-18' AND '2026-06-18'\"}}}" \
  > "$RAW_DIR/google_ads_hourly.json"
echo "Done. Raw data saved to $RAW_DIR"
