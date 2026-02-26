"""
lin_fsm.py — LP FSM (SciPy HiGHS)
===================================
Implements all system requirements from specs/03-lp-fsm-system/system_requirements.md.
34 tests across 6 suites verify compliance.
"""
try:
    from .base import BatteryStateMachine, FSMContext, FSMResult
except ImportError:
    from base import BatteryStateMachine, FSMContext, FSMResult

import logging
import math
import statistics
from datetime import datetime, time, timedelta

import numpy as np
from scipy.optimize import linprog

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  No-Import Period helpers (Feature 010)
# ---------------------------------------------------------------------------
def _parse_no_import_periods(config_str: str) -> list[tuple[time, time]]:
    """Parse comma-separated 'HH:MM-HH:MM' strings into (start, end) time tuples.

    Returns empty list for empty/None input. Invalid entries are logged and skipped.
    """
    if not config_str or not config_str.strip():
        return []
    periods = []
    for part in config_str.split(","):
        part = part.strip()
        if "-" not in part:
            _LOGGER.warning(f"Invalid no-import period (no dash): '{part}'")
            continue
        try:
            start_str, end_str = part.split("-", 1)
            sh, sm = map(int, start_str.strip().split(":"))
            eh, em = map(int, end_str.strip().split(":"))
            periods.append((time(sh, sm), time(eh, em)))
        except (ValueError, IndexError) as e:
            _LOGGER.warning(f"Invalid no-import period '{part}': {e}")
            continue
    return periods


def _is_in_no_import_period(t: time, periods: list[tuple[time, time]]) -> bool:
    """Check if a local time falls within any no-import period.

    Handles midnight-spanning windows (e.g. 22:00-06:00).
    """
    for start, end in periods:
        if start <= end:
            # Normal window: e.g. 15:00-21:00
            if start <= t < end:
                return True
        else:
            # Midnight wrap: e.g. 22:00-06:00
            if t >= start or t < end:
                return True
    return False


# ---------------------------------------------------------------------------
#  FakeBattery — §6 of system requirements
# ---------------------------------------------------------------------------
class FakeBattery:
    """Lightweight battery model constructed from FSMContext config."""

    def __init__(
        self,
        capacity: float,
        current_charge: float,
        charge_limit: float,
        discharge_limit: float,
        charging_efficiency: float = 0.95,
        discharging_efficiency: float = 0.95,
    ):
        self.capacity = capacity
        self.current_charge = current_charge          # fraction 0-1
        self.charging_power_limit = charge_limit      # kW
        self.discharging_power_limit = discharge_limit  # kW
        self.charging_efficiency = charging_efficiency
        self.discharging_efficiency = discharging_efficiency


