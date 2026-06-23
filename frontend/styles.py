import streamlit as st

def inject_minimalist_css():
    st.markdown("""
        <style>
        /* Modern Minimalist Typographical Styling */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Clean Neutral Headers (No Gradients) */
        .page-title {
            color: var(--text-color);
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
            letter-spacing: -0.5px;
        }
        
        .page-subtitle {
            color: rgba(128, 128, 128, 0.7);
            font-size: 1rem;
            margin-bottom: 1.8rem;
        }
        
        /* Minimalist KPI Cards (Neutral Slate Borders) */
        .kpi-card {
            background: rgba(128, 128, 128, 0.03);
            border: 1px solid rgba(128, 128, 128, 0.15);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            margin-bottom: 15px;
        }
        
        .kpi-val {
            font-size: 28px;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 3px;
        }
        
        .kpi-lbl {
            font-size: 11px;
            color: rgba(128, 128, 128, 0.8);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }
        
        /* Minimalist Content Cards (Transparent/Light Grey, Thin Border) */
        .content-card {
            background: rgba(128, 128, 128, 0.02);
            border: 1px solid rgba(128, 128, 128, 0.12);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
            transition: border-color 0.2s ease;
        }
        .content-card:hover {
            border-color: rgba(128, 128, 128, 0.3);
        }
        
        .content-card h3 {
            font-size: 1.15rem;
            font-weight: 600;
            margin-top: 0;
            margin-bottom: 8px;
            color: var(--text-color);
        }
        
        .content-card p {
            font-size: 14px;
            line-height: 1.5;
            color: rgba(128, 128, 128, 0.9);
            margin-bottom: 12px;
        }
        
        .card-footer {
            font-size: 12px;
            color: rgba(128, 128, 128, 0.6);
            font-weight: 500;
        }
        
        /* Badges (Neutral, Muted Backgrounds) */
        .neutral-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: 1px solid rgba(128, 128, 128, 0.2);
            margin-right: 5px;
            background: rgba(128, 128, 128, 0.06);
            color: var(--text-color);
        }
        
        .badge-positive {
            background-color: rgba(16, 185, 129, 0.08);
            color: rgb(16, 185, 129);
            border-color: rgba(16, 185, 129, 0.25);
        }
        .badge-negative {
            background-color: rgba(239, 68, 68, 0.08);
            color: rgb(239, 68, 68);
            border-color: rgba(239, 68, 68, 0.25);
        }
        .badge-neutral {
            background-color: rgba(107, 114, 128, 0.08);
            color: rgb(107, 114, 128);
            border-color: rgba(107, 114, 128, 0.25);
        }
        
        /* SWOT Grid Layout */
        .swot-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        
        .swot-box {
            background: rgba(128, 128, 128, 0.02);
            border: 1px solid rgba(128, 128, 128, 0.12);
            border-radius: 6px;
            padding: 15px;
        }
        
        .swot-title {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        </style>
    """, unsafe_allow_html=True)

def render_header(title: str, subtitle: str):
    inject_minimalist_css()
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)

def system_sidebar():
    st.sidebar.markdown("### System Status")
    st.sidebar.info("Database: Connected\nQdrant Index: Ready\nAI Model: Ready")
