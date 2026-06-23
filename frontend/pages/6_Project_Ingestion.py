import streamlit as st
import plotly.express as px
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
    page_title="Scout - Project Ingestion",
    page_icon="🔍",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Header block
styles.render_header(
    "Project Ingestion Pipeline",
    "Search and ingest live articles on any topic or project directly into the Scout database and vector index."
)

# Initialize session state for ingest search term
if "ingest_search_term" not in st.session_state:
    st.session_state.ingest_search_term = ""

# Quick suggestions
st.markdown("#### Suggested Topics to Ingest")
sug_col1, sug_col2, sug_col3, sug_col4 = st.columns(4)
button_query = None
with sug_col1:
    if st.button("Solid State Battery", use_container_width=True):
        button_query = "solid state battery"
        st.session_state.ingest_search_term = "solid state battery"
with sug_col2:
    if st.button("Generative AI Regulation", use_container_width=True):
        button_query = "generative AI regulation"
        st.session_state.ingest_search_term = "generative AI regulation"
with sug_col3:
    if st.button("Hydrogen Fuel Cells", use_container_width=True):
        button_query = "hydrogen fuel cells"
        st.session_state.ingest_search_term = "hydrogen fuel cells"
with sug_col4:
    if st.button("Commercial Spaceflight", use_container_width=True):
        button_query = "commercial spaceflight"
        st.session_state.ingest_search_term = "commercial spaceflight"

# Main container for controls
st.markdown("### Ingest a New Project")
col_input, col_btn = st.columns([4, 1])

with col_input:
    query = st.text_input(
        "Enter Project Keywords or Topic...",
        key="ingest_search_term",
        placeholder="Type e.g., solid state battery, generative AI regulation, hyperloop...",
        label_visibility="collapsed"
    )

with col_btn:
    submit_btn = st.button("Start Ingestion", use_container_width=True)

# Resolve final query and run state
resolved_query = button_query or query
should_run = (submit_btn or (button_query is not None)) and resolved_query

if should_run:
    st.markdown("---")
    st.subheader(f"Ingesting and Analyzing Articles for: '{resolved_query}'")
    
    with st.spinner("Executing ingestion pipeline: parsing Google News RSS feed, downloading full content, classifying industry, computing FinBERT sentiment, extracting KeyBERT keywords, and indexing into Qdrant..."):
        try:
            response = requests.post(f"{API_URL}/api/articles/ingest-keyword", params={"q": resolved_query}, timeout=90)
            response.raise_for_status()
            res_data = response.json()
            
            stats = res_data.get("stats", {})
            articles = res_data.get("articles", [])
            
            # Display KPIs
            kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
            with kpi_col1:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-val">{stats.get('total_fetched', 0)}</div>
                        <div class="kpi-lbl">Total Fetched</div>
                    </div>
                """, unsafe_allow_html=True)
            with kpi_col2:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-val" style="color: rgb(16, 185, 129);">{stats.get('new_ingested', 0)}</div>
                        <div class="kpi-lbl">Newly Ingested</div>
                    </div>
                """, unsafe_allow_html=True)
            with kpi_col3:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-val" style="color: rgb(107, 114, 128);">{stats.get('duplicates_skipped', 0)}</div>
                        <div class="kpi-lbl">Duplicates Skipped</div>
                    </div>
                """, unsafe_allow_html=True)
            with kpi_col4:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-val" style="color: rgb(239, 68, 68);">{stats.get('errors', 0)}</div>
                        <div class="kpi-lbl">Errors Encountered</div>
                    </div>
                """, unsafe_allow_html=True)
            
            if not articles:
                if stats.get('duplicates_skipped', 0) > 0:
                    st.info("All fetched articles are already present in the database. No new records were added.")
                else:
                    st.warning("No articles could be retrieved for this search query. Please try different keywords.")
            else:
                st.success(f"Successfully processed and stored {len(articles)} new articles in the database!")
                
                # Visualizations
                vis_col1, vis_col2 = st.columns([1, 1])
                
                df_articles = pd.DataFrame(articles)
                
                with vis_col1:
                    st.markdown("#### Sentiment Distribution")
                    sentiment_counts = df_articles['sentiment'].value_counts().reset_index()
                    sentiment_counts.columns = ['Sentiment', 'Count']
                    
                    color_discrete_map = {
                        "positive": "#10b981", # emerald-500
                        "negative": "#ef4444", # red-500
                        "neutral": "#6b7280"  # gray-500
                    }
                    
                    fig_pie = px.pie(
                        sentiment_counts,
                        values='Count',
                        names='Sentiment',
                        color='Sentiment',
                        color_discrete_map=color_discrete_map,
                        hole=0.4
                    )
                    fig_pie.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_family="Inter",
                        height=300,
                        margin=dict(l=10, r=10, t=10, b=10)
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
                with vis_col2:
                    st.markdown("#### Industry Classifications")
                    ind_counts = df_articles['industry'].value_counts().reset_index()
                    ind_counts.columns = ['Industry', 'Count']
                    
                    fig_bar = px.bar(
                        ind_counts,
                        x='Count',
                        y='Industry',
                        orientation='h',
                        color_discrete_sequence=["#475569"], # Slate-600
                    )
                    fig_bar.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_family="Inter",
                        xaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.15)"),
                        yaxis=dict(showgrid=False),
                        height=300,
                        margin=dict(l=10, r=10, t=10, b=10)
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
                # Ingested List
                st.markdown("---")
                st.markdown("### Newly Ingested Articles")
                
                for art in articles:
                    sent = art["sentiment"]
                    badge_class = "badge-positive" if sent == "positive" else ("badge-negative" if sent == "negative" else "badge-neutral")
                    
                    kws_span = ""
                    for kw in art["keywords"]:
                        kws_span += f'<span class="neutral-badge">{kw}</span>'
                        
                    st.markdown(f"""
                        <div class="content-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <h5 style="margin: 0; font-size: 1.05rem; font-weight: 600;">{art['title']}</h5>
                                <div>
                                    <span class="neutral-badge {badge_class}">{sent}</span>
                                    <span class="neutral-badge">{art['industry']}</span>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                                <div>
                                    {kws_span}
                                    <span style="font-size: 11.5px; color: rgba(128,128,128,0.6); margin-left: 10px;">Source: <b>{art['source']}</b></span>
                                </div>
                                <a href="{art['url']}" target="_blank" style="font-size: 12.5px; color: var(--text-color); text-decoration: underline; font-weight: 600;">Read Original ↗</a>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown("---")
                st.info("The newly ingested articles are now indexed in the vector store and relational database. You can head over to the AI Analyst page and ask questions about this project!")
                
        except Exception as e:
            st.error(f"Failed to execute ingestion pipeline: {e}")
elif submit_btn and not resolved_query:
    st.warning("Please enter a valid search term.")

st.sidebar.markdown("---")
styles.system_sidebar()

