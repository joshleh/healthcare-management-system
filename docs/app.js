const summary = {
  patients: 1000,
  appointments: 1000,
  totalBilling: 510275708,
};

const csvPaths = {
  daily: "./data/query_2_daily_appointment_count.csv",
  doctors: "./data/query_3_most_active_doctors.csv",
  billing: "./data/query_4_total_billing_per_patient.csv",
  procedures: "./data/query_5_most_common_medical_procedures.csv",
};

const state = {};

init();

async function init() {
  setSummary();

  try {
    const [daily, doctors, billing, procedures] = await Promise.all([
      loadCsv(csvPaths.daily),
      loadCsv(csvPaths.doctors),
      loadCsv(csvPaths.billing),
      loadCsv(csvPaths.procedures),
    ]);

    state.daily = daily.map((row) => ({
      date: row.Date,
      total: Number(row.TotalAppointments),
    }));
    state.doctors = doctors.map((row) => ({
      name: row.DoctorName,
      specialty: row.Specialization,
      total: Number(row.TotalAppointments),
    }));
    state.billing = billing.map((row) => ({
      name: row.PatientName,
      total: Number(row.TotalBilled),
    }));
    state.procedures = procedures.map((row) => ({
      name: row.ProcedureName,
      total: Number(row.TimesPerformed),
    }));

    hydrateHighlights();
    renderLineChart("#appointments-chart", state.daily);
    renderBars("#doctors-chart", state.doctors, {
      valueKey: "total",
      labelKey: "name",
      accent: false,
    });
    renderBillingTable("#billing-table", state.billing.slice(0, 6));
    renderBars("#procedures-chart", state.procedures.slice(0, 6), {
      valueKey: "total",
      labelKey: "name",
      accent: true,
    });
  } catch (error) {
    console.error("Unable to load dashboard data", error);
    renderLoadError();
  }
}

function setSummary() {
  setText("#metric-patients", formatNumber(summary.patients));
  setText("#metric-appointments", formatNumber(summary.appointments));
  setText("#metric-billing", formatCurrencyShort(summary.totalBilling));
}

function hydrateHighlights() {
  const topDoctor = state.doctors[0];
  const topProcedure = state.procedures[0];
  const busiestDay = state.daily.reduce((best, current) => {
    return current.total > best.total ? current : best;
  }, state.daily[0]);

  setText("#top-doctor", topDoctor.name);
  setText("#top-doctor-detail", `${topDoctor.specialty} • ${topDoctor.total} appointments`);
  setText("#top-procedure", topProcedure.name);
  setText("#top-procedure-detail", `${topProcedure.total} occurrences in the reporting export`);
  setText("#busiest-day", formatDate(busiestDay.date));
  setText("#busiest-day-detail", `${busiestDay.total} appointments in the busiest operating window`);
}

