import os, io, datetime as dt, streamlit as st
from twelvedata import TDClient
from json import JSONDecodeError

# UI config
st.set_page_config(page_title="Smart Equity Dossier", layout="wide")
st.markdown("""
<style>
body { background: #191c1f; color: #e6eefa; }
.section-title { color: #39ff14; font-size:1.3em; margin-top:1rem; }
a { color: #39ff14; }
</style>
""", unsafe_allow_html=True)

# API keys
TD_KEY = st.secrets.get("TD_API_KEY") or os.getenv("TD_API_KEY")
td = TDClient(apikey=TD_KEY) if TD_KEY else None
PPLX_KEY = st.secrets.get("PPLX_API_KEY") or os.getenv("PPLX
