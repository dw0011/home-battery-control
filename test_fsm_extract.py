import urllib.request
import json
from datetime import datetime
import sys
import numpy as np
from scipy.optimize import linprog

sys.path.append('custom_components')
from house_battery_control.fsm.lin_fsm import LinearBatteryStateMachine
from house_battery_control.fsm.base import FSMContext

def parse_isoformat(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

def test():
    print("Fetching HA API...")
    data = json.loads(urllib.request.urlopen('http://homeassistant.local:8123/hbc/api/status', timeout=5).read().decode())
    
    # We must construct FSMContext manually like coordinator.py does.
    rates = data.get('rates', [])
    solar = data.get('solar_forecast', [])
    load_f = data.get('load_forecast', [])
    
    if not rates:
        print("No rates.")
        return
        
    rates_timeline = rates
    fallback_len = len(rates_timeline)
    
    aligned_solar = []
    if rates_timeline and solar:
        for rate in rates_timeline:
            rate_start = parse_isoformat(rate['start']) if isinstance(rate['start'], str) else rate['start']
            def diff(x):
                x_start = parse_isoformat(x['start']) if isinstance(x['start'], str) else x['start']
                return abs((x_start - rate_start).total_seconds())
            closest = min(solar, key=diff)
            if diff(closest) <= 1800:
                aligned_solar.append({"kw": closest['kw']})
            else:
                aligned_solar.append({"kw": 0.0})
    else:
        aligned_solar = [{"kw": 0.0} for _ in range(fallback_len)]
        
    # Ensure load_forecast is populated
    load_out = []
    if not load_f:
        load_out = [{"kw": 0.0} for _ in range(fallback_len)]
    else:
        for item in load_f:
            load_out.append({"kw": item.get('kw', 0.0)})
        if len(load_out) < fallback_len:
            for _ in range(fallback_len - len(load_out)):
                load_out.append({"kw": 0.0})

    soc = float(data.get('soc', 50.0))
    current_price = float(rates[0].get('price', 0.0)) if rates else 0.0
    
    print("Building FSMContext...")
    ctx = FSMContext(
        soc=soc,
        solar_production=0.0,
        load_power=0.0,
        grid_voltage=240.0,
        current_price=current_price,
        forecast_solar=aligned_solar,
        forecast_load=load_out,
        forecast_price=rates,
        config={
            "battery_capacity": 13.5,
            "battery_rate_max": 5.0,
            "inverter_limit": 5.0,
            "round_trip_efficiency": 0.90
        }
    )
    
    print("Running LinearBatteryStateMachine...")
    fsm = LinearBatteryStateMachine()
    
    # Let's mock _LOGGER to see the failure reason!
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    res = fsm.calculate_next_state(ctx)
    print(f"FSM returned state: {res.state}")
    print(f"FSM returned reason: {res.reason}")
    print(f"Sequence length: {len(res.future_plan)}")
    
    if len(res.future_plan) > 0:
        pv_max = max(x.get('pv', 0.0) for x in res.future_plan)
        print(f"Max PV inside FSM sequence output: {pv_max}")
    else:
        print("Sequence is empty!")

if __name__ == "__main__":
    test()
