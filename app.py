import os
import io
import datetime as dt
import streamlit as st

# Lazy imports inside functions
def import_dependencies():
    global requests, yfinance, pd, BeautifulSoup, PdfReader, Presentation, OpenAI, feedparser
    import requests
    import yfinance as yf
    import pandas as pd
    from bs4 import BeautifulSoup
    from pypdf import PdfReader
    from pptx import Presentation
    from openai import OpenAI
    import feedparser

import_dependencies()

# UI Config & Styles
st.set_page_config(page_title="Smart Equity Dossier", layout="wide")
ACCENT = "#39ff14"
BG = "#191c1f"
CARD = "#2a2d31"
st.markdown(f"""
<style>
body {{background-color:{BG}; color:#e6eefa;}}
.stApp {{background:{BG};}}
.section-title {{color:{ACCENT}; font-size:1.25em; margin-top:1rem;}}
.card {{background:{CARD}; padding:1rem; border-radius:8px;}}
a {{color:{ACCENT};}}
</style>
""", unsafe_allow_html=True)

# Perplexity.Client Setup
PPLX_KEY = st.secrets.get("PPLX_API_KEY") or os.getenv("PPLX_API_KEY")
client = OpenAI(api_key=PPLX_KEY, base_url="https://api.perplexity.ai") if PPLX_KEY else None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
}

def resolve_ticker(ticker):
    yf_ticker = yf.Ticker(f"{ticker}.NS")
    info = yf_ticker.info
    if info.get("regularMarketPrice") is not None:
        hist = yf_ticker.history(period="5y")
        return f"{ticker}.NS", info, hist
    else:
        yf_ticker = yf.Ticker(f"{ticker}.BO")
        info = yf_ticker.info
        if info.get("regularMarketPrice") is not None:
            hist = yf_ticker.history(period="5y")
            return f"{ticker}.BO", info, hist
    return None, None, None

def read_html_table_screener(ticker_code, table_index):
    url = f"https://www.screener.in/company/{ticker_code}/consolidated/"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table", class_="data-table")
    if len(tables) > table_index:
        # Use pure Python parser to avoid lxml build issues
        return pd.read_html(str(tables[table_index]), flavor="html5lib")[0]
    return None

def fetch_rss_items(rss_url, max_items=5):
    resp = requests.get(rss_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(resp.content, "xml")
    items = soup.find_all("item")[:max_items]
    return [{"title": item.title.text, "link": item.link.text, "date": item.pubDate.text[:16]} for item in items]

def get_news_google(ticker, count=5):
    url = f"https://news.google.com/rss/search?q={ticker}+stock+india"
    return fetch_rss_items(url, count)

def get_news_et_top(count=5):
    url = "https://economictimes.indiatimes.com/rssfeedstopstories.cms"
    return fetch_rss_items(url, count)

def get_news_et_industry(count=5):
    url = "https://economictimes.indiatimes.com/rss/etindustryrss.cms"
    return fetch_rss_items(url, count)

def get_news_mint(count=5):
    url = "https://www.livemint.com/rss/news"
    return fetch_rss_items(url, count)

def get_management_info(ticker_code):
    url = f"https://www.screener.in/company/{ticker_code}/company-information/"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    names = soup.find_all("td", class_="align-left")
    return [n.text.strip() for n in names][:5] if names else ["No management data found."]

def extract_text_from_file(file_bytes, filename):
    if filename.lower().endswith(".pdf"):
        pdf = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif filename.lower().endswith(".pptx"):
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
        return "Perplexity API key is missing or invalid."
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text[:12000]}  # truncate to limit tokens
    ]
    try:
        response = client.chat.completions.create(model="sonar-pro", messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Error during Perplexity API call: {e}"

# Sidebar: Input
st.sidebar.title("🔍 Search & Upload")
user_input = st.sidebar.text_input("Enter stock ticker (NSE/BSE code) or company name")
uploaded_files = st.sidebar.file_uploader("Upload PPT/PDF (Investor Presentation, Calls)", accept_multiple_files=True, type=['pdf', 'pptx'])

if not user_input:
    st.info("Enter a ticker symbol in the sidebar to begin.")
    st.stop()

ticker_resolved, stock_info, stock_hist = resolve_ticker(user_input.upper())
if ticker_resolved is None:
    st.error("Ticker not found on Yahoo Finance. Please check input.")
    st.stop()

ticker_code = ticker_resolved.replace(".NS", "").replace(".BO", "")
st.markdown(f"<div class='section-title'>💹 {ticker_resolved}</div>", unsafe_allow_html=True)

# Price summary
c1, c2, c3 = st.columns(3)
c1.metric("Current Price", f"₹{stock_info.get('regularMarketPrice', 'N/A')}")
c2.metric("52-Week High", f"₹{stock_info.get('fiftyTwoWeekHigh', 'N/A')}")
c3.metric("52-Week Low", f"₹{stock_info.get('fiftyTwoWeekLow', 'N/A')}")
st.line_chart(stock_hist["Close"])

# Sectoral Trends & Triggers
st.markdown("<div class='section-title'>🌐 Sectoral Trends & Triggers (Last 7 Days)</div>", unsafe_allow_html=True)
sector = stock_info.get("sector", "")
sector_news = get_news_google(sector, 7) if sector else []
for item in sector_news:
    st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

# News & Competition
st.markdown("<div class='section-title'>📰 News & Competition</div>", unsafe_allow_html=True)
st.markdown("**Google News (Company)**")
company_news = get_news_google(ticker_code, 5)
for item in company_news:
    st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

st.markdown("**Economic Times - Top Stories**")
et_top_news = get_news_et_top(5)
for item in et_top_news:
    st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

st.markdown("**Economic Times - Industry News**")
et_ind_news = get_news_et_industry(5)
for item in et_ind_news:
    st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

st.markdown("**Mint - Latest News**")
mint_news_list = get_news_mint(5)
for item in mint_news_list:
    st.write(f"- [{item['title']}]({item['link']}) — *{item['date']}*")

# Forum threads (ValuePickr and Reddit)
import pandas as pd
from psaw import PushshiftAPI

def fetch_valuepickr_threads(n=15):
    feed_url = "https://valuepickr4.rssing.com/chan-72344682/latest.php"
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=90)
    feed = feedparser.parse(feed_url)
    threads = []
    for entry in feed.entries:
        pub = dt.datetime(*entry.published_parsed[:6])
        if pub < cutoff:
            continue
        import re
        m = re.search(r"\[Replies:\s*(\d+)\]", entry.title)
        replies = int(m.group(1)) if m else 0
        threads.append({"Date": pub, "Replies": replies, "Topic": entry.title.split(" [")[0], "URL": entry.link})
    df = pd.DataFrame(threads)
    df = df.sort_values(["Replies", "Date"], ascending=False)
    return df.head(n)

