# Feature 035: Spill Penalty Sign Inversion

## 1. Description
The LP solver is currently attempting to fill the battery as fast as possible prior to periods with high solar generation and negative export prices. This occurs because the spill variable `s[i]` (introduced in Feature 032) was assigned an objective weight of `price_sell[i]`. In a cost-minimization LP formulation, a negative `price_sell` acts as a numerical reward. Consequently, the LP maximizes spilling by intentionally saturating the battery early, completely defeating the purpose of the feature.

The fix ensures that negative export prices translate into positive mathematical penalties in the solver's objective function.

## 2. Requirements

- **FR-001 (Spill Penalty Costing):** The objective coefficient for the spill variable `s[i]` shall equal the positive cost of spilling to the grid. Specifically, it shall be `max(0.0, -price_sell[i])`.
- **FR-002 (Positive Export Neutrality):** When `price_sell` is positive, the spill variable shall incur 0 cost. The opportunity cost of charging from solar is already correctly modeled within the `c[i]` variable's objective weight (`max(0.001, price_sell[i])`).
- **FR-003 (Verification):** A test case must verify that when grid import is cheap but solar export is heavily penalized (negative), the LP prefers to leave battery headroom to absorb the solar rather than filling up early on the cheap import.
