import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import styles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import styles

st.set_page_config(
    page_title="Scout — Dashboard",
    page_icon="📊",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Header block
styles.render_header(
    "Market Analytics Dashboard",
    "Overview of macro-market trends, public sentiment shifts, and emerging industry keywords."
)

# Cache data calls for 5 minutes (300 seconds)
@st.cache_data(ttl=300)
def fetch_sentiment_summary():
    response = requests.get(f"{API_URL}/api/analytics/sentiment", timeout=5)
    response.raise_for_status()
    return response.json()

@st.cache_data(ttl=300)
def fetch_sentiment_trend():
    response = requests.get(f"{API_URL}/api/analytics/sentiment-trend?days=30", timeout=5)
    response.raise_for_status()
    return response.json()

@st.cache_data(ttl=300)
def fetch_keywords():
    response = requests.get(f"{API_URL}/api/analytics/keywords?days=7", timeout=5)
    response.raise_for_status()
    return response.json()

try:
    # 1. Fetch data
    sentiment_data = fetch_sentiment_summary()
    trend_data = fetch_sentiment_trend()
    keyword_data = fetch_keywords()
    
    # 2. Process data for KPI Cards
    sent_dict = {item["sentiment"]: item for item in sentiment_data}
    total_articles = sum(item["count"] for item in sentiment_data)
    
    pos_pct = sent_dict.get("positive", {}).get("percentage", 0.0) if "positive" in sent_dict else 0.0
    neg_pct = sent_dict.get("negative", {}).get("percentage", 0.0) if "negative" in sent_dict else 0.0
    
    # Row 1: KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-val">{total_articles}</div>
            <div class="kpi-lbl">Total Articles</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-val">4</div>
            <div class="kpi-lbl">Industries Tracked</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-val" style="color: rgb(16, 185, 129);">{pos_pct:.1f}%</div>
            <div class="kpi-lbl">Positive Sentiment</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-val" style="color: rgb(239, 68, 68);">{neg_pct:.1f}%</div>
            <div class="kpi-lbl">Negative Sentiment</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Row 2: Two charts side by side
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("### Sentiment Distribution")
        df_pie = pd.DataFrame(sentiment_data)
        
        # Professional Muted Colors
        color_map = {
            "positive": "#10b981", # emerald-500
            "negative": "#ef4444", # red-500
            "neutral": "#6b7280"  # gray-500
        }
        
        fig_pie = px.pie(
            df_pie, 
            values="count", 
            names="sentiment", 
            color="sentiment",
            color_discrete_map=color_map,
            hole=0.45
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="Inter",
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            margin=dict(t=10, b=10, l=10, r=10)
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with chart_col2:
        st.markdown("### Sentiment Over Time (30 Days)")
        df_trend = pd.DataFrame(trend_data)
        
        if not df_trend.empty:
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=df_trend["date"], y=df_trend["positive"], 
                mode="lines+markers", name="Positive", 
                line=dict(color="#10b981", width=2),
                marker=dict(size=4)
            ))
            fig_line.add_trace(go.Scatter(
                x=df_trend["date"], y=df_trend["negative"], 
                mode="lines+markers", name="Negative", 
                line=dict(color="#ef4444", width=2),
                marker=dict(size=4)
            ))
            fig_line.add_trace(go.Scatter(
                x=df_trend["date"], y=df_trend["neutral"], 
                mode="lines+markers", name="Neutral", 
                line=dict(color="#6b7280", width=1.5),
                marker=dict(size=3)
            ))
            
            fig_line.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_family="Inter",
                xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", title="Date"),
                yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", title="Article Count"),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                margin=dict(t=10, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No time series sentiment data available yet.")
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Row 3: Top 10 keywords
    st.markdown("### Top Trending Keywords (Last 7 Days)")
    df_kw = pd.DataFrame(keyword_data)
    
    if not df_kw.empty:
        df_kw_top10 = df_kw.head(10).iloc[::-1]
        
        fig_bar = px.bar(
            df_kw_top10,
            x="score",
            y="keyword",
            orientation="h",
            labels={"score": "Importance Score", "keyword": "Keyword"},
            color="score",
            color_continuous_scale="greys" # Minimalist grayscale theme
        )
        
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="Inter",
            xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
            yaxis=dict(showgrid=False),
            coloraxis_showscale=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=380
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No trending keyword data available yet.")
        
except Exception as e:
    st.error("Unable to connect to the Scout API backend server.")
    st.info("Please make sure the FastAPI backend is running at http://localhost:8000.")
    st.exception(e)

st.sidebar.markdown("---")
styles.system_sidebar()
