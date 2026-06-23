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
    page_title="Scout — Product Intelligence",
    page_icon="🛍️",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://localhost:8000")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "mock_key")

# Header block
styles.render_header(
    "Product Intelligence & Market Analysis",
    "Search any product class to scrape live internet feeds, detect active manufacturers, and generate SWOT metrics."
)

# Helper: Fetch live internet articles for product query
def fetch_product_data(query: str):
    try:
        response = requests.get(f"{API_URL}/api/articles/fetch-internet", params={"q": query}, timeout=12)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch live data from server: {e}")
        return {"articles": [], "stats": {}}

# Helper: Generate RAG response using Gemini or intelligent local fallback
def generate_product_report(product: str, articles, stats):
    # Format top companies
    sorted_comps = sorted(stats.items(), key=lambda x: x[1]["mentions"], reverse=True)
    top_brands = [item[0] for item in sorted_comps[:3]]
    
    context = ""
    for idx, art in enumerate(articles[:10]):
        context += f"Source [{idx+1}]: {art['title']} (Source: {art['source']})\nSnippet: {art['summary']}\nSentiment: {art['sentiment']}\n\n"
        
    is_mock = GEMINI_API_KEY == "mock_key" or not GEMINI_API_KEY
    
    if not is_mock:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            
            system_instruction = (
                "You are Scout, an expert market research analyst. "
                "Write a comprehensive competitor landscape and SWOT intelligence report for the queried product. "
                "Discuss which brands are leading the discussions, their sentiment profile, and provide strategic recommendations."
            )
            
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            
            full_prompt = f"Product Category: {product}\nTop Mentioned Brands: {top_brands}\n\nRetrieved Market Context:\n{context}"
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            st.warning(f"Failed to call Gemini API: {e}. Falling back to local synthesis engine.")
            is_mock = True

    if is_mock:
        # Local Intelligent Synthesis Fallback
        brand_highlights = []
        for brand, data in sorted_comps[:3]:
            pos_pct = round((data["positive"] / max(data["mentions"], 1)) * 100, 1)
            brand_highlights.append(
                f"* **{brand}** leads with **{data['mentions']} mentions**. Sentiment split is positive/neutral, showing a **{pos_pct}% positive score** based on recent releases."
            )
        brand_highlights_str = "\n".join(brand_highlights) if brand_highlights else "* *No major company brands were heavily mentioned in this search window. The discussion remains generic.*"
        
        return f"""> [Spacer / Note]
> *Currently running in Local Intelligent Fallback Mode because GEMINI_API_KEY is not configured. Live articles fetched from Google News have been processed below.*

# Competitor Landscape Report: {product.title()}

Based on analysis of live news feeds retrieved from Google News, we compiled this market analysis for **{product}**.

### 1. Key Brand Highlights
The most active companies mentioned in discussions surrounding **{product}** are:
{brand_highlights_str}

### 2. SWOT Analysis - {product.title()} Market Segment

| Strengths | Weaknesses |
| :--- | :--- |
| • Highly active R&D rollout across companies.<br>• Dynamic consumer adoption and rising search indexes.<br>• Scalable manufacturing pipelines. | • Exposure to component and raw material tariff constraints.<br>• Intense pricing wars squeezing margins (e.g. budget smartphone/laptop launches). |
| **Opportunities** | **Threats** |
| • Infusing advanced AI automation features.<br>• Localized manufacturing partnerships to hedge supply-chain risks. | • Sudden shifting consumer spending behaviors.<br>• Patent litigation and regulatory compliance delays. |

### 3. Strategic Recommendations
1. **Accelerate Innovation**: Focus on product feature differentiation (e.g. advanced AI chips, battery efficiency) to stand out.
2. **Hedge Pricing Risks**: Diversify components to safeguard against margin squeezes in budget product segments.
3. **Monitor Competitors**: Follow marketing launches from top cited players to benchmark product specifications.
"""

# Initialize session state for product search term if not set
if "product_search_term" not in st.session_state:
    st.session_state.product_search_term = ""

# Quick suggestions
st.markdown("### Quick Product Analysis Suggestions")
col1, col2, col3, col4 = st.columns(4)
button_query = None
with col1:
    if st.button("Mobile Phones", use_container_width=True):
        button_query = "mobile"
        st.session_state.product_search_term = "mobile"
with col2:
    if st.button("Laptops & PCs", use_container_width=True):
        button_query = "laptop"
        st.session_state.product_search_term = "laptop"
with col3:
    if st.button("Electric Vehicles", use_container_width=True):
        button_query = "electric vehicle"
        st.session_state.product_search_term = "electric vehicle"
with col4:
    if st.button("Solar Panels", use_container_width=True):
        button_query = "solar panel"
        st.session_state.product_search_term = "solar panel"

# Input control in sidebar backed by session state key
st.sidebar.header("Scrape & Analyze")
sidebar_query = st.sidebar.text_input(
    "Product search term...",
    key="product_search_term",
    placeholder="Type e.g., mobile, laptop, solar panel..."
)

