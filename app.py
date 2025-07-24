import os, io, time, datetime as dt, streamlit as st
from json import JSONDecodeError

# Lazy-load heavy libraries when needed
def _lazy_imports():
    global requests, yf, pd, BeautifulSoup, PdfReader, Presentation, OpenAI, feedparser
    import requests
    import yfinance as yf
    import pandas as pd
    from bs4 import BeautifulSoup
    from pypdf import PdfReader
    from pptx import Presentation
    from openai import OpenAI
    import feedparser

_lazy_imports()

# UI config
st.set_page_config(page_title="Smart Equity Dossier", layout="wide")
st.markdown("""
<style>
body { background: #191c1f; color: #e6eefa; }
.section-title { color: #39ff14; font-size:1.3em; margin-top:1rem; }
a { color: #39ff14; }
</style>
""", unsafe_allow_html=True)

# Perplexity client
PPLX_KEY = st.secrets.get("PPLX_API_KEY") or os.getenv("PPLX_API_KEY")
client = None
if PPLX_KEY:
    from openai import OpenAI as _OpenAI
    client = _OpenAI(api_key=PPLX_KEY, base_url="https://api.perplexity.ai")

HEADERS = {"User-Agent":"Mozilla/5.0"}

def resolve_ticker(user_input, retries=2, pause=1.0):
    """Try .NS then .BO with retries and fallback to yf.download."""
    base = user_input.strip().upper()
    for suffix in (".NS", ".BO"):
        tkr = f"{base}{suffix}"
        for i in range(retries):
            try:
                stock = yf.Ticker(tkr)
                info = stock.info
                hist = stock.history(period="5y")
                if info.get("regularMarketPrice") and not hist.empty:
                    return tkr, info, hist
                # fallback
                data = yf.download(tkr, period="5y", progress=False)
                if not data.empty:
                    return tkr, {"regularMarketPrice": data["Close"][-1]}, data
                break
            except JSONDecodeError:
                time.sleep(pause)
            except Exception:
                time.sleep(pause)
    return None, None, None

def fetch_rss(url, n=5):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(resp.content, "xml")
    return [{"title":i.title.text, "link":i.link.text, "date":i.pubDate.text[:16]} for i in soup.find_all("item")[:n]]

def read_screener_table(code, idx):
    resp = requests.get(f"https://www.screener.in/company/{code}/consolidated/", headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table", class_="data-table")
    if len(tables)>idx:
        return pd.read_html(str(tables[idx]), flavor="html5lib")[0]
    return None

def extract_text(b, fn):
    ext = fn.lower()
    if ext.endswith(".pdf"):
        pdf = PdfReader(io.BytesIO(b))
        return "\n".join(p.extract_text() or "" for p in pdf.pages)
    if ext.endswith(".pptx"):
        prs = Presentation(io.BytesIO(b))
        txt=[]
        for slide in prs.slides:
            for shp in slide.shapes:
                if hasattr(shp,"text"):
                    txt.append(shp.text)
        return "\n".join(txt)
    return ""

def analyze_ai(text, prompt):
    if not client: return "⚠️ Perplexity key missing."
    try:
        res = client.chat.completions.create(
            model="sonar-pro",
            messages=[{"role":"system","content":prompt},{"role":"user","content":text[:12000]}]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# Sidebar
st.sidebar.title("🔍 Search & Upload")
query = st.sidebar.text_input("Enter ticker or company")
uploads = st.sidebar.file_uploader("Upload PPT/PDF", accept_multiple_files=True, type=["pdf","pptx"])

if not query:
    st.info("Enter a stock ticker to begin."); st.stop()

ticker, info, hist = resolve_ticker(query)
if not ticker:
    st.error("No data found for that ticker."); st.stop()

code = ticker.replace(".NS","").replace(".BO","")
st.markdown(f"<div class='section-title'>💹 {ticker}</div>", unsafe_allow_html=True)

# Price & Chart
c1,c2,c3 = st.columns(3)
c1.metric("Price", f"₹{info.get('regularMarketPrice','N/A')}")
c2.metric("52W High", f"₹{info.get('fiftyTwoWeekHigh','N/A')}")
c3.metric("52W Low", f"₹{info.get('fiftyTwoWeekLow','N/A')}")
if not hist.empty: st.line_chart(hist["Close"])

# Sector Trends
st.markdown("<div class='section-title'>🌐 Sectoral Trends</div>", unsafe_allow_html=True)
sector = info.get("sector","")
if sector:
    for item in fetch_rss(f"https://news.google.com/rss/search?q={sector}+india",7):
        st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

# News & Competition
st.markdown("<div class='section-title'>📰 News & Competition</div>", unsafe_allow_html=True)
for label,url in [
    ("Google News",f"https://news.google.com/rss/search?q={code}+stock+india"),
    ("ET Top Stories","https://economictimes.indiatimes.com/rssfeedstopstories.cms"),
    ("ET Industry","https://economictimes.indiatimes.com/rss/etindustryrss.cms"),
    ("Mint","https://www.livemint.com/rss/news")
]:
    st.markdown(f"**{label}**")
    for i in fetch_rss(url,5):
        st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")

# Financial Tables
for title,idx in [("📊 P&L (5Y)",0),("📐 Ratios",1),("🤝 Peers",2)]:
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    df = read_screener_table(code,idx)
    df is not None and st.dataframe(df) or st.info(f"{title} unavailable.")

# Community Threads
st.markdown("<div class='section-title'>💬 Community Threads (90d)</div>", unsafe_allow_html=True)
# ValuePickr
vp = fetch_rss("https://valuepickr4.rssing.com/chan-72344682/latest.php",15)
import pandas as pd
df_vp = pd.DataFrame([{"Date":i["date"],"Topic":i["title"],"URL":i["link"]} for i in vp])
st.dataframe(df_vp)
# Reddit via Google News search
reddit = fetch_rss(f"https://news.google.com/rss/search?q={code}+site:reddit.com",15)
df_rd = pd.DataFrame([{"Date":i["date"],"Title":i["title"],"URL":i["link"]} for i in reddit])
st.markdown("**Reddit Top Posts**"); st.dataframe(df_rd)

# AI Management Analysis
if uploads and client:
    st.markdown("<div class='section-title'>🤖 AI Management Analysis</div>", unsafe_allow_html=True)
    for f in uploads:
        txt = extract_text(f.read(), f.name)
        summ = analyze_ai(txt,"Summarize management commentary.")
        mat  = analyze_ai(txt,"Score management integrity.")
        st.subheader(f.name); st.write(summ); st.write("**Integrity Matrix:**", mat)
elif not client:
    st.warning("Perplexity API key not set—AI disabled.")

# Quick Link
st.markdown("<div class='section-title'>🔗 ValuePickr Search</div>", unsafe_allow_html=True)
st.markdown(f"[Search {code} on ValuePickr](https://forum.valuepickr.com/search?q={code})")
