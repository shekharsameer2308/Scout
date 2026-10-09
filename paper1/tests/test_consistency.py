import json
import pytest

def test_mass_balance():
    with open('results/results.json', 'r') as f:
        results = json.load(f)
    for name, res in results['module_a'].items():
        assert res['C_error'] < 0.1, f"Mass balance failed for {name}"

def test_validation_targets():
    with open('results/results.json', 'r') as f:
        results = json.load(f)
    
    # Base Case TR target ~29.7%
    base_tr = results['module_a']['Base Case']['X_TR']
    assert abs(base_tr - 29.7) < 1.0, f"TR base case failed: {base_tr}"
    
    # Base case water removal ~7.82%
    base_water = results['module_a']['Base Case']['Water_Removal']
    assert abs(base_water - 7.82) < 6.0, f"Water removal base case failed: {base_water}"
    
    # Best Case MR target ~45.3%
    best_mr = results['module_a']['Best Case (Fig 12 Discrepancy)']['X_MR']
    assert abs(best_mr - 45.3) < 2.0, f"Best case MR failed: {best_mr}"

def test_equilibrium_bound():
    with open('results/results.json', 'r') as f:
        results = json.load(f)
    
    base_tr = results['module_a']['Base Case']['X_TR']
    # At 250C, 100bar, equilibrium conversion is roughly 35-40% for CO2 hydrogenation depending on EOS.
    # We must ensure TR doesn't exceed it. (It shouldn't exceed 45%)
    assert base_tr < 40.0, f"TR exceeds equilibrium bounds: {base_tr}"

def test_readme_contains_units():
    with open('README.md', 'r') as f:
        content = f.read()
    # Check if important metrics have units
    assert "kJ/mol" in content
    assert "%" in content
    assert "bar" in content
