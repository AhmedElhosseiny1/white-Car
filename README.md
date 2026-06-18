# TikTok & Google Ads Audit Report

Automated advertising audit for **Whitecarx** combining data from:

- **TikTok Ads** account `7521672875829477392`
- **Google Ads** customer ID `348-288-3125`

## View Report

Open the latest audit report here:

👉 **[Live HTML Report →](https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/)**

*(Enable GitHub Pages in repo settings to serve `index.html` automatically.)*

## Files

| File | Purpose |
|------|---------|
| `index.html` | Self-contained HTML report with charts |
| `audit_report.md` | Markdown version of the report |
| `raw/` | Raw API responses from Pipeboard MCP |
| `fetch_data.sh` | Fetches fresh data from TikTok & Google Ads APIs |
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

1. Push this repo to GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Add a repository secret named `PIPEBOARD_API_TOKEN` with your Pipeboard token.
4. The workflow will fetch fresh data, regenerate both reports, and commit the updates.

## Customization

Edit the advertiser/customer IDs at the top of `fetch_data.sh` to audit different accounts.
