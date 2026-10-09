from models.module_a import run_simulation_A
import numpy as np
import models.module_a as mod_a
mod_a.D0_H2O_MULT = 350

dm = 0.010
OM_Vr = 133.33
dw = np.sqrt(4 * dm / OM_Vr + dm**2)

params = {
    'T': 250.0, 'P_ret': 100.0, 'P_perm': 1.0,
    'GHSV': 500.0, 'S_F': 10.0, 'W_cat': 0.1,
    'pol_factor': 1.0, 'L': 0.25,
    'dm': dm, 'dw': dw, 'tm': 0.005, 'is_MR': True
}
res_mr, Fin, Fsin = run_simulation_A(params)
F_CO2_in = Fin[0]
X_mr = (F_CO2_in - res_mr.y[0,-1]) / F_CO2_in * 100
print(f"X_MR: {X_mr:.2f}%")
