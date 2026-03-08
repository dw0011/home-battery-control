import asyncio
import os
from enum import Enum

from homeassistant.helpers.storage import Store


# Minimal mock of Home Assistant classes needed to test Store
class MockConfig:
    def __init__(self):
        self.config_dir = os.getcwd()

    def path(self, *path):
        return os.path.join(self.config_dir, *path)

class MockBus:
    def async_listen_once(self, *args, **kwargs):
        return lambda: None

class CoreState(Enum):
    not_running = 0
    starting = 1
    running = 2
    stopping = 3

class MockHass:
    def __init__(self):
        self.config = MockConfig()
        self.loop = asyncio.get_event_loop()
        self.data = {}
        self.bus = MockBus()
        self.state = CoreState.running

    def async_create_task_internal(self, coroutine, name=None, eager_start=False):
        return self.loop.create_task(coroutine)

    def async_add_executor_job(self, target, *args):
        return self.loop.run_in_executor(None, target, *args)

# We need to simulate the exact async_delay_save behaviour from HA

async def test_store_save_loop():
    hass = MockHass()

    # Store creates files in config/.storage
    os.makedirs(".storage", exist_ok=True)
    hass.config.config_dir = "."

    store = Store(hass, 1, "hbc.cost_data")

    print("1. Initial load:", await store.async_load())

    cumulative_cost = 0.0
    acquisition_cost = 0.10

    print("2. Simulating tick 1: Adding $2.50 to cost")
    cumulative_cost += 2.50

    # Simulate exactly what coordinator.py does:
    store.async_delay_save(
        lambda: {
            "cumulative_cost": cumulative_cost,
            "acquisition_cost": acquisition_cost
        },
        delay=0.1
    )

    print("3. Waiting for delay_save to fire...")
    await asyncio.sleep(0.5)

    # Now simulate a reboot (new Store instance reading from disk)
    store2 = Store(hass, 1, "hbc.cost_data")
    loaded = await store2.async_load()
    print("4. Loaded after reboot:", loaded)

if __name__ == "__main__":
    asyncio.run(test_store_save_loop())
