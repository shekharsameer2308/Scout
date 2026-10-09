# Consistency Audit

## Findings
1. **Missing Module B:** The previous instruction mandated removing Module B, but the current prompt requires auditing and fixing both Module A and Module B. Module B code is currently missing from the repository.
2. **Hardcoded Parameters (Multiple Truths):**
   - Constants like `R = 8.314`, `T = 250`, geometry (`dm = 0.010`), and pre-exponential multipliers (`D0_H2O_MULT = 300`) are hardcoded in `models/module_a.py`.
   - `app.py` independently re-defines slider defaults, geometries, and operating conditions.
   - `ml/surrogate.py` re-defines the `T = 250` and `P_ret = 100` defaults.
3. **No Central Output File:** `results.json` does not exist. The dashboard and ML modules run simulations on the fly rather than reading from a central validated output dataset.
4. **Validation Check Discrepancy:** The previous `render_validation` in `app.py` hardcoded validation strings rather than dynamically comparing model results to paper targets.
5. **No Universal Case Definitions:** `app.py` uses "Base Case", "Best Case", but these are not defined systematically in a unified configuration.
6. **Paper Discrepancy (O_M/V_r):** P3 uses $O_M/V_r = 133.3$ in Fig. 12 but $26.67$ in the final text for the best case. This discrepancy is currently hidden inside `app.py` logic instead of being explicitly documented and modeled as two separate defined cases.

## Action Plan
- Consolidate all constants, paper targets, geometry, and cases into `config/parameters.yaml`.
- Rewrite `models/solver.py` to be a pure function taking in `yaml` configurations.
- Write `scripts/run_all_cases.py` to populate `results/results.json`.
- Refactor the dashboard and README generators to pull entirely from `results.json`.
