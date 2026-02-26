# Technical Research: Cost Persistence

## Decision
Use Home Assistant's built-in `homeassistant.helpers.storage.Store` feature to save and load state cleanly across restarts for `cumulative_cost` and `acquisition_cost`.

## Rationale
- The HA `Store` API is designed specifically to persist internal integration state asynchronously to disk (in `.storage/`) without blocking the event loop or abusing entity attributes.
- It handles delayed writes automatically (`async_delay_save()`), meaning we can update the running state in memory every 5-minute tick and it will incrementally flush to disk without thrashing I/O.
- On initialization (`__init__` or `_async_setup`), the coordinator can `await store.async_load()` to flawlessly resume from the last known state, eliminating the issue of the metrics resetting to 0.00 / 0.10.

## Alternatives Considered
- **Entity Attributes / HA Recorder**: Relying on HA's SQL recorder requires history spanning back forever and parsing state history on boot, which is slow, unreliable if the DB purges, and doesn't explicitly guarantee state recovery if the sensor is unavailable.
- **Custom JSON File**: Creating our own I/O file operations is an anti-pattern in HA and risks blocking the event loop or causing race conditions. The native `Store` perfectly solves this natively.
