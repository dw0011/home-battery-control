"""Test the Telemetry Cost Tracker module (Feature 031)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.house_battery_control.const import (
    CONF_EXPORT_TODAY_ENTITY,
    CONF_IMPORT_TODAY_ENTITY,
    CONF_TRACKER_EXPORT_PRICE,
    CONF_TRACKER_IMPORT_PRICE,
)

# This import will intentionally fail until the class is implemented (TDD step)
from custom_components.house_battery_control.telemetry_tracker import (
    TelemetryCostTracker,
)
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_config():
    """Mock the config data with the required cost tracking sensors."""
    return {
        CONF_IMPORT_TODAY_ENTITY: "sensor.import_kwh",
        CONF_EXPORT_TODAY_ENTITY: "sensor.export_kwh",
        CONF_TRACKER_IMPORT_PRICE: "sensor.amber_import",
        CONF_TRACKER_EXPORT_PRICE: "sensor.amber_export",
    }

@pytest.mark.asyncio
@patch("custom_components.house_battery_control.telemetry_tracker.Store")
async def test_tick_standard_accumulation(mock_store_class, mock_config):
    """Test standard accumulation with positive deltas."""
    # Setup mock store instance
    mock_store_instance = AsyncMock()
    mock_store_instance.async_load.return_value = None
    mock_store_class.return_value = mock_store_instance

    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.states.get = MagicMock()

    tracker = TelemetryCostTracker(hass, mock_config)

    # Mocking initial load
    tracker._last_import = 10.0
    tracker._last_export = 5.0
    tracker.cumulative_cost = 100.0

    def mock_get_state(entity_id):
        state = MagicMock()
        if entity_id == "sensor.import_kwh":
            state.state = "10.5" # 0.5 kWh used
        elif entity_id == "sensor.export_kwh":
            state.state = "5.2"  # 0.2 kWh exported
        elif entity_id == "sensor.amber_import":
            state.state = "0.20" # 20c per kWh
        elif entity_id == "sensor.amber_export":
            state.state = "0.10" # 10c per kWh (feed-in)
        else:
            return None
        return state

    hass.states.get.side_effect = mock_get_state

    # Execute tick
    await tracker._on_tick("dummy_time")

    # Expected cost: 100.0 + (0.5 * 0.20) - (0.2 * 0.10) ?
    # Wait, usually export is negative cost (revenue). If price is positive 0.10, earning money reduces cost.
    # The specification says: `import_delta * import_price + export_delta * export_price`. Amber provides negative values for earning, or we subtract? Let's check existing coordinator math:
    # Actually, Amber prices are positive for importing, negative for feed-in (usually). Wait, the spec example had `state: "-0.02"` which means Amber Express returns negative prices for earning feed-in or negative wholesale.
    # 0.5 kWh import @ 0.20 = 0.10
    # 0.2 kWh export @ 0.10 = 0.02
    # Total = 100.12
    assert tracker.cumulative_cost == pytest.approx(100.12)
    assert tracker._last_import == 10.5
    assert tracker._last_export == 5.2

@pytest.mark.asyncio
@patch("custom_components.house_battery_control.telemetry_tracker.Store")
async def test_midnight_reset_interpolation(mock_store_class, mock_config):
    """Test exactly handling a midnight kWh reset where current < last."""
    mock_store_instance = AsyncMock()
    mock_store_instance.async_load.return_value = None
    mock_store_class.return_value = mock_store_instance

    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()

    tracker = TelemetryCostTracker(hass, mock_config)
    tracker._last_import = 15.0
    tracker._last_export = 8.0
    tracker.cumulative_cost = 200.0

    def mock_get_state(entity_id):
        state = MagicMock()
        if entity_id == "sensor.import_kwh":
            state.state = "0.3" # Reset happened, now at 0.3
        elif entity_id == "sensor.export_kwh":
            state.state = "0.0" # Reset happened, now at 0.0
        elif entity_id == "sensor.amber_import":
            state.state = "0.50"
        elif entity_id == "sensor.amber_export":
            state.state = "-0.10"
        return state

    hass.states.get.side_effect = mock_get_state

    await tracker._on_tick("dummy_time")

    # Import delta should be explicitly set to 0.3, not (0.3 - 15.0) -> negative
    # Export delta should be explicitly set to 0.0, not (0.0 - 8.0) -> negative
    # 0.3 * 0.50 = 0.15
    assert tracker.cumulative_cost == pytest.approx(200.15)
    assert tracker._last_import == 0.3
    assert tracker._last_export == 0.0
