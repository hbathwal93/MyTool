import os, io, datetime as dt, streamlit as st
from json import JSONDecodeError

# Lazy imports inside functions
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

# UI config & styling
st.set_page_config(page_title="Smart Equity Dossier", layout="wide")
st.markdown("""
<style>
body { background-color: #191c1f; color: #e6eefa; }
.section-title { color: #39ff14; font-size:1.3em; margin-top:1rem; }
a { color: #39ff14; }
</style>
""", unsafe_allow_html=True)

# Perplexity AI client setup
PPLX_KEY = st.secrets.get("PPLX_API_KEY") or os.getenv("PPLX_API_KEY")
client = None
if PPLX_KEY:
    from openai import OpenAI as _OpenAI
    client = _OpenAI(api_key=PPLX_KEY, base_url="https://api.perplexity.ai")

HEADERS = {"User-Agent": "Mozilla/5.0"}

def resolve_ticker(user_input: str):
    """Try NSE then BSE; catch JSONDecodeError and other exceptions."""
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

def extract_text(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader as _PdfReader
        pdf = _PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
    if filename.lower().endswith(".pptx"):
        from pptx import Presentation as _Presentation
        prs = _Presentation(io.BytesIO(file_bytes))
        texts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    texts.append(shape.text)
        return "\n".join(texts)
    return ""

def analyze_perplexity(text: str, prompt: str) -> str:
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

# Sidebar input
st.sidebar.title("🔍 Search & Upload")
query = st.sidebar.text_input("Enter NSE/BSE ticker or company name")
uploads = st.sidebar.file_uploader("Upload PPT/PDF for AI analysis", accept_multiple_files=True, type=["pdf","pptx"])

if not query:
    st.info("Enter a ticker to begin.")
    st.stop()

ticker, info, hist = resolve_ticker(query)
if ticker is None:
    st.error("❌ Could not fetch data for that ticker. Please check the symbol or try again later.")
    st.stop()

code = ticker.replace(".NS","").replace(".BO","")
st.markdown(f"<div class='section-title'>💹 {ticker}</div>", unsafe_allow_html=True)

# Price & chart
c1, c2, c3 = st.columns(3)
c1.metric("Current Price", f"₹{info.get('regularMarketPrice','N/A')}")
c2.metric("52W High", f"₹{info.get('fiftyTwoWeekHigh','N/A')}")
c3.metric("52W Low", f"₹{info.get('fiftyTwoWeekLow','N/A')}")
if not hist.empty:
    st.line_chart(hist["Close"])

# Sectoral Trends & Triggers
st.markdown("<div class='section-title'>🌐 Sectoral Trends & Triggers</div>", unsafe_allow_html=True)
sector = info.get("sector","")
if sector:
    for i in fetch_rss_items(f"https://news.google.com/rss/search?q={sector}+india", 7):
        st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")

# News & Competition
st.markdown("<div class='section-title'>📰 News & Competition</div>", unsafe_allow_html=True)
# Google News (company)
for i in fetch_rss_items(f"https://news.google.com/rss/search?q={code}+stock+india",5):
    st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")
# ET Top Stories
st.markdown("**Economic Times - Top Stories**")
for i in fetch_rss_items("https://economictimes.indiatimes.com/rssfeedstopstories.cms",5):
    st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")
# ET Industry
st.markdown("**Economic Times - Industry News**")
for i in fetch_rss_items("https://economictimes.indiatimes.com/rss/etindustryrss.cms",5):
    st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")
# Mint
st.markdown("**Mint - Latest News**")
for i in fetch_rss_items("https://www.livemint.com/rss/news",5):
    st.write(f"- [{i['title']}]({i['link']}) — *{i['date']}*")

# P&L, Ratios, Peers
st.markdown("<div class='section-title'>📊 Profit & Loss (5Y)</div>", unsafe_allow_html=True)
pnl = read_screener_table(code,0)
if pnl is not None: st.dataframe(pnl) 
else: st.info("P&L unavailable.")
st.markdown("<div class='section-title'>📐 Key Ratios</div>", unsafe_allow_html=True)
rat = read_screener_table(code,1)
if rat is not None: st.dataframe(rat)
else: st.info("Ratios unavailable.")
st.markdown("<div class='section-title'>🤝 Peer Comparison</div>", unsafe_allow_html=True)
pe = read_screener_table(code,2)
if pe is not None: st.dataframe(pe)
else: st.info("Peers unavailable.")

# Community Threads
st.markdown("<div class='section-title'>💬 Community Threads (90d)</div>", unsafe_allow_html=True)
# ValuePickr
vp = feedparser.parse("https://valuepickr4.rssing.com/chan-72344682/latest.php")
threads=[]; cutoff=dt.datetime.utcnow()-dt.timedelta(days=90)
for e in vp.entries:
    pub=dt.datetime(*e.published_parsed[:6])
    if pub<cutoff: continue
    import re
    m=re.search(r"\[Replies:\s*(\d+)\]", e.title)
    threads.append({"Date":pub,"Replies":int(m.group(1)) if m else 0,"Topic":e.title.split(" [")[0],"URL":e.link})
df_vp = pd.DataFrame(threads).sort_values(["Replies","Date"],ascending=False).head(15)
st.dataframe(df_vp)
# Reddit via Google News
items = fetch_rss_items(f"https://news.google.com/rss/search?q={code}+site:reddit.com",15)
df_rd = pd.DataFrame([{"Date":i["date"],"Title":i["title"],"URL":i["link"]} for i in items])
st.markdown("**Reddit Top Discussions**")
st.dataframe(df_rd)

# AI-Powered Management Analysis
if uploads and client:
    st.markdown("<div class='section-title'>🤖 AI Management Analysis</div>", unsafe_allow_html=True)
    for f in uploads:
        b=f.read(); txt=extract_text(b,f.name)
        with st.spinner(f"Analyzing {f.name}…"):
            summ=analyze_perplexity(txt,"You are an equity analyst. Summarize management commentary.")
            mat=analyze_perplexity(txt,"Score management integrity: Guidance, Delivery, Transparency, Governance.")
        st.subheader(f.name); st.write(summ); st.write("**Integrity Matrix:**", mat)
elif not client:
    st.warning("Perplexity API key missing—AI sections disabled.")

# Quick ValuePickr link
st.markdown("<div class='section-title'>🔗 ValuePickr Forum Search</div>", unsafe_allow_html=True)
st.markdown(f"[Search on ValuePickr for {code}](https://forum.valuepickr.com/search?q={code})")
