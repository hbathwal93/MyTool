import streamlit as st
import os
from openai import OpenAI
import pandas as pd
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="Investment Research Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional look
st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
    padding: 2rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
}
.analysis-section {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 8px;
    margin: 1rem 0;
    border-left: 4px solid #2a5298;
}
.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
}
.recommendation-buy { background-color: #d4edda; border: 1px solid #c3e6cb; }
.recommendation-hold { background-color: #fff3cd; border: 1px solid #ffeaa7; }
.recommendation-sell { background-color: #f8d7da; border: 1px solid #f5c6cb; }
</style>
""", unsafe_allow_html=True)

# Initialize Perplexity client - OPTIMIZED FOR RENDER.COM
@st.cache_resource
def init_perplexity_client():
    # For Render.com, prioritize environment variables over st.secrets
    api_key = os.getenv("PPLX_API_KEY")
    
    # Only try st.secrets if environment variable is not found
    if not api_key:
        try:
            api_key = st.secrets.get("PPLX_API_KEY")
        except (FileNotFoundError, AttributeError):
            # No secrets file found, which is expected on Render.com
            pass
    
    if api_key:
        return OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
    return None

client = init_perplexity_client()

def query_perplexity(prompt, model="sonar-pro"):
    """Query Perplexity API with error handling"""
    if not client:
        return "⚠️ Perplexity API key not configured. Please add PPLX_API_KEY as environment variable on Render.com."
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional equity research analyst. Provide detailed, fact-based analysis with specific data points, sources, and clear reasoning. Always include current dates and verify information accuracy."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error querying Perplexity: {str(e)}"

# Header
st.markdown("""
<div class="main-header">
    <h1>📊 Professional Investment Research Platform</h1>
    <p>Comprehensive Stock Analysis Powered by Perplexity AI</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for input
st.sidebar.header("🔍 Stock Analysis")
ticker_input = st.sidebar.text_input(
    "Enter Stock Ticker or Company Name:",
    placeholder="e.g., TCS, RELIANCE, AAPL",
    help="Enter NSE/BSE ticker for Indian stocks or standard ticker for international stocks"
)

analysis_date = datetime.now().strftime("%B %d, %Y")
st.sidebar.info(f"Analysis Date: {analysis_date}")

if st.sidebar.button("🚀 Generate Complete Analysis", type="primary"):
    if not ticker_input:
        st.error("Please enter a stock ticker or company name.")
    elif not client:
        st.error("Perplexity API key not configured. Please check your environment variables on Render.com.")
    else:
        ticker = ticker_input.upper().strip()
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Analysis sections
        sections = [
            ("🌐 Sectoral Trends & Triggers", "sectoral_analysis"),
            ("📰 News & Competition", "news_competition"),
            ("💰 Financial Analysis - P&L", "financial_pl"),
            ("🏦 Financial Analysis - Balance Sheet", "financial_bs"),
            ("💸 Financial Analysis - Cash Flow", "financial_cf"),
            ("📊 Ratio Analysis", "ratio_analysis"),
            ("👥 Management Evaluation", "management_eval"),
            ("📈 Management Guidance & Delivery", "management_guidance"),
            ("📋 Investor Presentations Analysis", "investor_presentations"),
            ("🎙️ Conference Calls Analysis", "conference_calls"),
            ("💬 Community & Forum Analysis", "community_analysis"),
            ("📑 Annual Report Forensics", "annual_report"),
            ("🎯 Management Integrity Matrix", "integrity_matrix"),
            ("🚀 Growth Triggers", "growth_triggers"),
            ("💎 Valuation Analysis", "valuation_analysis"),
            ("🎭 Scenario Analysis", "scenario_analysis"),
            ("⭐ Final Recommendation", "final_recommendation")
        ]
        
        results = {}
        
        for i, (title, key) in enumerate(sections):
            status_text.text(f"Analyzing: {title}")
            progress_bar.progress((i + 1) / len(sections))
            
            # Generate specific prompts for each section
            prompt = generate_section_prompt(key, ticker, analysis_date)
            results[key] = query_perplexity(prompt)
            
        status_text.text("Analysis Complete!")
        progress_bar.progress(1.0)
        
        # Display results
        display_analysis_results(ticker, results, analysis_date)

def generate_section_prompt(section_key, ticker, date):
    """Generate specific prompts for each analysis section"""
    
    base_context = f"Analyze {ticker} stock as of {date}. Provide current, factual data with sources."
    
    prompts = {
        "sectoral_analysis": f"""
        {base_context}
        
        Provide a comprehensive sectoral analysis covering:
        1. Current sector trends and growth drivers
        2. Industry structure and competitive dynamics
        3. Recent regulatory changes and policy impacts
        4. Technological disruptions affecting the sector
        5. Upcoming government actions or regulatory changes
        6. Macroeconomic factors influencing the industry
        
        Focus on both positive and negative triggers with specific examples and timeframes.
        """,
        
        "news_competition": f"""
        {base_context}
        
        Analyze recent news and competitive landscape:
        1. Key news from the past 30 days affecting {ticker}
        2. Major competitor developments and announcements
        3. Market share changes and competitive positioning
        4. Industry-wide developments impacting all players
        5. Regulatory news affecting the company/sector
        
        Categorize news as positive, negative, or neutral with reasoning.
        """,
        
        "financial_pl": f"""
        {base_context}
        
        Conduct deep P&L analysis for the last 5 years:
        1. Revenue trends, growth rates, and seasonality
        2. Gross margin evolution and cost structure changes
        3. Operating leverage and efficiency metrics
        4. One-time items and extraordinary expenses
        5. Earnings quality and sustainability assessment
        6. Forward-looking revenue and margin implications
        
        Provide specific numbers, percentages, and year-over-year comparisons.
        """,
        
        "financial_bs": f"""
        {base_context}
        
        Analyze balance sheet strength over 5 years:
        1. Asset quality and composition changes
        2. Debt levels, leverage ratios, and debt maturity profile
        3. Working capital trends and efficiency
        4. Capital allocation patterns
        5. Return on assets and equity trends
        6. Balance sheet risks and strengths vs sector norms
        
        Include specific financial ratios and benchmark comparisons.
        """,
        
        "financial_cf": f"""
        {base_context}
        
        Examine cash flow patterns for 5 years:
        1. Operating cash flow trends and quality
        2. Free cash flow generation and consistency
        3. Capital expenditure patterns and efficiency
        4. Financing activities and dividend policy
        5. Cash conversion cycle analysis
        6. Any unusual cash flow patterns or anomalies
        
        Focus on cash flow sustainability and capital allocation effectiveness.
        """,
        
        "ratio_analysis": f"""
        {base_context}
        
        Provide comprehensive ratio analysis in tabular format:
        Create a table with columns: Ratio | Current | 5-Year Trend | Industry Average | Analysis
        
        Cover these key ratios:
        - Profitability ratios (ROE, ROA, ROCE, Gross/Operating/Net margins)
        - Liquidity ratios (Current, Quick, Cash ratios)
        - Leverage ratios (Debt-to-equity, Interest coverage, Debt service)
        - Efficiency ratios (Asset turnover, Inventory turnover, Receivables turnover)
        - Valuation ratios (P/E, P/B, EV/EBITDA, Price-to-Sales)
        
        Explain trends, drivers, and management influence for each.
        """,
        
        "management_eval": f"""
        {base_context}
        
        Evaluate management quality and track record:
        1. CEO and key executives' background and tenure
        2. Strategic execution capability and past performance
        3. Crisis management and adaptability
        4. Capital allocation decisions and effectiveness
        5. Board composition and independence
        6. Management compensation alignment with performance
        7. Transparency in communications and reporting
        8. Any governance concerns or red flags
        
        Provide specific examples and track record evidence.
        """,
        
        "management_guidance": f"""
        {base_context}
        
        Analyze management guidance history and credibility:
        1. Historical guidance vs actual performance over past 3 years
        2. Quality and specificity of current forward guidance
        3. Management's conservatism vs aggressiveness in projections
        4. Sector comparison of guidance accuracy
        5. Recent changes in guidance and explanations provided
        6. Credibility assessment based on delivery track record
        
        Include specific guidance figures and actual outcomes.
        """,
        
        "investor_presentations": f"""
        {base_context}
        
        Review investor presentations from the last 12 quarters:
        1. Key strategic initiatives and business updates
        2. Product launches and market expansion plans
        3. Segmental performance and revenue mix evolution
        4. EBITDA trends and margin guidance
        5. Capital expenditure plans and utilization
        6. Management's strategic pivots and rationale
        7. Performance against previously stated targets
        
        Extract key themes and assess execution against promises.
        """,
        
        "conference_calls": f"""
        {base_context}
        
        Summarize recent conference calls (last 12 quarters):
        1. Management tone and confidence levels
        2. Growth outlook and new product pipeline
        3. Margin trends and cost management initiatives
        4. Capacity utilization and expansion plans
        5. M&A commentary and corporate actions
        6. Competitive positioning and market share discussions
        7. Guidance changes and reasoning
        
        Compare statements with actual delivery and flag inconsistencies.
        """,
        
        "community_analysis": f"""
        {base_context}
        
        Analyze investor community discussions (last 90 days):
        1. ValuePickr forum discussions and key insights
        2. Reddit and other investment community sentiment
        3. Common concerns and bullish/bearish arguments
        4. Unique insights not found in mainstream analysis
        5. Consensus opinion and contrarian viewpoints
        6. Risk factors highlighted by retail investors
        
        Summarize key themes and assess credibility of community insights.
        """,
        
        "annual_report": f"""
        {base_context}
        
        Conduct forensic analysis of the latest annual report:
        1. Accounting policy changes and their impact
        2. Related party transactions and potential conflicts
        3. Contingent liabilities and off-balance-sheet items
        4. Audit qualifications or concerns raised
        5. Management discussion and forward-looking statements
        6. Hidden gems or strategic insights in disclosures
        7. Any red flags or unusual accounting treatments
        
        Focus on items that might not be evident in standard financial analysis.
        """,
        
        "integrity_matrix": f"""
        {base_context}
        
        Create Management Integrity Matrix with scores (1-10) and evidence:
        
        1. Guidance Accuracy (Score/10): Historical accuracy of forecasts
        2. Delivery vs Promise (Score/10): Execution of stated plans
        3. Transparency & Disclosure (Score/10): Quality of communication
        4. Governance Flags (Score/10): Any red flags or concerns
        5. Overall Integrity (Score/10): Combined assessment
        
        For each KPI, provide:
        - Specific score out of 10
        - 2-3 concrete examples as evidence
        - Reasoning for the score assigned
        - Recent developments affecting the score
        """,
        
        "growth_triggers": f"""
        {base_context}
        
        Identify key growth catalysts and triggers:
        1. Operating leverage potential and scalability
        2. Capacity utilization trends and expansion benefits
        3. Recent acquisitions and their revenue contribution
        4. New product launches and market penetration
        5. Market expansion opportunities (geographic/segment)
        6. Technology upgrades and digital transformation impact
        7. Regulatory changes benefiting the company
        
        Quantify potential impact and provide realistic timelines.
        """,
        
        "valuation_analysis": f"""
        {base_context}
        
        Comprehensive valuation analysis:
        1. Current valuation ratios: P/E, P/S, PEG, P/B, EV/EBITDA
        2. Peer comparison with 3-4 closest competitors
        3. Historical valuation trends (5-year range)
        4. Sector average comparisons
        5. DCF-based intrinsic value estimate
        6. Sum-of-parts valuation if applicable
        7. Assessment: Overvalued, fairly valued, or undervalued
        
        Provide specific numbers, peer names, and reasoning for valuation conclusion.
        """,
        
        "scenario_analysis": f"""
        {base_context}
        
        Create three detailed scenarios:
        
        BULL CASE:
        - Key catalysts and positive triggers
        - Revenue/margin upside potential
        - Target price and timeline
        - Probability assessment
        - Investment strategy recommendations
        
        BASE CASE:
        - Realistic growth assumptions
        - Steady-state margins and returns
        - Fair value estimate
        - Most likely outcome
        - Prudent positioning strategy
        
        BEAR CASE:
        - Key risks and negative catalysts
        - Downside scenarios and impact
        - Worst-case target price
        - Risk mitigation strategies
        - Exit triggers
        
        Include specific price targets and probability weightings.
        """,
        
        "final_recommendation": f"""
        {base_context}
        
        Provide final investment recommendation:
        1. Overall investment thesis (Buy/Hold/Sell)
        2. Key supporting arguments (3-4 main points)
        3. Target price and time horizon
        4. Risk-reward assessment
        5. Position sizing recommendations
        6. Key monitoring triggers and metrics
        7. Conditions that would change the recommendation
        
        Structure as executive summary suitable for investment committee presentation.
        Ensure recommendation is clearly justified based on all previous analysis.
        """
    }
    
    return prompts.get(section_key, f"{base_context}\n\nProvide detailed analysis for {section_key}")

def display_analysis_results(ticker, results, date):
    """Display comprehensive analysis results"""
    
    # Main title
    st.markdown(f"""
    # 📊 Comprehensive Investment Analysis: {ticker}
    **Analysis Date:** {date}
    **Generated by:** Perplexity AI-Powered Research Platform
    
    ---
    """)
    
    # Executive Summary Tab Layout
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Core Analysis", "💼 Management & Governance", "📊 Valuation & Scenarios", "🎯 Final Recommendation"])
    
    with tab1:
        # Core financial analysis
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 🌐 Sectoral Trends & Triggers")
            st.markdown(results.get('sectoral_analysis', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 💰 Profit & Loss Analysis (5-Year)")
            st.markdown(results.get('financial_pl', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 💸 Cash Flow Analysis (5-Year)")
            st.markdown(results.get('financial_cf', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 📰 News & Competition")
            st.markdown(results.get('news_competition', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 🏦 Balance Sheet Analysis (5-Year)")
            st.markdown(results.get('financial_bs', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 📊 Comprehensive Ratio Analysis")
            st.markdown(results.get('ratio_analysis', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        # Management and governance analysis
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 👥 Management Evaluation")
            st.markdown(results.get('management_eval', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 📋 Investor Presentations Analysis")
            st.markdown(results.get('investor_presentations', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 💬 Community & Forum Analysis")
            st.markdown(results.get('community_analysis', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 📈 Management Guidance & Delivery")
            st.markdown(results.get('management_guidance', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 🎙️ Conference Calls Analysis")
            st.markdown(results.get('conference_calls', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 📑 Annual Report Forensics")
            st.markdown(results.get('annual_report', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Management Integrity Matrix - Full width
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.markdown("## 🎯 Management Integrity Matrix")
        st.markdown(results.get('integrity_matrix', 'Analysis not available'))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        # Valuation and scenario analysis
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 🚀 Growth Triggers")
            st.markdown(results.get('growth_triggers', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.markdown("## 💎 Valuation Analysis")
            st.markdown(results.get('valuation_analysis', 'Analysis not available'))
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Scenario Analysis - Full width
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.markdown("## 🎭 Scenario Analysis: Bull, Base & Bear Cases")
        st.markdown(results.get('scenario_analysis', 'Analysis not available'))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab4:
        # Final recommendation with highlight
        recommendation_text = results.get('final_recommendation', 'Recommendation not available')
        
        # Try to extract recommendation type for styling
        rec_class = "recommendation-hold"  # default
        if "buy" in recommendation_text.lower() and "don't buy" not in recommendation_text.lower():
            rec_class = "recommendation-buy"
        elif "sell" in recommendation_text.lower():
            rec_class = "recommendation-sell"
        
        st.markdown(f'<div class="analysis-section {rec_class}">', unsafe_allow_html=True)
        st.markdown("## ⭐ Final Investment Recommendation")
        st.markdown(recommendation_text)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Download button for full report
        full_report = generate_full_report(ticker, results, date)
        st.download_button(
            label="📄 Download Complete Analysis Report",
            data=full_report,
            file_name=f"{ticker}_Investment_Analysis_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )

def generate_full_report(ticker, results, date):
    """Generate downloadable markdown report"""
    report = f"""# Investment Analysis Report: {ticker}
Generated on: {date}
Analyst: AI-Powered Research Platform

---

## Executive Summary
{results.get('final_recommendation', 'Not available')}

---

## 1. Sectoral Trends & Triggers
{results.get('sectoral_analysis', 'Not available')}

---

## 2. News & Competition Analysis
{results.get('news_competition', 'Not available')}

---

## 3. Financial Analysis

### 3.1 Profit & Loss (5-Year Review)
{results.get('financial_pl', 'Not available')}

### 3.2 Balance Sheet Analysis (5-Year Review)
{results.get('financial_bs', 'Not available')}

### 3.3 Cash Flow Statement Analysis (5-Year Review)
{results.get('financial_cf', 'Not available')}

---

## 4. Ratio Analysis
{results.get('ratio_analysis', 'Not available')}

---

## 5. Management Evaluation

### 5.1 Overall Management Assessment
{results.get('management_eval', 'Not available')}

### 5.2 Management Guidance & Delivery
{results.get('management_guidance', 'Not available')}

### 5.3 Investor Presentations Analysis
{results.get('investor_presentations', 'Not available')}

### 5.4 Conference Calls Analysis
{results.get('conference_calls', 'Not available')}

---

## 6. Community & Forum Analysis
{results.get('community_analysis', 'Not available')}

---

## 7. Annual Report Forensics
{results.get('annual_report', 'Not available')}

---

## 8. Management Integrity Matrix
{results.get('integrity_matrix', 'Not available')}

---

## 9. Growth Triggers
{results.get('growth_triggers', 'Not available')}

---

## 10. Valuation Analysis
{results.get('valuation_analysis', 'Not available')}

---

## 11. Scenario Analysis
{results.get('scenario_analysis', 'Not available')}

---

## 12. Final Recommendation
{results.get('final_recommendation', 'Not available')}

---

*This report was generated using AI-powered analysis and should be used in conjunction with additional research and professional advice.*
"""
    return report

# Sidebar information
st.sidebar.markdown("---")
st.sidebar.markdown("### 📝 Analysis Includes:")
st.sidebar.markdown("""
✅ Sectoral trends & triggers  
✅ News & competition analysis  
✅ 5-year financial forensics  
✅ Comprehensive ratio analysis  
✅ Management evaluation  
✅ Community sentiment analysis  
✅ Growth triggers identification  
✅ Valuation & peer comparison  
✅ Bull/Bear/Base scenarios  
✅ Final investment recommendation  
""")

st.sidebar.markdown("### ⚙️ Configuration")
if st.sidebar.button("🔧 Check API Configuration"):
    if client:
        st.sidebar.success("✅ Perplexity API Connected")
    else:
        st.sidebar.error("❌ Perplexity API Key Missing")
        st.sidebar.info("Add PPLX_API_KEY as environment variable on Render.com")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Professional Investment Research Platform | Powered by Perplexity AI<br>
    <small>For educational and research purposes. Not financial advice.</small></p>
</div>
""", unsafe_allow_html=True)
