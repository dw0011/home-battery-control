"""Debug: analyze spurious charge requests in plan table."""
import json
from collections import Counter

with open("API Data/hbc_status_20260306.json") as f:
    d = json.load(f)

plan = d.get("plan", [])

# --- State distribution ---
states = Counter(r.get("FSM State", "?") for r in plan)
print("=== STATE DISTRIBUTION ===")
for s, c in states.most_common():
    print(f"  {s}: {c}")

# --- All CHARGE_GRID rows ---
print("\n=== CHARGE_GRID ROWS ===")
charge_rows = [(i, r) for i, r in enumerate(plan) if r.get("FSM State") == "CHARGE_GRID"]
print(f"  Count: {len(charge_rows)}")
for i, r in charge_rows:
    print(f"  [{i:3d}] {r.get('Local Time','?'):>8s} "
          f"Import={r.get('Import Rate','?'):>6s} "
          f"Export={r.get('Export Rate','?'):>6s} "
          f"Net={r.get('Net Grid','?'):>7s} "
          f"SoC={r.get('SoC Forecast','?'):>6s} "
          f"Limit={r.get('Limit','?'):>4s} "
          f"Load={r.get('Load Forecast','?'):>5s} "
          f"PV={r.get('PV Forecast','?'):>5s}")

# --- All DISCHARGE_GRID rows ---
print("\n=== DISCHARGE_GRID ROWS ===")
dg_rows = [(i, r) for i, r in enumerate(plan) if r.get("FSM State") == "DISCHARGE_GRID"]
print(f"  Count: {len(dg_rows)}")
for i, r in dg_rows[:20]:
    print(f"  [{i:3d}] {r.get('Local Time','?'):>8s} "
          f"Import={r.get('Import Rate','?'):>6s} "
          f"Export={r.get('Export Rate','?'):>6s} "
          f"Net={r.get('Net Grid','?'):>7s} "
          f"SoC={r.get('SoC Forecast','?'):>6s} "
          f"Limit={r.get('Limit','?'):>4s} "
          f"AcqCost={r.get('Acq. Cost','?'):>6s}")

# --- State transitions (find CG adjacent to DG) ---
print("\n=== STATE TRANSITIONS ===")
for i in range(1, len(plan)):
    prev = plan[i-1].get("FSM State", "?")
    curr = plan[i].get("FSM State", "?")
    if prev != curr:
        print(f"  [{i-1:3d}->{i:3d}] {plan[i-1].get('Local Time','?'):>8s} -> {plan[i].get('Local Time','?'):>8s}: {prev} -> {curr}")

# --- Row 0 (current action) ---
print("\n=== ROW 0 (CURRENT ACTION) ===")
if plan:
    for k, v in plan[0].items():
        print(f"  {k}: {v}")

# --- Price analysis around charge rows ---
if charge_rows:
    print("\n=== PRICE CONTEXT AROUND CHARGE ROWS ===")
    for ci, (i, r) in enumerate(charge_rows):
        print(f"\n  --- CHARGE_GRID at row {i} ({r.get('Local Time','?')}) ---")
        start = max(0, i - 2)
        end = min(len(plan), i + 3)
        for j in range(start, end):
            marker = " >>>" if j == i else "    "
            p = plan[j]
            print(f"  {marker} [{j:3d}] {p.get('Local Time','?'):>8s} "
                  f"State={p.get('FSM State','?'):>20s} "
                  f"Import={p.get('Import Rate','?'):>6s} "
                  f"Export={p.get('Export Rate','?'):>6s} "
                  f"SoC={p.get('SoC Forecast','?'):>6s} "
                  f"Net={p.get('Net Grid','?'):>7s}")
