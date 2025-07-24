import os
import io
import datetime as dt
import streamlit as st

# Lazy-load heavy dependencies inside functions
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

from json import JSONDecodeError

# UI config & styling
st.set_page_config(page_title="Smart Equity Dossier", layout="wide")
st.markdown("""
<style>
body { background-color: #191c1f; color: #e6eefa; }
.stApp { background: #191c1f; }
.section-title { color: #39ff14; font-size:1.3em; margin-top:1rem; }
.card { background:#2a2d31; padding:1rem; border-radius:8px; }
a { color: #39ff14; }
</style>
""", unsafe_allow_html=True)

# Perplexity AI client setup
PPLX_KEY = st.secrets.get("PPLX_API_KEY") or os.getenv("PPLX_API_KEY")
client = OpenAI(api_key=PPLX_KEY, base_url="https://api.perplexity.ai") if PPLX_KEY else None

HEADERS = {"User-Agent": "Mozilla/5.0"}

def resolve_ticker(user_input: str):
    """
    Try NSE (.NS) then BSE (.BO). 
    Catch JSONDecodeError and other exceptions.
    """
    base = user_input.strip().upper()
    for suffix in (".NS", ".BO"):
        tkr = f"{base}{suffix}"
        try:
            stock = yf.Ticker(tkr)
            info = stock.info
            hist = stock.history(period="5y")
            if info.get("regularMarketPrice") is not None and not hist.empty:
                return tkr, info, hist
        except JSONDecodeError:
            continue
        except Exception:
            continue
    return None, None, None

def fetch_rss_items(rss_url: str, max_items: int = 5):
    resp = requests.get(rss_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(resp.content, "xml")
    items = soup.find_all("item")[:max_items]
    return [{"title": i.title.text, "link": i.link.text, "date": i.pubDate.text[:16]} for i in items]

def read_screener_table(code: str, idx: int):
    url = f"https://www.screener.in/company/{code}/consolidated/"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table", class_="data-table")
    if len(tables) > idx:
        return pd.read_html(str(tables[idx]), flavor="html5lib")[0]
    return None

def extract_text_from_file(b: bytes, filename: str) -> str:
    ext = filename.lower()
    if ext.endswith(".pdf"):
        pdf = PdfReader(io.BytesIO(b))
        return "\n".join(p.extract_text() or "" for p in pdf.pages)
    if ext.endswith(".pptx"):
        prs = Presentation(io.BytesIO(b))
        texts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    texts.append(shape.text)
        return "\n".join(texts)
    return ""

def analyze_doc_with_perplexity(text: str, prompt: str) -> str:
    if client is None:
        return "⚠️ Perplexity API key not set."
    try:
        res = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:12000]}
            ]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# Sidebar
st.sidebar.title("🔍 Search & Upload")
query = st.sidebar.text_input("Enter NSE/BSE ticker or company name")
uploads = st.sidebar.file_uploader("Upload PPT/PDF for AI analysis", accept_multiple_files=True, type=["pdf","pptx"])

if not query:
    st.info("Enter a ticker to begin.")
    st.stop()

# Resolve ticker
ticker, info, hist = resolve_ticker(query)
if not ticker:
    st.error("Could not fetch data. Check ticker or try later.")
    st.stop()

code = ticker.replace(".NS","").replace(".BO","")
st.markdown(f"<div class='section-title'>💹 {ticker}</div>", unsafe_allow_html=True)

# Price & Chart
c1,c2,c3 = st.columns(3)
c1.metric("Current Price", f"₹{info.get('regularMarketPrice','N/A')}")
c2.metric("52W High", f"₹{info.get('fiftyTwoWeekHigh','N/A')}")
c3.metric("52W Low", f"₹{info.get('fiftyTwoWeekLow','N/A')}")
if not hist.empty:
    st.line_chart(hist["Close"])
else:
    st.info("No historical data.")

# Sectoral Trends & Triggers
st.markdown("<div class='section-title'>🌐 Sectoral Trends & Triggers</div>", unsafe_allow_html=True)
sector = info.get("sector","")
if sector:
    items = fetch_rss_items(f"https://news.google.com/rss/search?q={sector}+india", 7)
    for i in items:
        st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")
