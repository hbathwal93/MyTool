import os, io, datetime as dt, streamlit as st
from twelvedata import TDClient
import pandas as pd

# UI config
st.set_page_config(page_title="Smart Equity Dossier", layout="wide")
st.markdown("""
<style>
body { background:#191c1f; color:#e6eefa; }
.section-title { color:#39ff14; font-size:1.3em; margin-top:1rem; }
a { color:#39ff14; }
</style>
""", unsafe_allow_html=True)

# API keys
TD_KEY = st.secrets.get("TD_API_KEY") or os.getenv("TD_API_KEY")
td = TDClient(apikey=TD_KEY) if TD_KEY else None
PPLX_KEY = st.secrets.get("PPLX_API_KEY") or os.getenv("PPLX_API_KEY")
if PPLX_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=PPLX_KEY, base_url="https://api.perplexity.ai")
else:
    client = None

# Helpers
def get_time_series(symbol):
    try:
        return td.time_series(symbol=symbol, interval="1day", outputsize=1825).as_pandas()
    except Exception:
        return pd.DataFrame()

def get_current_price(symbol):
    try:
        return float(td.price(symbol=symbol).as_json()["value"])
    except Exception:
        return None

def fetch_rss(url, n=5):
    import requests
    from bs4 import BeautifulSoup
    resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(resp.content, "xml")
    return [{"title":i.title.text, "link":i.link.text, "date":i.pubDate.text[:16]}
            for i in soup.find_all("item")[:n]]

def extract_text(b, fn):
    if fn.lower().endswith(".pdf"):
        from pypdf import PdfReader
        pdf = PdfReader(io.BytesIO(b))
        return "\n".join(p.extract_text() or "" for p in pdf.pages)
    if fn.lower().endswith(".pptx"):
        from pptx import Presentation
        prs = Presentation(io.BytesIO(b))
        txt=[]
        for slide in prs.slides:
            for shp in slide.shapes:
                if hasattr(shp,"text"):
                    txt.append(shp.text)
        return "\n".join(txt)
    return ""

def analyze_ai(text, prompt):
    if not client:
        return "⚠️ Perplexity key missing."
    res = client.chat.completions.create(
        model="sonar-pro",
        messages=[{"role":"system","content":prompt},
                  {"role":"user","content":text[:12000]}]
    )
    return res.choices[0].message.content

# Sidebar
st.sidebar.title("🔍 Search & Upload")
symbol = st.sidebar.text_input("Enter symbol (e.g. RELIANCE.BSE or INFY.NSE)")
uploads = st.sidebar.file_uploader("Upload PDF/PPTX", accept_multiple_files=True, type=["pdf","pptx"])
if not symbol:
    st.info("Enter a symbol to begin."); st.stop()

# Data fetch
ts = get_time_series(symbol)
price = get_current_price(symbol)
if ts.empty or price is None:
    st.error(f"No data for {symbol}. Please check symbol or API limits."); st.stop()

# Display price & chart
st.markdown(f"<div class='section-title'>💹 {symbol}</div>", unsafe_allow_html=True)
c1,c2,c3 = st.columns(3)
c1.metric("Current Price", f"₹{price}")
c2.metric("52W High", f"₹{ts['high'].max():.2f}")
c3.metric("52W Low", f"₹{ts['low'].min():.2f}")
st.line_chart(ts["close"])

# News & competition
st.markdown("<div class='section-title'>📰 News & Competition</div>", unsafe_allow_html=True)
for label,url in [
    ("Google News", f"https://news.google.com/rss/search?q={symbol}+stock+india"),
    ("ET Top Stories","https://economictimes.indiatimes.com/rssfeedstopstories.cms"),
    ("ET Industry","https://economictimes.indiatimes.com/rss/etindustryrss.cms"),
    ("Mint","https://www.livemint.com/rss/news")
]:
    st.markdown(f"**{label}**")
    for item in fetch_rss(url,5):
        st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

# Forum threads
st.markdown("<div class='section-title'>💬 Community Threads (90d)</div>", unsafe_allow_html=True)
import feedparser
vp = feedparser.parse("https://valuepickr4.rssing.com/chan-72344682/latest.php")
threads=[]; cutoff=dt.datetime.utcnow()-dt.timedelta(days=90)
for e in vp.entries:
    pub=dt.datetime(*e.published_parsed[:6])
    if pub<cutoff: continue
    import re
    m=re.search(r"\[Replies:\s*(\d+)\]", e.title)
    threads.append({"Date":pub,"Replies":int(m.group(1)) if m else0,
                    "Topic":e.title.split(" [")[0],"URL":e.link})
st.dataframe(pd.DataFrame(threads).sort_values(["Replies","Date"],ascending=False).head(15))

# AI-powered analysis
if uploads and client:
    st.markdown("<div class='section-title'>🤖 AI Management Analysis</div>", unsafe_allow_html=True)
    for f in uploads:
        text = extract_text(f.read(), f.name)
        summ = analyze_ai(text, "Summarize management commentary: strategy, guidance, risks.")
        mat  = analyze_ai(text, "Score management integrity: Guidance Accuracy, Delivery vs Promise, Transparency, Governance.")
        st.subheader(f.name); st.write(summ); st.write("**Integrity Matrix:**", mat)
elif not client:
    st.warning("Perplexity API key missing—AI sections disabled.")

# Quick forum search link
st.markdown("<div class='section-title'>🔗 ValuePickr Forum Search</div>", unsafe_allow_html=True)
st.markdown(f"[Search discussions for {symbol}](https://forum.valuepickr.com/search?q={symbol})")
