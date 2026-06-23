import streamlit as st
import requests
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import styles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import styles

st.set_page_config(
    page_title="Scout — AI Analyst",
    page_icon="🤖",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://localhost:8000")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "mock_key")

# Header block
styles.render_header(
    "AI Analyst Report Generator",
    "Enter research topics, industry questions, or request SWOT reports built from gathered intelligence."
)

# Helper: Retrieve matching articles from SQL database
def retrieve_articles(query: str, limit: int = 5):
    db = SessionLocal()
    try:
        # Simple token-based keyword search on title and content
        tokens = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]
        if not tokens:
            return db.query(Article).order_by(Article.published_date.desc()).limit(limit).all()
            
        # Build filter conditions matching any keyword token
        from sqlalchemy import or_
        conditions = []
        for token in tokens:
            conditions.append(Article.title.ilike(f"%{token}%"))
            conditions.append(Article.content.ilike(f"%{token}%"))
            
        results = db.query(Article).filter(or_(*conditions)).order_by(Article.published_date.desc()).limit(limit).all()
        
        # If no keyword matches, fallback to latest articles
        if not results:
            results = db.query(Article).order_by(Article.published_date.desc()).limit(limit).all()
            
        return results
    except Exception as e:
        st.error(f"Error querying database: {e}")
        return []
    finally:
        db.close()

# Helper: Generate RAG response using Gemini or intelligent local fallback
def generate_response(prompt: str, articles):
    context = ""
    for idx, art in enumerate(articles):
        context += f"Source [{idx+1}]: {art.title}\nSource URL: {art.url}\nContent: {art.content or art.summary}\n\n"
        
    is_mock = GEMINI_API_KEY == "mock_key" or not GEMINI_API_KEY
    
    if not is_mock:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            
            system_instruction = (
                "You are Scout, an expert market intelligence and competitor research assistant. "
                "Synthesize a structured research report based ONLY on the provided article context. "
                "Cite your sources using [1], [2], etc. "
                "Provide detailed findings, bullet points, and tables. Keep a premium, analytical tone."
            )
            
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            
            full_prompt = f"User Request: {prompt}\n\nRetrieved Article Context:\n{context}"
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            st.warning(f"Failed to call Gemini API: {e}. Falling back to local synthesis engine.")
            is_mock = True

    if is_mock:
        # Local Intelligent Synthesis Fallback
        prompt_lower = prompt.lower()
        
        cited_sources = []
        for idx, art in enumerate(articles):
            cited_sources.append(f"| [{idx+1}] | [{art.title}]({art.url}) | {art.source} | {art.industry} |")
            
        sources_table = "\n".join(cited_sources)
        
        if "swot" in prompt_lower:
            company = "Competitor"
            for c in ["tesla", "byd", "toyota", "ford", "gm", "samsung", "tsmc", "apple", "google", "microsoft", "amazon", "meta", "nvidia"]:
                if c in prompt_lower:
                    company = c.upper()
                    break
                    
            summary_points = []
            for art in articles:
                summary_points.append(f"- **{art.title}**: {art.summary[:150]}... (Source: {art.source})")
                
            summary_points_str = "\n".join(summary_points[:3])
            
            return f"""> [!NOTE]
> *Running in Local Synthesis Fallback Mode (GEMINI_API_KEY not configured). Synthesizing database articles below.*

# SWOT Intelligence Report: {company}

Based on recent market ingestion feeds, we have compiled a SWOT analysis for **{company}**.

### 1. Market Background Insights
The database indicates active developments matching the sector:
{summary_points_str}

### 2. SWOT Grid

| Strengths | Weaknesses |
| :--- | :--- |
| • Strong presence in primary sector.<br>• Highly cited brand recognition across media channels.<br>• Consistent updates of data capabilities [1]. | • Exposure to regulatory scrutiny and global supply constraints.<br>• Dependency on key regional supplier dynamics [2]. |
| **Opportunities** | **Threats** |
| • Expanding into emerging AI-driven workflows.<br>• Leveraging localized consumer demand and green energy shifts [3]. | • Intensive competitor pricing campaigns (e.g., EV price wars).<br>• Sudden macroeconomic supply-chain halts. |

### 3. Cited Database Sources
| ID | Article Title | Publisher | Industry |
| :--- | :--- | :--- | :--- |
{sources_table}
"""
        else:
            summary_points = []
            for idx, art in enumerate(articles):
                summary_points.append(f"### {idx+1}. {art.title}\n* **Key Detail**: {art.summary[:250]}...\n* **Source**: [{art.source}]({art.url}) | **Sector**: `{art.industry}`")
                
            summary_points_str = "\n\n".join(summary_points)
            
            return f"""> [!NOTE]
> *Running in Local Synthesis Fallback Mode (GEMINI_API_KEY not configured). Synthesizing database articles below.*

# Market Intelligence Report

We retrieved **{len(articles)} relevant articles** from the database matching your query.

## Executive Summary
The primary focus of recent publications is the expansion of technological capabilities, regional market entries, and shifting policy parameters. In particular, the sector represents volatile sentiment shifts driven by macro competitive pressure.

## Detailed Findings
{summary_points_str}

## Strategic Recommendations
1. **Leverage Tech Stacks**: Adapt product roadmaps to match growing AI and automation trends.
2. **Monitor Policy Changes**: Keep track of local supply constraints and tariff announcements.
3. **Diversify Feeds**: Expand database collection criteria to minimize single-feed blindspots.

## Cited Database Sources
| ID | Article Title | Publisher | Industry |
| :--- | :--- | :--- | :--- |
{sources_table}
"""

# Initialize SessionLocal db connection imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from database.connection import SessionLocal
from database.models.article import Article

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display conversation history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Quick start prompts
st.markdown("### Quick Research Suggestions")
col1, col2, col3 = st.columns(3)
button_prompt = None
with col1:
    if st.button("EV Competitor Trends", use_container_width=True):
        button_prompt = "Summarize recent EV competitor trends (Tesla, BYD)"
with col2:
    if st.button("Generate BYD SWOT Analysis", use_container_width=True):
        button_prompt = "Generate a SWOT analysis for BYD"
with col3:
    if st.button("Defense Sector Overview", use_container_width=True):
        button_prompt = "What are the latest developments in the defense industry?"

chat_prompt = st.chat_input("Ask Scout a research question...")
prompt = chat_prompt or button_prompt

if prompt:
    # Append user prompt
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Retrieving local database context and synthesizing report..."):
            # 1. Retrieve articles
            articles = retrieve_articles(prompt, limit=5)
            
            # 2. Generate response
            response = generate_response(prompt, articles)
            st.markdown(response)
            
    # Append assistant response
    st.session_state.chat_history.append({"role": "assistant", "content": response})

st.sidebar.markdown("---")
styles.system_sidebar()
