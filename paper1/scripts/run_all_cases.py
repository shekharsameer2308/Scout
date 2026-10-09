import sys
import os
import yaml
import json
import numpy as np

sys.path.append(os.path.abspath('.'))
from models.solver import run_simulation_A, run_simulation_B

def main():
    with open('config/parameters.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    results = {'module_a': {}, 'module_b': {}}
    
    # Run Module A Cases
    for case in config['module_a']['cases']:
        name = case['name']
        print(f"Running A: {name}")
        
        # TR
        res_tr, Fin, Fsin = run_simulation_A(case, is_MR=False)
        # MR
        res_mr, _, _ = run_simulation_A(case, is_MR=True)
        
        F_CO2_in = Fin[0]
        X_tr = (F_CO2_in - res_tr.y[0, -1]) / F_CO2_in * 100
        S_tr = res_tr.y[3, -1] / (F_CO2_in - res_tr.y[0, -1] + 1e-10) * 100
        Y_tr = X_tr * S_tr / 100
        
        X_mr = (F_CO2_in - res_mr.y[0, -1]) / F_CO2_in * 100
        S_mr = res_mr.y[3, -1] / (F_CO2_in - res_mr.y[0, -1] + 1e-10) * 100
        Y_mr = X_mr * S_mr / 100
        
        water_rem = res_mr.y[5, -1] / (res_mr.y[2, -1] + res_mr.y[5, -1] + 1e-10) * 100
        
        C_in = Fin[0] + Fin[3] + Fin[4]
        Fout = res_mr.y[:, -1]
        C_out = Fout[0] + Fout[3] + Fout[4] + Fout[6]
        c_err = abs(C_in - C_out) / (C_in + 1e-10) * 100
        
        results['module_a'][name] = {
            'X_TR': float(X_tr),
            'X_MR': float(X_mr),
            'Gain_X': float(X_mr - X_tr),
            'S_TR': float(S_tr),
            'S_MR': float(S_mr),
            'Y_TR': float(Y_tr),
            'Y_MR': float(Y_mr),
            'Water_Removal': float(water_rem),
            'C_error': float(c_err),
            'profile_x': res_mr.x.tolist(),
            'mr_y': res_mr.y.tolist(),
            'tr_y': res_tr.y.tolist()
        }
        
    # Run Module B Cases
    for case in config['module_b']['cases']:
        name = case['name']
        print(f"Running B: {name}")
        
        res_mr, Fin_NH3 = run_simulation_B(case, is_MR=True)
        res_tr, _ = run_simulation_B(case, is_MR=False)
        
        X_tr = (Fin_NH3 - res_tr.y[0, -1]) / Fin_NH3 * 100
        X_mr = (Fin_NH3 - res_mr.y[0, -1]) / Fin_NH3 * 100
        
        HRF = res_mr.y[3, -1] / (1.5 * Fin_NH3) * 100
        
        results['module_b'][name] = {
            'X_TR': float(X_tr),
            'X_MR': float(X_mr),
            'Gain_X': float(X_mr - X_tr),
            'HRF': float(HRF),
            'profile_x': res_mr.x.tolist(),
            'mr_y': res_mr.y.tolist(),
            'tr_y': res_tr.y.tolist()
        }
        
    os.makedirs('results', exist_ok=True)
    with open('results/results.json', 'w') as f:
        json.dump(results, f, indent=2)
        
if __name__ == '__main__':
    main()
