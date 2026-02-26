"""Powerwall Executor — translates FSM states into battery commands.

Responsible for:
- Mapping FSM states to HA service calls
- Deduplicating commands (don't re-send if state unchanged)
- Providing a human-readable summary of the last command
"""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    CONF_OBSERVATION_MODE,
    CONF_SCRIPT_CHARGE,
    CONF_SCRIPT_CHARGE_STOP,
    CONF_SCRIPT_DISCHARGE,
    CONF_SCRIPT_DISCHARGE_STOP,
    STATE_CHARGE_GRID,
    STATE_CHARGE_SOLAR,
    STATE_DISCHARGE_GRID,
    STATE_DISCHARGE_HOME,
    STATE_IDLE,
    STATE_PRESERVE,
)

_LOGGER = logging.getLogger(__name__)

# Command descriptions per state
_STATE_DESCRIPTIONS = {
    STATE_IDLE: "Self-Consumption mode, no grid charging",
    STATE_CHARGE_GRID: "Backup mode, grid charging enabled",
    STATE_CHARGE_SOLAR: "Self-Consumption mode, solar only",
    STATE_DISCHARGE_HOME: "Self-Consumption mode, reserve 0%",
    STATE_DISCHARGE_GRID: "Time-Based mode, export enabled",
    STATE_PRESERVE: "Backup mode, reserve 100%",
}


class PowerwallExecutor:
    """Translates FSM states into Powerwall service calls."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        self._hass = hass
        self._config = config
        # Requested state (always updated — for dashboard display)
        self._last_state: str | None = None
        self._last_limit: float = 0.0
        # Executed state (only updated after successful command — for dedup)
        self._last_executed_state: str | None = None
        self._last_executed_limit: float = 0.0
        self._apply_count: int = 0

    @property
    def last_state(self) -> str | None:
        """Return the last requested state (for dashboard)."""
        return self._last_state

    @property
    def last_executed_state(self) -> str | None:
        """Return the last actually executed state (for diagnostics)."""
        return self._last_executed_state

    @property
    def apply_count(self) -> int:
        """Return how many times a state change was applied."""
        return self._apply_count

    async def apply_state(self, state: str, limit_kw: float) -> None:
        """Apply a new FSM state to the Powerwall.

        Always updates requested state for dashboard display.
        Deduplicates against last EXECUTED state, not last requested state.
        Observation mode suppresses execution without updating executed state.
        """
        # Always update requested state (dashboard can show what FSM wants)
        self._last_state = state
        self._last_limit = limit_kw

        # Observation mode: track request but do not execute
        if self._config.get(CONF_OBSERVATION_MODE, False):
            _LOGGER.info(f"Observation mode — suppressing: {state} (limit: {limit_kw:.1f} kW)")
            return

        # Dedup: only execute if different from last EXECUTED state
        if state == self._last_executed_state and limit_kw == self._last_executed_limit:
            _LOGGER.debug(f"State unchanged ({state}), skipping execute")
            return

        self._apply_count += 1
        _LOGGER.info(f"Applying state: {state} (limit: {limit_kw:.1f} kW)")

        # Execute the actual HA service calls
        await self._async_execute_commands(state, limit_kw)

        # Only update executed state AFTER successful execution
        self._last_executed_state = state
        self._last_executed_limit = limit_kw

    async def _async_execute_commands(self, state: str, limit_kw: float) -> None:
        """Determine and invoke which HA services to call for a given state.

        Executes the 4 configured scripts (Spec 3.6).
        """
        charge_script = self._config.get(CONF_SCRIPT_CHARGE)
        charge_stop_script = self._config.get(CONF_SCRIPT_CHARGE_STOP)
        discharge_script = self._config.get(CONF_SCRIPT_DISCHARGE)
        discharge_stop_script = self._config.get(CONF_SCRIPT_DISCHARGE_STOP)

        async def _call(entity_id: str | None, intent: str):
            if not entity_id:
                _LOGGER.info(f"CMD: {intent} (skipped: no script configured)")
                return
            _LOGGER.info(f"CMD: {intent} ({entity_id})")
            await self._hass.services.async_call("script", "turn_on", {"entity_id": entity_id})

        if state == STATE_CHARGE_GRID:
            await _call(charge_script, "Enable grid charging")
        elif state == STATE_DISCHARGE_HOME:
            await _call(charge_stop_script, "Self-Consumption (stop charge/discharge overrides)")
        elif state == STATE_PRESERVE:
            # Not fully addressed by 4-script logic yet, but logically it implies stopping discharge
            await _call(discharge_stop_script, "Preserve SoC (stop discharge)")
        elif state == STATE_CHARGE_SOLAR:
            await _call(charge_stop_script, "Solar charge only (stop forced charge)")
        elif state == STATE_DISCHARGE_GRID:
            await _call(discharge_script, "Enable export")
        else:
            # IDLE — neutral, ensure we are not forcing charge or discharge
            await _call(charge_stop_script, "Idle (stop forced charge)")
            await _call(discharge_stop_script, "Idle (stop forced discharge)")

    def get_command_summary(self) -> str:
        """Return a human-readable summary of the last command."""
        if self._last_state is None:
            return "No command sent yet"
        desc = _STATE_DESCRIPTIONS.get(self._last_state, "Unknown state")
        return f"{self._last_state}: {desc} (limit: {self._last_limit:.1f} kW)"
