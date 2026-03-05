# Feature Specification: Solver Input Separation

**Feature Branch**: `024-solver-input-separation`  
**Created**: 2026-03-05  
**Status**: Draft  
**Input**: User description: "Separate solver input preparation from solver logic — move price array construction, load/solar extraction, unit conversion, and no-import period timestamp mapping from lin_fsm.py into the coordinator. The solver should receive clean float arrays, not raw forecast dicts."

## User Scenarios & Testing

### User Story 1 - Correct Row-0 Price in Solver (Priority: P1)

During discharge-profitable periods, the system sometimes requests an unexpected charge. This occurs because the solver's first row uses a live 5-minute dispatch price (from the Current Import Price Entity sensor) while subsequent rows use the 30-minute forecast prices from Amber's forecast attribute. When the live dispatch price spikes above the forecast price, the solver perceives a false price drop from row 0 to row 1 and responds with a charge decision.

The coordinator should present the solver with a single, consistent price timeline where t=0 already contains the live price — no row-0 override in the solver.

**Why this priority**: This is the root cause of the reported production bug — unexpected charge commands during discharge windows.

**Independent Test**: A test case where `current_price` is 50 c/kWh and `forecast_price[0].import_price` is 15 c/kWh must produce a price array where `price_buy[0]` is 50 c/kWh AND `price_buy[1]` is the next forecast interval — not 15 c/kWh.

**Acceptance Scenarios**:

1. **Given** the coordinator has a live import price of 50 c/kWh and a forecast array starting at 15 c/kWh, **When** the solver receives the price arrays, **Then** `price_buy[0]` is 50 and `price_buy[1]` is the second forecast interval's import price — there is no orphaned forecast element.
2. **Given** the current export price entity reports 8 c/kWh but the forecast array's first element has 5 c/kWh, **When** the solver receives the price arrays, **Then** `price_sell[0]` is 8 — the live value overrides the forecast's first element.
3. **Given** no current price entities are configured, **When** the coordinator builds price arrays, **Then** `price_buy[0]` is the time-matched value from the rates array (existing `get_import_price_at(now)` behaviour).

---

### User Story 2 - Solver Receives Clean Float Arrays (Priority: P1)

The solver currently parses raw forecast dicts (`{"import_price": ..., "export_price": ...}`, `{"kw": ...}`) and performs unit conversion (kW → kWh). This is data marshalling, not optimisation logic. The coordinator should provide ready-to-consume `list[float]` arrays.

**Why this priority**: Separation of concerns prevents future bugs from data-format assumptions leaking into optimisation logic.

**Independent Test**: The solver's `calculate_next_state` receives pre-built float arrays and never calls `.get()` on dict entries or performs isinstance checks on forecast items.

**Acceptance Scenarios**:

1. **Given** the coordinator has forecast data in dict format, **When** it builds solver inputs, **Then** the price, load, and solar arrays are `list[float]` with 288 elements each.
2. **Given** a forecast array shorter than 288 elements, **When** the coordinator pads it, **Then** the result is exactly 288 elements with the last value repeated.
3. **Given** kW-based load and solar forecasts, **When** the coordinator converts to kWh per 5-min step, **Then** each value is multiplied by `5/60`.

---

### User Story 3 - No-Import Period Resolution in Coordinator (Priority: P2)

The solver currently parses the `no_import_periods` config string, iterates forecast timestamps, performs timezone conversions, and builds a `set[int]` of blocked steps. This is entirely a coordinator responsibility — the solver should receive pre-resolved `set[int]` indices.

**Why this priority**: Timezone handling and config parsing in the solver is a maintenance risk and violates separation of concerns.

**Independent Test**: The solver receives `no_import_steps: set[int]` directly and performs no timezone conversion or config string parsing.

**Acceptance Scenarios**:

1. **Given** `no_import_periods = "15:00-21:00"` and a forecast starting at 14:00 local, **When** the coordinator resolves step indices, **Then** steps corresponding to 15:00-21:00 are in the `no_import_steps` set.
2. **Given** empty `no_import_periods`, **When** the coordinator resolves step indices, **Then** `no_import_steps` is `None` or an empty set.

