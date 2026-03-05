# Implementation Plan: 025 — Acquisition Cost Tracker Fix

**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/025-acq-cost-tracker-fix/spec.md)
**Branch**: `025-acq-cost-tracker-fix`

## Summary

Remove the redundant weighted-average acquisition cost tracker in the coordinator (L612-634) and replace it with a single assignment from the solver's authoritative `future_plan[0]["acquisition_cost"]` value. This eliminates the double-count bug and ensures the dashboard, storage, and solver all agree.

## Proposed Changes

### Component: Coordinator (`coordinator.py`)

#### [MODIFY] [coordinator.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/coordinator.py)

**Change 1 — Replace tracker block (L612-634)** with:
```python
# Sync acquisition cost from solver (FR-001, FR-002)
solver_acq = future_plan[0].get("acquisition_cost")
if solver_acq is not None:
    self.acquisition_cost = solver_acq
```

This removes 22 lines of buggy weighted-average code and replaces with 3 lines that read the solver's idempotent snapshot value.

**Change 2 — No change to cumulative cost tracker (L600-610)**. FR-006 requires cumulative cost to remain untouched.

**Change 3 — No change to storage persistence (L636-644)**. The same `self.acquisition_cost` field is persisted — it just now contains the solver's correct value.

**Change 4 — No change to data return dict (L685)**. `"acquisition_cost": round(self.acquisition_cost, 4)` remains, but now returns the solver's value.

---

### Component: Tests

#### [NEW] Tests in `test_coordinator.py` or new file

**T01** — `test_acq_cost_syncs_from_solver_plan`: Given a coordinator with `future_plan[0]["acquisition_cost"] = 0.135`, after the update cycle, `self.acquisition_cost` equals `0.135`.

**T02** — `test_acq_cost_persists_on_empty_plan`: Given `future_plan = []`, after the update cycle, `self.acquisition_cost` retains its previous value (no reset to 0).

**T03** — `test_acq_cost_no_double_count`: Run the update cycle twice with the same plan. `self.acquisition_cost` should be identical both times (idempotent, no accumulation).

**T04** — `test_cumulative_cost_unchanged`: The cumulative cost tracker logic must continue to work identically (regression guard).

## Verification Plan

### Automated Tests
```bash
pytest tests/ -v --tb=short
```
All 190+ existing tests must pass, plus 4 new tests.

### Manual Verification
After deploy, check the dashboard stat card shows ~13.5c (matching plan row 0), not 0.00.
