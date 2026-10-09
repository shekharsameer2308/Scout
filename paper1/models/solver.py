import numpy as np
from scipy.integrate import solve_ivp
import yaml

with open('config/parameters.yaml', 'r') as f:
    config = yaml.safe_load(f)

R = config['constants']['R']['value']

def calculate_kinetics_A(T, pCO2, pH2, pH2O, pCH3OH, pCO):
    k_params = config['module_a']['kinetics']
    pCO2 = np.maximum(pCO2, 1e-10)
    pH2 = np.maximum(pH2, 1e-10)
    pH2O = np.maximum(pH2O, 1e-10)
    pCH3OH = np.maximum(pCH3OH, 1e-10)
    pCO = np.maximum(pCO, 1e-10)
    
    k1 = float(k_params['k1_pre']) * np.exp(float(k_params['k1_E']) / (R * T))
    k2 = float(k_params['k2_pre']) * np.exp(float(k_params['k2_E']) / (R * T))
    K_H2O = float(k_params['K_H2O_pre']) * np.exp(float(k_params['K_H2O_E']) / (R * T))
    sqrt_K_H2 = float(k_params['sqrt_K_H2_pre']) * np.exp(float(k_params['sqrt_K_H2_E']) / (R * T))
    K_H2O_H2 = float(k_params['K_H2O_H2'])
    
    Keq1 = 10**(3066 / T - 10.592)
    Keq2 = 10**(-2073 / T + 2.029)
    
    D = 1 + K_H2O_H2 * (pH2O / pH2) + sqrt_K_H2 * np.sqrt(pH2) + K_H2O * pH2O
    
    term1 = (pH2O * pCH3OH) / (Keq1 * pH2**3 * pCO2)
    term2 = (pH2O * pCO) / (Keq2 * pH2 * pCO2)
    
    r_CO2 = k1 * pCO2 * pH2 * (1 - term1) / (D**3)
    r_RWGS = k2 * pCO2 * (1 - term2) / D
    
    return r_CO2, r_RWGS

def calculate_permeation_A(T, p_ret_Pa, p_perm_Pa, tm, pol_factor=1.0):
    p_params = config['module_a']['permeation']
    rho_m = float(p_params['rho_m'])
    b0 = np.array(p_params['b0'], dtype=float)
    dH_ads = np.array(p_params['dH_ads'], dtype=float)
    q_sat = np.array(p_params['q_sat'], dtype=float)
    Ea = np.array(p_params['Ea'], dtype=float)
    D0 = np.array(p_params['D0'], dtype=float)
    D0[0] *= float(p_params['D0_H2O_MULT'])
    
    p_i_ret = np.array(p_ret_Pa) * pol_factor
    p_i_perm = np.array(p_perm_Pa)
    
    b_i = b0 * np.exp(dH_ads / (R * T))
    D_i = D0 * np.exp(-Ea / (R * T))
    
    sum_bp_ret = np.sum(b_i * p_i_ret)
    sum_bp_perm = np.sum(b_i * p_i_perm)
    
    theta_ret = b_i * p_i_ret / (1 + sum_bp_ret)
    theta_perm = b_i * p_i_perm / (1 + sum_bp_perm)
    
    theta_avg = 0.5 * (theta_ret + theta_perm)
    theta_v = 1.0 - np.sum(theta_avg)
    
    D_ij_matrix = np.zeros((3,3))
    D_H2O_CH3OH = 3e-9
    D_ij_matrix[0,1] = D_ij_matrix[1,0] = D_H2O_CH3OH
    D_ij_matrix[0,2] = D_ij_matrix[2,0] = 1e-4
    D_ij_matrix[1,2] = D_ij_matrix[2,1] = 1e-4

    d_theta_dz = (theta_ret - theta_perm) / tm
    
    B = np.zeros((3,3))
    Gamma = np.zeros((3,3))
    for i in range(3):
        for j in range(3):
            if i == j:
                sum_term = sum(theta_avg[k] / D_ij_matrix[i,k] for k in range(3) if k != i)
                B[i,i] = 1.0 / D_i[i] + sum_term
                Gamma[i,i] = 1.0 + theta_avg[i] / theta_v
            else:
                B[i,j] = -theta_avg[i] / D_ij_matrix[i,j]
                Gamma[i,j] = theta_avg[i] / theta_v
                
    try:
        B_inv = np.linalg.inv(B)
    except:
        B_inv = np.diag(D_i)
        
    q_mat = np.diag(q_sat)
    flux = rho_m * q_mat @ B_inv @ Gamma @ d_theta_dz
    return flux

