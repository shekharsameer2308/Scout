import streamlit as st
import os
import sys

# Ensure frontend path is in search path
sys.path.append(os.path.dirname(__file__))
import styles

st.set_page_config(
    page_title="Scout — Market Intelligence Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

styles.render_header(
    "Scout — Market Intelligence",
    "An AI-assisted platform for monitoring industries, tracking competitors, and researching market developments."
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="content-card">
        <h3>Market Dashboard</h3>
        <p>Monitor industry trends, keyword frequencies, and sentiment over time. Get a real-time overview of current market activity.</p>
        <div class="card-footer">Select <b>1 Dashboard</b> in the sidebar to view sentiment analytics.</div>
    </div>
    <div class="content-card">
        <h3>Market Explorer</h3>
        <p>Explore gathered news articles by industry, read AI-generated summaries, track trending topics, and query articles using dynamic filters.</p>
        <div class="card-footer">Select <b>2 Market Explorer</b> in the sidebar to search and explore articles.</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="content-card">
        <h3>AI Analyst</h3>
        <p>Ask complex research questions and let Scout generate comprehensive, structured reports backed by real citations from the article database.</p>
        <div class="card-footer">Select <b>3 AI Analyst</b> in the sidebar to chat with Scout.</div>
    </div>
    <div class="content-card">
        <h3>Competitor Intelligence</h3>
        <p>Compare competitors' mention volume and sentiment trends side by side, and view automated SWOT analyses.</p>
        <div class="card-footer">Select <b>4 Competitor Intelligence</b> in the sidebar to begin research.</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="content-card">
    <h3>Product Intelligence & Market Analysis</h3>
    <p>Search any custom product class (e.g. mobile, laptop, solar panel) to fetch live internet feeds, identify active competitor manufacturers, and compile dynamic SWOT reports.</p>
    <div class="card-footer">Select <b>5 Product Analysis</b> in the sidebar to scrape and analyze products.</div>
</div>
<div class="content-card">
    <h3>Project Ingestion Pipeline</h3>
    <p>Search and ingest live articles on any custom topic or project directly into the Scout database and vector index, running the full NLP pipeline automatically.</p>
    <div class="card-footer">Select <b>6 Project Ingestion</b> in the sidebar to ingest and analyze new data.</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.success("Select a page above to start.")
styles.system_sidebar()
