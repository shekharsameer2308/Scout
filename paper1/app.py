import streamlit as st
import json
import plotly.graph_objects as go
import pandas as pd
from models.solver import run_simulation_A, run_simulation_B
import yaml

with open('results/results.json', 'r') as f:
    RESULTS = json.load(f)

with open('config/parameters.yaml', 'r') as f:
    CONFIG = yaml.safe_load(f)

st.set_page_config(page_title="Membrane Reactor Simulator", layout="wide")

st.markdown("""
<style>
    :root {
        --slate: #475569;
        --emerald: #10b981;
        --red: #ef4444;
        --gray: #6b7280;
    }
    .content-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-val { font-size: 24px; font-weight: bold; color: var(--emerald); }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("Catalytic Membrane Reactor Simulator")
    
    tabs = st.tabs(["Overview & 3D Diagram", "Equations", "Results Table", "Module A (CO2)", "Module B (NH3)"])
    
    with tabs[0]:
        st.header("3D Reactor Architecture")
        st.image("figures/3d_cutaway.png", use_container_width=True)
        st.image("figures/2d_cross_section.png", use_container_width=True)
        
    with tabs[1]:
        st.header("Equations")
        st.latex(r"r_{\text{CO}_2} = \frac{k_1 p_{\text{CO}_2} p_{\text{H}_2} [1 - \text{term}_1]}{D^3}")
        st.latex(r"(J) = \rho_m [q_{\text{sat}}] [B]^{-1} [\Gamma] \frac{d\theta}{dz}")
        
    with tabs[2]:
        st.header("Pre-computed Results Database")
        df_a = pd.DataFrame.from_dict({k: {
            'X_TR (%)': v['X_TR'], 'X_MR (%)': v['X_MR'], 
            'Gain (pp)': v['Gain_X'], 'Water Removal (%)': v['Water_Removal']
        } for k, v in RESULTS['module_a'].items()}, orient='index')
        st.subheader("Module A (CO2 Hydrogenation)")
        st.dataframe(df_a.style.format(precision=1), use_container_width=True)
        
        df_b = pd.DataFrame.from_dict({k: {
            'X_TR (%)': v['X_TR'], 'X_MR (%)': v['X_MR'], 'H2 Recovery (%)': v['HRF']
        } for k, v in RESULTS['module_b'].items()}, orient='index')
        st.subheader("Module B (Ammonia Decomposition)")
        st.dataframe(df_b.style.format(precision=1), use_container_width=True)
        
    with tabs[3]:
        st.header("Module A Axial Profiles")
        case = st.selectbox("Select Case (Module A)", list(RESULTS['module_a'].keys()))
        data = RESULTS['module_a'][case]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data['profile_x'], y=data['mr_y'][0], name="CO2 (MR)", line=dict(color="#475569", width=3)))
        fig.add_trace(go.Scatter(x=data['profile_x'], y=data['mr_y'][3], name="CH3OH (MR)", line=dict(color="#10b981", width=3)))
        fig.add_trace(go.Scatter(x=data['profile_x'], y=data['tr_y'][0], name="CO2 (TR)", line=dict(color="#475569", dash='dash')))
        fig.update_layout(title="Molar Flow Rates", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        st.header("Module B Axial Profiles")
        case_b = st.selectbox("Select Case (Module B)", list(RESULTS['module_b'].keys()))
        data_b = RESULTS['module_b'][case_b]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data_b['profile_x'], y=data_b['mr_y'][0], name="NH3 (MR)", line=dict(color="#475569", width=3)))
        fig.add_trace(go.Scatter(x=data_b['profile_x'], y=data_b['mr_y'][2], name="H2 (MR)", line=dict(color="#10b981", width=3)))
        fig.update_layout(title="Molar Flow Rates", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
