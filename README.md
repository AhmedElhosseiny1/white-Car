# TikTok, Meta & Google Ads Audit Report

Automated advertising audit for **Whitecarx** combining data from:

- **TikTok Ads** account `7521672875829477392`
- **Meta Ads** account `908730431603058`
- **Google Ads** customer ID `348-288-3125`

## View Report

Open the latest audit report here:

👉 **[Live HTML Report →](https://ahmedelhosseiny1.github.io/white-Car/)**

## Files

| File | Purpose |
|------|---------|
| `index.html` | Self-contained HTML report with charts |
| `audit_report.md` | Markdown version of the report |
| `raw/` | Raw API responses from Pipeboard MCP |
| `fetch_data.sh` | Fetches fresh data from all three ad platforms |
| `generate_html_report.py` | Builds `index.html` from raw data |
| `generate_report.py` | Builds `audit_report.md` from raw data |
| `.github/workflows/generate-report.yml` | GitHub Actions automation |

## Local Usage

```bash
# 1. Set your Pipeboard API token
export PIPEBOARD_API_TOKEN=pk_your_token_here

# 2. Fetch fresh data
bash fetch_data.sh

# 3. Generate reports
python3 generate_html_report.py
python3 generate_report.py

# 4. Open the report
open index.html
```

## Automation

The included GitHub Actions workflow runs daily at 06:00 UTC and on manual trigger. To enable it:

1. Ensure the repo is on GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Add a repository secret named `PIPEBOARD_API_TOKEN` with your Pipeboard token.
4. The workflow will fetch fresh data, regenerate both reports, and commit the updates.

## Customization

Edit the account IDs at the top of `fetch_data.sh` to audit different accounts.