# ---------------------------------------------------------------------------
#  LinearBatteryController — core LP solver (SciPy translation of GLOP source)
# ---------------------------------------------------------------------------
class LinearBatteryController:
    """
    Translates the original GLOP competition LP formulation into SciPy's linprog.

    Variable layout (1D vector x):
        g[0..N-1]   grid import          bounds: [0, ∞)
        c[0..N-1]   battery charge       bounds: [0, charge_limit_kwh]
        dh[0..N-1]  discharge to home    bounds: [-max_home_kwh, 0]
        dg[0..N-1]  discharge to grid    bounds: [-max_grid_kwh, 0]
        b[0..N]     battery state        bounds: [safe_lb, capacity]
    """

    def __init__(self):
        self.step = 288

    def propose_state_of_charge(
        self,
        battery: FakeBattery,
        price_buy: list[float],
        price_sell: list[float],
        load_forecast: list[float],
        pv_forecast: list[float],
        acquisition_cost: float = 0.0,
        raw_acquisition_cost: float = 0.0,
        reserve_soc: float = 0.0,
        no_import_steps: set[int] | None = None,
    ):
        number_step = min(288, self.step)

        # --- Physical parameters ---
        capacity = battery.capacity
        eta_in = battery.charging_efficiency
        eta_out = 1.0 / battery.discharging_efficiency
        current = capacity * battery.current_charge
        charge_limit = battery.charging_power_limit * (5.0 / 60.0)   # kW → kWh per step
        dis_limit = battery.discharging_power_limit * (5.0 / 60.0)

        # --- Net energy requirement per step ---
        energy = [load_forecast[i] - pv_forecast[i] for i in range(number_step)]

        # --- Variable offsets ---
        g_off = 0
        c_off = number_step
        dh_off = 2 * number_step
        dg_off = 3 * number_step
        b_off = 4 * number_step
        num_vars = 4 * number_step + (number_step + 1)

        # --- Objective function (§7 of system requirements) ---
        obj = np.zeros(num_vars)
        bounds = []

        _blocked = no_import_steps or set()
        for i in range(number_step):
            # Grid import: use raw price (can be negative = incentive to import)
            # FR-001: Solver must see the economic benefit of negative import prices
            # FR-002: Upper-bound g[i] during negative prices to prevent unbounded LP
            obj[g_off + i] = price_buy[i]
            if i in _blocked:
                # No-import period: force grid import to zero (Feature 010)
                bounds.append((0.0, 0.0))
            elif price_buy[i] < 0:
                # Physical bound: can't import more than load + battery charge rate
                max_import = load_forecast[i] + charge_limit
                bounds.append((0.0, max_import))
            else:
                bounds.append((0.0, None))

        for i in range(number_step):
            # Charge: opportunity cost = max(ε, sell_price) + tiebreaker — §7.2
            obj[c_off + i] = max(0.001, price_sell[i]) + max(0.0, price_buy[i]) / 1000.0
            bounds.append((0.0, charge_limit))

        for i in range(number_step):
            # Discharge to home: opportunity cost = max(ε, sell_price)
            obj[dh_off + i] = max(0.001, price_sell[i])
            max_home = max(0.0, energy[i])
            bounds.append((-max_home, 0.0))

        for i in range(number_step):
            # Discharge to grid: opportunity cost = max(ε, sell_price)
            # FR-002: Lock grid discharge to zero when export is below raw acquisition cost
            obj[dg_off + i] = max(0.001, price_sell[i])
            if price_sell[i] < raw_acquisition_cost:
                bounds.append((0.0, 0.0))  # Export unprofitable — gate closed
            else:
                max_home = max(0.0, energy[i])
                max_grid = max(0.0, dis_limit - max_home)
                bounds.append((-max_grid, 0.0))

        # Battery state bounds with dynamic feasibility gradient — §8
        reserve_kwh = capacity * (reserve_soc / 100.0)
        for i in range(number_step + 1):
            if i == number_step:
                # Terminal valuation — §9
                obj[b_off + i] = -max(0.001, acquisition_cost)
            else:
                obj[b_off + i] = 0.0
            physically_accessible = current + i * charge_limit * eta_in
            safe_lb = min(reserve_kwh, physically_accessible)
            bounds.append((safe_lb, capacity))

        # --- Inequality constraints: grid balance ---
        # g[i] - c[i] - dh[i] - dg[i] >= energy[i]
        # Rewrite: -g[i] + c[i] + dh[i] + dg[i] <= -energy[i]
        a_ub = np.zeros((number_step, num_vars))
        b_ub = np.zeros(number_step)
        for i in range(number_step):
            a_ub[i, g_off + i] = -1.0
            a_ub[i, c_off + i] = 1.0
            a_ub[i, dh_off + i] = 1.0
            a_ub[i, dg_off + i] = 1.0
            b_ub[i] = -energy[i]

        # --- Equality constraints: battery dynamics ---
        # b[0] = current
        # b[i+1] = b[i] + c[i]*eta_in + dh[i]*eta_out + dg[i]*eta_out
        a_eq = np.zeros((number_step + 1, num_vars))
        b_eq = np.zeros(number_step + 1)

        a_eq[0, b_off] = 1.0
        b_eq[0] = current

        for i in range(number_step):
            a_eq[i + 1, c_off + i] = eta_in
            a_eq[i + 1, dh_off + i] = eta_out
            a_eq[i + 1, dg_off + i] = eta_out
            a_eq[i + 1, b_off + i] = 1.0
            a_eq[i + 1, b_off + i + 1] = -1.0
            b_eq[i + 1] = 0.0

        # --- Solve ---
        res = linprog(obj, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq,
                      bounds=bounds, method="highs")

        if not res.success:
            _LOGGER.warning("LP solver failed: %s", res.message)
            return battery.current_charge, 0.0, 0.0, 0.0, []

        # --- Extract first-step outputs ---
        b_1 = res.x[b_off + 1]
        objective_value = res.fun
        dh_0 = abs(res.x[dh_off])
        dg_0 = abs(res.x[dg_off])

        # --- Build 288-step future plan sequence ---
        running_capacity = battery.current_charge
        running_cost = acquisition_cost
        running_cum_cost = 0.0
        sequence = []

        for i in range(number_step):
            step_b = res.x[b_off + i + 1]
            step_c = res.x[c_off + i]
            step_g = res.x[g_off + i]
            step_dh = abs(res.x[dh_off + i])
            step_dg = abs(res.x[dg_off + i])

            # --- Acquisition cost tracking — §12 (uses raw unclamped prices) ---
            if step_c > 0.001:
                charge_from_grid = min(step_c, step_g)
                charge_cost = charge_from_grid * price_buy[i]
                current_value = running_capacity * running_cost
                new_value = current_value + charge_cost
                new_capacity = running_capacity + step_c
                if new_capacity > 0:
                    running_cost = new_value / new_capacity
            running_capacity = step_b

            # --- Net grid flow — §11.2 (energy balance, inherently handles degeneracy) ---
            net_grid_kwh = load_forecast[i] - pv_forecast[i] + step_c - step_dh - step_dg
            net_grid_kw = net_grid_kwh * (60.0 / 5.0)

            # --- State classification — §11.3 (solver variables, same approach as §10.2) ---
            if step_dg > 0.005:
                state = "DISCHARGE_GRID"
            elif step_c > 0.005 and step_g > 0.005:
                state = "CHARGE_GRID"
            else:
                state = "SELF_CONSUMPTION"

            # --- Cumulative cost tracking — §3.4 (raw prices, net grid flow) ---
            if net_grid_kwh > 0:
                running_cum_cost += net_grid_kwh * price_buy[i]
            else:
                running_cum_cost += net_grid_kwh * price_sell[i]

            sequence.append({
                "target_soc": (step_b / capacity) * 100.0,
                "state": state,
                "net_grid": net_grid_kw,
                "load": load_forecast[i] * (60.0 / 5.0),
                "pv": pv_forecast[i] * (60.0 / 5.0),
                "import_price": price_buy[i],
                "export_price": price_sell[i],
                "acquisition_cost": running_cost,
                "cumulative_cost": running_cum_cost,
            })

        return b_1 / capacity, objective_value, dh_0, dg_0, sequence


