# BUG-030 Follow-Up: Solver-Direct Cost Passthrough

## Goal Description
The `cumulative_cost` metric remains broken, creeping infinitesimally or appearing stuck at `0.00` instead of accurately tracking spending.

**Root Cause:**
While `lin_fsm.py` correctly calculates the cumulative cost per interval using `net_grid_kwh * price`, `coordinator.py` attempts to manually replicate this math. However, it mistakenly multiplies `net_grid_kwh` by `(5/60)` a second time, erroneously treating `kWh` as `kW`, and fracturing the tracked cost by a factor of 12. 
Furthermore, the `coordinator.py` disk save threshold requires a drift of `> 0.0001` per tick to trigger `async_delay_save()`. Due to the fractured calculation, small standard intervals drop below this threshold and simply never persist to the `.storage` file.

**Proposed Solution:**
Since the solver mathematically guarantees the exact price calculation for the 5-minute projection, `coordinator.py` should cease all dual-calculation. It should blindly pull the `cumulative_cost` directly from `sequence[0]` (the solver's completed mathematical step). 

## Proposed Changes

### 1. `custom_components/house_battery_control/coordinator.py`
Simplify the accumulation logic inside `_update_data()` to grab the solver's row 0 value.
#### [MODIFY] coordinator.py
- Delete the lines calculating `f_net_grid` and `interval_cost = f_net_grid * price * (5/60)`.
- Replace with `self.cumulative_cost = float(future_plan[0].get("cumulative_cost", self.cumulative_cost))`
- Adjust the disk-save drift logic to compare `abs(self.cumulative_cost - self._last_saved_cost) > 0.01` to ensure cents-level persistence.

## Verification
- Unit tests (`pytest tests/`) evaluate `cumulative_cost` logic correctly.
- In-memory HA simulation ticks up linearly as intended.
