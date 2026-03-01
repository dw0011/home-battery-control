import logging
from datetime import datetime, timedelta
from typing import Any, List

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class LoadPredictor:
    """Predicts house load based on history and (optionally) weather."""

    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self.last_history_raw: list[list[dict]] = []
        self.last_history: list[dict] = []

    async def async_predict(
        self,
        start_time: datetime,
        temp_forecast: List[Any] | None = None,
        high_sensitivity: float = 0.0,
        low_sensitivity: float = 0.0,
        high_threshold: float = 25.0,
        low_threshold: float = 15.0,
        duration_hours: int = 24,
        load_entity_id: str | None = None,
        weather_entity_id: str | None = None,
    ) -> List[dict]:
        """
        Predict load for the next N hours in 5-minute intervals.
        Derives kW from kWh deltas with a safety cap.
        Fetches history via the internal HA API and formats it exactly like the REST endpoint.
        """
        intervals = int(duration_hours * 60 / 5)
        prediction = []
        current = start_time

        # Robustly detect if this is an energy sensor (kWh) or power sensor (kW)
        if not load_entity_id:
            return []

        # Get history for the specified duration
        state = self._hass.states.get(load_entity_id)
        is_energy_sensor = False
        if state:
            unit = state.attributes.get("unit_of_measurement", "").lower()
            if "wh" in unit:  # kWh, Wh, mWh
                is_energy_sensor = True

        historic_states_raw = []
        if not getattr(self, "testing_bypass_history", False):
            self.last_history_raw = []

        # Fetch history via internal API exactly 5 days up to start_time
        if load_entity_id and not getattr(self, "testing_bypass_history", False):
            from homeassistant.components.recorder import history

            end_date = start_time
            start_date = end_date - timedelta(days=5)

            try:
                states_dict = await self._hass.async_add_executor_job(
                    history.get_significant_states,
                    self._hass,
                    start_date,
                    end_date,
                    [load_entity_id],
                )
                historic_states_raw = states_dict.get(load_entity_id, [])

                # Format to exact REST API match
                formatted_states = []
                for s in historic_states_raw:
                    formatted_states.append(
                        {
                            "entity_id": s.entity_id,  # type: ignore
                            "state": s.state,  # type: ignore
                            # Preserve exact isoformat with original timezone (like +00:00)
                            # We use .replace(microsecond=0) because standard HA REST API
                            # usually trims microseconds in this endpoint.
                            "last_changed": s.last_changed.replace(microsecond=0).isoformat(),  # type: ignore
                            "last_updated": s.last_updated.replace(microsecond=0).isoformat(),  # type: ignore
                            "attributes": dict(s.attributes),  # type: ignore
                        }
                    )

                # REST API returns a list of lists (one per entity)
                if formatted_states:
                    self.last_history_raw = [formatted_states]

            except Exception as e:
                _LOGGER.error(f"Error fetching load history via internal API: {e}")

        # The prediction loop requires the internal list
        historic_states_parsed = self.last_history_raw[0] if self.last_history_raw else []

        # Build statistical 24hr forecast if data exists using the native user module
        from .historical_analyzer import (
            build_historical_profile,
            extract_temp_data,
            extract_valid_data,
        )

        valid_data = extract_valid_data(historic_states_parsed)

        # Fetch temperature history from weather entity (T003)
        temp_data = None
        if weather_entity_id and not getattr(self, "testing_bypass_history", False):
            try:
                from homeassistant.components.recorder import history as rec_history

                end_date = start_time
                start_date = end_date - timedelta(days=5)

                temp_states_dict = await self._hass.async_add_executor_job(
                    rec_history.get_significant_states,
                    self._hass,
                    start_date,
                    end_date,
                    [weather_entity_id],
                )
                temp_states_raw = temp_states_dict.get(weather_entity_id, [])

                formatted_temp_states = []
                for s in temp_states_raw:
                    formatted_temp_states.append(
                        {
                            "state": s.state,  # type: ignore
                            "last_changed": s.last_changed.replace(microsecond=0).isoformat(),  # type: ignore
                            "attributes": dict(s.attributes),  # type: ignore
                        }
                    )

                if formatted_temp_states:
                    temp_data = extract_temp_data(formatted_temp_states)

            except Exception as e:
                _LOGGER.warning(f"Could not fetch temperature history: {e}")

        # Build Profile with optional temperature data
        target_tz = start_time.tzinfo if start_time.tzinfo else None
        historical_profile = build_historical_profile(
            valid_data, target_tz, is_energy_sensor, temp_data=temp_data
        )

        # Naive lookup for temperature at a given time
        def get_temp_at(target_time: datetime) -> float:
            if not temp_forecast:
                return 20.0  # Standard mild temp
            # Find closest interval in forecast
            closest = temp_forecast[0]
            if "datetime" in closest:
                min_diff = abs((target_time - closest["datetime"]).total_seconds())
            else:
                min_diff = float("inf")
            for item in temp_forecast:
                if "datetime" in item:
                    diff = abs((target_time - item["datetime"]).total_seconds())
                    if diff < min_diff:
                        min_diff = diff
                        closest = item
            return closest.get("temperature", 20.0)

        # Track previous legitimate usage for midnight anomaly bridging
        # (Fallback loop preserved for missing slots)

        for _ in range(intervals):
            time_slot = current.strftime("%H:%M")
            derived_kw = None

            if time_slot in historical_profile:
                slot_data = historical_profile[time_slot]
                if is_energy_sensor:
                    derived_kw = slot_data["load_kw"] * 12.0
                else:
                    derived_kw = slot_data["load_kw"]

            if derived_kw is None:
                # Fallback Dummy Profile
                hour = current.hour
                derived_kw = 0.5
                if 17 <= hour <= 21:  # Evening Peak
                    derived_kw = 2.5
                elif 7 <= hour <= 9:  # Morning Peak
                    derived_kw = 1.5

            # Temperature adjustment — delta-based when history available (FR-003/004/005)
            temp = get_temp_at(current)
            slot_hist_temp = None
            if time_slot in historical_profile:
                slot_hist_temp = historical_profile[time_slot].get("avg_temp")

            # FR-010/011: track diagnostic values for plan output
            temp_delta = None
            load_adjustment = 0.0

            if slot_hist_temp is not None:
                # Delta-based: compare forecast to historical avg for this slot
                # FR-004: forecast > high_threshold → adjust by delta × sensitivity
                # FR-005: forecast < low_threshold → adjust by -delta × sensitivity
                # FR-009: negative adjustments allowed (floor at 0.0 kW applied later)
                temp_delta = round(temp - slot_hist_temp, 2)
                if temp > high_threshold:
                    load_adjustment = round(temp_delta * high_sensitivity, 2)
                    derived_kw += load_adjustment
                elif temp < low_threshold:
                    load_adjustment = round((-temp_delta) * low_sensitivity, 2)
                    derived_kw += load_adjustment
            else:
                # Fallback: original absolute threshold (FR-008)
                if temp > high_threshold:
                    load_adjustment = round((temp - high_threshold) * high_sensitivity, 2)
                    derived_kw += load_adjustment
                elif temp < low_threshold:
                    load_adjustment = round((low_threshold - temp) * low_sensitivity, 2)
                    derived_kw += load_adjustment

            # Round off to 2 decimals (preserve 0.0 floor)
            kw_final = round(max(0.0, derived_kw), 2)

            prediction.append({
                "start": current.isoformat(),
                "kw": kw_final,
                "temp_delta": temp_delta,
                "load_adjustment_kw": load_adjustment,
            })
            current += timedelta(minutes=5)

        return prediction
