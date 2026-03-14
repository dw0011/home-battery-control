# Feature 035 Plan: Spill Penalty Sign Inversion

## 1. Goal Description
Fix the LP solver's objective function so that negative export prices correctly penalize the `s` (spill) variable, rather than rewarding it. This prevents the solver from charging the battery early from the grid just to deliberately drop solar into negative export pricing and collect mathematical rewards.

## 2. Proposed Changes

### Core Logic
#### [MODIFY] [lin_fsm.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/lin_fsm.py)
- Change `obj[s_off + i] = price_sell[i]` to `obj[s_off + i] = max(0.0, -price_sell[i])`. This ensures that negative solar export prices are converted into positive mathematical penalties in the LP's minimization goal, while positive export prices assess a $0 spill penalty (as opportunity cost is already captured by `c[i]`).

### Tests
#### [MODIFY] [test_fsm_lin.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_fsm_lin.py)
- Re-add and update `test_spill_variable_penalises_negative_export` to verify that given a period of cheap grid import followed by a period of heavy PV + negative export price, the solver strictly prefers to leave headroom for the PV period, rather than filling up early and spilling the PV.

## 3. Verification Plan
### Automated Tests
- Run `pytest tests/test_fsm_lin.py -k test_spill_variable_penalises_negative_export` to check the modified objective penalty logic directly.
- Run `pytest tests/` to verify no regressions in existing heuristics and behaviors.
- The recent `TestBug034Regression` will also serve to verify that 100% capacity behavior is intact.