def run_simulation_A(params, is_MR=True):
    # Co-current IVP method for extreme stability
    L = config['module_a']['geometry']['L']['value']
    dm = config['module_a']['geometry']['dm']['value']
    tm = config['module_a']['geometry']['tm']['value']
    
    O_M_V_r = params['O_M_V_r']
    dw = np.sqrt(4 * dm / O_M_V_r + dm**2)
    
    T = params['T'] + 273.15
    P_ret = params['P_ret']
    P_perm = params['P_perm']
    GHSV = params['GHSV']
    S_F = params['S_F']
    rho_B = params['rho_B']
    pol_factor = params['pol_factor']
    
    A_cross = (np.pi / 4.0) * (dw**2 - dm**2)
    V_r = A_cross * L
    W_cat = rho_B * V_r
    A_m = np.pi * dm
    
    Q_feed_N = V_r * GHSV / 3600.0
    mol_vol = config['constants']['mol_vol']['value']
    F_feed_tot = Q_feed_N / mol_vol
    
    y_feed = np.array([0.25, 0.75, 0.0, 0.0, 0.0]) # CO2, H2, H2O, CH3OH, CO
    F_in = F_feed_tot * y_feed
    F_sweep_in = S_F * F_feed_tot
    
    def ivp_fun(z, y):
        F = np.maximum(y[0:5], 1e-10)
        Fs = np.maximum(y[5:8], 1e-10)
        
        F_tot = np.sum(F)
        p_i = (F / F_tot) * P_ret
        pCO2, pH2, pH2O, pCH3OH, pCO = p_i
        
        r_CO2, r_RWGS = calculate_kinetics_A(T, pCO2, pH2, pH2O, pCH3OH, pCO)
        
        r_net = np.zeros(5)
        r_net[0] = -r_CO2 - r_RWGS
        r_net[1] = -3*r_CO2 - r_RWGS
        r_net[2] = r_CO2 + r_RWGS
        r_net[3] = r_CO2
        r_net[4] = r_RWGS
        
        dF = r_net * rho_B * A_cross
        dFs = np.zeros(3)
        
        if is_MR:
            Fs_tot = np.sum(Fs) + F_sweep_in
            p_perm_H2O = (Fs[0] / Fs_tot) * P_perm * 1e5
            p_perm_CH3OH = (Fs[1] / Fs_tot) * P_perm * 1e5
            p_perm_H2 = (Fs[2] / Fs_tot) * P_perm * 1e5
            
            p_ret_Pa = np.array([pH2O, pCH3OH, pH2]) * 1e5
            p_perm_Pa = np.array([p_perm_H2O, p_perm_CH3OH, p_perm_H2])
            
            flux = calculate_permeation_A(T, p_ret_Pa, p_perm_Pa, tm, pol_factor)
            J_H2O, J_CH3OH, J_H2 = flux
            
            J_H2O = np.minimum(J_H2O, F[2] / (A_m * 1e-3))
            J_CH3OH = np.minimum(J_CH3OH, F[3] / (A_m * 1e-3))
            J_H2 = np.minimum(J_H2, F[1] / (A_m * 1e-3))
            
            dF[2] -= J_H2O * A_m
            dF[3] -= J_CH3OH * A_m
            dF[1] -= J_H2 * A_m
            
            dFs[0] = J_H2O * A_m
            dFs[1] = J_CH3OH * A_m
            dFs[2] = J_H2 * A_m
            
        return np.concatenate((dF, dFs))

    y0 = np.concatenate((F_in, np.zeros(3)))
    res = solve_ivp(ivp_fun, [0, L], y0, method='BDF', t_eval=np.linspace(0, L, 50))
    res.x = res.t 
    return res, F_in, F_sweep_in

def run_simulation_B(params, is_MR=True):
    L = config['module_b']['geometry']['L']['value']
    T = params['T'] + 273.15
    P_ret = params['P_ret']
    P_perm = params['P_perm']
    F_in_NH3 = params['F_in_NH3']
    W_cat = params['W_cat']
    SMA = params['SMA'] # cm2 / g
    tm = params['tm']
    
    k_rate = config['module_b']['kinetics']['k_rate']
    K_H2 = config['module_b']['kinetics']['K_H2']
    Pe_H2 = config['module_b']['permeation']['Pe_H2']
    
    A_m = (SMA * 1e-4) * (W_cat * 1000) # m2
    
    def ivp_fun(z, y):
        F_NH3 = max(y[0], 1e-10)
        F_N2 = max(y[1], 1e-10)
        F_H2 = max(y[2], 1e-10)
        
        F_tot = F_NH3 + F_N2 + F_H2
        p_NH3 = (F_NH3 / F_tot) * P_ret
        p_H2 = (F_H2 / F_tot) * P_ret
        
        r_NH3 = k_rate * p_NH3 / (1 + K_H2 * p_H2)
        dF_NH3 = -r_NH3 * (W_cat / L)
        dF_N2 = 0.5 * r_NH3 * (W_cat / L)
        dF_H2 = 1.5 * r_NH3 * (W_cat / L)
        
        dF_H2_perm = 0.0
        if is_MR:
            J_H2 = (Pe_H2 / tm) * (np.sqrt(max(p_H2, 1e-10)) - np.sqrt(max(P_perm, 1e-10)))
            if J_H2 < 0: J_H2 = 0
            J_H2 = min(J_H2, F_H2 / (A_m / L * 1e-3))
            dF_H2 -= J_H2 * (A_m / L)
            dF_H2_perm = J_H2 * (A_m / L)
            
        return [dF_NH3, dF_N2, dF_H2, dF_H2_perm]
        
    y0 = [F_in_NH3, 0.0, 0.0, 0.0]
    res = solve_ivp(ivp_fun, [0, L], y0, method='BDF', t_eval=np.linspace(0, L, 50))
    res.x = res.t
    return res, F_in_NH3
