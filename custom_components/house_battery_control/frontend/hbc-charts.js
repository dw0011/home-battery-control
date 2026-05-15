import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

// Tiny helper element: accepts an `svgString` property and sets innerHTML directly.
// This avoids the unsafeHTML directive version-mismatch issue entirely.
if (!customElements.get("hbc-svg-inject")) {
  customElements.define("hbc-svg-inject", class extends HTMLElement {
    set svgString(val) {
      this.innerHTML = val || "";
    }
  });
}

export class HBCCharts extends LitElement {
  static get properties() {
    return {
      data: { type: Object },
    };
  }

  constructor() {
    super();
    this.data = {};
  }

  // ----------------------------------------------------------------
  // SVG Chart Engine
  // ----------------------------------------------------------------

  _buildSvgString({ rows, series, yMin, yMax, unit = "", showStateBg = false, height = 160 }) {
    const W = 800;
    const H = height;
    const PAD_LEFT = 48;
    const PAD_RIGHT = 8;
    const PAD_TOP = 12;
    const PAD_BOT = 30;
    const plotW = W - PAD_LEFT - PAD_RIGHT;
    const plotH = H - PAD_TOP - PAD_BOT;
    const n = rows.length;

    const parseNum = (v) => {
      const f = parseFloat(String(v).replace(/[^0-9.-]+/g, ""));
      return isNaN(f) ? 0 : f;
    };

    let autoMin = Infinity;
    let autoMax = -Infinity;
    rows.forEach(row => {
      series.forEach(s => {
        const v = parseNum(row[s.key]);
        if (v < autoMin) autoMin = v;
        if (v > autoMax) autoMax = v;
      });
    });
    if (autoMin === Infinity) { autoMin = 0; autoMax = 1; }
    if (autoMin === autoMax) { autoMin -= 1; autoMax += 1; }

    const dataMin = yMin !== undefined ? yMin : Math.floor(autoMin - Math.abs(autoMin) * 0.05);
    const dataMax = yMax !== undefined ? yMax : Math.ceil(autoMax + Math.abs(autoMax) * 0.05);
    const range = dataMax - dataMin || 1;

    const xOf = (i) => PAD_LEFT + (i / Math.max(n - 1, 1)) * plotW;
    const yOf = (v) => PAD_TOP + plotH - ((Math.max(dataMin, Math.min(dataMax, v)) - dataMin) / range) * plotH;

    // State background bands
    let bgBands = "";
    if (showStateBg && n > 0) {
      let bandStart = 0;
      let bandState = rows[0]["FSM State"] || rows[0]["State"] || "";
      for (let i = 1; i <= n; i++) {
        const cur = i < n ? (rows[i]["FSM State"] || rows[i]["State"] || "") : "";
        if (cur !== bandState || i === n) {
          const x1 = xOf(bandStart);
          const x2 = i < n ? xOf(i) : W - PAD_RIGHT;
          const bw = x2 - x1;
          let fill = "";
          if (bandState === "CHARGE_GRID")      fill = "rgba(0,255,136,0.08)";
          else if (bandState === "CHARGE_SOLAR") fill = "rgba(255,215,0,0.07)";
          else if (bandState === "DISCHARGE_GRID") fill = "rgba(255,80,80,0.08)";
          if (fill) bgBands += `<rect x="${x1.toFixed(1)}" y="${PAD_TOP}" width="${bw.toFixed(1)}" height="${plotH}" fill="${fill}"/>`;
          bandStart = i;
          bandState = cur;
        }
      }
    }

    // Zero line
    let zeroLine = "";
    if (dataMin < 0 && dataMax > 0) {
      const yz = yOf(0).toFixed(1);
      zeroLine = `<line x1="${PAD_LEFT}" y1="${yz}" x2="${W - PAD_RIGHT}" y2="${yz}" stroke="#444466" stroke-width="1" stroke-dasharray="4,4"/>`;
    }

    // Grid lines + Y labels
    const Y_TICKS = 4;
    let gridLines = "";
    let yLabels = "";
    for (let t = 0; t <= Y_TICKS; t++) {
      const v = dataMin + (range * t) / Y_TICKS;
      const y = yOf(v).toFixed(1);
      gridLines += `<line x1="${PAD_LEFT}" y1="${y}" x2="${W - PAD_RIGHT}" y2="${y}" stroke="#2a2a5e" stroke-width="1"/>`;
      const label = Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1);
      yLabels += `<text x="${PAD_LEFT - 4}" y="${y}" fill="#666688" font-size="10" text-anchor="end" dominant-baseline="middle">${label}</text>`;
    }