---

### Edge Cases

- Forecast array is completely empty — coordinator must provide 288 zeros, not pass empty list
- Current price entities configured but unavailable (sensor state "unavailable") — coordinator falls back to rates lookup
- Forecast array has fewer than 288 elements — coordinator pads by repeating last value
- No-import periods span midnight (e.g. "22:00-06:00") — must still resolve correctly

## Clarifications

### Session 2026-03-05

- Q: How do the prepared solver inputs transfer from coordinator to solver — mutate FSMContext, new dataclass, or bypass? → A: Option B — New `SolverInputs` dataclass added as an optional field on `FSMContext`. Coordinator populates it; LP solver reads it; other FSM implementations ignore it.
- Q: Where does the builder logic live — private coordinator method or standalone module? → A: Option A — Private method `_build_solver_inputs()` on `HBCDataUpdateCoordinator`. Has direct access to rates, config, forecasts, and live price entities.
- Q: What happens if `solver_inputs` is None when the LP solver runs? → A: Option A — Fail-fast. LP solver returns `FSMResult(state="ERROR", ...)`. Hard contract: coordinator MUST populate `solver_inputs` before calling LP solver.

## Requirements

### Functional Requirements

- **FR-001**: The coordinator MUST build `price_buy: list[float]` and `price_sell: list[float]` arrays of exactly 288 elements before passing to the solver.
- **FR-002**: The coordinator MUST override index 0 of the price arrays with the live current price (from `CONF_CURRENT_IMPORT_PRICE_ENTITY` or `rates.get_import_price_at(now)`) and the live current export price.
- **FR-003**: The coordinator MUST build `load_kwh: list[float]` and `pv_kwh: list[float]` arrays of exactly 288 elements, already converted from kW to kWh per 5-minute step.
- **FR-004**: The coordinator MUST resolve no-import periods into a `set[int]` of step indices before passing to the solver.
- **FR-005**: The solver (`calculate_next_state`) MUST NOT perform dict parsing, isinstance checks, unit conversion, or timezone conversion on input data.
- **FR-006**: The solver's `propose_state_of_charge` interface MUST accept clean `list[float]` arrays and `set[int]` for blocked steps (no change to the LP core).
- **FR-007**: All existing tests MUST continue to pass — no behavioural change to the optimisation output for identical inputs.
- **FR-008**: The LP solver MUST fail-fast with `FSMResult(state="ERROR")` if `context.solver_inputs` is `None`. This enforces the contract that the coordinator must populate solver inputs.
- **FR-009**: The coordinator MUST build solver inputs via a private method `_build_solver_inputs()` that has direct access to rates, config, forecasts, and live price entities.

### Key Entities

- **SolverInputs**: A new dataclass added to `fsm/base.py` with typed fields:
  - `price_buy: list[float]` — 288 import prices (c/kWh), t=0 is live price
  - `price_sell: list[float]` — 288 export prices (c/kWh), t=0 is live price
  - `load_kwh: list[float]` — 288 load values (kWh per 5-min step)
  - `pv_kwh: list[float]` — 288 solar values (kWh per 5-min step)
  - `no_import_steps: set[int] | None` — step indices where grid import is blocked
- **FSMContext**: Gains one new optional field: `solver_inputs: SolverInputs | None = None`. All existing fields remain unchanged. Raw forecast data still available for other FSM implementations.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The solver's `calculate_next_state` method contains zero dict `.get()` calls, zero `isinstance` checks on forecast items, and zero `kW * (5/60)` conversions.
- **SC-002**: For identical input data, the solver produces identical output before and after the refactor (byte-for-byte same `FSMResult`).
- **SC-003**: A test case with divergent live price vs forecast price produces the correct row-0 price (live price wins) with no orphaned forecast elements.
- **SC-004**: All 191 existing tests pass without modification (except test changes directly targeting the refactored code).
