# Implementation Plan: User Documentation

**Feature Branch**: `03-documentation`  
**Spec**: [spec.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/specs/03-documentation/spec.md)

## Proposed Changes

### Component 1: README.md (Rewrite)

#### [MODIFY] [README.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/README.md)

Complete rewrite. Structure:

1. **Header** — Project name, one-liner, badges (HACS, HA 2024.1+, MIT)
2. **What It Does** — 3-sentence elevator pitch
3. **Prerequisites** — Table: HA, HACS, Amber Electric integration, Solcast integration, Tesla/Powerwall via Teslemetry
4. **Installation** — HACS custom repo steps (numbered, copy-pasteable URL)
5. **Configuration** — 3-step flow summary table (Telemetry → Energy → Control), link to docs/configuration.md for detail
6. **Verifying It Works** — Check HBC sidebar entry, open panel, see power flow + FSM state
7. **Documentation** — Links to `/docs` pages
8. **Development** — pytest command, ruff command
9. **License** — MIT

**Removals**: Plan table references, wrong `/hbc` URL, `24-hour plan table` mention

---

### Component 2: docs/configuration.md (New)

#### [NEW] [configuration.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/docs/configuration.md)

Structure:

1. **Initial Setup** — Config flow walkthrough (3 steps with field explanations)
2. **Step 1: Telemetry** — Table of all entities: `battery_soc_entity`, `battery_power_entity`, `battery_power_invert`, `solar_entity`, `grid_entity`, `grid_power_invert`, `load_power_entity`
3. **Step 2: Energy & Metrics** — Table: cumulative sensors, temperature calibrations, battery specs, tariff entities, weather/solcast entities
4. **Step 3: Control Services** — Table: 4 scripts + `panel_admin_only` toggle
5. **Options Flow** — How to change settings after install (Settings → Integrations → Configure)
6. **Entity Inversion** — Explanation of when to use `battery_power_invert` and `grid_power_invert`

Source data: All `CONF_*` constants from `const.py` (26 keys) + `DEFAULT_*` values

---

### Component 3: docs/how-it-works.md (New)

#### [NEW] [how-it-works.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/docs/how-it-works.md)

Structure:

1. **Overview** — The system runs every 5 minutes, collects data, solves an optimisation problem, and sends a command to the Powerwall
2. **Data Pipeline** — Mermaid flowchart: Amber → RatesManager → rates[] → Coordinator → FSMContext → Solver → FSMResult → Executor → HA Scripts
3. **Inputs (exquisite detail)**:
   - **Tariffs** (`RateInterval`): `{start, end, import_price (c/kWh), export_price (c/kWh), type}`; 5-min intervals; 24h horizon; sourced from Amber Electric sensor attributes
   - **Solar Forecast** (`list[dict]`): `{start (ISO), kw (float)}`; 5-min intervals; 24h horizon; sourced from Solcast sensor `forecast` attribute
   - **Load Forecast** (`list[dict]`): `{start (ISO), kw (float)}`; 5-min intervals; 24h horizon; derived from 5-day HA recorder history + temperature adjustments
   - **Weather** (`list[dict]`): `{datetime, temperature, condition}`; hourly; sourced from HA weather entity forecast
   - **Battery State**: `soc (%)`, `battery_power (kW)`, `solar_production (kW)`, `grid_voltage (V)`, `current_price (c/kWh)`
   - **Battery Config**: `capacity (kWh)`, `charge_rate_max (kW)`, `inverter_limit (kW)`, `reserve_soc (%)`
4. **The Solver's Objectives** — What the LP solver tries to do:
   - **Objective**: Minimise total daily electricity cost (import cost − export revenue)
   - **Horizon**: 288 × 5-minute intervals (24 hours)
   - **Decision Variables**: For each interval — grid import (kW), grid export (kW), battery charge (kW), battery discharge (kW)
   - **Constraints respected**: SoC bounds (0% → 100%), charge/discharge rate limits, energy conservation per interval, reserve SoC floor
   - **What it does NOT do**: It does not predict prices — it consumes Amber's forward prices. It does not control individual cells. It does not learn from past behaviour.
5. **Outputs (exquisite detail)**:
   - **FSMResult**: `{state (str), limit_kw (float), reason (str), target_soc (float|None), projected_cost (float|None), future_plan (list[dict]|None)}`
   - **FSM States**: IDLE, CHARGE_GRID, CHARGE_SOLAR, DISCHARGE_HOME, DISCHARGE_GRID, PRESERVE — with what each means physically
   - **future_plan**: Array of 288 dicts, each representing 5 minutes of the optimal plan
6. **Execution** — How `PowerwallExecutor` maps states to scripts: state → script call table, deduplication logic
7. **The 5-Minute Cycle** — Coordinator update cadence, state change listeners, how changes propagate

---

### Component 4: docs/troubleshooting.md (New)

#### [NEW] [troubleshooting.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/docs/troubleshooting.md)

Common issues:

1. **Dashboard shows no data** — Check sensor entities are correct, check HA logs
2. **FSM is stuck in IDLE** — Check tariff entity has forecast data, check Solcast is working
3. **Battery power shows negative when charging** — Use inversion toggle
4. **Grid power direction is wrong** — Use grid inversion toggle
5. **Panel not visible in sidebar** — Check `panel_admin_only` setting, check admin status
6. **401 Unauthorized on API** — API requires admin auth
7. **Sensors show "unavailable"** — Prerequisite integration not set up

---

### Component 5: docs/architecture.md (New)

#### [NEW] [architecture.md](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/docs/architecture.md)

Brief contributor guide:

1. **Module map** — Table of all 19 source files with one-line purpose
2. **Data flow diagram** — Mermaid: sensors → managers → coordinator → FSM → executor → HA
3. **Testing** — Test suite structure, how to run, conftest patterns
4. **Code style** — ruff, mypy, type hints

---

### Component 6: manifest.json fix

#### [MODIFY] [manifest.json](file:///c:/Users/markn/OneDrive%20-%20IXL%20Signalling/0-01%20AI%20Programming/AI%20Coding/House%20Battery%20Control/custom_components/house_battery_control/manifest.json)

Fix `documentation` and `issue_tracker` URLs from `markn/house_battery_control` to `RangeyRover/home-battery-control`.

## Verification Plan

### Automated Tests
- No code changes → existing `pytest tests/ -v` still passes (133 tests)

### Manual Verification
- Push to GitHub → check README renders correctly on repo landing page
- Check all `/docs` links resolve
- Check manifest URLs are correct
