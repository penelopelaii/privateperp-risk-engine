# Notebooks

Exploratory analysis. Start the kernel from the repository root so `risk_engine`
imports without any path manipulation:

```python
from risk_engine import RiskInputs, evaluate_risk

evaluate_risk(RiskInputs(**profile["inputs"]))
```

Notebooks are for exploration only. Anything worth keeping moves into
`risk_engine/` (if it is logic) or `simulations/` (if it is an experiment),
where it can be tested and re-run.

Clear outputs before committing.
