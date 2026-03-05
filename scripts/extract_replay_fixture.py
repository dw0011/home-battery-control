"""Extract solver inputs from API status dump for offline replay testing."""
import json

with open("API Data/hbc_status_2026-03-05T07-48-17-896Z.json") as f:
    d = json.load(f)

plan = d.get("plan", [])

# --- Config ---
print("=== CONFIG ===")
for k in ["soc", "capacity", "charge_rate_max", "inverter_limit",
           "acquisition_cost", "current_price", "no_import_periods",
           "observation_mode", "target_soc"]:
    print(f"  {k}: {d.get(k)}")

# --- Extract arrays from plan table ---
print(f"\n=== PLAN TABLE ({len(plan)} rows) ===")
load_kw = []
pv_kw = []
import_price = []
export_price = []
soc_forecast = []
states = []
net_grid = []

for row in plan:
    load_kw.append(float(row.get("Load Forecast", "0")))
    pv_kw.append(float(row.get("PV Forecast", "0")))
    import_price.append(float(row.get("Import Rate", "0")))
    export_price.append(float(row.get("Export Rate", "0")))
    soc_str = row.get("SoC Forecast", "0%").replace("%", "")
    soc_forecast.append(float(soc_str))
    states.append(row.get("FSM State", "?"))
    net_grid.append(float(row.get("Net Grid", "0")))

# --- Extract from rates array (full data) ---
rates = d.get("rates", [])
rates_import = [float(r.get("import_price", 0)) for r in rates]
rates_export = [float(r.get("export_price", 0)) for r in rates]

print(f"  Load range: {min(load_kw):.2f} - {max(load_kw):.2f} kW")
print(f"  PV range: {min(pv_kw):.2f} - {max(pv_kw):.2f} kW")
print(f"  Import range: {min(rates_import):.2f} - {max(rates_import):.2f}")
print(f"  Export range: {min(rates_export):.4f} - {max(rates_export):.2f}")
print(f"  SoC range: {min(soc_forecast):.1f}% - {max(soc_forecast):.1f}%")
print(f"  States: {dict(zip(*reversed(list(zip(*[(s, 1) for s in states])))))}")

# --- Find the anomaly ---
print("\n=== SOC RATE CHANGES ===")
for i in range(1, len(soc_forecast)):
    delta = soc_forecast[i] - soc_forecast[i-1]
    if abs(delta) > 1.5:  # More than 1.5% per step
        implied_kw = abs(delta) / 100.0 * 27.0 / (5/60)
        print(f"  [{i:3d}] {plan[i].get('Local Time','?'):>6s} "
              f"SoC={soc_forecast[i]:5.1f}% delta={delta:+.1f}% "
              f"load={load_kw[i]:.2f} pv={pv_kw[i]:.2f} "
              f"net_grid={net_grid[i]:.2f} implied={implied_kw:.1f}kW")

# --- Build fixture dict ---
fixture = {
    "soc": d["soc"],
    "capacity": d.get("capacity"),
    "charge_rate_max": d.get("charge_rate_max"),
    "inverter_limit": d.get("inverter_limit"),
    "acquisition_cost": d["acquisition_cost"],
    "current_price": d["current_price"],
    "no_import_periods": d.get("no_import_periods"),
    "rates": rates,
    "load_kw": load_kw,
    "pv_kw": pv_kw,
    "soc_forecast": soc_forecast,
    "states": states,
    "net_grid": net_grid,
}

with open("API Data/solver_replay_fixture.json", "w") as out:
    json.dump(fixture, out, indent=2)
print(f"\n=== Fixture saved to API Data/solver_replay_fixture.json ===")
