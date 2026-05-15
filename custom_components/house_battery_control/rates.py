import logging
from datetime import datetime, timedelta
from typing import List, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


class RateInterval(TypedDict):
    start: datetime
    end: datetime
    import_price: float  # c/kWh
    export_price: float  # c/kWh
    type: str  # ACTUAL or FORECAST


class RatesManager:
    """Manages fetching and processing tariff rates from Amber Electric or Flow Power."""

    def __init__(
        self,
        hass: HomeAssistant,
        import_entity_id: str,
        export_entity_id: str,
        use_amber_express: bool = False,
        use_flow_power: bool = False,
    ):
        self._hass = hass
        self._import_entity_id = import_entity_id
        self._export_entity_id = export_entity_id
        self._use_amber_express = use_amber_express
        self._use_flow_power = use_flow_power
        self._rates: List[RateInterval] = []

    def update(self) -> None:
        """Fetch latest rates from both import and export sensors."""
        if self._use_flow_power:
            import_rates = self._parse_flow_power_entity(self._import_entity_id, "import")
            export_rates = self._parse_flow_power_entity(self._export_entity_id, "export")
        elif self._use_amber_express:
            import_rates = self._parse_amber_express_entity(self._import_entity_id, "import")
            export_rates = self._parse_amber_express_entity(self._export_entity_id, "export")
        else:
            import_rates = self._parse_entity(self._import_entity_id, "import")
            export_rates = self._parse_entity(self._export_entity_id, "export")

        # Merge by matching start times, floored to 5-minute boundaries.
        # Import and export sensors call utcnow() independently so their "current"
        # entries can have sub-second different timestamps (e.g. 11:43:15.1 vs
        # 11:43:15.4). Without flooring these would produce two separate entries
        # at the same display time — one with import_price=0.0 — causing the LP
        # to treat that slot as free electricity and decide to charge.
        merged: dict[datetime, RateInterval] = {}
        for r in import_rates:
            key = self._floor_to_5min(r["start"])
            existing_export = merged[key]["export_price"] if key in merged else 0.0
            merged[key] = {
                "start": key,
                "end": key + timedelta(minutes=5),
                "import_price": r["price"],
                "export_price": existing_export,
                "type": r["type"],
            }
        for r in export_rates:
            key = self._floor_to_5min(r["start"])
            if key in merged:
                merged[key]["export_price"] = r["price"]
            else:
                merged[key] = {
                    "start": key,
                    "end": key + timedelta(minutes=5),
                    "import_price": 0.0,
                    "export_price": r["price"],
                    "type": r["type"],
                }

        self._rates = sorted(merged.values(), key=lambda x: x["start"])
        _LOGGER.debug(f"Loaded {len(self._rates)} rate intervals")

    def _parse_entity(self, entity_id: str, label: str) -> list:
        """Parse rate intervals from an Amber sensor entity."""
        state = self._hass.states.get(entity_id)
        if not state:
            _LOGGER.warning(f"{label} price entity {entity_id} not found")
            return []

        raw_data = (
            state.attributes.get("forecast")
            or state.attributes.get("forecasts")
            or state.attributes.get("future_prices")
            or state.attributes.get("variable_intervals")
        )

        if not raw_data:
            _LOGGER.warning(f"No forecast data in {entity_id}")
            return []

        parsed = []
        for interval in raw_data:
            try:
                start_ts = dt_util.parse_datetime(
                    interval.get("start_time") or interval.get("periodStart", "")
                )
                end_ts = dt_util.parse_datetime(
                    interval.get("end_time") or interval.get("periodEnd", "")
                )

                if not start_ts or not end_ts:
                    continue

                # Ensure timezone-aware (spec 4: TZ safety)
                start_ts = dt_util.as_utc(start_ts)
                end_ts = dt_util.as_utc(end_ts)

                price = float(interval.get("per_kwh") or interval.get("perKwh", 0))

                # Phase 8: Force chunking all intervals into 5-minute ticks
                chunk_duration = timedelta(minutes=5)
                current_ts = start_ts

                while current_ts < end_ts:
                    next_ts = current_ts + chunk_duration
                    if next_ts > end_ts:
                        next_ts = end_ts

                    parsed.append(
                        {
                            "start": current_ts,
                            "end": next_ts,
                            "price": price,
                            "type": interval.get("type") or interval.get("periodType", "UNKNOWN"),
                        }
                    )
                    current_ts = next_ts

            except (ValueError, KeyError) as e:
                _LOGGER.error(f"Error parsing {label} rate interval: {e}")
                continue

        parsed.sort(key=lambda x: x["start"])
        return parsed

    def _parse_amber_express_entity(self, entity_id: str, label: str) -> list:
        """Parse rate intervals specifically from an Amber Express sensor's 'forecasts' array."""
        state = self._hass.states.get(entity_id)
        if not state:
            _LOGGER.warning(f"Amber Express {label} price entity {entity_id} not found")
            return []

        # Amber Express explicitly embeds its 24h timeline inside the 'forecasts' attribute array
        raw_data = state.attributes.get("forecasts", [])

        if not raw_data:
            _LOGGER.warning(f"No forecasts array in Amber Express entity {entity_id}")
            return []

        parsed = []
        for interval in raw_data:
            try:
                start_ts = dt_util.parse_datetime(interval.get("start_time", ""))
                end_ts = dt_util.parse_datetime(interval.get("end_time", ""))

                if not start_ts or not end_ts:
                    continue

                # Ensure timezone-aware (spec 4: TZ safety)
                start_ts = dt_util.as_utc(start_ts)
                end_ts = dt_util.as_utc(end_ts)

                renewables = float(interval.get("renewables", 100.0))
                advanced = interval.get("advanced_price_predicted", {})

                predicted_price = float(advanced.get("predicted", interval.get("per_kwh", 0.0)))
                high_price = float(advanced.get("high", predicted_price))

                if renewables >= 35.0:
                    price = predicted_price
                elif renewables <= 25.0:
                    price = high_price
                else:
                    # Linear interpolation between 35% and 25% (a 10% band)
                    ratio_predicted = (renewables - 25.0) / 10.0
                    ratio_high = 1.0 - ratio_predicted
                    price = (ratio_predicted * predicted_price) + (ratio_high * high_price)

                # Phase 8: Force chunking all intervals into 5-minute ticks
                chunk_duration = timedelta(minutes=5)
                current_ts = start_ts

                while current_ts < end_ts:
                    next_ts = current_ts + chunk_duration
                    if next_ts > end_ts:
                        next_ts = end_ts

                    parsed.append(
                        {
                            "start": current_ts,
                            "end": next_ts,
                            "price": price,
                            "type": "FORECAST", # Amber Express is purely forecast arrays
                        }
                    )
                    current_ts = next_ts

            except (ValueError, KeyError, TypeError) as e:
                _LOGGER.error(f"Error parsing Amber Express {label} rate interval: {e}")
                continue

        parsed.sort(key=lambda x: x["start"])
        return parsed

    def _parse_flow_power_entity(self, entity_id: str, label: str) -> list:
        """Parse rate intervals from a Flow Power HA sensor.

        Flow Power sensors expose:
        - state: current live price in $/kWh
        - forecast_dict attribute: dict of "YYYY-MM-DD HH:MM:SS+HHMM" -> $/kWh
          in 30-minute steps (happy-hour export rates already baked in)

        Prices are converted from $/kWh to c/kWh (* 100).
        Each 30-min interval is chunked into 5-min sub-intervals.
        A synthetic "now -> first forecast" interval is prepended using the live price.
        """
        state = self._hass.states.get(entity_id)
        if not state:
            _LOGGER.warning(f"Flow Power {label} price entity {entity_id} not found")
            return []

        if state.state in ("unavailable", "unknown"):
            _LOGGER.warning(f"Flow Power {label} entity {entity_id} is {state.state}")
            return []

        # Current live price from sensor state ($/kWh -> c/kWh)
        try:
            current_price_cents = float(state.state) * 100.0
        except (ValueError, TypeError):
            current_price_cents = 0.0

        forecast_dict = state.attributes.get("forecast_dict", {})
        if not forecast_dict:
            _LOGGER.warning(f"No forecast_dict in Flow Power {label} entity {entity_id}")
            return []

        # Parse each timestamp -> price pair
        intervals: list[tuple[datetime, float]] = []
        for ts_str, price_dollars in forecast_dict.items():
            try:
                ts = dt_util.parse_datetime(str(ts_str))
                if ts:
                    ts = dt_util.as_utc(ts)
                    intervals.append((ts, float(price_dollars) * 100.0))
            except (ValueError, TypeError) as e:
                _LOGGER.debug(f"Could not parse Flow Power timestamp '{ts_str}': {e}")
                continue

        intervals.sort(key=lambda x: x[0])

        if not intervals:
            _LOGGER.warning(f"Flow Power {label} entity {entity_id} has no parseable forecast entries")
            return []

        # Build the working interval list:
        # Always prepend a "now -> next 30-min boundary" interval using the live sensor price.
        # This handles both cases:
        #   a) now < first_ts  (update arrived early — gap before first forecast slot)
        #   b) now >= first_ts (normal case — current slot has already started)
        # In both cases the current slot price is the live 5-min dispatch price, which is
        # more accurate than the 30-min TWAP forecast stored in forecast_dict.
        # Flow Power sensor state is in $/kWh; current_price_cents is already × 100.
        now = dt_util.utcnow()
        future_intervals = [(ts, price) for ts, price in intervals if ts > now]
        if future_intervals:
            intervals = [(now, current_price_cents)] + future_intervals
        else:
            # All forecast slots are in the past; just use live price for the next 30 min
            intervals = [(now, current_price_cents)]

        # Build 5-minute sub-intervals from each 30-min forecast slot
        chunk_duration = timedelta(minutes=5)
        parsed = []

        for i, (start_ts, price) in enumerate(intervals):
            end_ts = intervals[i + 1][0] if i + 1 < len(intervals) else start_ts + timedelta(minutes=30)

            current_ts = start_ts
            while current_ts < end_ts:
                next_ts = min(current_ts + chunk_duration, end_ts)
                parsed.append(
                    {
                        "start": current_ts,
                        "end": next_ts,
                        "price": round(price, 4),
                        "type": "FORECAST",
                    }
                )
                current_ts = next_ts

        parsed.sort(key=lambda x: x["start"])
        _LOGGER.debug(f"Flow Power {label}: parsed {len(parsed)} 5-min intervals from {len(intervals)} forecast slots")
        return parsed

    @staticmethod
    def _floor_to_5min(dt: datetime) -> datetime:
        """Floor a datetime to the nearest 5-minute boundary.

        Ensures import and export 'current price' entries (generated by separate
        utcnow() calls) always land on the same merge key even if they differ
        by a few milliseconds or seconds.
        """
        floored_minute = (dt.minute // 5) * 5
        return dt.replace(minute=floored_minute, second=0, microsecond=0)

    def get_rates(self) -> List[RateInterval]:
        """Return the processed list of rates."""
        return self._rates

    def get_import_price_at(self, time: datetime) -> float:
        """Get the import price for a specific time."""
        for rate in self._rates:
            if rate["start"] <= time < rate["end"]:
                return rate["import_price"]
        return 0.0

    def get_export_price_at(self, time: datetime) -> float:
        """Get the export price for a specific time."""
        for rate in self._rates:
            if rate["start"] <= time < rate["end"]:
                return rate["export_price"]
        return 0.0
