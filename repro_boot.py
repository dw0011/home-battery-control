import asyncio
from unittest.mock import AsyncMock, MagicMock

# Simulate the HA object and ConfigEntry
class MockHass:
    def __init__(self):
        self.data = {}

class MockEntry:
    def __init__(self):
        self.entry_id = "test_entry_123"
        self.data = {}
        self.options = {}

async def simulate_boot():
    # 1. Setup mocks
    hass = MockHass()
    entry = MockEntry()
    
    # 2. Mock the coordinator class
    class MockCoordinator:
        def __init__(self, hass, entry_id, config):
            self.cumulative_cost = 0.0
            
        async def async_load_stored_costs(self):
            # Simulate reading from disk where cost was $50.00
            print("  [Coordinator] Loading costs from disk...")
            self.cumulative_cost = 50.00
            
        async def async_config_entry_first_refresh(self):
            print("  [Coordinator] First refresh triggered.")
            # Important: What does the real first refresh do?
            # It calls _async_update_data, which calls the solver...
            # Does the solver reset it?
            pass

    print("--- Simulating HA Boot Sequence ---")
    
    # 3. Simulate __init__.py async_setup_entry
    config_data = dict(entry.data)
    coordinator = MockCoordinator(hass, entry.entry_id, config_data)
    
    await coordinator.async_load_stored_costs()
    print(f"Cost after load: ${coordinator.cumulative_cost}")
    
    await coordinator.async_config_entry_first_refresh()
    print(f"Cost after first refresh: ${coordinator.cumulative_cost}")

if __name__ == "__main__":
    asyncio.run(simulate_boot())
