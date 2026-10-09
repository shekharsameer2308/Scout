import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import streamlit as st
import itertools
from models.module_a import run_simulation_A

@st.cache_data
def generate_and_train_surrogate():
    """
    Runs a 2^4 factorial DOE (or custom grid) on the 1D model and trains a surrogate Random Forest.
    This demonstrates testing the model space using ML training.
    """
    ghsv_levels = [500, 5000]
    sf_levels = [1, 10]
    om_levels = [26.67, 133.33]
    dp_levels = [0, 99] # dP across membrane
    
    T = 250.0
    P_ret = 100.0
    
    grid = list(itertools.product(ghsv_levels, sf_levels, om_levels, dp_levels))
    
    data = []
    
    for (ghsv, sf, om, dp) in grid:
        dm = 0.010
        dw = np.sqrt(4 * dm / om + dm**2)
        
        params_tr = {
            'T': T, 'P_ret': P_ret, 'P_perm': P_ret, 'GHSV': ghsv, 'S_F': sf, 
            'W_cat': 0.1, 'pol_factor': 1.0, 'L': 0.25, 'dm': dm, 'dw': dw, 'tm': 0.005, 'is_MR': False
        }
        res_tr, Fin, Fsin = run_simulation_A(params_tr)
        F_CO2_in = Fin[0]
        X_tr = (F_CO2_in - res_tr.y[0,-1]) / F_CO2_in * 100
        
        params_mr = params_tr.copy()
        params_mr['P_perm'] = P_ret - dp
        params_mr['is_MR'] = True
        res_mr, _, _ = run_simulation_A(params_mr)
        X_mr = (F_CO2_in - res_mr.y[0,-1]) / F_CO2_in * 100
        
        # H2O removal
        water_rem = res_mr.y[5,-1] / (res_mr.y[2,-1] + res_mr.y[5,-1] + 1e-10) * 100
        
        data.append({
            'GHSV': ghsv,
            'S/F': sf,
            'O_M/V_r': om,
            'dP': dp,
            'X_TR': X_tr,
            'X_MR': X_mr,
            'Gain': X_mr - X_tr,
            'Water_Rem': water_rem
        })
        
    df = pd.DataFrame(data)
    
    X = df[['GHSV', 'S/F', 'O_M/V_r', 'dP']]
    y = df['Gain']
    
    rf = RandomForestRegressor(n_estimators=50, random_state=42)
    rf.fit(X, y)
    
    return df, rf
