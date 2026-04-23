import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

// Module-level recovery: after extended idle, HA may destroy the panel element
// without recreating it. Detect tab focus and reload if panel is missing.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible") return;
  if (!location.pathname.startsWith("/hbc-panel")) return;
  // Minimal delay for event loop to settle, then reload if panel is missing
  setTimeout(() => {
    if (!document.querySelector("hbc-panel")) {
      location.reload();
    }
  }, 100);
});

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
      _overrideLoading: { type: Boolean },
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
    this._overrideLoading = false;
    this._fallbackInterval = null;
    this._lastFetch = 0;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
    // 60s fallback timer for edge cases where entity state doesn't change (FR-004)
    this._fallbackInterval = setInterval(() => this._fetchData(), 60000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._fallbackInterval) clearInterval(this._fallbackInterval);
  }

  // Push-driven: react to HA hass changes instead of polling (FR-001, fixes #12)
  updated(changedProps) {
    super.updated(changedProps);
    if (!changedProps.has("hass")) return;
    const oldHass = changedProps.get("hass");
    if (!oldHass) {
      // First hass assignment — fetch immediately
      this._fetchData();
      return;
    }
    const oldState = oldHass.states["sensor.hbc_state"];
    const newState = this.hass.states["sensor.hbc_state"];
    if (!oldState || !newState) return;
    if (oldState.state !== newState.state || oldState.last_updated !== newState.last_updated) {
      this._debouncedFetch();
    }
  }

  // 10s debounce to avoid redundant fetches (FR-003)
  _debouncedFetch() {
    const now = Date.now();
    if (this._lastFetch && (now - this._lastFetch) < 10000) return;
    this._lastFetch = now;
    this._fetchData();
  }

  async _fetchData() {
    try {
      if (!this.hass) {
        this._error = "Home Assistant connection not available";
        this._loading = false;
        return;
      }
      // Use HA's fetchWithAuth which auto-refreshes expired tokens (fixes #7)
      let resp = await this.hass.fetchWithAuth("/hbc/api/status");
      if (resp.status === 401) {
        // Tab may have been idle — HA reconnects WebSocket on focus.
        // Rapid retry: 500ms apart, up to 5 attempts (fixes #11)
        for (let i = 0; i < 5; i++) {
          await new Promise(r => setTimeout(r, 500));
          if (!this.hass) break;
          resp = await this.hass.fetchWithAuth("/hbc/api/status");
          if (resp.status !== 401) break;
        }
        if (resp.status === 401) {
          this._error = "Insufficient permissions — admin access required";
          this._loading = false;
          return;
        }
      }
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      this._data = await resp.json();
      this._error = "";
    } catch (e) {
      this._error = e.message || String(e);
    }
    this._loading = false;
  }

  _switchTab(tab) {
    this._activeTab = tab;
  }

  _switchResolution(res) {
    this._planResolution = res;
  }

  // Feature 022: cache observability
  _renderCacheStatus() {
    if (!this._data) return "";
    const cacheDate = this._data.load_cache_date;
    const refreshedAt = this._data.load_cache_refreshed_at;
    const histStart = this._data.load_history_start;
    const histEnd = this._data.load_history_end;
    const ttlMin = this._data.load_cache_ttl_minutes;
    if (!cacheDate || !refreshedAt) return "Load history: fetching\u2026";
    const t = new Date(refreshedAt);
    const timeStr = t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const startDate = histStart ? new Date(histStart).toLocaleDateString() : "?";
    const endDate = histEnd ? new Date(histEnd).toLocaleDateString() : "?";
    const expiry = new Date(t.getTime() + (ttlMin || 360) * 60000);
    const expiryStr = expiry.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return `Load cache: ${startDate} \u2192 ${endDate} (refreshed ${timeStr}, expires ${expiryStr})`;
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

  _toggleMenu() {
    this.dispatchEvent(new Event("hass-toggle-menu", {
      bubbles: true,
      composed: true,
    }));
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

  // ── SVG Line Chart Helper ──────────────────────────────
  // Builds SVG as a string then uses .innerHTML binding to avoid LitElement 2.x
  // SVG namespace issues (nested html`` templates render in HTML namespace).
  _svgLineChart({ rows, series, yMin, yMax, unit = "", showStateBg = false }) {
    const W = 800, H = 210;
    const ml = 52, mr = 20, mt = 16, mb = 44;
    const cW = W - ml - mr;
    const cH = H - mt - mb;
    const n = rows.length;
    if (n < 2) return html`<p style="color:#8888aa;font-size:0.85em;">No chart data available.</p>`;

    const parseNum = (str) => {
      if (typeof str === "number") return str;
      const f = parseFloat(String(str).replace(/[^0-9.-]+/g, ""));
      return isNaN(f) ? 0 : f;
    };

    if (yMin === undefined || yMax === undefined) {
      const allVals = series.flatMap(s => rows.map(r => parseNum(r[s.key])));
      const mn = Math.min(...allVals);
      const mx = Math.max(...allVals);
      const pad = Math.max((mx - mn) * 0.1, 1);
      if (yMin === undefined) yMin = mn - pad;
      if (yMax === undefined) yMax = mx + pad;
    }
    if (yMax <= yMin) yMax = yMin + 1;

    const xScale = (i) => ml + (i / Math.max(n - 1, 1)) * cW;
    const yScale = (v) => mt + cH * (1 - Math.max(0, Math.min(1, (v - yMin) / (yMax - yMin))));

    const p = [];
    p.push(`<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block;" xmlns="http://www.w3.org/2000/svg">`);

    // State background shading
    if (showStateBg) {
      const stateColors = { "CHARGE_GRID": "rgba(0,255,136,0.12)", "DISCHARGE_GRID": "rgba(255,107,107,0.12)" };
      let segStart = 0, segState = (rows[0] && rows[0]["FSM State"]) || "";
      for (let i = 1; i <= n; i++) {
        const st = i < n ? (rows[i]["FSM State"] || "") : "";
        if (st !== segState || i === n) {
          const col = stateColors[segState];
          if (col) {
            const x1 = xScale(segStart), x2 = xScale(Math.min(i, n - 1));
            p.push(`<rect x="${x1.toFixed(1)}" y="${mt}" width="${Math.max(0, x2 - x1).toFixed(1)}" height="${cH}" fill="${col}"/>`);
          }
          segStart = i; segState = st;
        }
      }
    }

    // Y grid lines + tick labels
    for (let i = 0; i <= 4; i++) {
      const v = yMin + (yMax - yMin) * i / 4;
      const y = yScale(v);
      p.push(`<line x1="${ml}" y1="${y.toFixed(1)}" x2="${W - mr}" y2="${y.toFixed(1)}" stroke="rgba(255,255,255,0.07)" stroke-width="1"/>`);
      p.push(`<text x="${(ml - 5).toFixed(1)}" y="${(y + 3.5).toFixed(1)}" fill="#8888aa" font-size="10" text-anchor="end">${v.toFixed(1)}</text>`);
    }

    // Zero line (when range spans zero)
    if (yMin < 0 && yMax > 0) {
      const y0 = yScale(0);
      p.push(`<line x1="${ml}" y1="${y0.toFixed(1)}" x2="${W - mr}" y2="${y0.toFixed(1)}" stroke="rgba(255,255,255,0.25)" stroke-width="1" stroke-dasharray="4 3"/>`);
    }

    // Axes
    p.push(`<line x1="${ml}" y1="${mt}" x2="${ml}" y2="${mt + cH}" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>`);
    p.push(`<line x1="${ml}" y1="${mt + cH}" x2="${W - mr}" y2="${mt + cH}" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>`);

    // X time labels
    const step = Math.max(1, Math.floor(n / 6));
    for (let i = 0; i < n; i += step) {
      const t = rows[i]["Local Time"] || rows[i]["Time"] || "";
      const m = t.match(/(\d{1,2}:\d{2})/);
      if (m) {
        const x = xScale(i);
        p.push(`<line x1="${x.toFixed(1)}" y1="${(mt + cH).toFixed(1)}" x2="${x.toFixed(1)}" y2="${(mt + cH + 5).toFixed(1)}" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>`);
        p.push(`<text x="${x.toFixed(1)}" y="${(mt + cH + 16).toFixed(1)}" fill="#8888aa" font-size="10" text-anchor="middle">${m[1]}</text>`);
      }
    }

    // Unit label
    if (unit) p.push(`<text x="${(ml - 5).toFixed(1)}" y="${(mt - 4).toFixed(1)}" fill="#8888aa" font-size="9" text-anchor="end">${unit}</text>`);

    // Data polylines
    series.forEach(s => {
      const pts = rows.map((r, i) => `${xScale(i).toFixed(1)},${yScale(parseNum(r[s.key])).toFixed(1)}`).join(" ");
      p.push(`<polyline points="${pts}" fill="none" stroke="${s.color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`);
    });

    // Legend
    series.forEach((s, i) => {
      const lx = ml + i * 140;
      p.push(`<rect x="${lx.toFixed(1)}" y="${(H - 14).toFixed(1)}" width="14" height="3" fill="${s.color}" rx="1.5"/>`);
      p.push(`<text x="${(lx + 18).toFixed(1)}" y="${(H - 5).toFixed(1)}" fill="#cccccc" font-size="10">${s.label}</text>`);
    });

    p.push(`</svg>`);
    return html`<div class="chart-wrap" .innerHTML=${p.join("")}></div>`;
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

  // ── Manual Override ────────────────────────────────────
  async _setOverride(mode) {
    this._overrideLoading = true;
    try {
      const resp = await this.hass.fetchWithAuth("/hbc/api/override", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      await this._fetchData();
    } catch (e) {
      console.error("HBC override failed:", e);
    }
    this._overrideLoading = false;
  }

  _renderOverrideCard() {
    const overrideMode = this._data.manual_override || "auto";
    const isOverride = overrideMode !== "auto";
    const loading = this._overrideLoading;

    const modes = [
      { id: "charge",       label: "Grid Charge",   icon: "⚡", color: "#00ff88" },
      { id: "discharge",    label: "Force Export",  icon: "📤", color: "#ff6b6b" },
      { id: "self_powered", label: "Self-Powered",  icon: "🏠", color: "#6688ff" },
      { id: "auto",         label: "Resume Auto",   icon: "🤖", color: "#00d4ff" },
    ];

    return html`
      <div class="card${isOverride ? " override-active" : ""}">
        <h2>
          Manual Override
          ${isOverride ? html`<span class="override-badge">ACTIVE</span>` : ""}
        </h2>
        <p class="override-note">
          ${isOverride
            ? html`HBC auto-control is <strong>paused</strong>. Active mode: <strong>${overrideMode.replace("_", " ").toUpperCase()}</strong>`
            : "HBC is managing the battery automatically."}
        </p>
        <div class="override-buttons">
          ${modes.map(m => html`
            <button
              class="override-btn${overrideMode === m.id ? " active" : ""}"
              style="--btn-color:${m.color};"
              ?disabled=${loading}
              @click=${() => this._setOverride(m.id)}
            >
              <span class="override-btn-icon">${m.icon}</span>
              <span>${m.label}</span>
            </button>
          `)}
        </div>
      </div>
    `;
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
    const plan = d.plan || [];
    const export_price = plan.length > 0 ? parseFloat(plan[0]["Export Rate"] || 0) : 0;
    const import_today = d.import_today !== undefined ? d.import_today : 0;
    const export_today = d.export_today !== undefined ? d.export_today : 0;
    const state = d.state || "IDLE";
    const reason = d.reason || "";
    const noImportPeriods = d.no_import_periods || "";
    const observationMode = d.observation_mode || false;
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
            <div class="flow-icon">⚡</div>
            <div class="flow-value">${battery}</div>
            <div class="flow-label">Battery kW</div>
          </div>
          <div class="flow-item house">
            <div class="flow-icon">🏠</div>
            <div class="flow-value">${load}</div>
            <div class="flow-label">House kW</div>
          </div>
          <div class="flow-item soc-item">
            <div class="flow-icon">🔋</div>
            <div class="flow-value">${soc}%</div>
            <div class="flow-label">SoC</div>
          </div>
        </div>
      </div>
      ${this._renderOverrideCard()}
      <div class="card">
        <div class="status-grid">
          <div class="stat">
            <div class="stat-value">${price}</div>
            <div class="stat-label">Import c/kWh</div>
          </div>
          <div class="stat">
            <div class="stat-value">${export_price}</div>
            <div class="stat-label">Export c/kWh</div>
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
      ${(noImportPeriods || observationMode) ? html`
      <div class="constraints-bar">
        ${observationMode ? html`<span class="constraint-badge observation">👁 Observation Mode</span>` : ''}
        ${noImportPeriods ? html`<span class="constraint-badge no-import">🚫 No-Import: ${noImportPeriods}</span>` : ''}
      </div>
      ` : ''}
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
          <div class="stat">
            <div class="stat-value">${(d.acquisition_cost || 0).toFixed(2)}</div>
            <div class="stat-label">Acq Cost c/kWh</div>
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
      "Temp Δ",
      "Load Adj.",
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
          tempDelta: r["Temp Delta"] || "—",
          loadAdj: r["Load Adj."] || "0.00",
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

          const tempDeltaNum = (chunk.reduce((s, row) => s + parseNum(row["Temp Delta"]), 0) / chunk.length).toFixed(1);
          const tempDelta = chunk[0]["Temp Delta"] === "—" ? "—" : `${tempDeltaNum}°C`;
          const loadAdj = (chunk.reduce((s, row) => s + parseNum(row["Load Adj."]), 0) / chunk.length).toFixed(2);

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
            tempDelta,
            loadAdj,
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
      "Temp Δ": "",
      "Load Adj.": "",
      "SoC": "",
      "Cost": "",
      "Cumul. Cost": "",
      "Acq. Cost": "",
    };

    return html`
      <div class="card table-card">
        <div class="header" style="margin-bottom: 12px;">
          <h2 style="margin-bottom: 0;">24-Hour Plan <span style="font-size: 0.55em; font-weight: normal; opacity: 0.5; margin-left: 12px;">Updated: ${this._formatLastUpdate()}</span></h2>
          <div style="font-size: 0.75em; opacity: 0.5; margin-top: 2px;">${this._renderCacheStatus()}</div>
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
        "Temp Δ": r.tempDelta,
        "Load Adj.": r.loadAdj,
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

  // ── Charts Tab ────────────────────────────────────────
  _renderCharts() {
    const plan = this._data.plan || [];
    if (plan.length === 0) {
      return html`<div class="card"><p>No plan data available yet.</p></div>`;
    }
    // Downsample to 30-min resolution (every 6th 5-min row = 48 points)
    const rows = plan.filter((_, i) => i % 6 === 0);

    return html`
      <div class="card">
        <h2>Battery SoC Forecast</h2>
        <p class="chart-note">Green = charging from grid &nbsp;|&nbsp; Red = discharging to grid</p>
        ${this._svgLineChart({
          rows,
          series: [{ key: "SoC Forecast", color: "#00ff88", label: "State of Charge %" }],
          yMin: 0, yMax: 100,
          unit: "%",
          showStateBg: true,
        })}
      </div>
      <div class="card">
        <h2>Price Forecast</h2>
        ${this._svgLineChart({
          rows,
          series: [
            { key: "Import Rate", color: "#ff6b6b", label: "Import c/kWh" },
            { key: "Export Rate", color: "#ffd700", label: "Export c/kWh" },
          ],
          unit: "c/kWh",
        })}
      </div>
      <div class="card">
        <h2>Power Forecast</h2>
        ${this._svgLineChart({
          rows,
          series: [
            { key: "PV Forecast", color: "#ffd700", label: "Solar kW" },
            { key: "Load Forecast", color: "#ff8c00", label: "Load kW" },
            { key: "Net Grid", color: "#6688ff", label: "Grid kW (+ import)" },
          ],
          unit: "kW",
        })}
      </div>
      <div class="card">
        <h2>Projected Cumulative Cost</h2>
        ${this._svgLineChart({
          rows,
          series: [
            { key: "Cumul. Cost", color: "#00d4ff", label: "Cumulative Cost $" },
          ],
          unit: "$",
        })}
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
      <div class="toolbar">
        <button class="menu-btn" @click=${this._toggleMenu} aria-label="Menu">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
            <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
          </svg>
        </button>
        <span class="toolbar-title">House Battery Control</span>
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
          <button
            class="${this._activeTab === "charts" ? "active" : ""}"
            @click=${() => this._switchTab("charts")}
          >
            Charts
          </button>
        </div>
      </div>
      <div class="root">
        ${this._activeTab === "dashboard"
        ? this._renderDashboard()
        : this._activeTab === "charts"
          ? this._renderCharts()
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
      .toolbar {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 16px;
        background: #1a1a3e;
        border-bottom: 1px solid #2a2a5e;
        position: sticky;
        top: 0;
        z-index: 10;
      }
      .menu-btn {
        background: none;
        border: none;
        color: #e0e0e0;
        cursor: pointer;
        padding: 8px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s;
      }
      .menu-btn:hover {
        background: rgba(255, 255, 255, 0.1);
      }
      .toolbar-title {
        color: #00d4ff;
        font-size: 18px;
        font-weight: 600;
        flex: 1;
      }
      .root {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
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

      /* Active Constraints Bar */
      .constraints-bar {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        padding: 8px 0;
      }
      .constraint-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 16px;
        font-size: 13px;
        font-weight: 600;
      }
      .constraint-badge.no-import {
        background: linear-gradient(135deg, #ff8c00, #cc6600);
        color: #fff;
      }
      .constraint-badge.observation {
        background: linear-gradient(135deg, #ff4444, #cc0000);
        color: #fff;
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
      .chart-note {
        margin: -8px 0 10px;
        font-size: 11px;
        color: #666688;
      }

      /* Manual Override Card */
      .override-active {
        border: 1px solid #ff8c00;
      }
      .override-badge {
        display: inline-block;
        background: #ff8c00;
        color: #0f0f23;
        font-size: 0.55em;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 10px;
        margin-left: 8px;
        vertical-align: middle;
        letter-spacing: 0.05em;
      }
      .override-note {
        font-size: 0.85em;
        color: #8888aa;
        margin: -8px 0 14px;
      }
      .override-buttons {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 10px;
      }
      .override-btn {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.12);
        color: #aaaacc;
        border-radius: 8px;
        padding: 14px 8px;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        font-family: inherit;
        transition: all 0.15s;
      }
      .override-btn:hover:not(:disabled) {
        border-color: var(--btn-color);
        color: var(--btn-color);
        background: rgba(255,255,255,0.08);
      }
      .override-btn.active {
        border-color: var(--btn-color);
        color: var(--btn-color);
        background: rgba(255,255,255,0.08);
        font-weight: 600;
        box-shadow: 0 0 0 1px var(--btn-color);
      }
      .override-btn:disabled {
        opacity: 0.45;
        cursor: wait;
      }
      .override-btn-icon {
        font-size: 22px;
      }
    `;
  }
}

customElements.define("hbc-panel", HBCPanel);