# ---------------------------------------------------------------------------
#  LinearBatteryStateMachine — adapter for FSMContext/FSMResult interface
# ---------------------------------------------------------------------------
class LinearBatteryStateMachine(BatteryStateMachine):
    """
    Wraps LinearBatteryController to satisfy the BatteryStateMachine ABC.
    This is the entry point for both hybrid_tester.py and coordinator.py.
    """

    def __init__(self):
        self.controller = LinearBatteryController()

    def calculate_next_state(self, context: FSMContext) -> FSMResult:
        # Force 288-step horizon — §4
        number_step = 288
        self.controller.step = number_step

        # --- Extract & pad forecast arrays — §5 ---
        price_buy = [0.0] * number_step
        price_sell = [0.0] * number_step
        for t in range(number_step):
            if t == 0:
                price_buy[t] = float(context.current_price)
                price_sell[t] = float(context.current_export_price)
                continue

            idx = min(t, len(context.forecast_price) - 1) if context.forecast_price else 0
            if idx < len(context.forecast_price):
                entry = context.forecast_price[idx]
                if isinstance(entry, dict):
                    price_buy[t] = float(entry.get("import_price", 0.0))
                    price_sell[t] = float(entry.get(
                        "export_price",
                        float(entry.get("import_price", 0.0)) * 0.8,
                    ))
                else:
                    price_buy[t] = float(context.current_price)
                    price_sell[t] = float(context.current_price * 0.8)
            else:
                price_buy[t] = float(context.current_price)
                price_sell[t] = float(context.current_price * 0.8)

        load_f = [0.0] * number_step
        pv_f = [0.0] * number_step
        for t in range(number_step):
            # Solar
            idx = min(t, len(context.forecast_solar) - 1) if context.forecast_solar else 0
            if idx < len(context.forecast_solar):
                entry = context.forecast_solar[idx]
                pv_f[t] = float(entry.get("kw", 0.0)) if isinstance(entry, dict) else float(entry)
            # Load
            idx = min(t, len(context.forecast_load) - 1) if context.forecast_load else 0
            if idx < len(context.forecast_load):
                entry = context.forecast_load[idx]
                load_f[t] = float(entry.get("kw", 0.0)) if isinstance(entry, dict) else float(entry)

        # kW → kWh per 5-minute step — §4
        load_f = [kw * (5.0 / 60.0) for kw in load_f]
        pv_f = [kw * (5.0 / 60.0) for kw in pv_f]

        # --- Battery model — §6 ---
        capacity = max(13.5, context.config.get("battery_capacity",
                       context.config.get("capacity_kwh", 27.0)))
        limit_kw_charge = float(context.config.get("battery_rate_max", 6.3))
        limit_kw_discharge = float(context.config.get("inverter_limit", 10.0))
        current_soc = max(0.0, min(100.0, context.soc)) / 100.0

        rte = float(context.config.get("round_trip_efficiency", 0.90))
        one_way_eff = math.sqrt(rte)

        battery = FakeBattery(
            capacity=capacity,
            current_charge=current_soc,
            charge_limit=limit_kw_charge,
            discharge_limit=limit_kw_discharge,
            charging_efficiency=one_way_eff,
            discharging_efficiency=one_way_eff,
        )

        # --- Terminal valuation — §9 ---
        median_buy = statistics.median(price_buy) if price_buy else context.acquisition_cost
        blended = (median_buy + context.acquisition_cost) / 2.0
        terminal_valuation = max(context.acquisition_cost, blended)

        # --- No-Import Periods (Feature 010) ---
        no_import_steps: set[int] = set()
        nip_config = context.config.get("no_import_periods", "")
        nip_periods = _parse_no_import_periods(nip_config)
        if nip_periods and context.forecast_price:
            # Use forecast_price timestamps to map steps to wall-clock time
            for t in range(number_step):
                idx = min(t, len(context.forecast_price) - 1)
                entry = context.forecast_price[idx]
                if isinstance(entry, dict) and "start" in entry:
                    step_dt = entry["start"]
                    # Convert to local time for comparison
                    try:
                        local_t = step_dt.astimezone().time()
                    except Exception:
                        local_t = step_dt.time() if hasattr(step_dt, "time") else None
                    if local_t and _is_in_no_import_period(local_t, nip_periods):
                        no_import_steps.add(t)
            if no_import_steps:
                _LOGGER.info(
                    f"No-import periods active: {len(no_import_steps)} of {number_step} steps blocked"
                )

        # --- Solve ---
        try:
            target_soc_frac, projected_cost, raw_dh, raw_dg, sequence = (
                self.controller.propose_state_of_charge(
                    battery=battery,
                    price_buy=price_buy,
                    price_sell=price_sell,
                    load_forecast=load_f,
                    pv_forecast=pv_f,
                    acquisition_cost=terminal_valuation,
                    raw_acquisition_cost=context.acquisition_cost,
                    reserve_soc=float(context.config.get("reserve_soc", 0.0)),
                    no_import_steps=no_import_steps if no_import_steps else None,
                )
            )
        except Exception as e:
            _LOGGER.error("LP Solver failed: %s", e)
            return FSMResult(state="ERROR", limit_kw=0.0, reason=f"Solver Error: {e}")

        if target_soc_frac is None:
            return FSMResult(state="ERROR", limit_kw=0.0, reason="Solver returned None")

        target_soc_frac = float(target_soc_frac)

        # --- Immediate action classification — §10 ---
        target_delta_kwh = (target_soc_frac - current_soc) * capacity
        power_kw = target_delta_kwh * 12.0  # kWh per 5-min → kW

        if power_kw > 0.1:
            req = power_kw / battery.charging_efficiency
            return FSMResult(
                state="CHARGE_GRID",
                limit_kw=round(min(limit_kw_charge, req), 2),
                reason="LP Optimized Charge",
                target_soc=target_soc_frac * 100.0,
                projected_cost=projected_cost,
                future_plan=sequence,
            )
        elif power_kw < -0.1:
            req = abs(power_kw) * battery.discharging_efficiency
            dg_kw = raw_dg / (5.0 / 60.0)
            dh_kw = raw_dh / (5.0 / 60.0)

            if dg_kw > dh_kw:
                return FSMResult(
                    state="DISCHARGE_GRID",
                    limit_kw=round(min(limit_kw_discharge, req), 2),
                    reason="LP Optimized Grid Export",
                    target_soc=target_soc_frac * 100.0,
                    projected_cost=projected_cost,
                    future_plan=sequence,
                )
            else:
                return FSMResult(
                    state="SELF_CONSUMPTION",
                    limit_kw=0.0,
                    reason="LP Optimized Self-Consumption",
                    target_soc=target_soc_frac * 100.0,
                    projected_cost=projected_cost,
                    future_plan=sequence,
                )

        return FSMResult(
            state="SELF_CONSUMPTION",
            limit_kw=0.0,
            reason="LP Optimization: No action needed",
            target_soc=target_soc_frac * 100.0,
            projected_cost=projected_cost,
            future_plan=sequence,
        )