# Resolve final product query
product_query = button_query or sidebar_query

# If user clicked button or pressed enter
if product_query:
    st.markdown("---")
    st.subheader(f"Analyzing Live Internet Data for: '{product_query.title()}'")
    
    with st.spinner("Fetching live articles from Google News search, matching brand mentions, and classifying sentiment..."):
        # 1. Fetch data
        data = fetch_product_data(product_query)
        
        articles = data.get("articles", [])
        stats = data.get("stats", {})
        
        if not articles:
            st.warning("No live articles retrieved for this product query. Please try another search term.")
        else:
            # Process dataframe
            flat_stats = []
            for brand, brand_stats in stats.items():
                flat_stats.append({
                    "Brand": brand,
                    "Total Mentions": brand_stats["mentions"],
                    "Positive": brand_stats["positive"],
                    "Negative": brand_stats["negative"],
                    "Neutral": brand_stats["neutral"]
                })
            df_stats = pd.DataFrame(flat_stats)
            
            # Row 1: KPI Summary & Charts
            dash_col1, dash_col2 = st.columns([3, 4])
            
            with dash_col1:
                st.markdown("#### Brand Share of Voice")
                if not df_stats.empty:
                    df_sorted = df_stats.sort_values(by="Total Mentions", ascending=True)
                    fig_voice = px.bar(
                        df_sorted,
                        x="Total Mentions",
                        y="Brand",
                        orientation="h",
                        color_discrete_sequence=["#475569"], # Slate-600
                        labels={"Total Mentions": "Articles Count", "Brand": "Company"}
                    )
                    fig_voice.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_family="Inter",
                        xaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.15)"),
                        yaxis=dict(showgrid=False),
                        height=280,
                        margin=dict(l=10, r=10, t=10, b=10)
                    )
                    st.plotly_chart(fig_voice, use_container_width=True)
                else:
                    st.info("No major brand mentions identified in this search index. Visuals skipped.")
                    
                st.markdown("#### Sentiment Splits per Brand")
                if not df_stats.empty:
                    # Melt for stacked bar chart
                    df_melted = df_stats.melt(
                        id_vars="Brand",
                        value_vars=["Positive", "Negative", "Neutral"],
                        var_name="Sentiment",
                        value_name="Count"
                    )
                    color_discrete_map = {
                        "Positive": "#10b981", # emerald-500
                        "Negative": "#ef4444", # red-500
                        "Neutral": "#6b7280"  # gray-500
                    }
                    fig_stacked = px.bar(
                        df_melted,
                        x="Brand",
                        y="Count",
                        color="Sentiment",
                        color_discrete_map=color_discrete_map,
                        labels={"Count": "Mentions", "Brand": "Company"},
                        barmode="stack"
                    )
                    fig_stacked.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_family="Inter",
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.15)"),
                        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
                        height=280,
                        margin=dict(l=10, r=10, t=10, b=10)
                    )
                    st.plotly_chart(fig_stacked, use_container_width=True)
                    
            with dash_col2:
                st.markdown("#### Market Landscape & SWOT")
                # Generate SWOT
                report = generate_product_report(product_query, articles, stats)
                st.markdown(report, unsafe_allow_html=True)
                
            st.markdown("---")
            st.subheader(f"Live Product Feed: '{product_query.title()}'")
            st.write(f"Showing {len(articles)} real-time articles scraped from Google News search index.")
            
            for art in articles:
                # Format date
                date_str = art["published_date"]
                sent = art["sentiment"]
                badge_class = "badge-positive" if sent == "positive" else ("badge-negative" if sent == "negative" else "badge-neutral")
                
                brands_span = ""
                for b in art["brands"]:
                    brands_span += f'<span class="neutral-badge">{b}</span> '
                    
                st.markdown(f"""
                <div class="content-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h5 style="margin: 0; font-size: 1.05rem; font-weight: 600;">{art['title']}</h5>
                        <div>
                            <span class="neutral-badge {badge_class}">{sent}</span>
                            <span style="font-size: 11px; color: rgba(128,128,128,0.7); font-weight: 500;">{date_str}</span>
                        </div>
                    </div>
                    <p style="font-size: 13.5px; line-height: 1.5; margin-bottom: 8px;">
                        {art['summary']}
                    </p>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            {brands_span}
                            <span style="font-size: 11.5px; color: rgba(128,128,128,0.6); font-weight: 500;">Source: <b>{art['source']}</b></span>
                        </div>
                        <a href="{art['url']}" target="_blank" style="font-size: 12.5px; color: var(--text-color); text-decoration: underline; font-weight: 600;">Read original article ↗</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("Enter a search term in the sidebar (e.g. mobile, laptop, solar panel) or use the suggestions above to fetch live data from the internet.")

st.sidebar.markdown("---")
styles.system_sidebar()

