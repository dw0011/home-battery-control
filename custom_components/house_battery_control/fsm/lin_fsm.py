try:
    from .base import BatteryStateMachine, FSMContext, FSMResult
except ImportError:
    from base import BatteryStateMachine, FSMContext, FSMResult
import logging

_LOGGER = logging.getLogger(__name__)


class LinearBatteryController(object):
    def __init__(self):
        self.step = 288  # For 24 hour 5 min resolution

    def propose_state_of_charge(
        self,
        site_id,
        timestamp,
        battery,
        actual_previous_load,
        actual_previous_pv_production,
        price_buy,
        price_sell,
        load_forecast,
        pv_forecast,
        acquisition_cost=0.0,
    ):

        self.step -= 1
        if self.step == 1:
            return 0
        if self.step > 1:
            number_step = min(288, self.step)

        #
        energy = [None] * number_step

        for i in range(number_step):
            # Energy array tracks net load requirements
            energy[i] = load_forecast[i] - pv_forecast[i]
        # battery
        capacity = battery.capacity
        charging_efficiency = battery.charging_efficiency
        discharging_efficiency = 1.0 / battery.discharging_efficiency
        current = capacity * battery.current_charge
        limit = battery.charging_power_limit
        dis_limit = battery.discharging_power_limit

        # Convert kw limits to kwh limits per 5 min step
        limit = limit * (5.0 / 60.0)
        dis_limit = dis_limit * (5.0 / 60.0)

        # Scipy linprog
        import numpy as np
        from scipy.optimize import linprog

        # Define x vector structure:
        # [grid(0..N-1), charge(0..N-1), dh(0..N-1), dg(0..N-1), battery(0..N)]
        num_vars = 4 * number_step + (number_step + 1)
        c = np.zeros(num_vars)
        bounds = []

        g_offset = 0
        c_offset = number_step
        dh_offset = 2 * number_step
        dg_offset = 3 * number_step
        b_offset = 4 * number_step

        for i in range(number_step):
            # Cost of grid import is precisely the purchase price.
            # (Previously Pb - Ps, which assumed baseline grid flow was a sold asset).
            c[g_offset + i] = price_buy[i]
            bounds.append((0.0, None))

        for i in range(number_step):
            # Charging from the grid is implicitly captured by `g`.
            # Charging from PV prevents exporting it, losing Ps.
            c[c_offset + i] = price_sell[i] + price_buy[i] / 1000.0
            bounds.append((0.0, limit))

        for i in range(number_step):
            # Discharging to the home reduces grid import `g`.
            # `g` already natively saves `Pb`.
            # We must set this to `Ps` offset so it balances the opportunity cost of not exporting.
            c[dh_offset + i] = price_sell[i]
            max_home_kwh = max(0.0, energy[i])
            bounds.append((-max_home_kwh, 0.0))

        for i in range(number_step):
            c[dg_offset + i] = price_sell[i]
            max_home_kwh = max(0.0, energy[i])
            max_grid_kwh = max(0.0, dis_limit - max_home_kwh)
            bounds.append((-max_grid_kwh, 0.0))

        for i in range(number_step + 1):
            if i == number_step:
                # b[-1] coef
                c[b_offset + i] = -max(0.001, acquisition_cost)
            else:
                c[b_offset + i] = 0.0
            bounds.append((0.0, capacity))

        # Inequalities (a_ub @ x <= b_ub)
        # grid[i] - charge[i] - dh[i] - dg[i] >= energy[i]
        # Rewrite as: -grid[i] + charge[i] + dh[i] + dg[i] <= -energy[i]
        a_ub = np.zeros((number_step, num_vars))
        b_ub = np.zeros(number_step)
        for i in range(number_step):
            a_ub[i, g_offset + i] = -1.0
            a_ub[i, c_offset + i] = 1.0
            a_ub[i, dh_offset + i] = 1.0
            a_ub[i, dg_offset + i] = 1.0
            b_ub[i] = -energy[i]

        # Equalities (a_eq @ x == b_eq)
        # 1. b[0] == current
        # 2. b[i+1] == b[i] + charge[i]*eff_in + dh[i]*eff_out + dg[i]*eff_out
        # Rewrite 2 as: charge[i]*eff_in + dh[i]*eff_out + dg[i]*eff_out + b[i] - b[i+1] == 0
        a_eq = np.zeros((number_step + 1, num_vars))
        b_eq = np.zeros(number_step + 1)

        a_eq[0, b_offset] = 1.0
        b_eq[0] = current

        for i in range(number_step):
            a_eq[i + 1, c_offset + i] = charging_efficiency
            a_eq[i + 1, dh_offset + i] = discharging_efficiency
            a_eq[i + 1, dg_offset + i] = discharging_efficiency
            a_eq[i + 1, b_offset + i] = 1.0
            a_eq[i + 1, b_offset + i + 1] = -1.0
            b_eq[i + 1] = 0.0

        # Solve
        res = linprog(c, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")

        if not res.success:
            _LOGGER.warning("Linear solver could not find optimal solution: %s", res.message)
            return battery.current_charge, 0.0, 0.0, 0.0, []

        b_1 = res.x[b_offset + 1]
        obj = res.fun
        dh_0 = abs(res.x[dh_offset])
        dg_0 = abs(res.x[dg_offset])

        running_capacity = battery.current_charge
        running_cost = acquisition_cost

        sequence = []
        for i in range(number_step):
            step_b = res.x[b_offset + i + 1]
            step_c = res.x[c_offset + i]
            step_g = res.x[g_offset + i]
            step_dh = abs(res.x[dh_offset + i])
            step_dg = abs(res.x[dg_offset + i])

            # Track dynamic acquisition cost based on interval charging flows
            if step_c > 0.001:
                # Attribute imported energy costs directly to the battery up to the charged volume.
                charge_from_grid = min(step_c, step_g)
                charge_cost = charge_from_grid * price_buy[i]

                current_value = running_capacity * running_cost
                new_value = current_value + charge_cost
                new_capacity = running_capacity + step_c

                if new_capacity > 0:
                    running_cost = new_value / new_capacity

            running_capacity = step_b

            # Interpret the mathematical flows into semantic controller states
            # We map to the 3 native hardware modes required by the HA Home Battery Controller.
            # Any state that is not explicitly forcing grid import or grid export is simply
            # delegating back to the inverter's automated Self-Consumption mode.
            if step_dg > 0.005:
                state = "DISCHARGE_GRID"
            elif step_c > 0.005 and step_g > 0.005:
                state = "CHARGE_GRID"
            else:
                state = "SELF_CONSUMPTION"

            # Calculate actual bidirectional net grid flow predicted by the solver
            # The continuous LP solver can mathematically 'degenerate' by simultaneously evaluating
            # step_c and step_dh on the exact same interval to artificially minimize the objective boundary
            # cost of step_g. Physical batteries cannot charge and discharge simultaneously.
            net_grid_kwh = load_forecast[i] - pv_forecast[i]
            if state == "CHARGE_GRID":
                net_grid_kwh += step_c
            else:
                net_grid_kwh += step_c - step_dh - step_dg

            sequence.append(
                {
                    "target_soc": (step_b / capacity) * 100.0,
                    "state": state,
                    "net_grid": net_grid_kwh * (60.0 / 5.0),
                    "load": load_forecast[i] * (60.0 / 5.0),
                    "pv": pv_forecast[i] * (60.0 / 5.0),
                    "import_price": price_buy[i],
                    "export_price": price_sell[i],
                    "acquisition_cost": running_cost,
                }
            )

        return b_1 / capacity, obj, dh_0, dg_0, sequence


class FakeBattery:
    def __init__(
        self,
        capacity,
        current_charge,
        charge_limit,
        discharge_limit,
        charging_efficiency=0.95,
        discharging_efficiency=0.95,
    ):
        self.capacity = capacity
        # charge state in percentage (0-1)
        self.current_charge = current_charge
        self.charging_power_limit = charge_limit
        self.discharging_power_limit = discharge_limit
        self.charging_efficiency = charging_efficiency
        self.discharging_efficiency = discharging_efficiency


class LinearBatteryStateMachine(BatteryStateMachine):
    """
    Implementation using pywraplp solver.
    """

    def __init__(self):
        self.controller = LinearBatteryController()

    def calculate_next_state(self, context: FSMContext) -> FSMResult:
        # Force a strict 24-hour horizon (288 steps) to push the terminal boundary value out of frame.
        # This prevents the solver from prematurely dumping energy to the grid if the API forecast data falls short.
        number_step = 288

        # Always reset step count in loop for stateless evaluation
        self.controller.step = number_step

        price_buy = [0.0] * number_step
        price_sell = [0.0] * number_step
        for t in range(number_step):
            idx = min(t, len(context.forecast_price) - 1) if len(context.forecast_price) > 0 else 0
            if idx < len(context.forecast_price):
                if isinstance(context.forecast_price[idx], dict):
                    price_buy[t] = float(context.forecast_price[idx].get("import_price", 0.0))
                    price_sell[t] = float(
                        context.forecast_price[idx].get(
                            "export_price",
                            float(context.forecast_price[idx].get("import_price", 0.0)) * 0.8,
                        )
                    )
                else:
                    price_buy[t] = float(context.current_price)
                    price_sell[t] = float(context.current_price * 0.8)
            else:
                price_buy[t] = float(context.current_price)
                price_sell[t] = float(context.current_price * 0.8)

        load_f = [0.0] * number_step
        pv_f = [0.0] * number_step
        for t in range(number_step):
            # Pad solar with the last known assumed solar
            idx = min(t, len(context.forecast_solar) - 1) if len(context.forecast_solar) > 0 else 0
            if idx < len(context.forecast_solar):
                if isinstance(context.forecast_solar[idx], dict):
                    pv_f[t] = float(context.forecast_solar[idx].get("kw", 0.0))
                else:
                    pv_f[t] = float(context.forecast_solar[idx])
            else:
                pv_f[t] = 0.0

            # Pad load with the last known assumed load
            idx = min(t, len(context.forecast_load) - 1) if len(context.forecast_load) > 0 else 0
            if idx < len(context.forecast_load):
                if isinstance(context.forecast_load[idx], dict):
                    load_f[t] = float(context.forecast_load[idx].get("kw", 0.0))
                else:
                    load_f[t] = float(context.forecast_load[idx])
            else:
                load_f[t] = 0.0

        # Convert kW to kWh for the discrete step bounds
        load_f = [kw * (5.0 / 60.0) for kw in load_f]
        pv_f = [kw * (5.0 / 60.0) for kw in pv_f]

        capacity = max(
            13.5, context.config.get("battery_capacity", context.config.get("capacity_kwh", 27.0))
        )
        limit_kw_charge = float(context.config.get("battery_rate_max", 6.3))
        limit_kw_discharge = float(context.config.get("inverter_limit", 10.0))
        current_soc_perc = max(0.0, min(100.0, context.soc)) / 100.0

        import math

        # Extract Round Trip Efficiency (RTE) from config. Default to 0.90 if missing.
        rte = float(context.config.get("round_trip_efficiency", 0.90))
        # Mathematical one-way efficiency is the square root of the round trip efficiency
        one_way_eff = math.sqrt(rte)

        battery = FakeBattery(
            capacity=capacity,
            current_charge=current_soc_perc,
            charge_limit=limit_kw_charge,
            discharge_limit=limit_kw_discharge,
            charging_efficiency=one_way_eff,
            discharging_efficiency=one_way_eff,
        )

        # Dynamic terminal valuation to prevent the solver dumping the battery to 0% at the horizon boundary.
        # We use a mathematically blended weight: the average of the median import price and the acquisition cost.
        # This explicitly tells the solver "tomorrow's energy has value" (preventing a dump)
        # without making it so high that it incentivizes hoarding 26c grid power today.
        import statistics

        median_buy_price = (
            statistics.median(price_buy) if len(price_buy) > 0 else context.acquisition_cost
        )
        blended_valuation = (median_buy_price + context.acquisition_cost) / 2.0
        terminal_valuation = max(context.acquisition_cost, blended_valuation)

        try:
            target_soc_perc, projected_cost, raw_home_dis, raw_grid_dis, sequence = (
                self.controller.propose_state_of_charge(
                    site_id=0,
                    timestamp="00:00",
                    battery=battery,
                    actual_previous_load=0,
                    actual_previous_pv_production=0,
                    price_buy=price_buy,
                    price_sell=price_sell,
                    load_forecast=load_f,
                    pv_forecast=pv_f,
                    acquisition_cost=terminal_valuation,
                )
            )
        except Exception as e:
            _LOGGER.error("Linear Solver failed: %s", e)
            return FSMResult(state="IDLE", limit_kw=0.0, reason=f"Solver Error: {e}")

        if target_soc_perc is None:
            return FSMResult(state="IDLE", limit_kw=0.0, reason="Solver returned None")

        target_soc_perc = float(target_soc_perc)

        # Convert the Target SoC percentage back into an FSM Action Limit Kw
        target_delta_kwh = (target_soc_perc - current_soc_perc) * capacity

        # Convert kwh to kw (5 minute intervals means * 12)
        power_kw = target_delta_kwh * 12.0

        if power_kw > 0.1:
            req_power = power_kw / battery.charging_efficiency
            return FSMResult(
                state="CHARGE_GRID",
                limit_kw=round(min(limit_kw_charge, req_power), 2),
                reason="LP Optimized Charge",
                target_soc=target_soc_perc * 100.0,
                projected_cost=projected_cost,
                future_plan=sequence,
            )
        elif power_kw < -0.1:
            req_power = abs(power_kw) * battery.discharging_efficiency
            net_grid_export = raw_grid_dis / (5.0 / 60.0)
            net_home_offset = raw_home_dis / (5.0 / 60.0)

            if net_grid_export > net_home_offset:
                return FSMResult(
                    state="DISCHARGE_GRID",
                    limit_kw=round(min(limit_kw_discharge, req_power), 2),
                    reason="LP Optimized Grid Export",
                    target_soc=target_soc_perc * 100.0,
                    projected_cost=projected_cost,
                    future_plan=sequence,
                )
            else:
                return FSMResult(
                    state="DISCHARGE_HOME",
                    limit_kw=round(min(limit_kw_discharge, req_power), 2),
                    reason="LP Optimized Home Discharge",
                    target_soc=target_soc_perc * 100.0,
                    projected_cost=projected_cost,
                    future_plan=sequence,
                )

        return FSMResult(
            state="IDLE",
            limit_kw=0.0,
            reason="LP Optimization: Idle optimal",
            target_soc=target_soc_perc * 100.0,
            projected_cost=projected_cost,
            future_plan=sequence,
        )
