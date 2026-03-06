import asyncio
import math
from datetime import datetime
from custom_components.house_battery_control.rates import RatesManager
import homeassistant.util.dt as dt_util

class MockState:
    def __init__(self, state, attributes):
        self.state = state
        self.attributes = attributes

class MockStates:
    def __init__(self, entities):
        self._entities = entities
    def get(self, entity_id):
        return self._entities.get(entity_id)

class MockHass:
    def __init__(self, entities):
        self.states = MockStates(entities)

async def test_amber_express():
    mock_forecasts = [
        {
            "per_kwh": -0.0637,
            "start_time": "2026-03-06T22:50:01+00:00",
            "end_time": "2026-03-06T23:00:00+00:00",
            "renewables": 74.0,
            "advanced_price_predicted": {"predicted": 0.05, "high": 0.10}
        },
        {
            "per_kwh": 0.10,
            "start_time": "2026-03-06T23:00:01+00:00",
            "end_time": "2026-03-06T23:30:00+00:00",
            "renewables": 30.0, # Blend 50/50
            "advanced_price_predicted": {"predicted": 0.20, "high": 0.40} 
        }
    ]

    entities = {
        "sensor.import_price": MockState(
            0.05, 
            {"forecasts": mock_forecasts}
        ),
        "sensor.export_price": MockState(
            0.05, 
            {"forecasts": mock_forecasts}
        )
    }
    
    hass = MockHass(entities)
    
    try:
        # Initialize RatesManager with new flag (should fail if flag doesn't exist)
        mgr = RatesManager(hass, "sensor.import_price", "sensor.export_price", use_amber_express=True)
        mgr.update()
        
        rates = mgr.get_rates()
        print(f"Rates parsed: {len(rates)}")
        if len(rates) == 0:
            print("FAIL: No rates parsed")
            exit(1)
        
        # Test 1: First 10 minutes (2 ticks) should be pure predicted (74% > 35%) -> 0.05
        print(f"Tick 0 price: {rates[0]['import_price']}")
        assert math.isclose(rates[0]["import_price"], 0.05, rel_tol=1e-5)
        assert math.isclose(rates[1]["import_price"], 0.05, rel_tol=1e-5)
        
        # Test 2: Next 30 minutes (6 ticks) should be 50/50 blend (30% renewables) -> 0.30
        print(f"Tick 2 price: {rates[2]['import_price']}")
        assert math.isclose(rates[2]["import_price"], 0.30, rel_tol=1e-5)
        
        print("SUCCESS: Amber Express parsed correctly")
        exit(0)
    except TypeError as e:
        print(f"FAIL (Expected natively): {e}")
        exit(1)
    except AssertionError as e:
        print(f"FAIL (Expected natively on math): {e}")
        exit(1)
    except Exception as e:
        print(f"FAIL: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(test_amber_express())
