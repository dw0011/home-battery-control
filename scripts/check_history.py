import json
import sys

def check_snapshot(filepath):
    print(f"Loading {filepath}...")
    with open(filepath) as f:
        d = json.load(f)
        
    print("\n=== Current Snapshot ===")
    ss = d.get('solver_snapshot', {})
    if not ss:
        print("No solver_snapshot found!")
        return

    si = ss.get('solver_inputs', {})
    bat = ss.get('battery', {})
    res = ss.get('result', {})
    
    print(f"State: {res.get('state')} | Limit: {res.get('limit_kw')} kW")
    print(f"Acq Cost: {ss.get('acquisition_cost')}")
    print(f"SoC: {bat.get('soc')}%")
    print(f"Buy prices (0-5): {si.get('price_buy', [])[:5]}")
    print(f"Sell prices (0-5): {si.get('price_sell', [])[:5]}")
    
    load = si.get('load_kwh', [])
    pv = si.get('pv_kwh', [])
    energy = [load[i] - pv[i] for i in range(min(5, len(load)))]
    print(f"Energy deficit (0-5): {[round(e, 3) for e in energy]}")

    print("\n=== Previous 10 Transitions ===")
    transitions = d.get('state_transitions', [])
    for i, t in enumerate(transitions):
        t_res = t.get('result', {})
        tsi = t.get('solver_inputs', {})
        tload = tsi.get('load_kwh', [])
        tpv = tsi.get('pv_kwh', [])
        tenergy = (tload[0] - tpv[0]) if tload and tpv else 0.0
        
        print(f"[{i}] {t.get('timestamp')}")
        print(f"    State: {t_res.get('state')} | limit: {t_res.get('limit_kw')} kW | SoC: {t.get('battery',{}).get('soc')}%")
        print(f"    Buy[0]: {tsi.get('price_buy',[0])[0]} | Sell[0]: {tsi.get('price_sell',[0])[0]} | Energy[0]: {round(tenergy,3)}")

if __name__ == "__main__":
    check_snapshot(sys.argv[1])
