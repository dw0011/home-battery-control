# Implementation Plan: No-Import Periods (Demand Charge Windows)

**Branch**: `010-no-import-periods` | **Date**: 2026-02-26 | **Spec**: [spec.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/010-no-import-periods/spec.md)

## Summary

Add configurable no-import time windows that force the LP solver's grid import variable `g[i]` to zero during specified periods. This prevents demand charge penalties from grid charging during peak windows.

## Technical Design

### Architecture

The `RateInterval` entries from `RatesManager` already carry `start` datetime timestamps. The `LinearBatteryStateMachine.calculate_next_state()` already iterates through forecast entries by index `t`. The timestamps from the rate entries provide the mapping from LP step index `t` to wall-clock time, which is compared against configured no-import periods.

### Data Flow

```
Config (HH:MM-HH:MM strings)
  → coordinator passes config dict to FSMContext
  → lin_fsm.calculate_next_state() reads config
  → propose_state_of_charge() receives no_import_periods
  → For each step i, check if timestamp falls in any period
  → Set g[i] bound to (0, 0) if blocked
```

## Proposed Changes

### Component 1: Constants

#### [MODIFY] [const.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/const.py)

Add: `CONF_NO_IMPORT_PERIODS = "no_import_periods"`

---

### Component 2: LP Solver

#### [MODIFY] [lin_fsm.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/fsm/lin_fsm.py)

**In `propose_state_of_charge()`**: Add a `no_import_steps: set[int]` parameter (a set of step indices where import is blocked). In the bounds loop for `g[i]`, if `i in no_import_steps`, set bound to `(0.0, 0.0)`.

**In `calculate_next_state()`**: 
1. Read `CONF_NO_IMPORT_PERIODS` from `context.config`
2. Parse the comma-separated `HH:MM-HH:MM` strings into `(start_hour, start_min, end_hour, end_min)` tuples
3. For each step `t` (0..287), compute the wall-clock time: `now + t * 5 minutes`
4. Check if that time falls in any configured no-import period
5. Build `no_import_steps: set[int]` and pass to `propose_state_of_charge()`

Helper function `_parse_no_import_periods(config_str: str) -> list[tuple[int,int,int,int]]` — pure function, easily tested.

Helper function `_is_in_no_import_period(local_time: time, periods: list) -> bool` — handles midnight wrapping.

---

### Component 3: Config Flow

#### [MODIFY] [config_flow.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/config_flow.py)

Add `CONF_NO_IMPORT_PERIODS` as a `TextSelector` in the Options flow `async_step_control`. Placeholder text: "e.g. 15:00-21:00,06:00-09:00"

---

### Component 4: Coordinator

#### [MODIFY] [coordinator.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/coordinator.py)

Pass `no_import_periods` through the FSMContext config dict (line 422).

---

### Component 5: Translations

#### [MODIFY] strings.json + translations/en.json

Add label and description for `no_import_periods`.

---

### Component 6: Tests

#### [MODIFY] [test_fsm_lin.py](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/tests/test_fsm_lin.py)

New tests:
- `test_parse_no_import_periods_single` — parse "15:00-21:00"
- `test_parse_no_import_periods_multiple` — parse "15:00-21:00,06:00-09:00"
- `test_parse_no_import_periods_empty` — empty string returns empty list
- `test_is_in_no_import_period_within` — 16:00 in 15:00-21:00
- `test_is_in_no_import_period_outside` — 10:00 not in 15:00-21:00
- `test_is_in_no_import_period_midnight_wrap` — 23:00 in 22:00-06:00
- `test_no_import_period_lp_zero_import` — full LP solve with a blocked period, verify `g[i]==0` for blocked steps

## Verification Plan

### Automated Tests
- `pytest tests/test_fsm_lin.py -v` (targeted)
- `pytest tests/ -v` (full suite)

### Manual Verification
- Deploy to HA, configure "15:00-21:00", check plan table shows zero import during that window
