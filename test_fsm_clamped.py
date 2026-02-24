import urllib.request
import json
from datetime import datetime
import sys

sys.path.append('custom_components')
from house_battery_control.fsm.lin_fsm import LinearBatteryStateMachine
from house_battery_control.fsm.base import FSMContext

def parse_isoformat(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

def test():
    data = json.loads(urllib.request.urlopen('http://homeassistant.local:8123/hbc/api/status', timeout=5).read().decode())
    
    rates = data.get('rates', [])
    solar = data.get('solar_forecast', [])
    load_f = data.get('load_forecast', [])
    
    # CLAMP NEGATIVE PRICES
    safe_rates = []
    for r in rates:
        sr = dict(r)
        import_price = sr.get('import_price', sr.get('price', 0.0))
        if import_price < 0.0:
            sr['import_price'] = 0.0
            if 'price' in sr:
                sr['price'] = 0.0
        safe_rates.append(sr)
        
    rates_timeline = safe_rates
    fallback_len = len(rates_timeline)
    
    aligned_solar = []
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
            
    load_out = []
    for item in load_f:
        load_out.append({"kw": item.get('kw', 0.0)})
    if len(load_out) < fallback_len:
        for _ in range(fallback_len - len(load_out)):
            load_out.append({"kw": 0.0})

    soc = float(data.get('soc', 50.0))
    cp = sum(x.get('price', 0.0) for x in rates[:1])
    
    ctx = FSMContext(
        soc=soc,
        solar_production=0.0,
        load_power=0.0,
        grid_voltage=240.0,
        current_price=cp if cp >= 0 else 0.0,
        forecast_solar=aligned_solar,
        forecast_load=load_out,
        forecast_price=safe_rates,
        config={
            "battery_capacity": 13.5,
            "battery_rate_max": 5.0,
            "inverter_limit": 5.0,
            "round_trip_efficiency": 0.90
        }
    )
    
    fsm = LinearBatteryStateMachine()
    import logging
    logging.basicConfig(level=logging.WARNING)
    res = fsm.calculate_next_state(ctx)
    print(f"FSM returned state: {res.state}, Reason: {res.reason}, Plan len: {len(res.future_plan or [])}")
    if res.future_plan:
        print(f"Max PV: {max(x.get('pv', 0.0) for x in res.future_plan)}")

if __name__ == "__main__":
    test()
