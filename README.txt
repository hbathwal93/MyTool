# Smart Equity Dossier – README

**Last Updated:** July 24, 2025

## Overview
Smart Equity Dossier is a Streamlit-based, dark-mode research for Indian equities (NSE & BSE). Enter any valid ticker or company name to receive a structured, multi-source analysis that helps you monitor your portfolio and conduct in-depth investment research.

## Key Features
1. **Price & Chart**  
   -  Live (or near-real-time) current price, 52-week high/low and 5-year price history chart via Yahoo Finance.  
2. **Sectoral Trends & Triggers**  
   -  Top sector themes and growth drivers (past 7 days) via Google News RSS filtered by sector.  
3. **News & Competition**  
   -  Company-specific news (Google News RSS).  
   -  Economic Times top stories & industry news via official ET RSS feeds.  
   -  Mint headlines via Livemint RSS feed.  
4. **Forum Pulse (Last 90 Days)**  
   -  Top 15 ValuePickr threads (by replies) via RSS.  
   -  Top 15 Reddit submissions (by comment count) from relevant subreddits via Pushshift API.  
5. **Valuation Snapshot**  
   -  Key ratios (P/E, P/S, P/B, PEG, EV/EBITDA) fetched from Yahoo Finance’s statistics.  
6. **AI-Powered Management Analysis**  
   -  Upload investor presentations, conference-call transcripts or annual reports (PDF/PPTX).  
   -  Perplexity AI extracts:  
     – Management commentary (strategy, guidance, risk, capital allocation)  
     – Management Integrity Matrix (scores for Guidance Accuracy, Delivery, Transparency, Governance)  

## Data Sources & Time Lags
| Section                     | Source                                | Time Lag / Update Frequency          |
|-----------------------------|---------------------------------------|--------------------------------------|
| Price & Chart               | Yahoo Finance                         | ~5–15 min delayed                     |
| Sectoral Triggers           | Google News RSS                       | Real-time RSS (minutes)               |
| Company News                | Google News RSS, ET & Mint RSS feeds  | Real-time RSS (minutes)               |
| Forum Threads               | ValuePickr RSS, Reddit Pushshift API  | 90-day rolling window; near real-time |
| Valuation Ratios            | Yahoo Finance                         | ~5–15 min delayed                     |
| Management Analysis         | Perplexity AI (on upload)             | On-demand; API response ~10–20 sec    |

## Required Inputs
1. **Ticker or Company Name** (e.g., TCS, INFY, ECORECO)  
2. **Optional Document Uploads** (PDF or PPTX) for:  
   - Investor presentations  
   - Conference-call transcripts  
   - Annual reports  

## Deployment & Configuration
- **Streamlit Cloud**: Deploy via GitHub repo containing `app.py` and `requirements.txt`.  
- **Secrets**: Add `PPLX_API_KEY` (your Perplexity API key) in Streamlit Cloud secrets or as an environment variable.  
- **Dependencies** (excerpt of `requirements.txt`):
  ```
  streamlit
  yfinance
  requests
  beautifulsoup4
  feedparser
  psaw
  pypdf
  python-pptx
  openai
  lxml
  ```

## Usage Notes
- **Ticker Resolution**: Attempts `.NS` (NSE) first; if unavailable, falls back to `.BO` (BSE).  
- **Forum Scraping**: May be subject to source-site rate limits or blocking on Streamlit Cloud; consider running locally for full access.  
- **AI Analysis**: Requires valid `PPLX_API_KEY`. Free Perplexity plans allow limited daily file analyses.  
- **Performance**: Initial load per ticker ≈ 5–10 sec; subsequent runs cached for session.  

## Limitations
- **Financial Statements Skipped**: Detailed P&L, balance sheet, and cash-flow tables are omitted by design.  
- **Forum Reliability**: Thread counts reflect engagement, not sentiment quality.  
- **RSS Dependence**: RSS feeds may change structure—occasionally adjust parsing logic.  

Use this README to understand what the tool provides, the underlying data sources and their update cadence, required inputs, and any practical considerations. Enjoy streamlined, AI-enhanced equity research!
