# Feature 032: SoC-Cap Plan Guard (BUG-034)

## 1. Description

When the LP solver's optimal solution includes importing grid energy during intervals where the battery is already at 100% SoC, the plan builder must recognise that this energy has no physical destination. A full battery cannot accept further charge. The current plan builder faithfully transcribes the LP solution's grid import variable (`g[i]`) and charge variable (`c[i]`) into the forecast table regardless of the battery state, producing physically impossible forecast rows that show `CHARGE_GRID` at `100.0%` SoC with large positive `Net Grid` values.

### Root Cause Analysis

There are two distinct but related problems:

#### Problem A: Plan Builder Display Bug (Phantom Imports)

The LP solver correctly optimises total cost. When import prices are negative (Amber Express pays the user to consume), the solver rationally imports energy even when the battery is full — because importing at a negative price reduces total objective cost. The LP's battery state variable `b[i]` is correctly upper-bounded at `capacity`, so the solver "knows" the energy can't go into the battery. But two downstream problems arise:

1. **Net Grid Calculation (line 255):** `net_grid_kwh = load - pv + charge - dh - dg`. The `charge` term (`step_c`) remains positive even though `b[i]` is capped at capacity. This produces a phantom positive Net Grid value — the plan claims the house is importing several kW from the grid when in reality the battery cannot accept it.

2. **State Classification (line 261):** `step_c > 0.005 and step_g > 0.005` triggers `CHARGE_GRID`. Since both the charge and grid import variables are positive (the LP found them profitable), the state is classified as CHARGE_GRID even though no physical charge can occur.

#### Problem B: LP Forced Export Blind Spot (Cost Exposure)

The LP solver has no variable representing **forced solar export**. When PV > Load and the battery is full, excess solar energy physically *must* export to the grid — the user cannot curtail solar production. If export prices are negative at that time, the user incurs a real financial penalty.

However, the LP's objective function only covers its decision variables (`g`, `c`, `dh`, `dg`). The unavoidable export flow `(pv - load)` when the battery is full is invisible to the optimiser. This means the LP can fill the battery early at cheap/negative import prices — believing it's saving money — without accounting for the downstream forced exports at negative export prices that this strategy causes.

The grid balance constraint `g[i] - c[i] - dh[i] - dg[i] >= energy[i]` is trivially satisfied when `energy[i] < 0` (PV > Load), but the cost of the resulting export never enters the objective function.

### Impact

- The user sees 4-6 kW of grid import at `100%` SoC for hours during peak solar, which is physically impossible
- At 15:00–15:25, the import price flips positive, and the plan now shows a *cost* for phantom imports that will never actually happen
- **The LP may fill the battery early on cheap prices, then the user is forced to export excess solar at negative prices — a cost the solver never considered**
- The cumulative cost forecast diverges from reality because it accounts for energy flows that cannot physically occur
- User trust in the forecast is undermined

## 2. User Scenarios & Acceptance Criteria

### Scenario 1: Battery Full During Negative Import Prices
**Given** the battery SoC is at 100% in the forecast  
**And** the import price is negative (e.g. -$0.05/kWh)  
**When** the plan builder constructs the forecast row  
**Then** the charge variable is clamped to zero for that step  
**And** Net Grid reflects only the unavoidable energy balance (load - pv)  
**And** the FSM State is `SELF_CONSUMPTION` (not `CHARGE_GRID`)  
**And** if PV > Load, the excess is shown as negative Net Grid (export)

### Scenario 2: Battery Full During Positive Import Prices
**Given** the battery SoC is at 100% in the forecast  
**And** the import price is positive  
**When** the plan builder constructs the forecast row  
**Then** no grid import for charging is shown  
**And** Net Grid only reflects the house load deficit if load > pv  
**And** the FSM State is `SELF_CONSUMPTION`

### Scenario 3: Battery Approaching Full
**Given** the battery SoC is at 99% in the forecast  
**And** only 0.1 kWh of headroom remains before capacity  
**When** the LP solver proposes 0.5 kWh of charge  
**Then** the plan builder clamps the charge to the available headroom (0.1 kWh)  
**And** Net Grid and state reflect only the physically achievable charge

### Scenario 4: Normal Charging (Not Full)
**Given** the battery SoC is at 60% in the forecast  
**When** the LP solver proposes charging  
**Then** the plan builder passes through the LP solution unchanged  
**And** Net Grid and state classification work exactly as they do today  
**And** no regression occurs in the normal charging path

