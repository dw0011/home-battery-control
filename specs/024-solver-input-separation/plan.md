# Implementation Plan: Solver Input Separation

**Feature Branch**: `024-solver-input-separation`  
**Spec**: [spec.md](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/024-solver-input-separation/spec.md)

## Proposed Changes

### Component 1: SolverInputs Dataclass

#### [MODIFY] [base.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/base.py)

Add new `SolverInputs` dataclass before `FSMContext`:

```python
@dataclass
class SolverInputs:
    price_buy: list[float]       # 288 import prices (c/kWh), t=0 = live price
    price_sell: list[float]      # 288 export prices (c/kWh), t=0 = live price
    load_kwh: list[float]        # 288 load values (kWh per 5-min step)
    pv_kwh: list[float]          # 288 solar values (kWh per 5-min step)
    no_import_steps: set[int] | None = None  # blocked step indices
```

Add optional field to `FSMContext`:

```python
solver_inputs: SolverInputs | None = None
```

---

### Component 2: Tests (Written FIRST — TDD)

#### [MODIFY] [test_fsm_lin.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_fsm_lin.py)

Add new test class `TestSolverInputsSeparation`:

1. **test_solver_fails_fast_without_solver_inputs** — Verify `calculate_next_state` returns `FSMResult(state="ERROR")` when `context.solver_inputs is None`. (FR-008)

2. **test_solver_uses_solver_inputs_prices** — Verify that when `solver_inputs` is populated, row 0 uses `solver_inputs.price_buy[0]` (not `context.current_price`). Confirms old row-0 override code is gone. (FR-005, SC-001)

3. **test_solver_no_dict_parsing** — Verify solver works with empty/None `forecast_price` list on context when `solver_inputs` is populated. Proves solver doesn't fall back to dict parsing. (FR-005)

#### [NEW] [test_solver_inputs_builder.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_solver_inputs_builder.py)

Test the coordinator's `_build_solver_inputs()` method:

4. **test_build_price_arrays_from_rates** — Given a rates list with forecast dicts, verify `price_buy` and `price_sell` are `list[float]` of length 288. (FR-001)

5. **test_build_price_row0_uses_live_price** — Given `CONF_CURRENT_IMPORT_PRICE_ENTITY` configured with value 50, and forecast[0] at 15, verify `price_buy[0] == 50` and `price_buy[1] == forecast[1].import_price`. (FR-002, SC-003 — THE BUG FIX)

6. **test_build_price_row0_fallback_no_entity** — Given no current price entity configured, verify `price_buy[0]` comes from `rates.get_import_price_at(now)`. (FR-002 fallback)

7. **test_build_load_pv_arrays** — Given forecast dicts with `{"kw": 2.0}`, verify conversion to kWh: `2.0 * 5/60 = 0.1667`. Length 288. (FR-003)

8. **test_build_pads_short_arrays** — Given 100-element forecast, verify result is 288 with last value repeated. (Edge case)

9. **test_build_empty_forecast_returns_zeros** — Given empty forecast arrays, verify 288 zeros. (Edge case)

10. **test_build_no_import_steps** — Given `no_import_periods = "15:00-21:00"` and a forecast starting at 14:00 local, verify correct step indices in `no_import_steps`. (FR-004)

11. **test_build_no_import_empty** — Given empty `no_import_periods`, verify `no_import_steps` is None. (FR-004)

---

### Component 3: Coordinator Builder Method

#### [MODIFY] [coordinator.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/coordinator.py)

Add `_build_solver_inputs()` method to `HBCDataUpdateCoordinator`:

```
def _build_solver_inputs(self, rates_list, forecast_load, forecast_solar, 
                          current_price, current_export_price) -> SolverInputs:
```

This method:
1. Builds `price_buy[288]` and `price_sell[288]` from `rates_list` dicts
2. Overrides index 0 with `current_price` / `current_export_price`
3. Extracts `kw` from forecast dicts → `list[float]`
4. Converts kW → kWh per step (`× 5/60`)
5. Pads all arrays to exactly 288 elements
6. Resolves `no_import_periods` config into `set[int]` step indices using forecast timestamps
7. Returns `SolverInputs`

Update `_async_update_data()` to:
- Call `_build_solver_inputs()` after assembling forecasts and prices
- Set `fsm_context.solver_inputs = solver_inputs` before calling `calculate_next_state`

---

### Component 4: Solver Cleanup

#### [MODIFY] [lin_fsm.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/lin_fsm.py)

Replace `calculate_next_state` lines 313-396 with:

```python
# Fail-fast if solver_inputs not populated (FR-008)
if context.solver_inputs is None:
    return FSMResult(state="ERROR", limit_kw=0.0, 
                     reason="solver_inputs not populated by coordinator")

si = context.solver_inputs
price_buy = si.price_buy
price_sell = si.price_sell
load_f = si.load_kwh
pv_f = si.pv_kwh
no_import_steps = si.no_import_steps
```

**Remove entirely:**
- L313-321: `_pad()` helper and dict extraction
- L323-339: Price array construction with row-0 override
- L341-349: Load/solar extraction and kW→kWh conversion
- L375-396: No-import period timestamp resolution

**Keep unchanged:**
- L351-368: FakeBattery construction (solver-internal)
- L370-373: Terminal valuation (solver-specific heuristic)
- L398-466: LP solve + result classification

---

### Component 5: Existing Test Updates

#### [MODIFY] [test_fsm_lin.py](file:///C:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_fsm_lin.py)

Update `base_context` fixture to populate `solver_inputs` field. All existing tests that create `FSMContext` directly must include a `SolverInputs` object — otherwise they'll hit the fail-fast ERROR.

The `base_context` fixture (L14-42) currently builds forecast dicts. Update it to also build a `SolverInputs` from those same dicts so existing tests pass unchanged.

---

## Execution Order (TDD)

| Phase | What | File(s) | Depends On |
|-------|------|---------|------------|
| 1 | Add `SolverInputs` dataclass + `FSMContext` field | `base.py` | Nothing |
| 2 | Write failing tests (tests 1-11) | `test_fsm_lin.py`, `test_solver_inputs_builder.py` | Phase 1 |
| 3 | Run tests — confirm they fail | — | Phase 2 |
| 4 | Implement `_build_solver_inputs()` on coordinator | `coordinator.py` | Phase 1 |
| 5 | Clean up solver `calculate_next_state` | `lin_fsm.py` | Phase 1 |
| 6 | Update `base_context` fixture in existing tests | `test_fsm_lin.py` | Phase 5 |
| 7 | Run full suite — all 191+ tests pass | — | Phase 4-6 |

## Verification Plan

### Automated Tests
- `pytest tests/ -v` — all 191 existing tests pass + 11 new tests = 202+ expected
- `pytest tests/test_solver_inputs_builder.py -v` — new builder tests in isolation

### Regression Check
- Run `scripts/test_fsm_offline.py` to verify solver output is identical for same inputs before/after refactor (SC-002)
