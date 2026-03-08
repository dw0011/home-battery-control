# Feature 031: Dedicated Cumulative Cost Telemetry Tracker

## 1. Description
Extract the historical `cumulative_cost` tracking functionality entirely out of the core predictive HBC coordinator. The feature establishes a dedicated, isolated telemetry tracking mechanism that calculates the actual monetary value of electrons traded with the grid. It ceases to rely on the predictive FSM solver's mathematics, and instead utilizes real-world grid imports/exports and live pricing (e.g., from Amber Express) to perfectly track financial impact independent of solver execution execution rates.

## 2. Clarifications
### Session 2026-03-08
- Q: Which precision level from the Amber Express sensor should the tracker use for its calculations? → A: Option A (The exact `attributes.raw` float value).
- Q: How should the system handle a 5-minute tick if the Amber Express sensor is temporarily `unavailable` or `unknown` (e.g., API outage)? → A: Option B (Proceed with calculation by reusing the last known valid price).

## 3. User Scenarios & Acceptance Criteria

### Scenario 1: Isolated Financial Tracking
**Given** the user's solar and battery setup is actively fluctuating power to and from the grid  
**When** the system runs continuously over a 24-hour period  
**Then** the `cumulative_cost` sensor precisely mirrors the financial value of the actual physical electrons traded.  
**And** the cost tracking is completely impervious to the core FSM solver executing ten times in a minute or once in an hour.

### Scenario 2: Accurate Pricing Source
**Given** an Amber Express setup  
**When** the grid price physically shifts from 20c to 40c during a 5-minute interval  
**Then** the new cost tracker detects the new price vector and accurately invoices the exact duration of time spent at 20c and time spent at 40c based on the underlying grid power flow, using real-time price entities rather than forecasted theoretical rates.

## 3. Method (Single-Tick kWh Delta Tracking)
The cost tracking mechanism leverages absolute `kWh` integrations provided by physical hardware, executed on a simple time-based polling loop.
1. **Time Cadence**: The tracker operates strictly on a 5-minute clock boundary (e.g., `XX:00`, `XX:05`).
2. **Volume Delta**: At each 5-minute tick, the system reads the current `import_kwh` and `export_kwh` sensors and subtracts the values held from the previous tick to find the exact energy volume traded.
3. **Implicit Settlement**: Because the retailer price sensor naturally lags (settling ~4 minutes after the physical period ends), the system simply reads the *currently available* price sensor at the 5-minute tick. It inherently assumes this price represents the settled rate for the freshly completed block.
4. **Billing Calculation**: It multiplies the calculated `kWh` deltas by this price, appends the financial value to the `cumulative_cost` sensor, and saves the new `kWh` values to memory for the next 5-minute tick.

## 5. Sensors & Configuration
* **Dedicated Configuration Page**: The HBC Home Assistant integration UI will feature a separate, dedicated configuration page specifically for Telemetry Cost Tracking sensors.
* **Required Sensors**: 
  - Accumulated Grid Import (`kWh`)
  - Accumulated Grid Export (`kWh`)
  - Current Grid Import Price (`$/kWh`): *Must extract the precise `attributes.raw` float value, ignoring the rounded `state` string.*
* **Optional Feature**: Supplying sensors on this page is entirely optional.
* **Fallback Behavior**: If the telemetry tracking sensors are not supplied by the user, the predictive `cumulative_cost` metric will revert to starting at $0.00 for every solver run (abandoning continuous historical tracking).

## 6. Functional Requirements
1. **Solver Independence**: The historical cost tracking must be completely decoupled from the predictive FSM solver's mathematics.
2. **Delta Integration**: The tracking architecture calculates cost exclusively by multiplying `kWh` accumulated deltas by the price that was active during that delta.
3. **Data Persistence**: The accumulated value must reliably persist across system reboots, saving immediately upon any financial drift exceeding a negligible threshold (e.g., >$0.01).
4. **Resiliency to Gaps**: If the price API drops offline or returns an `unavailable`/`unknown` state, the tracker will defend the tick by reusing the last known valid price to calculate the current 5-minute volume delta.

## 7. Success Criteria
* **Accuracy Metrics**: Historical cost tracking aligns perfectly with HA native Energy Dashboard integrations or retail billing over a 7-day period (within a 5% margin of telemetry error).
* **Solver Desync Prevention**: Running the solver manually 500 times in a row via a debug script causes $0.00 artificial drift to the physical cumulative cost tracker.
* **Component Modularity**: The core prediction engine architecture is fundamentally blind to tracking past expenses, focusing only on predicting the future.

## 8. Scope Boundaries
* **In Scope**: Creating a dedicated config flow page for cost sensors; new independent logical module for utility tracking; 5-minute price locking.
* **Out of Scope**: Fetching historical API prices retroactively; replacing the HA native Energy Dashboard.

## 9. Assumptions
* Telemetry entities configured by the user (Grid Power, Current Price) update reliably and frequently enough to provide a relatively smooth integral curve.
* Users care about the continuous live tracking of dollars natively within HBC for immediate observation, alongside long-term analysis provided by HA Energy.
