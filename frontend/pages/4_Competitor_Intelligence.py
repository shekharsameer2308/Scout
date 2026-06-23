import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import styles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import styles

st.set_page_config(
    page_title="Scout — Competitor Intelligence",
    page_icon="⚔️",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Header block
styles.render_header(
    "Competitor Intelligence Portal",
    "Analyze competitor brand presence, sentiment splits, and comparative SWOT analytics."
)

# Helper: Fetch summaries of all competitors
@st.cache_data(ttl=60)
def fetch_competitor_summaries():
    try:
        response = requests.get(f"{API_URL}/api/analytics/competitors", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching competitor summaries: {e}")
        return []

# Helper: Fetch details for a specific competitor
def fetch_competitor_mentions(company_name: str):
    try:
        response = requests.get(f"{API_URL}/api/analytics/competitors/{company_name}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching competitor mentions: {e}")
        return []

# Load overall competitors
comp_data = fetch_competitor_summaries()

if not comp_data:
    st.info("No competitor mention data available. Make sure to run the ingestion pipeline to parse competitor mentions.")
else:
    df_comp = pd.DataFrame(comp_data)
    
    # Left column: Comparative analysis, Right column: Deep-dive
    col1, col2 = st.columns([3, 4])
    
    with col1:
        st.subheader("Competitor Share of Voice")
        st.markdown("Comparison of total mention counts across all companies on the watchlist.")
        
        # Sort values ascending for a clean horizontal bar chart layout
        df_comp_sorted = df_comp.sort_values(by="total_mentions", ascending=True)
        
        fig_bar = px.bar(
            df_comp_sorted,
            x="total_mentions",
            y="company_name",
            orientation="h",
            color_discrete_sequence=["#475569"], # Slate-600
            labels={"total_mentions": "Mention Count", "company_name": "Company"}
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="Inter",
            xaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.15)"),
            yaxis=dict(showgrid=False),
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Side-by-Side Comparison")
        
        # Select two competitors for quick comparison table
        comp_list = df_comp["company_name"].tolist()
        comp_a = st.selectbox("Select Competitor A", comp_list, index=0)
        comp_b = st.selectbox("Select Competitor B", comp_list, index=min(1, len(comp_list)-1))
        
        row_a = df_comp[df_comp["company_name"] == comp_a].iloc[0]
        row_b = df_comp[df_comp["company_name"] == comp_b].iloc[0]
        
        # Build comparative table
        compare_dict = {
            "Metric": ["Total Mentions", "Positive Mentions", "Negative Mentions", "Neutral Mentions"],
            comp_a: [
                row_a["total_mentions"],
                row_a["sentiment_breakdown"].get("positive", 0),
                row_a["sentiment_breakdown"].get("negative", 0),
                row_a["sentiment_breakdown"].get("neutral", 0)
            ],
            comp_b: [
                row_b["total_mentions"],
                row_b["sentiment_breakdown"].get("positive", 0),
                row_b["sentiment_breakdown"].get("negative", 0),
                row_b["sentiment_breakdown"].get("neutral", 0)
            ]
        }
        df_compare = pd.DataFrame(compare_dict)
        st.dataframe(df_compare, use_container_width=True, hide_index=True)
        
    with col2:
        st.subheader("Competitor Profile Deep-Dive")
        
        # Deep-dive Selector
        target_company = st.selectbox("Select Target Company", comp_list, index=0)
        target_row = df_comp[df_comp["company_name"] == target_company].iloc[0]
        
        # Calculate Primary Industry
        ind_breakdown = target_row["industry_breakdown"]
        primary_ind = max(ind_breakdown, key=ind_breakdown.get) if ind_breakdown else "N/A"
        
        # KPI metrics
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-val">{target_row['total_mentions']}</div>
                <div class="kpi-lbl">Total Mentions</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col2:
            sent_breakdown = target_row["sentiment_breakdown"]
            pos_pct = round((sent_breakdown.get("positive", 0) / max(target_row["total_mentions"], 1)) * 100, 1)
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-val" style="color: rgb(16, 185, 129);">{pos_pct}%</div>
                <div class="kpi-lbl">Positive Ratio</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-val" style="color: rgb(107, 114, 128); font-size: 20px; padding: 5px 0;">{primary_ind.title()}</div>
                <div class="kpi-lbl">Primary Sector</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Sentiment Chart
        st.markdown("#### Sentiment Distribution")
        sent_labels = list(sent_breakdown.keys())
        sent_values = list(sent_breakdown.values())
        
        if sent_values:
            color_map = {
                "positive": "#10b981", # emerald-500
                "negative": "#ef4444", # red-500
                "neutral": "#6b7280"  # gray-500
            }
            fig_donut = px.pie(
                names=sent_labels,
                values=sent_values,
                color=sent_labels,
                color_discrete_map=color_map,
                hole=0.5
            )
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_family="Inter",
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                height=260,
                margin=dict(t=10, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("No sentiment metrics generated for this competitor.")
            
        # SWOT grid
        st.markdown("#### SWOT Intelligence")
        st.markdown(f"""
        <div class="swot-grid">
            <div class="swot-box" style="border-color: rgba(16, 185, 129, 0.25);">
                <div class="swot-title" style="color: rgb(16, 185, 129);">Strengths</div>
                <div style="font-size: 13px; line-height: 1.5;">
                    • High frequency mentions in key sectors.<br>
                    • Active technological rollouts and operational scaling.<br>
                    • Resilient corporate presence.
                </div>
            </div>
            <div class="swot-box" style="border-color: rgba(239, 68, 68, 0.25);">
                <div class="swot-title" style="color: rgb(239, 68, 68);">Weaknesses</div>
                <div style="font-size: 13px; line-height: 1.5;">
                    • Subject to high public debate and media scrutiny.<br>
                    • Supply vulnerabilities and regional dependency.
                </div>
            </div>
            <div class="swot-box" style="border-color: rgba(59, 130, 246, 0.25);">
                <div class="swot-title" style="color: rgb(59, 130, 246);">Opportunities</div>
                <div style="font-size: 13px; line-height: 1.5;">
                    • Emerging automation integration.<br>
                    • Capitalize on green transition demands in primary markets.
                </div>
            </div>
            <div class="swot-box" style="border-color: rgba(107, 114, 128, 0.25);">
                <div class="swot-title" style="color: rgb(107, 114, 128);">Threats</div>
                <div style="font-size: 13px; line-height: 1.5;">
                    • Regulatory compliance adjustments.<br>
                    • Competitor price reductions and market saturation.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(f"Mention Ingestion Feed for {target_company}")
    
    mentions = fetch_competitor_mentions(target_company)
    
    if not mentions:
        st.info("No detailed mention occurrences found.")
    else:
        st.write(f"Displaying {len(mentions)} mention events.")
        for m in mentions:
            pub_dt = datetime.fromisoformat(m["published_date"].replace("Z", "+00:00"))
            date_str = pub_dt.strftime("%B %d, %Y")
            
            sent = m["sentiment"]
            badge_class = "badge-positive" if sent == "positive" else ("badge-negative" if sent == "negative" else "badge-neutral")
            
            st.markdown(f"""
            <div class="content-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h5 style="margin: 0; font-size: 1.05rem; font-weight: 600;">{m['article_title']}</h5>
                    <div>
                        <span class="neutral-badge {badge_class}">{sent}</span>
                        <span style="font-size: 11px; color: rgba(128,128,128,0.7); margin-left: 10px; font-weight: 500;">{date_str}</span>
                    </div>
                </div>
                <p style="font-size: 13.5px; font-style: italic; border-left: 2px solid rgba(128,128,128,0.2); padding-left: 10px; margin-bottom: 10px;">
                    "...{m['context_snippet']}..."
                </p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 11.5px; color: rgba(128,128,128,0.6); font-weight: 500;">Mentions in article: <b>{m['mention_count']}</b></span>
                    <a href="{m['article_url']}" target="_blank" style="font-size: 12.5px; color: var(--text-color); text-decoration: underline; font-weight: 600;">View source ↗</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
st.sidebar.markdown("---")
styles.system_sidebar()

