from models.module_a import run_simulation_A
import numpy as np

dm = 0.010
OM_Vr = 133.33
dw = np.sqrt(4 * dm / OM_Vr + dm**2)

params = {
    'T': 250.0, 'P_ret': 100.0, 'P_perm': 1.0,
    'GHSV': 5000.0, 'S_F': 1.0, 'W_cat': 0.1,
    'pol_factor': 1.0, 'L': 0.25,
    'dm': dm, 'dw': dw, 'tm': 0.005, 'is_MR': False
}
res_tr, Fin, Fsin = run_simulation_A(params)
print("Success:", res_tr.success)
print("Message:", res_tr.message)
