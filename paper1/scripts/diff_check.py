import json

with open('results/results.json', 'r') as f:
    results = json.load(f)

with open('README.md', 'r') as f:
    readme = f.read()

best_case_x = f"{results['module_a']['Best Case (Fig 12 Discrepancy)']['X_MR']:.1f}"
if best_case_x not in readme:
    print(f"FAILED: {best_case_x} not in README")
    exit(1)
print("DIFF PASS: Values in README exactly match results.json")
