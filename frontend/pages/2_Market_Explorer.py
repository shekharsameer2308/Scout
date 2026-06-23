import streamlit as st
import requests
import os
import sys
import pandas as pd
import plotly.express as px
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import styles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import styles

st.set_page_config(
    page_title="Scout — Market Explorer",
    page_icon="🧭",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Header block
styles.render_header(
    "Market Explorer & Trend Intelligence",
    "Analyze dynamic topic clusters, track growth velocity, and search key intelligence."
)

# Helper function to query APIs
@st.cache_data(ttl=60)
def fetch_topics():
    try:
        response = requests.get(f"{API_URL}/api/analytics/topics?limit=20", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []

@st.cache_data(ttl=60)
def fetch_topic_velocity():
    try:
        response = requests.get(f"{API_URL}/api/analytics/topics/velocity?days=7", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []

def fetch_articles(search="", industry="", topic=""):
    params = {"limit": 50}
    if search:
        params["search"] = search
    if industry and industry != "All":
        params["industry"] = industry
    if topic and topic != "All":
        params["topic"] = topic
        
    try:
        response = requests.get(f"{API_URL}/api/articles", params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching articles: {e}")
        return []

# Setup Sidebar Filters
st.sidebar.header("Filter & Search")
search_query = st.sidebar.text_input("Search articles...", placeholder="Type keywords, e.g. AI, solar, drone...")

industries = ["All", "logistics", "pharma", "agriculture", "defense"]
industry_filter = st.sidebar.selectbox("Filter by Industry", industries)

# Load topics dynamically for filter dropdown
topic_list = ["All"]
db_topics = fetch_topics()
for t in db_topics:
    topic_list.append(t["topic_name"])
topic_filter = st.sidebar.selectbox("Filter by Topic Cluster", topic_list)

# Main dashboard columns
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Topic Growth Velocity (Last 7 Days)")
    st.markdown("Metrics comparing mention frequency shifts in the **last 7 days** vs the **previous 7 days**.")
    
    velocity_data = fetch_topic_velocity()
    if velocity_data:
        df_vel = pd.DataFrame(velocity_data)
        
        # Color coding helper
        def style_velocity(val):
            color = 'rgb(16, 185, 129)' if val > 0 else ('rgb(239, 68, 68)' if val < 0 else 'rgba(128, 128, 128, 0.6)')
            return f'color: {color}; font-weight: 600;'
            
        df_disp = df_vel.rename(columns={
            "topic_name": "Topic Name",
            "current_count": "Current Count (7d)",
            "previous_count": "Previous Count (7d)",
            "velocity_pct": "Velocity %"
        })
        
        # Display with color styling
        st.dataframe(
            df_disp.style.map(style_velocity, subset=["Velocity %"]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No topic velocity data available. Make sure to run the topic modeling batch job.")

with col2:
    st.subheader("Top Topic Frequency")
    if db_topics:
        df_topics = pd.DataFrame(db_topics)
        fig_topics = px.bar(
            df_topics.head(10),
            x="frequency",
            y="topic_name",
            orientation="h",
            color="frequency",
            color_continuous_scale="greys", # Minimalist Grayscale
            labels={"frequency": "Article Count", "topic_name": "Topic Name"}
        )
        fig_topics.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="Inter",
            xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
            yaxis=dict(showgrid=False),
            coloraxis_showscale=False,
            height=320,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_topics, use_container_width=True)
    else:
        st.info("No topic clusters generated yet.")

st.markdown("---")
st.subheader("Article Intelligence Feed")

articles = fetch_articles(search=search_query, industry=industry_filter, topic=topic_filter)

if articles:
    st.write(f"Showing {len(articles)} matching articles.")
    for art in articles:
        pub_dt = datetime.fromisoformat(art["published_date"].replace("Z", "+00:00"))
        date_str = pub_dt.strftime("%B %d, %Y")
        
        st.markdown(f"""
        <div class="content-card">
            <h3>{art['title']}</h3>
            <div style="margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 5px;">
                <span class="neutral-badge">{art['industry']}</span>
                <span class="neutral-badge">{art['topic_name'] if art['topic_name'] else 'Unassigned'}</span>
                <span class="neutral-badge">{art['source']}</span>
                <span style="font-size: 12px; color: rgba(128, 128, 128, 0.7); margin-left: 5px; align-self: center;">{date_str}</span>
            </div>
            <p>{art['summary']}</p>
            <a href="{art['url']}" target="_blank" style="font-size: 13px; color: var(--text-color); text-decoration: underline; font-weight: 500;">Read original article &rarr;</a>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No articles found matching the current search criteria or filters.")

st.sidebar.markdown("---")
styles.system_sidebar()