### Scenario 5: Forced Solar Export at Negative Export Prices
**Given** the battery is at 100% SoC (having been filled earlier at cheap prices)  
**And** PV generation exceeds house load (e.g. PV=4.2kW, Load=2.5kW)  
**And** the export price is negative (e.g. -$0.14/kWh)  
**When** the plan builder constructs the forecast row  
**Then** Net Grid shows the forced export as negative (e.g. -1.7 kW)  
**And** the cumulative cost correctly accounts for the penalty of exporting at a negative price  
**And** the LP solver should have considered this forced export penalty when originally deciding whether to fill the battery early

## 3. Functional Requirements

### Part A: Plan Builder Guard (No LP Changes)

### FR-001: SoC Headroom Gate
Before computing Net Grid and state classification for each forecast step, the plan builder must calculate the available battery headroom: `headroom = capacity - b[i]`. If `headroom <= 0`, the charge variable (`step_c`) must be clamped to zero.

### FR-002: Charge Clamping to Headroom
If `0 < headroom < step_c`, the charge variable must be clamped to `headroom` (not zero). Only the physically achievable portion of the charge is reflected in the forecast.

### FR-003: Grid Import Adjustment
When charge is clamped (FR-001 or FR-002), the grid import variable (`step_g`) must be reduced by the same amount as the charge reduction. Grid import exists only to serve load deficit and battery charging; if charging is reduced, the corresponding grid import is no longer needed.

### FR-004: Net Grid Recalculation
After clamping, Net Grid must be recalculated using the adjusted charge and grid import values. The formula `net_grid_kwh = load - pv + clamped_charge - dh - dg` must produce physically realistic energy flows.

### FR-005: State Reclassification
After clamping, the state classification must be re-evaluated using the adjusted values. If charge drops below the threshold (0.005), the state must revert to `SELF_CONSUMPTION`.

### FR-006: Cumulative Cost Accuracy
Cumulative cost must be computed using the adjusted Net Grid values, not the raw LP solution. This ensures the forecast cost trajectory matches the physically achievable energy flows.

### Part B: LP Forced Export Awareness (LP Solver Enhancement)

### FR-007: Forced Export Spill Variable
The LP solver must introduce a new decision variable `s[i]` (spill/forced export) for each step, representing the unavoidable solar export when PV > Load and the battery cannot absorb the excess. The spill variable must be costed in the objective function at the export price `price_sell[i]`, so the solver sees the true financial impact of a full battery during solar generation.

### FR-008: Spill Constraint
For each step, the spill variable must satisfy: when PV > Load and charge headroom is zero, `s[i] >= (pv[i] - load[i])`. This forces the solver to account for the export cost of excess solar when the battery is full.

## 4. Non-Functional Requirements

### NFR-001: Performance
Part A adds O(1) operations per forecast step. Part B adds N additional variables and constraints to the LP, which is negligible relative to the existing 5N variable formulation.

### NFR-002: Backward Compatibility
All existing test cases for normal charging, discharging, and self-consumption must continue to pass unchanged.

## 5. Success Criteria

- When SoC = 100% in any forecast row, the FSM State is never `CHARGE_GRID`
- When SoC = 100% in any forecast row, Net Grid is never positive unless load > pv (i.e. the house genuinely needs grid power to serve load)
- When SoC = 100% and PV > Load, the forecast correctly shows export and costs it at the export price
- The LP solver considers the cost of forced solar exports when deciding whether to charge the battery early
- Cumulative Cost at the end of the forecast horizon matches the physically achievable cost
- All existing unit tests pass without modification

## 6. Assumptions

- The LP solver's `b[i]` variable correctly represents battery state after accounting for efficiency losses
- The plan builder's `step_b` value (line 237) is the authoritative SoC for each step
- Clamping charge at the plan builder level does not invalidate the LP solution for subsequent steps, because the LP already caps `b[i]` at capacity in its own constraints
- The `soc_correction` accumulator (BUG-025B, line 233) must also account for energy retained by the SoC-cap guard
- Solar curtailment is not physically available to the user — excess solar must always export

## 7. Dependencies

- Feature 031 (Telemetry Cost Tracker): The real-world cumulative cost is tracked independently. This fix only affects the *forecast* cost display.
- BUG-025B (Acquisition Cost Gate): The `soc_correction` pattern already exists and provides a proven template for carrying forward energy adjustments across forecast steps.