    // X labels
    let xLabels = "";
    const xStep = Math.max(1, Math.floor(n / 8));
    for (let i = 0; i < n; i += xStep) {
      const x = xOf(i).toFixed(1);
      const t = rows[i]["Time"] || "";
      const label = t.length >= 5 ? t.slice(0, 5) : t;
      xLabels += `<text x="${x}" y="${H - PAD_BOT + 14}" fill="#666688" font-size="10" text-anchor="middle">${label}</text>`;
    }

    // Series polylines
    let paths = "";
    series.forEach(s => {
      const pts = rows.map((row, i) => {
        const v = parseNum(row[s.key]);
        return `${xOf(i).toFixed(1)},${yOf(v).toFixed(1)}`;
      }).join(" ");
      const dash = s.dash ? `stroke-dasharray="${s.dash}"` : "";
      paths += `<polyline points="${pts}" fill="none" stroke="${s.color}" stroke-width="2" ${dash} stroke-linejoin="round" stroke-linecap="round"/>`;
    });

    // Legend
    let legend = "";
    let lx = PAD_LEFT;
    const ly = H - 6;
    series.forEach(s => {
      const dash = s.dash ? `stroke-dasharray="${s.dash}"` : "";
      legend += `<line x1="${lx}" y1="${ly}" x2="${lx + 16}" y2="${ly}" stroke="${s.color}" stroke-width="2" ${dash}/>`;
      const legendLabel = unit ? `${s.label} (${unit})` : s.label;
      legend += `<text x="${lx + 20}" y="${ly + 4}" fill="#aaaacc" font-size="10">${legendLabel}</text>`;
      lx += 110;
    });

    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block;">`
      + bgBands + gridLines + zeroLine + paths + yLabels + xLabels + legend
      + `</svg>`;
  }

  _svgLineChart(opts) {
    const { rows } = opts;
    if (!rows || rows.length === 0) {
      return html`<div class="chart-empty">No plan data available</div>`;
    }
    const svgStr = this._buildSvgString(opts);
    // Use hbc-svg-inject (plain HTMLElement) to avoid unsafeHTML directive issues
    return html`<div class="chart-wrap"><hbc-svg-inject .svgString=${svgStr}></hbc-svg-inject></div>`;
  }

  _getRows30min() {
    const plan = this.data.plan || [];
    return plan.filter((_, i) => i % 6 === 0);
  }

  render() {
    const plan = this.data.plan || [];
    if (plan.length === 0) {
      return html`
        <div class="card">
          <p class="chart-empty">No plan data available. Waiting for scheduler…</p>
        </div>
      `;
    }

    const rows = this._getRows30min();

    return html`
      <div class="card">
        <h2>Battery State of Charge</h2>
        ${this._svgLineChart({
          rows,
          series: [{ key: "SoC Forecast", color: "#00ff88", label: "SoC" }],
          yMin: 0,
          yMax: 100,
          unit: "%",
          showStateBg: true,
        })}
      </div>

      <div class="card">
        <h2>Price Forecast</h2>
        ${this._svgLineChart({
          rows,
          series: [
            { key: "Import Rate", color: "#ff6b6b", label: "Import" },
            { key: "Export Rate", color: "#00ff88", label: "Export", dash: "6,3" },
          ],
          unit: "c/kWh",
          showStateBg: false,
        })}
      </div>

      <div class="card">
        <h2>Power Forecast</h2>
        ${this._svgLineChart({
          rows,
          series: [
            { key: "PV Forecast",   color: "#ffd700", label: "Solar" },
            { key: "Load Forecast", color: "#00d4ff", label: "Load" },
            { key: "Net Grid",      color: "#ff6b6b", label: "Grid", dash: "4,2" },
          ],
          unit: "kW",
          showStateBg: true,
        })}
      </div>

      <div class="card">
        <h2>Cumulative Cost</h2>
        ${this._svgLineChart({
          rows,
          series: [{ key: "Cumul. Cost", color: "#00d4ff", label: "Cumulative Cost" }],
          unit: "$",
          showStateBg: false,
        })}
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      }
      .card {
        background: #1a1a3e;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        color: #e0e0e0;
      }
      h2 {
        color: #00d4ff;
        margin: 0 0 12px;
        font-size: 18px;
        font-weight: 500;
        user-select: none;
      }
      .chart-wrap {
        width: 100%;
        overflow: hidden;
        border-radius: 6px;
        background: #12122a;
        padding: 4px 0;
      }
      hbc-svg-inject {
        display: block;
        width: 100%;
      }
      .chart-empty {
        text-align: center;
        color: #8888aa;
        padding: 40px 0;
        font-size: 14px;
      }
    `;
  }
}

customElements.define("hbc-charts", HBCCharts);
