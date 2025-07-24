import os, io, datetime as dt
import streamlit as st

# Minimal imports up-front: heavy libs loaded inside functions
def lazy_imports():
    global requests, yfinance, pd, BeautifulSoup, PdfReader, Presentation, OpenAI, feedparser
    import requests
    import yfinance as yf
    import pandas as pd
    from bs4 import BeautifulSoup
    from pypdf import PdfReader
    from pptx import Presentation
    from openai import OpenAI
    import feedparser

lazy_imports()

# --- CONFIG & STYLES
st.set_page_config(page_title="Smart Equity Dossier", layout="wide")
st.markdown("""
<style>
body { background-color: #191c1f; color:#e6eefa;}
.stApp { background:#191c1f; }
.section-title { color:#39ff14; font-size:1.25em; margin-top:1rem; }
.card { background:#2a2d31; padding:1rem; border-radius:8px; }
a { color:#39ff14; }
</style>
""", unsafe_allow_html=True)

# --- API Secret/key
PPLX_KEY = st.secrets.get("PPLX_API_KEY") or os.getenv("PPLX_API_KEY")
client = None
if PPLX_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=PPLX_KEY, base_url="https://api.perplexity.ai")

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64)"}

def resolve_ticker(ticker):
    import yfinance as yf
    ticker, _ = ticker.strip().upper(), None
    for s in [".NS", ".BO"]:
        tkr = f"{ticker}{s}"
        info = yf.Ticker(tkr).info
        if info.get("regularMarketPrice"):
            hist = yf.Ticker(tkr).history(period="5y")
            return tkr, info, hist
    return None, None, None

def read_html_table_screener(ticker_code, table_index):
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd
    url = f"https://www.screener.in/company/{ticker_code}/consolidated/"
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    tables = soup.find_all("table", class_="data-table")
    if len(tables) > table_index:
        return pd.read_html(str(tables[table_index]), flavor="html5lib")[0]
    return None

def fetch_rss_items(rss_url, max_items=5):
    import requests
    from bs4 import BeautifulSoup
    r = requests.get(rss_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.content, "xml")
    items = soup.find_all("item")[:max_items]
    return [{"title": i.title.text, "link": i.link.text, "date": i.pubDate.text[:16]} for i in items]

def get_news(feed_func, arg, label):
    news = feed_func(arg)
    st.markdown(f"**{label}**")
    for item in news:
        st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

def get_management_info(ticker_code):
    import requests
    from bs4 import BeautifulSoup
    url = f"https://www.screener.in/company/{ticker_code}/company-information/"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    names = soup.find_all("td", class_="align-left")
    return [n.text.strip() for n in names][:5] if names else ["No management data found."]

def extract_text_from_file(file_bytes, filename):
    ext = filename.lower()
    if ext.endswith(".pdf"):
        from pypdf import PdfReader
        pdf = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif ext.endswith(".pptx"):
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
        return f"Error during Perplexity API call: {e}"

# --- ValuePickr & Reddit: use only feedparser, skip psaw for reliability
def fetch_valuepickr_threads(n=15):
    import feedparser, re
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=90)
    feed = feedparser.parse("https://valuepickr4.rssing.com/chan-72344682/latest.php")
    threads = []
    for entry in feed.entries:
        dt_p = dt.datetime(*entry.published_parsed[:6])
        if dt_p < cutoff:
            continue
        m = re.search(r"\[Replies:\s*(\d+)\]", entry.title)
        replies = int(m.group(1)) if m else 0
        threads.append({"Date": dt_p, "Replies": replies, "Topic": entry.title.split(" [")[0], "URL": entry.link})
    import pandas as pd
    df = pd.DataFrame(threads)
    if df.empty:
        return df
    return df.sort_values(["Replies", "Date"], ascending=False).head(n)

def fetch_reddit_threads_gnews(ticker, n=15):
    # work around unreliable Pushshift: get top Reddit posts via Google News RSS search for "reddit"
    news = fetch_rss_items(f"https://news.google.com/rss/search?q={ticker}+site:reddit.com", n)
    import pandas as pd
    return pd.DataFrame([{"Date": i['date'], "Title": i['title'], "URL": i['link']} for i in news])

# --- Streamlit sidebar/input
st.sidebar.title("🔍 Search & Upload")
user_input = st.sidebar.text_input("Enter NSE/BSE ticker or company name")
uploaded_files = st.sidebar.file_uploader("Upload Investor Presentations/PDFs", accept_multiple_files=True, type=['pdf', 'pptx'])