def fetch_reddit_threads(subreddits, n=15):
    api = PushshiftAPI()
    now = int(dt.datetime.utcnow().timestamp())
    since = now - 90 * 86400
    posts = []
    for sub in subreddits:
        gen = api.search_submissions(subreddit=sub, after=since, filter=['title', 'num_comments', 'score', 'created_utc', 'full_link'], sort='desc', sort_type='num_comments', limit=n)
        for post in gen:
            posts.append({
                "Date": dt.datetime.utcfromtimestamp(post.created_utc),
                "Subreddit": sub,
                "Comments": post.num_comments,
                "Score": post.score,
                "Title": post.title,
                "URL": post.full_link
            })
    df = pd.DataFrame(posts)
    df = df.sort_values(["Comments", "Score"], ascending=False)
    return df.head(n)

st.markdown("<div class='section-title'>💬 Investor Community Threads (Last 90 Days)</div>", unsafe_allow_html=True)
st.markdown("**ValuePickr Top Discussions**")
vp_df = fetch_valuepickr_threads()
st.dataframe(vp_df)

st.markdown("**Reddit Top Discussions** in r/IndianStockMarket, r/Stocks, r/investingindia")
reddit_df = fetch_reddit_threads(["IndianStockMarket", "Stocks", "investingindia"])
st.dataframe(reddit_df)

# Perplexity AI Management Analysis Section
if uploaded_files and client:
    st.markdown("<div class='section-title'>🤖 AI-Powered Management Analysis</div>", unsafe_allow_html=True)
    for f in uploaded_files:
        bytes_data = f.read()
        text_content = extract_text_from_file(bytes_data, f.name)
        with st.spinner(f"Analyzing {f.name}…"):
            management_summary = analyze_perplexity_document(
                text_content,
                "You are an equity research analyst. Provide a concise bulleted overview of management commentary focusing on strategic direction, guidance, risks, and governance."
            )
            integrity_matrix = analyze_perplexity_document(
                text_content,
                "Assess management integrity by scoring Guidance Accuracy, Delivery vs Promise, Transparency, Governance Flags from 1 to 10 with justification."
            )
        st.subheader(f"Document: {f.name}")
        st.markdown("### Management Summary")
        st.write(management_summary)
        st.markdown("### Integrity Matrix")
        st.write(integrity_matrix)
else:
    if not PPLX_KEY:
        st.warning("Upload PPT/PDF files to enable AI-Powered Management Analysis. Perplexity API key missing.")

# Community Insight Quick Link
st.markdown("<div class='section-title'>🔗 ValuePickr Forum Search</div>", unsafe_allow_html=True)
st.markdown(f"[Open ValuePickr discussions for {ticker_code}](https://forum.valuepickr.com/search?q={ticker_code})")