else:
    st.info("Sector info unavailable.")

# News & Competition
st.markdown("<div class='section-title'>📰 News & Competition</div>", unsafe_allow_html=True)
# Google News (company)
items = fetch_rss_items(f"https://news.google.com/rss/search?q={code}+stock+india", 5)
for i in items:
    st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")
# ET Top Stories
items = fetch_rss_items("https://economictimes.indiatimes.com/rssfeedstopstories.cms", 5)
st.markdown("**Economic Times - Top Stories**")
for i in items:
    st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")
# ET Industry
items = fetch_rss_items("https://economictimes.indiatimes.com/rss/etindustryrss.cms", 5)
st.markdown("**Economic Times - Industry News**")
for i in items:
    st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")
# Mint
items = fetch_rss_items("https://www.livemint.com/rss/news", 5)
st.markdown("**Mint - Latest News**")
for i in items:
    st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")

# Profit & Loss Table (Screener)
st.markdown("<div class='section-title'>📊 Profit & Loss (5Y)</div>", unsafe_allow_html=True)
pnl = read_screener_table(code, 0)
if pnl is not None:
    st.dataframe(pnl)
else:
    st.info("P&L table unavailable.")

# Key Ratios
st.markdown("<div class='section-title'>📐 Key Financial Ratios</div>", unsafe_allow_html=True)
rat = read_screener_table(code,1)
if rat is not None:
    st.dataframe(rat)
else:
    st.info("Ratios unavailable.")

# Peer Comparison
st.markdown("<div class='section-title'>🤝 Peer Comparison</div>", unsafe_allow_html=True)
peers = read_screener_table(code,2)
if peers is not None:
    st.dataframe(peers)
else:
    st.info("Peer data unavailable.")

# Community Threads
st.markdown("<div class='section-title'>💬 Community Threads (90d)</div>", unsafe_allow_html=True)
# ValuePickr
import feedparser
feed = feedparser.parse("https://valuepickr4.rssing.com/chan-72344682/latest.php")
threads=[]
cutoff=dt.datetime.utcnow()-dt.timedelta(days=90)
for e in feed.entries:
    pub=dt.datetime(*e.published_parsed[:6])
    if pub<cutoff: continue
    import re
    m=re.search(r"\[Replies:\s*(\d+)\]", e.title)
    cnt=int(m.group(1)) if m else 0
    threads.append({"Date":pub,"Replies":cnt,"Topic":e.title.split(" [")[0],"URL":e.link})
df_vp = pd.DataFrame(threads).sort_values(["Replies","Date"],ascending=False).head(15)
st.dataframe(df_vp)
# Reddit via Google News
items = fetch_rss_items(f"https://news.google.com/rss/search?q={code}+site:reddit.com",15)
df_rd=pd.DataFrame([{"Date":i["date"],"Title":i["title"],"URL":i["link"]} for i in items])
st.markdown("**Reddit Top Discussions**")
st.dataframe(df_rd)

# AI-Powered Management Analysis
if uploads and client:
    st.markdown("<div class='section-title'>🤖 AI Management Analysis</div>", unsafe_allow_html=True)
    for f in uploads:
        data = f.read()
        txt = extract_text_from_file(data, f.name)
        with st.spinner(f"Analyzing {f.name}…"):
            summary = analyze_doc_with_perplexity(txt,
                "You are an equity analyst. Summarize management commentary on strategy, guidance, risks.")
            matrix = analyze_doc_with_perplexity(txt,
                "Score management integrity: Guidance Accuracy, Delivery vs Promise, Transparency, Governance.")
        st.subheader(f.name)
        st.write(summary)
        st.write("**Integrity Matrix:**", matrix)
elif not client:
    st.warning("Perplexity API key missing—AI sections disabled.")

# Quick forum link
st.markdown("<div class='section-title'>🔗 ValuePickr Forum Search</div>", unsafe_allow_html=True)
st.markdown(f"[Search on ValuePickr for {code}](https://forum.valuepickr.com/search?q={code})")