if not user_input:
    st.info("Enter a ticker symbol in the sidebar to begin.")
    st.stop()

ticker_resolved, stock_info, stock_hist = resolve_ticker(user_input.upper())
if ticker_resolved is None or stock_info is None:
    st.error("Ticker not found or no current data (Yahoo Finance).")
    st.stop()

ticker_code = ticker_resolved.replace(".NS", "").replace(".BO", "")
st.markdown(f"<div class='section-title'>💹 {ticker_resolved}</div>", unsafe_allow_html=True)

# --- Price summary metrics
c1, c2, c3 = st.columns(3)
c1.metric("Current Price", f"₹{stock_info.get('regularMarketPrice', 'N/A')}")
c2.metric("52-Week High", f"₹{stock_info.get('fiftyTwoWeekHigh', 'N/A')}")
c3.metric("52-Week Low", f"₹{stock_info.get('fiftyTwoWeekLow', 'N/A')}")
if not stock_hist.empty:
    st.line_chart(stock_hist["Close"])
else:
    st.info("Pricing data history not available.")

# --- Sectoral Trends & Triggers
st.markdown("<div class='section-title'>🌐 Sectoral Trends & Triggers (Last 7 Days)</div>", unsafe_allow_html=True)
sector = stock_info.get("sector", "")
if sector:
    get_news(fetch_rss_items, f"https://news.google.com/rss/search?q={sector}+india", "Google News Sector")
else:
    st.info("No sector specified for this company.")

# --- News & Competition (Google, ET, Mint)
st.markdown("<div class='section-title'>📰 News & Competition</div>", unsafe_allow_html=True)
get_news(fetch_rss_items, f"https://news.google.com/rss/search?q={ticker_code}+stock+india", "Google News (Company)")
get_news(fetch_rss_items, "https://economictimes.indiatimes.com/rssfeedstopstories.cms", "Economic Times - Top Stories")
get_news(fetch_rss_items, "https://economictimes.indiatimes.com/rss/etindustryrss.cms", "Economic Times - Industry News")
get_news(fetch_rss_items, "https://www.livemint.com/rss/news", "Mint - Latest News")

# --- Community Threads: ValuePickr & Reddit
st.markdown("<div class='section-title'>💬 Community Threads (Last 90 Days)</div>", unsafe_allow_html=True)
st.markdown("**ValuePickr Top Discussions**")
vp_df = fetch_valuepickr_threads()
if not vp_df.empty:
    st.dataframe(vp_df)
else:
    st.info("No ValuePickr forum threads found.")

st.markdown("**Reddit Top Posts (via Google News search)**")
reddit_df = fetch_reddit_threads_gnews(ticker_code)
if not reddit_df.empty:
    st.dataframe(reddit_df)
else:
    st.info("No Reddit posts found.")

# --- AI Management Analysis (Perplexity)
if uploaded_files and client:
    st.markdown("<div class='section-title'>🤖 AI-Powered Management Analysis</div>", unsafe_allow_html=True)
    for f in uploaded_files:
        file_bytes = f.read()
        text_content = extract_text_from_file(file_bytes, f.name)
        with st.spinner(f"Analyzing {f.name} with Perplexity AI…"):
            mgmt_summary = analyze_perplexity_document(
                text_content,
                "You are an equity research analyst. Provide a concise bulleted summary of management commentary focusing on strategy, guidance, risks, and governance from this company document."
            )
            integrity_matrix = analyze_perplexity_document(
                text_content,
                "Assess management integrity: Score Guidance Accuracy, Delivery vs Promise, Transparency, and Governance Flags from 1 to 10, with evidence from this document."
            )
        st.subheader(f"Document: {f.name}")
        st.markdown("#### Management Summary")
        st.write(mgmt_summary)
        st.markdown("#### Integrity Matrix")
        st.write(integrity_matrix)
elif not client:
    st.warning("Add your Perplexity API key in Streamlit secrets for AI sections.")

# Quick ValuePickr Search Link
st.markdown("<div class='section-title'>🔗 ValuePickr Forum Search</div>", unsafe_allow_html=True)
st.markdown(f"[Open ValuePickr discussions for {ticker_code}](https://forum.valuepickr.com/search?q={ticker_code})")
