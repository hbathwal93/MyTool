import os, io, datetime as dt
import streamlit as st
import requests, yfinance as yf, pandas as pd
from bs4 import BeautifulSoup
import feedparser

# UI Config
st.set_page_config(page_title="Smart Equity Dossier", layout="wide")
st.markdown("""
<style>
body { background-color: #191c1f; color:#e6eefa;}
.stApp { background:#191c1f; }
.section-title { color:#39ff14; font-size:1.25em; margin-top:1rem; }
a { color:#39ff14; }
</style>
""", unsafe_allow_html=True)

# API Setup
PPLX_KEY = st.secrets.get("PPLX_API_KEY") or os.getenv("PPLX_API_KEY")
client = None
if PPLX_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=PPLX_KEY, base_url="https://api.perplexity.ai")

HEADERS = {"User-Agent": "Mozilla/5.0"}

def resolve_ticker(ticker):
    base = ticker.strip().upper()
    for suffix in [".NS", ".BO"]:
        tkr = f"{base}{suffix}"
        info = yf.Ticker(tkr).info
        if info.get("regularMarketPrice"):
            hist = yf.Ticker(tkr).history(period="5y")
            return tkr, info, hist
    return None, None, None

def fetch_rss_items(rss_url, max_items=5):
    try:
        feed = feedparser.parse(rss_url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.title,
                "link": entry.link,
                "date": entry.published[:16] if hasattr(entry, 'published') else "Unknown"
            })
        return items
    except:
        return []

def extract_text_from_file(file_bytes, filename):
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader
        pdf = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif filename.lower().endswith(".pptx"):
        from pptx import Presentation
        prs = Presentation(io.BytesIO(file_bytes))
        text_runs = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text_runs.append(shape.text)
        return "\n".join(text_runs)
    return ""

def analyze_perplexity_document(text, prompt):
    if client is None:
        return "🔑 Perplexity Pro API key not set."
    try:
        resp = client.chat.completions.create(
            model="sonar-pro", 
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:12000]}
            ]
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# Sidebar
st.sidebar.title("🔍 Search & Upload")
user_input = st.sidebar.text_input("Enter stock ticker")
uploaded_files = st.sidebar.file_uploader("Upload documents", accept_multiple_files=True, type=['pdf', 'pptx'])

if not user_input:
    st.info("Enter a ticker in the sidebar to begin.")
    st.stop()

ticker, info, hist = resolve_ticker(user_input.upper())
if not ticker:
    st.error("Ticker not found.")
    st.stop()

code = ticker.replace(".NS", "").replace(".BO", "")
st.markdown(f"<div class='section-title'>💹 {ticker}</div>", unsafe_allow_html=True)

# Price Display
c1, c2, c3 = st.columns(3)
c1.metric("Current Price", f"₹{info.get('regularMarketPrice', 'N/A')}")
c2.metric("52W High", f"₹{info.get('fiftyTwoWeekHigh', 'N/A')}")
c3.metric("52W Low", f"₹{info.get('fiftyTwoWeekLow', 'N/A')}")
st.line_chart(hist["Close"])

# Sectoral News
st.markdown("<div class='section-title'>🌐 Sectoral Trends</div>", unsafe_allow_html=True)
sector = info.get("sector", "")
if sector:
    sector_news = fetch_rss_items(f"https://news.google.com/rss/search?q={sector}+india")
    for item in sector_news:
        st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

# Company News
st.markdown("<div class='section-title'>📰 Company News</div>", unsafe_allow_html=True)
company_news = fetch_rss_items(f"https://news.google.com/rss/search?q={code}+stock+india")
for item in company_news:
    st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

# Economic Times News
st.markdown("**Economic Times Top Stories**")
et_news = fetch_rss_items("https://economictimes.indiatimes.com/rssfeedstopstories.cms")
for item in et_news:
    st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

# Mint News
st.markdown("**Mint Latest News**")
mint_news = fetch_rss_items("https://www.livemint.com/rss/news")
for item in mint_news:
    st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

# AI Analysis
if uploaded_files and client:
    st.markdown("<div class='section-title'>🤖 AI-Powered Analysis</div>", unsafe_allow_html=True)
    for f in uploaded_files:
        file_bytes = f.read()
        text_content = extract_text_from_file(file_bytes, f.name)
        with st.spinner(f"Analyzing {f.name}..."):
            analysis = analyze_perplexity_document(
                text_content,
                "Analyze this document for management commentary, strategy, and key insights."
            )
        st.subheader(f"Analysis: {f.name}")
        st.write(analysis)

# Community Links
st.markdown("<div class='section-title'>🔗 Community</div>", unsafe_allow_html=True)
st.markdown(f"[ValuePickr discussions for {code}](https://forum.valuepickr.com/search?q={code})")
