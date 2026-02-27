"""Tests for the Execute module — translates FSM states into Powerwall commands.

Updated for Feature 07: Executor State Cleanup.
Tests the 4-state transition-aware command logic.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from custom_components.house_battery_control.const import (
    CONF_OBSERVATION_MODE,
    CONF_SCRIPT_CHARGE,
    CONF_SCRIPT_CHARGE_STOP,
    CONF_SCRIPT_DISCHARGE,
    CONF_SCRIPT_DISCHARGE_STOP,
    STATE_CHARGE_GRID,
    STATE_DISCHARGE_GRID,
    STATE_ERROR,
    STATE_SELF_CONSUMPTION,
)
from custom_components.house_battery_control.execute import PowerwallExecutor


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def config():
    return {
        CONF_SCRIPT_CHARGE: "script.force_charge",
        CONF_SCRIPT_CHARGE_STOP: "script.charge_stop",
        CONF_SCRIPT_DISCHARGE: "script.force_discharge",
        CONF_SCRIPT_DISCHARGE_STOP: "script.discharge_stop",
    }


@pytest.fixture
def executor(mock_hass, config):
    return PowerwallExecutor(mock_hass, config)


# --- State to command mapping ---


def test_executor_init(executor):
    """Executor should construct without errors."""
    assert executor is not None


@pytest.mark.asyncio
async def test_charge_grid_calls_charge_script(executor, mock_hass):
    """CHARGE_GRID should call the charge script."""
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    assert executor.last_state == STATE_CHARGE_GRID
    mock_hass.services.async_call.assert_called_with(
        "script", "turn_on", {"entity_id": "script.force_charge"}
    )


@pytest.mark.asyncio
async def test_discharge_grid_calls_discharge_script(executor, mock_hass):
    """DISCHARGE_GRID should call the discharge script."""
    await executor.apply_state(STATE_DISCHARGE_GRID, limit_kw=5.0)
    assert executor.last_state == STATE_DISCHARGE_GRID
    mock_hass.services.async_call.assert_called_with(
        "script", "turn_on", {"entity_id": "script.force_discharge"}
    )


# --- Transition-aware stop tests ---


@pytest.mark.asyncio
async def test_self_consumption_after_charge_calls_only_charge_stop(executor, mock_hass):
    """CHARGE_GRID → SELF_CONSUMPTION should call only charge_stop (not discharge_stop)."""
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    mock_hass.services.async_call.reset_mock()

    await executor.apply_state(STATE_SELF_CONSUMPTION, limit_kw=0.0)
    assert executor.last_state == STATE_SELF_CONSUMPTION
    mock_hass.services.async_call.assert_called_once_with(
        "script", "turn_on", {"entity_id": "script.charge_stop"}
    )


@pytest.mark.asyncio
async def test_self_consumption_after_discharge_calls_only_discharge_stop(executor, mock_hass):
    """DISCHARGE_GRID → SELF_CONSUMPTION should call only discharge_stop (not charge_stop)."""
    await executor.apply_state(STATE_DISCHARGE_GRID, limit_kw=5.0)
    mock_hass.services.async_call.reset_mock()

    await executor.apply_state(STATE_SELF_CONSUMPTION, limit_kw=0.0)
    assert executor.last_state == STATE_SELF_CONSUMPTION
    mock_hass.services.async_call.assert_called_once_with(
        "script", "turn_on", {"entity_id": "script.discharge_stop"}
    )


@pytest.mark.asyncio
async def test_self_consumption_from_idle_no_calls(executor, mock_hass):
    """SELF_CONSUMPTION when nothing was active → no script calls."""
    await executor.apply_state(STATE_SELF_CONSUMPTION, limit_kw=0.0)
    assert executor.last_state == STATE_SELF_CONSUMPTION
    # No stop commands needed — nothing was active
    mock_hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_charge_to_discharge_stops_charge_first(executor, mock_hass):
    """CHARGE_GRID → DISCHARGE_GRID should stop charge then start discharge."""
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    mock_hass.services.async_call.reset_mock()

    await executor.apply_state(STATE_DISCHARGE_GRID, limit_kw=5.0)
    calls = mock_hass.services.async_call.call_args_list
    assert len(calls) == 2
    # First call: stop charge
    assert calls[0] == (("script", "turn_on", {"entity_id": "script.charge_stop"}),)
    # Second call: start discharge
    assert calls[1] == (("script", "turn_on", {"entity_id": "script.force_discharge"}),)


@pytest.mark.asyncio
async def test_discharge_to_charge_stops_discharge_first(executor, mock_hass):
    """DISCHARGE_GRID → CHARGE_GRID should stop discharge then start charge."""
    await executor.apply_state(STATE_DISCHARGE_GRID, limit_kw=5.0)
    mock_hass.services.async_call.reset_mock()

    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    calls = mock_hass.services.async_call.call_args_list
    assert len(calls) == 2
    # First call: stop discharge
    assert calls[0] == (("script", "turn_on", {"entity_id": "script.discharge_stop"}),)
    # Second call: start charge
    assert calls[1] == (("script", "turn_on", {"entity_id": "script.force_charge"}),)


# --- ERROR state tests ---


@pytest.mark.asyncio
async def test_error_after_charge_stops_charge(executor, mock_hass):
    """ERROR after CHARGE_GRID should call charge_stop."""
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    mock_hass.services.async_call.reset_mock()

    await executor.apply_state(STATE_ERROR, limit_kw=0.0)
    mock_hass.services.async_call.assert_called_once_with(
        "script", "turn_on", {"entity_id": "script.charge_stop"}
    )


@pytest.mark.asyncio
async def test_error_after_discharge_stops_discharge(executor, mock_hass):
    """ERROR after DISCHARGE_GRID should call discharge_stop."""
    await executor.apply_state(STATE_DISCHARGE_GRID, limit_kw=5.0)
    mock_hass.services.async_call.reset_mock()

    await executor.apply_state(STATE_ERROR, limit_kw=0.0)
    mock_hass.services.async_call.assert_called_once_with(
        "script", "turn_on", {"entity_id": "script.discharge_stop"}
    )


# --- Dedup and observation mode ---


@pytest.mark.asyncio
async def test_no_repeat_if_same_state(executor, mock_hass):
    """Should not re-apply if state hasn't changed."""
    await executor.apply_state(STATE_SELF_CONSUMPTION, limit_kw=0.0)
    await executor.apply_state(STATE_SELF_CONSUMPTION, limit_kw=0.0)
    assert executor.apply_count == 1


