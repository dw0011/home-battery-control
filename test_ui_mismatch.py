import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.house_battery_control.coordinator import HBCDataUpdateCoordinator
from custom_components.house_battery_control.fsm.base import FSMContext
from custom_components.house_battery_control.fsm.lin_fsm import LinearBatteryStateMachine
from homeassistant.util import dt as dt_util

class MockHass:
    def async_add_executor_job(self, func, *args, **kwargs):
        return func(*args, **kwargs)

async def test():
    print("Initializing FSM and Mock Coordinator...")
    hass = MockHass()
    coordinator = HBCDataUpdateCoordinator.__new__(HBCDataUpdateCoordinator)
    coordinator.hass = hass
    coordinator.config = {}
    fsm = LinearBatteryStateMachine()

    now = datetime(2025, 2, 20, 12, 0, tzinfo=timezone.utc)
    
    rates = []
    solar_forecast = []
    load_forecast = []
    
    # Generate exactly 24 hours of 5-min intervals
    current = now
    for i in range(288):
        rates.append({
            "start": current,
            "end": current + timedelta(minutes=5),
            "import_price": 10.0,
            "export_price": 5.0,
        })
        # Note: solar_forecast natively has 'start' and 'kw'
        solar_forecast.append({
            "start": current,
            "kw": 5.0  # Constant 5kW solar
        })
        # Note: load_forecast natively uses isoformat strings!
        load_forecast.append({
            "start": current.isoformat(),
            "kw": 2.5  # Constant 2.5kW load
        })
        current += timedelta(minutes=5)

    # Replicate coordinator.py 'aligned_solar' logic
    aligned_solar = []
    for rate in rates:
        rate_start = rate["start"]
        closest = min(solar_forecast, key=lambda x: abs((x["start"] - rate_start).total_seconds()))
        if abs((closest["start"] - rate_start).total_seconds()) <= 1800:
            aligned_solar.append({"kw": closest["kw"]})
        else:
            aligned_solar.append({"kw": 0.0})

    ctx = FSMContext(
        soc=50.0,
        solar_production=5.0,
        load_power=2.5,
        grid_voltage=240.0,
        current_price=10.0,
        forecast_solar=aligned_solar,
        forecast_load=load_forecast,
        forecast_price=rates,
        config={"battery_capacity": 27.0, "charge_rate_max": 6.3, "inverter_limit": 10.0},
        acquisition_cost=0.0
    )

    result = fsm.calculate_next_state(ctx)
    future_plan = result.future_plan
    
    print(f"future_plan length: {len(future_plan)}")
    if future_plan:
        print(f"Sample future_plan[0]: {future_plan[0]}")
    else:
        print("future_plan empty!")

    table = coordinator._build_diagnostic_plan_table(
        rates=rates,
        solar_forecast=solar_forecast,
        load_forecast=load_forecast,
        weather=[],
        current_soc=50.0,
        future_plan=future_plan,
    )

    print(f"Table length: {len(table)}")
    if table:
        print(f"Sample table[0]: {table[0]}")

if __name__ == "__main__":
    asyncio.run(test())
