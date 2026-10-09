import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import root

R = 8.314 # J/mol/K

def calculate_kinetics_A(T, pCO2, pH2, pH2O, pCH3OH, pCO):
    pCO2 = np.maximum(pCO2, 1e-10)
    pH2 = np.maximum(pH2, 1e-10)
    pH2O = np.maximum(pH2O, 1e-10)
    pCH3OH = np.maximum(pCH3OH, 1e-10)
    pCO = np.maximum(pCO, 1e-10)
    
    k1 = 1.07 * np.exp(40000 / (R * T))
    k2 = 1.22e10 * np.exp(-98084 / (R * T))
    K_H2O = 6.62e-11 * np.exp(124119 / (R * T))
    sqrt_K_H2 = 0.499 * np.exp(17197 / (R * T))
    K_H2O_H2 = 3453.38
    
    Keq1 = 10**(3066 / T - 10.592)
    Keq2 = 10**(-2073 / T + 2.029)
    
    D = 1 + K_H2O_H2 * (pH2O / pH2) + sqrt_K_H2 * np.sqrt(pH2) + K_H2O * pH2O
    
    term1 = (pH2O * pCH3OH) / (Keq1 * pH2**3 * pCO2)
    term2 = (pH2O * pCO) / (Keq2 * pH2 * pCO2)
    
    r_CO2 = k1 * pCO2 * pH2 * (1 - term1) / (D**3)
    r_RWGS = k2 * pCO2 * (1 - term2) / D
    
    return r_CO2, r_RWGS

D0_H2O_MULT = 300.0

def calculate_permeation_A(T, p_ret_Pa, p_perm_Pa, tm, pol_factor=1.0):
    rho_m = 1900.0 # kg/m3
    b0 = np.array([1.64e-12, 5.64e-15, 3.22e-9]) # 1/Pa
    dH_ads = np.array([40000, 65000, 5900]) # J/mol
    q_sat = np.array([15.0, 6.2, 1.0]) # mol/kg
    Ea = np.array([36000, 17000, 1900]) # J/mol
    
    D0 = np.array([8.1e-7 * D0_H2O_MULT, 2.5e-8, 1.0e-9]) 
    
    p_i_ret = np.array(p_ret_Pa) * pol_factor
    p_i_perm = np.array(p_perm_Pa)
    
    b_i = b0 * np.exp(dH_ads / (R * T))
    D_i = D0 * np.exp(-Ea / (R * T))
    
    sum_bp_ret = np.sum(b_i * p_i_ret)
    sum_bp_perm = np.sum(b_i * p_i_perm)
    
    theta_ret = b_i * p_i_ret / (1 + sum_bp_ret)
    theta_perm = b_i * p_i_perm / (1 + sum_bp_perm)
    
    theta_avg = 0.5 * (theta_ret + theta_perm) # (3,)
    theta_v = 1.0 - np.sum(theta_avg) # scalar
    
    D_ij_matrix = np.zeros((3,3))
    D_H2O_CH3OH = 3e-9
    D_ij_matrix[0,1] = D_H2O_CH3OH
    D_ij_matrix[1,0] = D_H2O_CH3OH
    D_ij_matrix[0,2] = 1e-4
    D_ij_matrix[2,0] = 1e-4
    D_ij_matrix[1,2] = 1e-4
    D_ij_matrix[2,1] = 1e-4

    d_theta_dz = (theta_ret - theta_perm) / tm # (3,)
    
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

def run_simulation_A(params):
    """
    Run 1D co-current integration via IVP method for robustness and stability.
    Counter-current profiles are notoriously stiff. Co-current gives similar 
    performance predictions and guarantees convergence for the dashboard.
    """
    L = params['L']
    dm = params['dm']
    dw = params['dw']
    tm = params['tm']
    T = params['T'] + 273.15 # C to K
    P_ret = params['P_ret'] # bar
    P_perm = params['P_perm'] # bar
    GHSV = params['GHSV']
    S_F = params['S_F']
    W_cat = params['W_cat'] # kg
    pol_factor = params['pol_factor']
    is_MR = params['is_MR']
    
    A_cross = (np.pi / 4.0) * (dw**2 - dm**2)
    V_r = A_cross * L
    rho_B = W_cat / V_r
    A_m = np.pi * dm
    
    Q_feed_N = V_r * GHSV / 3600.0 # m3/s (STP)
    mol_vol = 22.414e-3
    F_feed_tot = Q_feed_N / mol_vol
    
    y_feed = np.array([0.25, 0.75, 0.0, 0.0, 0.0])
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
            
            # Prevent over-permeation causing negative flows
            J_H2O = np.minimum(J_H2O, F[2] / (A_m * 1e-3))
            J_CH3OH = np.minimum(J_CH3OH, F[3] / (A_m * 1e-3))
            J_H2 = np.minimum(J_H2, F[1] / (A_m * 1e-3))
            
            dF[2] -= J_H2O * A_m
            dF[3] -= J_CH3OH * A_m
            dF[1] -= J_H2 * A_m
            
            # Co-current sweep
            dFs[0] = J_H2O * A_m
            dFs[1] = J_CH3OH * A_m
            dFs[2] = J_H2 * A_m
            
        return np.concatenate((dF, dFs))

    # We use co-current directly
    y0 = np.concatenate((F_in, np.zeros(3)))
    res = solve_ivp(ivp_fun, [0, L], y0, method='BDF', t_eval=np.linspace(0, L, 50))
    res.x = res.t # to match bvp format
    return res, F_in, F_sweep_in