@pytest.mark.asyncio
async def test_state_change_increments_count(executor):
    """Changing state should increment the apply count."""
    await executor.apply_state(STATE_SELF_CONSUMPTION, limit_kw=0.0)
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    assert executor.apply_count == 2


@pytest.mark.asyncio
async def test_get_command_summary(executor):
    """Should return a human-readable summary of the last command."""
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    summary = executor.get_command_summary()
    assert isinstance(summary, str)
    assert len(summary) > 0


# --- Observation mode tests (Feature 009) ---


@pytest.mark.asyncio
async def test_observation_mode_suppresses_execution(mock_hass):
    """Commands should NOT be called when observation_mode is True."""
    config = {
        CONF_SCRIPT_CHARGE: "script.force_charge",
        CONF_OBSERVATION_MODE: True,
    }
    executor = PowerwallExecutor(mock_hass, config)
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)

    # State should be tracked for dashboard
    assert executor.last_state == STATE_CHARGE_GRID
    # But no service call should be made
    mock_hass.services.async_call.assert_not_called()
    # Executed state should remain None
    assert executor.last_executed_state is None
    # Apply count should NOT increment (no actual execution)
    assert executor.apply_count == 0


@pytest.mark.asyncio
async def test_observation_mode_exit_triggers_execution(mock_hass):
    """Toggling observation_mode OFF should allow the next call to execute."""
    config = {
        CONF_SCRIPT_CHARGE: "script.force_charge",
        CONF_OBSERVATION_MODE: True,
    }
    executor = PowerwallExecutor(mock_hass, config)

    # Call while in observation mode — suppressed
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    mock_hass.services.async_call.assert_not_called()

    # Toggle observation mode OFF
    config[CONF_OBSERVATION_MODE] = False

    # Same state called again — should NOW execute because _last_executed_state is None
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    mock_hass.services.async_call.assert_called_with(
        "script", "turn_on", {"entity_id": "script.force_charge"}
    )
    assert executor.apply_count == 1
    assert executor.last_executed_state == STATE_CHARGE_GRID


@pytest.mark.asyncio
async def test_observation_mode_dedup_after_real_execution(mock_hass):
    """After real execution, same state should be deduped normally."""
    config = {
        CONF_SCRIPT_CHARGE: "script.force_charge",
        CONF_OBSERVATION_MODE: False,
    }
    executor = PowerwallExecutor(mock_hass, config)

    # First call — executes
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    assert executor.apply_count == 1
    mock_hass.services.async_call.reset_mock()

    # Second call with same state — deduped
    await executor.apply_state(STATE_CHARGE_GRID, limit_kw=6.3)
    assert executor.apply_count == 1  # No increment
    mock_hass.services.async_call.assert_not_called()
