"""Replay a debug snapshot through the solver and inspect raw LP variables at step 0.

Usage: python scripts/replay_snapshot.py "API Data/hbc_debug_2026-03-06T0203.json"

Purpose: Isolate whether row-0 CHARGE_GRID is caused by the removed
post-solve binary search smoother from the original 1st Place solver.
"""
import json
import sys
import numpy as np
import statistics
from scipy.optimize import linprog


def replay(path: str):
    with open(path) as f:
        d = json.load(f)

    ss = d.get("solver_snapshot")
    if not ss:
        print("ERROR: No solver_snapshot in this dump. Was this captured on v1.5.2+?")
        sys.exit(1)

    si = ss["solver_inputs"]
    bat = ss["battery"]

    price_buy = si["price_buy"]
    price_sell = si["price_sell"]
    load_kwh = si["load_kwh"]
    pv_kwh = si["pv_kwh"]

    soc = bat["soc"] / 100.0
    capacity = bat["capacity"]
    charge_rate_max = bat["charge_rate_max"]
    rte = bat.get("round_trip_efficiency", 0.90)
    reserve_soc = bat.get("reserve_soc", 0.0)
    acquisition_cost = ss["acquisition_cost"]

    # Solver parameters (matching lin_fsm.py)
    eta_in = rte  # approximate: charging_efficiency
    eta_out = 1.0 / rte  # discharging efficiency (reciprocal)
    current = capacity * soc
    charge_limit = charge_rate_max * (5.0 / 60.0)
    dis_limit = charge_rate_max * (5.0 / 60.0)  # same rate

    number_step = min(288, len(price_buy))
    energy = [load_kwh[i] - pv_kwh[i] for i in range(number_step)]

    # Variable offsets (same as lin_fsm.py)
    g_off = 0
    c_off = number_step
    dh_off = 2 * number_step
    dg_off = 3 * number_step
    b_off = 4 * number_step
    num_vars = 4 * number_step + (number_step + 1)

    # Objective
    obj = np.zeros(num_vars)
    bounds = [None] * num_vars

    for i in range(number_step):
        obj[g_off + i] = price_buy[i]
        bounds[g_off + i] = (0.0, None)

        obj[c_off + i] = max(0.001, price_sell[i]) + max(0.0, price_buy[i]) / 1000.0
        bounds[c_off + i] = (0.0, charge_limit)

        sell_opp = max(0.001, price_sell[i])
        obj[dh_off + i] = sell_opp
        max_home = max(0.0, energy[i])
        bounds[dh_off + i] = (-max_home, 0.0)

        max_grid = max(0.0, dis_limit - max_home)
        obj[dg_off + i] = sell_opp
        bounds[dg_off + i] = (-max_grid, 0.0)

    # Battery state bounds + terminal valuation
    median_buy = statistics.median(price_buy)
    blended = (median_buy + acquisition_cost) / 2.0
    terminal_valuation = max(acquisition_cost, blended)
    reserve_kwh = capacity * (reserve_soc / 100.0)

    for i in range(number_step + 1):
        if i == number_step:
            obj[b_off + i] = -max(0.001, terminal_valuation)
        else:
            obj[b_off + i] = 0.0
        physically_accessible = current + i * charge_limit * eta_in
        safe_lb = min(reserve_kwh, physically_accessible)
        bounds[b_off + i] = (safe_lb, capacity)

    # Grid balance inequality
    a_ub = np.zeros((number_step, num_vars))
    b_ub = np.zeros(number_step)
    for i in range(number_step):
        a_ub[i, g_off + i] = -1.0
        a_ub[i, c_off + i] = 1.0
        a_ub[i, dh_off + i] = 1.0
        a_ub[i, dg_off + i] = 1.0
        b_ub[i] = -energy[i]

    # Battery dynamics equality
    a_eq = np.zeros((number_step + 1, num_vars))
    b_eq = np.zeros(number_step + 1)
    a_eq[0, b_off + 0] = 1.0
    b_eq[0] = current
    for i in range(number_step):
        a_eq[i + 1, c_off + i] = eta_in
        a_eq[i + 1, dh_off + i] = eta_out
        a_eq[i + 1, dg_off + i] = eta_out
        a_eq[i + 1, b_off + i] = 1.0
        a_eq[i + 1, b_off + i + 1] = -1.0

    # Solve
    res = linprog(obj, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")

    if not res.success:
        print(f"SOLVER FAILED: {res.message}")
        sys.exit(1)

    # Extract step 0 variables
    step_c_0 = res.x[c_off + 0]
    step_g_0 = res.x[g_off + 0]
    step_dh_0 = abs(res.x[dh_off + 0])
    step_dg_0 = abs(res.x[dg_off + 0])
    b_0 = res.x[b_off + 0]
    b_1 = res.x[b_off + 1]

    target_soc_frac = b_1 / capacity

    # State classification (same as lin_fsm.py L258-263)
    if step_dg_0 > 0.005:
        state_0 = "DISCHARGE_GRID"
    elif step_c_0 > 0.005 and step_g_0 > 0.005:
        state_0 = "CHARGE_GRID"
    else:
        state_0 = "SELF_CONSUMPTION"

    # Energy balance at step 0
    net_grid_kwh = load_kwh[0] - pv_kwh[0] + step_c_0 - step_dh_0 - step_dg_0
    net_grid_kw = net_grid_kwh * 12.0

    print("=" * 70)
    print("REPLAY RESULTS — Step 0")
    print("=" * 70)
    print(f"Current SoC:     {soc*100:.1f}%  ({current:.2f} kWh / {capacity} kWh)")
    print(f"Target SoC:      {target_soc_frac*100:.2f}%  (b[1]={b_1:.4f} kWh)")
    print(f"SoC delta:       {(target_soc_frac - soc)*100:.3f}%")
    print()
    print("--- LP Variables at Step 0 ---")
    print(f"c[0]  (charge):     {step_c_0:.6f} kWh  (threshold: 0.005)")
    print(f"g[0]  (grid import):{step_g_0:.6f} kWh  (threshold: 0.005)")
    print(f"dh[0] (dis home):   {step_dh_0:.6f} kWh")
    print(f"dg[0] (dis grid):   {step_dg_0:.6f} kWh")
    print(f"b[0]:               {b_0:.4f} kWh")
    print(f"b[1]:               {b_1:.4f} kWh")
    print()
    print(f"State classification: {state_0}")
    print(f"Net grid import:     {net_grid_kw:.2f} kW  ({net_grid_kwh:.4f} kWh)")
    print()
    print("--- Inputs at Step 0 ---")
    print(f"price_buy[0]:   ${price_buy[0]}")
    print(f"price_sell[0]:  ${price_sell[0]}")
    print(f"load_kwh[0]:    {load_kwh[0]:.4f} kWh  ({load_kwh[0]*12:.2f} kW)")
    print(f"pv_kwh[0]:      {pv_kwh[0]:.4f} kWh  ({pv_kwh[0]*12:.2f} kW)")
    print(f"energy[0]:      {energy[0]:.4f} kWh  (load - pv, {'deficit' if energy[0] > 0 else 'surplus'})")

    # Original smoother analysis
    print()
    print("=" * 70)
    print("ORIGINAL SMOOTHER ANALYSIS")
    print("=" * 70)
    print("The original solver has a binary search smoother that fires when:")
    print("  energy[0] < 0 (PV surplus) AND discharge[0] >= 0 (no discharge)")
    print()
    print(f"energy[0] = {energy[0]:.4f}  {'< 0 YES' if energy[0] < 0 else '>= 0 NO'}")
    print(f"dh[0]+dg[0] = {step_dh_0 + step_dg_0:.6f}  {'>= 0 YES (smoother fires)' if step_dh_0 + step_dg_0 < 0.001 else '< 0 NO'}")

    if energy[0] < 0 and step_dh_0 + step_dg_0 < 0.001:
        # Count consecutive steps with same price and no discharge
        n = 0
        sum_charge = step_c_0
        for i in range(1, number_step):
            step_c_i = res.x[c_off + i]
            step_dg_i = abs(res.x[dg_off + i])
            step_dh_i = abs(res.x[dh_off + i])
            if (energy[i] > 0) or (step_dg_i > 0.001 or step_dh_i > 0.001) or (price_sell[i] != price_sell[i-1]):
                n = i
                break
            sum_charge += step_c_i

        print(f"\nSmoother would scan {n} consecutive steps with same sell price")
        print(f"Total charge across those steps: {sum_charge:.6f} kWh")

        if sum_charge <= 0:
            print("sum_charge <= 0: Smoother returns b[1] directly (no change)")
        else:
            # The smoother redistributes evenly
            per_step = sum_charge / n if n > 0 else 0
            smoothed_c0 = min(charge_limit, max(-(-1) - energy[0], 0))  # simplified
            smoothed_b1 = current + min(charge_limit, max(sum_charge / n if n > 0 else 0, 0)) * eta_in
            print(f"Smoother would redistribute {sum_charge:.6f} kWh across {n} steps")
            print(f"Per-step charge: {per_step:.6f} kWh")
            print(f"Smoothed b[1]: {smoothed_b1:.4f} kWh ({smoothed_b1/capacity*100:.2f}%)")
            print(f"Original b[1]: {b_1:.4f} kWh ({b_1/capacity*100:.2f}%)")

    print()
    print("=" * 100)
    print("LP SOLUTION — First 10 Steps")
    print("=" * 100)
    print(f"{'Step':>4} | {'Buy $':>8} | {'Sell $':>8} | {'Energy':>8} | {'c (charge)':>12} | {'g (grid)':>12} | {'dh (home)':>12} | {'dg (grid)':>12} | {'b (SoC)':>10} | {'State':>18}")
    for i in range(min(10, number_step)):
        sc = res.x[c_off + i]
        sg = res.x[g_off + i]
        sdh = abs(res.x[dh_off + i])
        sdg = abs(res.x[dg_off + i])
        sb = res.x[b_off + i + 1]
        if sdg > 0.005:
            st = "DISCHARGE_GRID"
        elif sc > 0.005 and sg > 0.005:
            st = "CHARGE_GRID"
        else:
            st = "SELF_CONSUMPTION"
        print(f"{i:4d} | {price_buy[i]:8.3f} | {price_sell[i]:8.3f} | {energy[i]:8.3f} | {sc:12.6f} | {sg:12.6f} | {sdh:12.6f} | {sdg:12.6f} | {sb/capacity*100:9.2f}% | {st:>18}")


if __name__ == "__main__":
    replay(sys.argv[1])
