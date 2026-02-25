import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

class HBCPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      panel: { type: Object },
      _activeTab: { type: String },
      _planResolution: { type: String },
      _hiddenCols: { type: Array },
      _sensorsHidden: { type: Boolean },
      _data: { type: Object },
      _error: { type: String },
      _loading: { type: Boolean },
    };
  }

  constructor() {
    super();
    this._activeTab = "dashboard";
    this._planResolution = "30min";
    this._hiddenCols = JSON.parse(localStorage.getItem("hbc_hidden_cols") || "[]");
    this._sensorsHidden = localStorage.getItem("hbc_sensors_hidden") === "true";
    this._data = {};
    this._error = "";
    this._loading = true;
    this._interval = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
    this._interval = setInterval(() => this._fetchData(), 30000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._interval) clearInterval(this._interval);
  }

  async _fetchData() {
    try {
      const token = this.hass && this.hass.auth && this.hass.auth.data
        ? this.hass.auth.data.access_token
        : null;
      const headers = token ? { "Authorization": `Bearer ${token}` } : {};
      const resp = await fetch("/hbc/api/status", { headers });
      if (resp.status === 401) {
        this._error = "Insufficient permissions — admin access required";
        this._loading = false;
        return;
      }
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      this._data = await resp.json();
      this._error = "";
    } catch (e) {
      this._error = e.message;
    }
    this._loading = false;
  }

  _switchTab(tab) {
    this._activeTab = tab;
  }

  _switchResolution(res) {
    this._planResolution = res;
  }

  _toggleCol(col) {
    let hidden = [...this._hiddenCols];
    if (hidden.includes(col)) {
      hidden = hidden.filter(c => c !== col);
    } else {
      hidden.push(col);
    }
    this._hiddenCols = hidden;
    localStorage.setItem("hbc_hidden_cols", JSON.stringify(hidden));
  }

  _toggleSensors() {
    this._sensorsHidden = !this._sensorsHidden;
    localStorage.setItem("hbc_sensors_hidden", this._sensorsHidden);
  }

  _calculateSummaryStats() {
    const plan = this._data.plan || [];
    if (plan.length === 0) {
      return { avgImport: "0.00", avgExport: "0.00", totalPV: "0.0", totalLoad: "0.0" };
    }

    const parseNum = (str) => parseFloat(String(str).replace(/[^0-9.-]+/g, "")) || 0;

    let sumImport = 0;
    let sumExport = 0;
    let sumPVKw = 0;
    let sumLoadKw = 0;

    plan.forEach(r => {
      sumImport += parseNum(r["Import Rate"]);
      sumExport += parseNum(r["Export Rate"]);
      sumPVKw += parseNum(r["PV Forecast"]);
      sumLoadKw += parseNum(r["Load Forecast"]);
    });

    const count = plan.length;
    return {
      avgImport: (sumImport / count).toFixed(2),
      avgExport: (sumExport / count).toFixed(2),
      // kW to kWh over 5-minute intervals (divide by 12)
      totalPV: (sumPVKw / 12).toFixed(1),
      totalLoad: (sumLoadKw / 12).toFixed(1)
    };
  }

  _formatLastUpdate() {
    const raw = this._data.last_update;
    if (!raw) return "—";
    try {
      const d = new Date(raw);
      if (isNaN(d.getTime())) return raw;
      return d.toLocaleString([], { dateStyle: "short", timeStyle: "medium" });
    } catch (e) {
      return raw;
    }
  }

  // ── Dashboard Tab ──────────────────────────────────────
  _renderDashboard() {
    const d = this._data;
    const soc = d.soc !== undefined ? d.soc : 0;
    const solar = d.solar_power !== undefined ? d.solar_power : 0;
    const grid = d.grid_power !== undefined ? d.grid_power : 0;
    const load = d.load_power !== undefined ? d.load_power : 0;
    const battery = d.battery_power !== undefined ? d.battery_power : 0;
    const price = d.current_price !== undefined ? d.current_price : 0;
    const import_today = d.import_today !== undefined ? d.import_today : 0;
    const export_today = d.export_today !== undefined ? d.export_today : 0;
    const state = d.state || "IDLE";
    const reason = d.reason || "";
    const summaryStats = this._calculateSummaryStats();

    return html`
      <div class="card">
        <h2>Power Flow</h2>
        <div class="flow-grid">
          <div class="flow-item solar">
            <div class="flow-icon">☀️</div>
            <div class="flow-value">${solar}</div>
            <div class="flow-label">Solar kW</div>
          </div>
          <div class="flow-item grid-item">
            <div class="flow-icon">🔌</div>
            <div class="flow-value">${grid}</div>
            <div class="flow-label">Grid kW</div>
          </div>
          <div class="flow-item battery-item">
            <div class="flow-icon">🔋</div>
            <div class="flow-value">${battery}</div>
            <div class="flow-label">Battery kW</div>
          </div>
          <div class="flow-item house">
            <div class="flow-icon">🏠</div>
            <div class="flow-value">${load}</div>
            <div class="flow-label">House kW</div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="status-grid">
          <div class="stat">
            <div class="stat-value">${soc}%</div>
            <div class="stat-label">SoC</div>
          </div>
          <div class="stat">
            <div class="stat-value">${price}</div>
            <div class="stat-label">Price c/kWh</div>
          </div>
          <div class="stat">
            <div class="stat-value">${import_today}</div>
            <div class="stat-label">Import kWh</div>
          </div>
          <div class="stat">
            <div class="stat-value">${export_today}</div>
            <div class="stat-label">Export kWh</div>
          </div>
          <div class="stat">
            <div class="state-badge">${state}</div>
            <div class="stat-label">${reason}</div>
          </div>
        </div>
      </div>
      <div class="card">
        <h2>24-Hour Forecast Summary</h2>
        <div class="status-grid">
          <div class="stat">
            <div class="stat-value">${summaryStats.avgImport}</div>
            <div class="stat-label">Avg Import c/kWh</div>
          </div>
          <div class="stat">
            <div class="stat-value">${summaryStats.avgExport}</div>
            <div class="stat-label">Avg Export c/kWh</div>
          </div>
          <div class="stat">
            <div class="stat-value">${summaryStats.totalPV}</div>
            <div class="stat-label">Total Gen kWh</div>
          </div>
          <div class="stat">
            <div class="stat-value">${summaryStats.totalLoad}</div>
            <div class="stat-label">Total Load kWh</div>
          </div>
        </div>
      </div>
      <div class="meta" style="text-align: center; padding: 8px 0; opacity: 0.6; font-size: 0.85em;">
        Plan last ran: ${this._formatLastUpdate()}
      </div>
      ${this._renderSensors()}
    `;
  }

  // ── Sensor Diagnostics (Spec 2.4) ─────────────────────
  _renderSensors() {
    const sensors = this._data.sensors || [];
    if (sensors.length === 0) return html``;

    return html`
      <div class="card">
        <h2 
          @click=${this._toggleSensors} 
          style="cursor: pointer; display: flex; justify-content: space-between; align-items: center;"
        >
          Sensor Status
          <span style="font-size: 0.8em; transform: rotate(${this._sensorsHidden ? '-90deg' : '0deg'}); transition: transform 0.2s;">▼</span>
        </h2>
        
        ${this._sensorsHidden ? html`` : html`
        <table>
          <thead><tr><th>Entity</th><th>State</th><th>Status</th></tr></thead>
          <tbody>
            ${sensors.map(
      (s) => html`
                <tr>
                  <td>${s.entity_id}</td>
                  <td>${s.state}</td>
                  <td>
                    <span class="badge ${s.available ? "ok" : "err"}">
                      ${s.available ? "✓" : "✗"}
                    </span>
                  </td>
                </tr>
              `
    )}
          </tbody>
        </table>
        `}
        <div class="meta">
          Last update: ${this._data.last_update || "—"} |
          Update #${this._data.update_count || 0}
        </div>
      </div>
    `;
  }

  // ── Plan Tab ───────────────────────────────────────────
  _renderPlan() {
    const plan = this._data.plan || [];

    if (plan.length === 0) {
      return html`<div class="card"><p>No plan data available yet.</p></div>`;
    }

    const cols = [
      "Time",
      "Local Time",
      "Import",
      "Export",
      "State",
      "Limit",
      "Net Grid",
      "PV",
      "Load",
      "Temp",
      "SoC",
      "Cost",
      "Cumul. Cost",
      "Acq. Cost",
    ];

    const parseNum = (str) => parseFloat(String(str).replace(/[^0-9.-]+/g, "")) || 0;

    const formatCostStr = (valStr) => {
      if (valStr === undefined || valStr === null) return "$0.00.0";
      const num = typeof valStr === "number" ? valStr : parseNum(valStr);
      if (isNaN(num)) return "$0.00.0";
      if (num === 0) return "$0.00.0";
      const abs = Math.abs(num);
      const sign = num < 0 ? "-$" : "$";
      let str;
      if (abs < 10) {
        const base = abs.toFixed(3); // e.g., "1.234"
        str = base.slice(0, 4) + "." + base.slice(4); // "1.23" + "." + "4" => "1.23.4"
      }
      else if (abs < 100) str = abs.toFixed(2);
      else if (abs < 1000) str = abs.toFixed(1);
      else str = abs.toFixed(0);
      return sign + str;
    };

    let rows = [];

    if (this._planResolution === "5min") {
      rows = plan.map((r) => {
        return {
          time: r["Time"] || "—",
          localTime: r["Local Time"] || "—",
          imp: r["Import Rate"] || "0.0",
          exp: r["Export Rate"] || "0.0",
          state: r["FSM State"] || "—",
          limit: r["Inverter Limit"] || "0%",
          grid: r["Net Grid"] || "0.00",
          pv: r["PV Forecast"] || "0.00",
          ld: r["Load Forecast"] || "0.00",
          temp: r["Air Temp Forecast"] || "—",
          soc: r["SoC Forecast"] || "—",
          cost: formatCostStr(r["Interval Cost"]),
          cumul: formatCostStr(r["Cumul. Cost"]),
          acq: formatCostStr(r["Acq. Cost"]),
        };
      });
    } else {
      let currentChunk = [];
      for (let i = 0; i < plan.length; i++) {
        const r = plan[i];
        currentChunk.push(r);

        const timeStr = r["Time"] || "";
        const isBoundary = timeStr.endsWith(":25") || timeStr.endsWith(":55");
        const isLast = i === plan.length - 1;

        if (isBoundary || isLast) {
          const chunk = currentChunk;
          currentChunk = [];
          if (chunk.length === 0) continue;

          const time = chunk[0]["Time"] || "—";
          const localTime = chunk[0]["Local Time"] || "—";

          const imp = (chunk.reduce((s, row) => s + parseNum(row["Import Rate"]), 0) / chunk.length).toFixed(2);
          const exp = (chunk.reduce((s, row) => s + parseNum(row["Export Rate"]), 0) / chunk.length).toFixed(2);

          let state = "SELF_CONSUMPTION";
          let limit = "0%";
          const chargeReq = chunk.find(row => row["FSM State"] === "CHARGE_GRID");
          const dischargeReq = chunk.find(row => row["FSM State"] === "DISCHARGE_GRID");

          if (chargeReq) {
            state = "CHARGE_GRID";
            limit = chargeReq["Inverter Limit"] || "100%";
          } else if (dischargeReq) {
            state = "DISCHARGE_GRID";
            limit = dischargeReq["Inverter Limit"] || "100%";
          }

          const grid = (chunk.reduce((s, row) => s + parseNum(row["Net Grid"]), 0) / chunk.length).toFixed(2);
          const pv = (chunk.reduce((s, row) => s + parseNum(row["PV Forecast"]), 0) / chunk.length).toFixed(2);
          const ld = (chunk.reduce((s, row) => s + parseNum(row["Load Forecast"]), 0) / chunk.length).toFixed(2);
          const tempNum = (chunk.reduce((s, row) => s + parseNum(row["Air Temp Forecast"]), 0) / chunk.length).toFixed(1);
          const temp = chunk[0]["Air Temp Forecast"] === "—" ? "—" : `${tempNum}°C`;

          const lastRow = chunk[chunk.length - 1];
          const soc = lastRow["SoC Forecast"] || "—";

          const costRaw = chunk.reduce((s, row) => s + parseNum(row["Interval Cost"]), 0);
          const cost = formatCostStr(costRaw);

          const cumul = formatCostStr(lastRow["Cumul. Cost"]);
          const acq = formatCostStr(chunk.reduce((s, row) => s + parseNum(row["Acq. Cost"]), 0) / chunk.length);

          rows.push({
            time,
            localTime,
            imp,
            exp,
            state,
            limit,
            grid,
            pv,
            ld,
            temp,
            soc,
            cost,
            cumul,
            acq,
          });
        }
      }
    }

    const summaryStats = this._calculateSummaryStats();
    const footerKeys = {
      "Time": "24h Summary:",
      "Local Time": "",
      "Import": summaryStats.avgImport,
      "Export": summaryStats.avgExport,
      "State": "",
      "Limit": "",
      "Net Grid": "",
      "PV": summaryStats.totalPV + " kwh",
      "Load": summaryStats.totalLoad + " kwh",
      "Temp": "",
      "SoC": "",
      "Cost": "",
      "Cumul. Cost": "",
      "Acq. Cost": "",
    };

    return html`
      <div class="card table-card">
        <div class="header" style="margin-bottom: 12px;">
          <h2 style="margin-bottom: 0;">24-Hour Plan</h2>
          <div class="tabs">
            <button
              class="${this._planResolution === "5min" ? "active" : ""}"
              @click=${() => this._switchResolution("5min")}
            >
              5 Min
            </button>
            <button
              class="${this._planResolution === "30min" ? "active" : ""}"
              @click=${() => this._switchResolution("30min")}
            >
              30 Min
            </button>
          </div>
          <div class="meta" style="font-size: 0.8em; opacity: 0.6; margin-left: 12px; align-self: center;">
            Updated: ${this._formatLastUpdate()}
          </div>
        </div>
        
        <div class="column-toggles" style="display: flex; flex-wrap: wrap; gap: 6px; padding: 0 16px 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 12px;">
          ${cols.map(c => html`
            <button
              class="${this._hiddenCols.includes(c) ? '' : 'active'}"
              style="background: ${this._hiddenCols.includes(c) ? 'transparent' : 'var(--primary-color)'}; color: ${this._hiddenCols.includes(c) ? 'inherit' : 'var(--text-primary-color, white)'}; border: 1px solid ${this._hiddenCols.includes(c) ? 'var(--divider-color, rgba(150,150,150,0.4))' : 'var(--primary-color)'}; border-radius: 4px; padding: 4px 8px; font-size: 0.8em; cursor: pointer; opacity: ${this._hiddenCols.includes(c) ? '0.5' : '1'}; transition: 0.2s ease;"
              @click=${() => this._toggleCol(c)}
            >
              ${c}
            </button>
          `)}
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                ${cols.filter(c => !this._hiddenCols.includes(c)).map((c) => html`<th>${c}</th>`)}
              </tr>
            </thead>
            <tbody>
              ${rows.map((r) => {
      const colKeys = {
        "Time": r.time,
        "Local Time": r.localTime,
        "Import": r.imp,
        "Export": r.exp,
        "State": r.state,
        "Limit": r.limit,
        "Net Grid": r.grid,
        "PV": r.pv,
        "Load": r.ld,
        "Temp": r.temp,
        "SoC": r.soc,
        "Cost": r.cost,
        "Cumul. Cost": r.cumul,
        "Acq. Cost": r.acq,
      };

      return html`
                  <tr class="${r.state === 'SELF_CONSUMPTION' ? 'state-self' : r.state === 'CHARGE_GRID' ? 'state-charge' : r.state === 'DISCHARGE_GRID' ? 'state-discharge' : ''}">
                    ${cols.filter(c => !this._hiddenCols.includes(c)).map(c => html`<td>${colKeys[c]}</td>`)}
                  </tr>
                `;
    })}
            </tbody>
            <tfoot>
              <tr style="font-weight: bold; background: rgba(255,255,255,0.05);">
                ${cols.filter(c => !this._hiddenCols.includes(c)).map(c => html`<td>${footerKeys[c] || ""}</td>`)}
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    `;
  }

  render() {
    if (this._loading) {
      return html`<div class="root"><p>Loading...</p></div>`;
    }
    if (this._error) {
      return html`<div class="root"><div class="card err-card">Error: ${this._error}</div></div>`;
    }

    return html`
      <div class="root">
        <div class="header">
          <h1>⚡ House Battery Control</h1>
          <div class="tabs">
            <button
              class="${this._activeTab === "dashboard" ? "active" : ""}"
              @click=${() => this._switchTab("dashboard")}
            >
              Dashboard
            </button>
            <button
              class="${this._activeTab === "plan" ? "active" : ""}"
              @click=${() => this._switchTab("plan")}
            >
              Plan
            </button>
          </div>
        </div>
        ${this._activeTab === "dashboard"
        ? this._renderDashboard()
        : this._renderPlan()}
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
        background: #0f0f23;
        color: #e0e0e0;
        min-height: 100vh;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          sans-serif;
      }
      .root {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
        flex-wrap: wrap;
        gap: 12px;
      }
      h1 {
        color: #00d4ff;
        margin: 0;
        font-size: 24px;
      }
      h2 {
        color: #00d4ff;
        margin: 0 0 16px;
        font-size: 18px;
      }
      .tabs {
        display: flex;
        gap: 4px;
        background: #1a1a3e;
        border-radius: 8px;
        padding: 4px;
      }
      .tabs button {
        background: transparent;
        color: #8888aa;
        border: none;
        padding: 8px 20px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
      }
      .tabs button.active {
        background: #00d4ff;
        color: #0f0f23;
        font-weight: 600;
      }
      .tabs button:hover:not(.active) {
        color: #e0e0e0;
      }
      .card {
        background: #1a1a3e;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
      }
      .err-card {
        background: #3e1a1a;
        color: #ff6b6b;
      }

      /* Power Flow Grid */
      .flow-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
      }
      .flow-item {
        background: #12122a;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        border: 1px solid #2a2a5e;
        transition: transform 0.2s;
      }
      .flow-item:hover {
        transform: translateY(-2px);
      }
      .flow-icon {
        font-size: 28px;
        margin-bottom: 8px;
      }
      .flow-value {
        font-size: 28px;
        font-weight: 700;
        color: #00d4ff;
      }
      .flow-label {
        font-size: 12px;
        color: #8888aa;
        margin-top: 4px;
      }
      .solar .flow-value {
        color: #ffd700;
      }
      .battery-item .flow-value {
        color: #00ff88;
      }

      /* Status Grid */
      .status-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 12px;
      }
      .stat {
        text-align: center;
      }
      .stat-value {
        font-size: 24px;
        font-weight: 700;
        color: #00d4ff;
      }
      .stat-label {
        font-size: 12px;
        color: #8888aa;
        margin-top: 4px;
      }
      .state-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        background: linear-gradient(135deg, #00d4ff, #0088cc);
        color: #0f0f23;
        font-weight: 700;
        font-size: 14px;
      }

      /* Tables */
      .table-card {
        overflow: hidden;
      }
      .table-wrap {
        overflow-x: auto;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
      }
      th {
        background: #12122a;
        color: #00d4ff;
        padding: 10px 8px;
        text-align: left;
        white-space: nowrap;
        position: sticky;
        top: 0;
      }
      td {
        padding: 8px;
        border-bottom: 1px solid #2a2a5e;
      }
      tr:nth-child(even) {
        background: #15153a;
      }
      tr.state-self {
        background-color: rgba(0, 212, 255, 0.15) !important;
      }
      tr.state-charge {
        background-color: rgba(0, 255, 136, 0.15) !important;
      }
      tr.state-discharge {
        background-color: rgba(255, 107, 107, 0.15) !important;
      }
      .badge {
        display: inline-block;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        text-align: center;
        line-height: 20px;
        font-size: 12px;
      }
      .badge.ok {
        background: #00ff88;
        color: #0f0f23;
      }
      .badge.err {
        background: #ff6b6b;
        color: #0f0f23;
      }
      .meta {
        margin-top: 12px;
        font-size: 11px;
        color: #666688;
      }
    `;
  }
}

customElements.define("hbc-panel", HBCPanel);