async function loadCsv(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Request failed for ${path} with status ${response.status}`);
  }
  const text = await response.text();
  return parseCsv(text);
}

function parseCsv(text) {
  const rows = [];
  const lines = text.trim().split(/\r?\n/);
  const headers = splitCsvLine(lines[0]);

  for (let i = 1; i < lines.length; i += 1) {
    const values = splitCsvLine(lines[i]);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });
    rows.push(row);
  }

  return rows;
}

function splitCsvLine(line) {
  const values = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    const nextChar = line[i + 1];

    if (char === '"' && inQuotes && nextChar === '"') {
      current += '"';
      i += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === "," && !inQuotes) {
      values.push(current);
      current = "";
      continue;
    }

    current += char;
  }

  values.push(current);
  return values;
}

function renderLineChart(selector, data) {
  const host = document.querySelector(selector);
  const width = 780;
  const height = 320;
  const padding = { top: 20, right: 16, bottom: 38, left: 16 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const maxValue = Math.max(...data.map((entry) => entry.total));
  const step = innerWidth / (data.length - 1);

  const points = data.map((entry, index) => {
    const x = padding.left + step * index;
    const y = padding.top + innerHeight - (entry.total / maxValue) * innerHeight;
    return `${x},${y}`;
  });

  const linePath = points.length ? `M ${points.join(" L ")}` : "";
  const areaPath = `${linePath} L ${padding.left + innerWidth},${padding.top + innerHeight} L ${padding.left},${padding.top + innerHeight} Z`;

  const tickIndexes = [0, Math.floor(data.length / 3), Math.floor((data.length * 2) / 3), data.length - 1];

  host.innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Daily appointment volume chart">
      <line class="axis-line" x1="${padding.left}" y1="${padding.top + innerHeight}" x2="${padding.left + innerWidth}" y2="${padding.top + innerHeight}"></line>
      <line class="grid-line" x1="${padding.left}" y1="${padding.top}" x2="${padding.left + innerWidth}" y2="${padding.top}"></line>
      <path class="area-path" d="${areaPath}"></path>
      <path class="line-path" d="${linePath}"></path>
      ${tickIndexes
        .map((index) => {
          const x = padding.left + step * index;
          return `<text class="tick-label" x="${x}" y="${height - 10}" text-anchor="middle">${shortDate(
            data[index].date
          )}</text>`;
        })
        .join("")}
      ${data
        .filter((entry) => entry.total === maxValue)
        .map((entry) => {
          const index = data.indexOf(entry);
          const x = padding.left + step * index;
          const y = padding.top + innerHeight - (entry.total / maxValue) * innerHeight;
          return `
            <circle class="dot" cx="${x}" cy="${y}" r="5"></circle>
            <text class="value-label" x="${x + 8}" y="${y - 8}">${entry.total} peak</text>
          `;
        })
        .join("")}
    </svg>
  `;
}

function renderBars(selector, data, options) {
  const host = document.querySelector(selector);
  const width = 420;
  const barHeight = 30;
  const gap = 14;
  const leftPad = 10;
  const topPad = 6;
  const labelWidth = 148;
  const maxValue = Math.max(...data.map((entry) => entry[options.valueKey]));
  const height = topPad * 2 + data.length * (barHeight + gap);

  const rows = data
    .map((entry, index) => {
      const y = topPad + index * (barHeight + gap);
      const barWidth = ((width - labelWidth - 50) * entry[options.valueKey]) / maxValue;
      const barClass = options.accent ? "bar soft" : "bar";
      return `
        <text class="chart-label" x="${leftPad}" y="${y + 19}">${truncate(entry[options.labelKey], 24)}</text>
        <rect class="${barClass}" x="${labelWidth}" y="${y}" width="${barWidth}" height="${barHeight}" rx="12"></rect>
        <text class="value-label" x="${labelWidth + barWidth + 8}" y="${y + 19}">${entry[options.valueKey]}</text>
      `;
    })
    .join("");

  host.innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Bar chart">
      ${rows}
    </svg>
  `;
}

function renderBillingTable(selector, rows) {
  const host = document.querySelector(selector);
  host.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Patient</th>
          <th>Total Billed</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr>
                <td>${row.name}</td>
                <td>${formatCurrency(row.total)}</td>
              </tr>
            `
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function shortDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function formatDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatCurrencyShort(value) {
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  }

  return `$${(value / 1_000_000).toFixed(1)}M`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function truncate(value, maxLength) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

function setText(selector, value) {
  const element = document.querySelector(selector);
  if (element) {
    element.textContent = value;
  }
}

function renderLoadError() {
  [
    "#appointments-chart",
    "#doctors-chart",
    "#billing-table",
    "#procedures-chart",
  ].forEach((selector) => {
    const element = document.querySelector(selector);
    if (element) {
      element.innerHTML = '<p class="muted">Data could not be loaded. Run the site through a local server or static host.</p>';
    }
  });

  setText("#top-doctor", "Data unavailable");
  setText("#top-doctor-detail", "The static data exports could not be loaded in this browsing context.");
  setText("#top-procedure", "Data unavailable");
  setText("#top-procedure-detail", "Try reopening the showcase from its hosted site.");
  setText("#busiest-day", "Data unavailable");
  setText("#busiest-day-detail", "Some browsers restrict local file access for data-driven sections.");
}
