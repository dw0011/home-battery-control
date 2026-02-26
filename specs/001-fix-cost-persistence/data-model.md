# Data Model: Cost Persistence

## Entities

### PersistentStoreData
A JSON schema defining the structure of the data saved to HA's `.storage/house_battery_control.cost_data` namespace.

**Fields**:
- `cumulative_cost` (Float): The running total of accumulated cost in dollars.
- `acquisition_cost` (Float): The running weighted average cost of energy stored in the battery, in c/kWh.

**Validation Rules**:
- Handled via simple type forecasting float. Graceful fallback on `None` or missing dict keys.

## Storage Specifications
- **Version**: 1
- **Key**: `house_battery_control.cost_data`
- **Location**: Home Assistant explicit `Store` class (`homeassistant.helpers.storage`).
